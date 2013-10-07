"""
Al - for Alan Turing

If someone says the bot's name in the channel followed by a ':',
e.g.

    <sam> al: hello!

the al will reply:

    <logbot> sam: I am AL

Run this script with four arguments:
e.g.
    <server/ip>:    'irc.freenode.net'
    <port>:         6667
    <channel>:      main
    <logfile>:      log/channel.log

    $ python AL.py irc.freenode.net 6667 main log/channel.log
"""


# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time, sys
from scrapers.cafescraper import scrapeCafe
from apis.weatherman import currentWeather


class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file


    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        self.file.write('%s %s\n' % (timestamp, message))
        self.file.flush()


    def close(self):
        self.file.close()



class LogBot(irc.IRCClient):
    """A logging IRC bot."""
   
    # the nickname might have problems with uniquness when connecting to freenode.net 
    nickname = "AL"
    __stored_messages = {} # used for user messages with the tell command
    

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.join(self.factory.channel)


    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.logger.close()


    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)


    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)


    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))
        parts = msg.split()
        
        # Check to see if they're sending me a private message
        if channel == self.nickname:
            msg = "It isn't nice to whisper!  Play nice with the group."
            self.msg(user, msg)
            return

        if parts[0] == self.nickname + ':':
            if parts[1] == 'cafe':
                try:
                    menu = scrapeCafe()
                    # make the menu all nice for chat purposes
                    menu_msg = 'Steam \'n Turren: {0}.\nField of Greens: {1}.\nFlavor & Fire: {2}.\nThe Grillery: {3}.\nMain Event: {4}'.format(
                        menu['soup'], menu['greens'], menu['flavor'], menu['grill'], menu['main'])
                    self.msg(channel, menu_msg)
                except Exception as e:
                    print e.message
                    self.msg(channel, 'Sorry, I do not understand')
                    pass

            if parts[1] == 'weather':
                try:
                    # get the weather and tell the channel
                    weather = currentWeather()
                    w_msg = '{0},  {1} degrees'.format(weather['status'], weather['temp'])
                    self.msg(channel, w_msg)
                except Exception as e:
                    print e.message
                    self.msg(channel, 'Sorry I do not understand')
                    pass

            if parts[1] == 'tell':
                try:
                    # form the message
                    target_user = parts[2]
                    tell_msg = '{0}, {1} said: {2}'.format(target_user, user, ' '.join(parts[3:]))
                    if target_user not in self.__stored_messages:
                        self.__stored_messages[target_user] = []
                    self.__stored_messages[target_user].append(tell_msg)
                    self.msg(channel, 'I will pass that along when {0} joins'.format(target_user))
                except Exception as e:
                    print e.message
                    self.msg(channel, 'Give me a message to tell someone!: `AL: tell <user> <message>`')


    def userJoined(self, user, channel):
        """This will get called when I see a user join a channel"""
        if user in self.__stored_messages:
            for k, v in self.__stored_messages.items():
                for message in v:
                    self.msg(channel, message)


    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))


    # irc callbacks
    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'



class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel, filename):
        self.channel = channel
        self.filename = filename

    def buildProtocol(self, addr):
        p = LogBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)
    
    # create factory protocol and application
    f = LogBotFactory(sys.argv[3], sys.argv[4])

    # connect factory to this host and port
    reactor.connectTCP(sys.argv[1], int(sys.argv[2]), f)

    # run bot
    reactor.run()
