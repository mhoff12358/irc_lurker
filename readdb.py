import sqlite3

import loadSettings

settings = loadSettings.loadSettings()

conn = sqlite3.connect(settings["database_file"])
cur = conn.cursor()

f = open("logout.txt", "w")
for line in cur.execute("SELECT * FROM magicBarn"):
	f.write(str(line[5])+"\n")
	print line[5]