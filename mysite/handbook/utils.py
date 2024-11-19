import requests
from django.conf import settings
import json

def send_mailgun_email(to_email, subject, variables):
    response = requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={
            "from": f"ESI Handbook <mailgun@{settings.MAILGUN_DOMAIN}>",
            "to": to_email,
            "subject": subject,
            "template": "Policy Request Received",
            "h:X-Mailgun-Variables":  json.dumps(variables),
        },
    )
    if response.status_code != 200:
        # Log the error or raise an exception
        print(f"Failed to send email: {response.text}")
    return response
