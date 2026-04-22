import requests
import os

url = "https://api.zeptomail.com/v1.1/email"
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": os.getenv('ZEPTOMAIL_API_TOKEN')
}

payload = {
    "from": {"address": "noreply@useautobus.com"},
    "to": [{"email_address": {"address": "cto@greenbraintech.com"}}],
    "subject": "Test Email",
    "htmlbody": "Test email sent successfully."
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())