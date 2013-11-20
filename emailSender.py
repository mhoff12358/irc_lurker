def sendmail(recipient, subject, text, attachments):
	import os, smtplib
	from email.message import Message
	from email.mime.multipart import MIMEMultipart
	from email.MIMEBase import MIMEBase
	from email.MIMEText import MIMEText
	from email import Encoders

	msg = MIMEMultipart()
	msg['subject'] = subject
	msg['From'] = 'padswayLurker@gmail.com'
	msg['To'] = recipient

	msg.attach(MIMEText(text))

	for f in attachments:
		fi = MIMEBase('application', "octet-stream")
		fi.set_payload(open(f, 'rb').read())
		Encoders.encode_base64(fi)
		fi.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
		msg.attach(fi)

	server = smtplib.SMTP('smtp.gmail.com:587')
	server.starttls()
	server.login('padswayLurker', 'lurkerpass')
	server.sendmail(msg['From'], msg['To'], msg.as_string())
	server.quit()
