

def loadSettings():
	REQUIRED_SETTINGS = ["database_file"]

	inFile = open("settings.txt")
	settings = {}

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