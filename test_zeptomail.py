import smtplib, ssl
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()
import os

port = int(os.getenv('ZEPTOMAIL_SMTP_PORT', 587))
smtp_server = os.getenv('ZEPTOMAIL_SMTP_HOST')
username = os.getenv('ZEPTOMAIL_SMTP_USERNAME')
password = os.getenv('ZEPTOMAIL_SMTP_PASSWORD')
message = "Test email sent successfully."
msg = EmailMessage()
msg['Subject'] = "Test Email"
msg['From'] = "noreply@useautobus.com"
msg['To'] = "cto@greenbraintech.com"
msg.set_content(message)
try:
    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(username, password)
            server.send_message(msg)
    elif port == 587:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
    else:
        print ("use 465 / 587 as port value")
        exit()
    print ("Email successfully sent")
except Exception as e:
    print (e)