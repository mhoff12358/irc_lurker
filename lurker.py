import sys, socket, string, time, re, os, emailSender, sqlite3, time, loadSettings, urllib2, random

class Client(object):
	log_on = False
	def __init__(self):
		#Loads the settings
		self.SETTINGS = loadSettings.loadSettings()

		#Socket initializations
		self.IDENT = self.SETTINGS["nick"]
		self.REALNAME = self.SETTINGS["nick"]
		self.CHANNELS = ["#padsway"]#self.SETTINGS["channel"].split(',')
		self.readBuffer = ""
		self.sock = socket.socket()
		self.lines = []

		#Opens up the connection to the database
		self.dbconn = sqlite3.connect("log.db")
		#Creates the tables if they don't already exist
		cur = self.dbconn.cursor()
		cur.execute("CREATE TABLE IF NOT EXISTS magicBarn (stamp datetime2, username text, realname text, weblocation text, msgtype text, contents text, meta text)")
		cur.execute("CREATE TABLE IF NOT EXISTS errorLines (stamp datetime2, errorline text)")
	
		#Connects to the irc and joins padsway
		self.sock.connect((self.SETTINGS["host"], int(self.SETTINGS["port"])))
		self.sock.send("NICK %s\r\n" % self.SETTINGS["nick"])
		self.sock.send("USER %s %s bla :%s\r\n" % (self.IDENT, self.SETTINGS["host"], self.REALNAME))
		
		#sets the socket to non-blocking
		self.sock.setblocking(0)
		
		cont = True
		#First loop, waits for foonetic to respond giving the all clear
		while cont:
			#updates the lines thing
			self.addToLines()
			while self.lines:
				#goes through each line looking to see if foonetic has responded finally
				line = self.lines.pop(0)
				print line
				if line[0:47] == ":NickServ!NickServ@services.foonetic.net NOTICE":
					cont = False

		self.mainLoop()
		
	def mainLoop(self):
		#Actually wants to join padsway now
		for channel in self.CHANNELS:
			self.sock.send("JOIN %s\r\n" % channel)

		cont = True
		#Checks for messages
		while cont:
			self.addToLines()
			while self.lines:
				line = self.lines.pop(0)
				#example line:
				# :mhoff!mhoff@hide-F11AB7E6.urh.illinois.edu PRIVMSG #padsway :testing
				# :Tingram!~Tingram@hide-C481D6AE.flgaroy.clients.pavlovmedia.com JOIN :#padsway
				# :mhoff|test!mhoff@hide-F11AB7E6.urh.illinois.edu PART #padsway :Leaving
				# :mhoff|test!mhoff@hide-F11AB7E6.urh.illinois.edu NICK :mhoff
				#:nick!realname@location MESSAGETYPE from :message (from is optional)
				print line
				firstmat = re.match(':(?P<USERNAME>.*?)!(?P<REALNAME>.*?)@(?P<WEBLOC>.*?) (?P<MESSAGE>.*)', line)
				
				if firstmat:
					message = firstmat.group("MESSAGE")

					if re.match("PRIVMSG", message):
						secondmat = re.match('(?P<MESSAGETYPE>.*?) (?P<RECIPIENT>.*?) :(?P<MESSAGE>.*)', message)
						if secondmat:
							if secondmat.group('RECIPIENT') == self.SETTINGS["nick"]:
								self.interpretCommand(firstmat.group('USERNAME'), secondmat.group('MESSAGE'))
							else:
								self.palookup(firstmat.group('USERNAME'), firstmat.group('REALNAME'), \
									firstmat.group('WEBLOC'), secondmat.group('MESSAGETYPE'), \
									secondmat.group('MESSAGE'), secondmat.group('RECIPIENT'))
								self.addToLog(firstmat.group('USERNAME'), firstmat.group('REALNAME'), \
									firstmat.group('WEBLOC'), secondmat.group('MESSAGETYPE'), \
									secondmat.group('MESSAGE'), secondmat.group('RECIPIENT'))
					elif re.match("JOIN", message):
						secondmat = re.match('(?P<MESSAGETYPE>.*?) :(?P<LOCATION>.*)', message)
						if secondmat:
							self.addToLog(firstmat.group('USERNAME'), firstmat.group('REALNAME'), \
								firstmat.group('WEBLOC'), secondmat.group('MESSAGETYPE'), secondmat.group('LOCATION'))
					elif re.match("QUIT", message):
						pass
					elif re.match("PART", message):
						secondmat = re.match('(?P<MESSAGETYPE>.*?) (?P<RECIPIENT>.*?) :(?P<MESSAGE>.*)', message)
						if secondmat:
							self.addToLog(firstmat.group('USERNAME'), firstmat.group('REALNAME'), \
								firstmat.group('WEBLOC'), secondmat.group('MESSAGETYPE'), \
								secondmat.group('MESSAGE'), secondmat.group('RECIPIENT'))
					elif re.match("NICK", message):
						secondmat = re.match('(?P<MESSAGETYPE>.*?) :(?P<NICK>.*)', message)
						if secondmat:
							self.addToLog(firstmat.group('USERNAME'), firstmat.group('REALNAME'), \
								firstmat.group('WEBLOC'), secondmat.group('MESSAGETYPE'), secondmat.group('NICK'))
					else:
						self.addToErrors(line)
				else:
					self.addToErrors(line)

	def getTime(self):
		t = time.localtime()
		#Time is a string formatted in the datetime2 format for sql
		return str(t[0])+"-"+str(t[1]).rjust(2, "0")+"-"+str(t[2]).rjust(2, "0")+" "+ \
			str(t[2]).rjust(3, "0")+":"+str(t[2]).rjust(4, "0")+":"+str(t[2]).rjust(5, "0")

	def addToErrors(self, line):
		cur = self.dbconn.cursor()
		cur.execute("INSERT INTO errorLines VALUES (?,?)", (self.getTime(), line))
		self.dbconn.commit()

	def addToLog(self, user, realname, weblocation, msgtype, contents, meta=""):
		if self.log_on:
			timeval = self.getTime()
			
			cur = self.dbconn.cursor()
			#inserts datetime username realname location weblocation messagetype from contents
			cur.execute("INSERT INTO magicBarn VALUES (?,?,?,?,?,?,?)", \
				(timeval, user, realname, weblocation, msgtype, contents, meta))
			self.dbconn.commit()

	def addToLines(self):
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

	def interpretCommand(self, user, message):
		mat = re.match('(?P<COMMAND>.*?) (<(?P<KEYWORDS>.*?)>)? (?P<TEXT>.*)', message)
		if mat:
			print mat.group('COMMAND')
			if mat.group('KEYWORDS'):
				print mat.group('KEYWORDS')
			print mat.group('TEXT')
			if mat.group('KEYWORDS'):
				keywords = re.findall('([^ ]*) ?', mat.group('KEYWORDS'))
			else:
				keywords = []
			print keywords
			if mat.group('COMMAND') == 'msg':
				print 'messaging now'
				mat2 = re.match('(?P<RECIPIENT>.*?) (?P<BODY>.*)', mat.group('TEXT'))
				if mat2:
					print 'made it to sending'
					if 'anon' in keywords:
						self.message(mat2.group('RECIPIENT'), 'anonymous said: ' + mat2.group('BODY'))
					elif 'subtle' in keywords:
						text = mat2.group('BODY')
						if len(text) >= 1 and text[0] == '/':
							text = " " + text
						self.message(mat2.group('RECIPIENT'), text)
					else:
						self.message(mat2.group('RECIPIENT'), user + ' said: ' + mat2.group('BODY'))
			elif mat.group('COMMAND') == 'getLogs':
				#print 'sending logs'
				attachments = ['log.txt']
				f = []
				for root, dirs, files in os.walk('.'):
					#print "files: ", files
					if f == []:
						f = files
				for i in f:
					if i[:9] == "logBackup":
						attachments.append(i)
				emailSender.sendmail(mat.group('TEXT'), 'logs', 'Here are some logs', attachments)
			elif mat.group('COMMAND') == 'newNick':
                		if self.SETTINGS["password"] in mat.group('KEYWORDS'):
                    			self.SETTINGS["nick"] = mat.group('TEXT').strip()
                    			print "new nick name: " + self.SETTINGS["nick"]
                    			self.sock.send("NICK %s\r\n" % (self.SETTINGS["nick"]))
				else:
					self.sock.send("PRIVMSG %s %s\r\n" %(user, "incorrect password"))

	def message(self, recipient, message):
		self.sock.send("PRIVMSG %s %s\r\n" % (recipient, message))

	def palookup(self, user, realname, weblocation, msgtype, contents, meta=""):
		m1 = re.match('(?:.\d*)?PA:(.*)', contents)
		if m1:
			print m1.groups()
			# try:
			search = 'http://www.penny-arcade.com/archive/results/search&keywords=' + \
						m1.groups()[0].strip(' ').replace(' ', '+')
			print search
			search_result = urllib2.urlopen(search)
			mat = re.search('<div class="imgTmb">.*?href="(.*?)".*?title="(.*?)".*?</div>', search_result.read())
			if mat:
				self.sock.send("PRIVMSG %s %s\r\n" %("#padsway", mat.groups()[1]+": "+mat.groups()[0]))
			else:
				names = ['Zach', 'Matt', 'Alex', 'Angus', 'Warren', 'Butt']
				self.sock.send("PRIVMSG %s %s\r\n" %("#padsway", "Penny Arcade has no witty joke, so I will substitute my own: "+names[random.randrange(len(names))]+"'s ability to play video games."))


client = Client()
