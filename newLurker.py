import sys, socket, string, time, re, os, emailSender, sqlite3, time, loadSettings, urllib2, random

def loadSettings(settingfiles = ["settings.txt"]):
	settings = {}

	for filename in settingfiles:
		inFile = open(filename)
		lines = inFile.readlines()
		for i in range(len(lines)):
			index = lines[i].find(":")
			lines[i] = lines[i][:len(lines[i])-1]
			if index == -1:
				print "Error, no : on line " + str(i+1)
			if index + 1 == len(lines[i]):
				value = ""
			else:
				value = lines[i][index+1:]
			settings[lines[i][:index]] = value

	return settings

class CoreBot(object):
	default_server_handles = {}
	default_user_handles = {}

	@classmethod
	def get_default_user_handles(cls):
		out_dict = {}
		out_dict.update(cls.default_user_handles)
		return out_dict

	@classmethod
	def get_default_server_handles(cls):
		out_dict = {}
		out_dict.update(cls.default_server_handles)
		return out_dict

	def __init__(self):
		#Loads the settings, should load any arbitrary settings that get set in the file
		self.settings = loadSettings()

		#Initializes the networking variables, the socket, the read buffer...
		self.sock = socket.socket()
		self.readBuffer = ""
		self.lines = []

		self.server_handles = self.__class__.get_default_server_handles()
		self.user_handles = self.__class__.get_default_user_handles()

	def connectToServer(self):
		#Connects to the irc and sets the lurker's information
		self.sock.connect((self.settings['host'], int(self.settings['port'])))
		#We want a non-blocking socket
		self.sock.setblocking(0)
		self.sock.send('NICK %s\r\n' % self.settings['nick'])
		self.sock.send('USER %s %s bla :%s\r\n' % (self.settings['nick'], self.settings['host'], self.settings['nick']))

		#Should add error handling code here to gracefully load a second nick if the first one is taken.

		cont = True
		#Loops waiting for the server to give the all clear.
		while cont:
			#Read in from the socket
			self.readSock()
			while self.lines:
				#goes through each line to see if the MOTD is finished
				line = self.retrieveLine()
				if re.match('(?:.*?\.)*.*? \d* %s :End of /MOTD command.' % self.settings['nick'], line):
					cont = False

		self.mainLoop()

	def readSock(self):
		#This method looks at the socket and adds anything that it finds to the read buffer
		#and then adds all the complete lines into the self.lines list
		
		#Recieves from the socket
		try:
			#Takes in the input from the server, if the server doesn't respond you get the exception
			reception = self.sock.recv(1024)
		except:
			#This means that nothing was recieved
			reception = ""
		
		#Handles the reception if there was one
		if reception:
			#Adds the text just gotten to the read buffer, then takes all the completed lines from the
			#read buffer and stores them in self.lines
			#The one exception being PING input, which is automatically PONG'd
			self.readBuffer += reception
			temp = string.split(self.readBuffer, "\n")
			self.readBuffer = temp.pop()
			for line in temp:
				if line[0:4] == "PING":
					self.sock.send("PONG %s\r\n" % line[5:])
				else:
					self.lines.append(line)

	def retrieveLine(self):
		#This method is used to read in a line from the buffer. It handles recording each line that is
		#received for debugging purposes. By default it does this by printing, but this could be replaced
		#with writing to a log file or something.
		line = self.lines.pop(0)
		print line
		return line
		
	def message(self, recipient, message):
		self.sock.send("PRIVMSG %s %s\r\n" % (recipient, message))

	def mainLoop(self):
		#Time to join the channels and start the real functionality
		for channel in self.settings['channels'].split(','):
			self.sock.send('JOIN %s\r\n' % channel)

		cont = True
		#Does a mainloop to chomp through all the incoming messages
		while cont:
			self.readSock()
			while self.lines:
				line = self.retrieveLine()
				#Incoming messages are broken up into two categories, server messages and user messages
				#Server messages come from the IRC server and have information about the client's state.
				#User messages are messages sent to the client, or to a channel the client is subscribed to.
				
				#Matches the line with the server message pattern. MESSAGENO is the tracking number for the
				#message, EXTRAS are some additional information that seems to be different depending on the
				#type of message, so I've just got it all bundled. Message is the actual message payload
				servmat = re.match(':(?:.*?\.)*.*? (?P<MESSAGENO>\d*) %s (?P<EXTRAS>.*?) :(?P<MESSAGE>.*)' % self.settings['nick'], line)
				if servmat:
					self.handleServer(servmat.groups())

				usermat = re.match(':(?P<USERNAME>.*?)!(?P<REALNAME>.*?)@(?P<WEBLOC>.*?) (?P<MESSAGE>.*)', line)
				if usermat:
					self.handleUser(usermat.groups())

	def handleServer(self, match):
		for serv_hand in self.server_handles.values():
			serv_hand(match)

	def handleUser(self, match):
		for user_hand in self.user_handles.values():
			user_hand(match)

	def add_handle(self, handle_type, name, function):
		if handle_type == "user":
			handles = self.user_handles
		else:
			handles = self.server_handles
		handles['name'] = function

class Recorder(CoreBot):
	# default_user_handles = 

	def __init__(self):
		super(Recorder, self).__init__()

		self.outfile = open("output/out_log.txt", 'a')
		self.add_handle('user', 'logger', self.log_user_input)

	def log_user_input(self, user_in):
		print user_in
		self.outfile.write(str(user_in)+"\n")

if __name__ == "__main__":
	client = Recorder()
	client.connectToServer()