import sqlite3

import loadSettings

settings = loadSettings.loadSettings()

conn = sqlite3.connect(settings["database_file"])
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS magicBarn (stamp datetime2, username text, realname text, weblocation text, msgtype text, contents text, meta text)")
cur.execute("CREATE TABLE IF NOT EXISTS errorLines (stamp datetime2, errorline text)")

conn.commit()
conn.close()