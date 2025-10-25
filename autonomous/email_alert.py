import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def send_alert(reasoning):
    msg = MIMEText(f"Methane anomaly detected!\n\n{reasoning}")
    msg["Subject"] = "⚠️ Methane Alert!"
    msg["From"] = os.getenv("EMAIL_SENDER")
    msg["To"] = os.getenv("EMAIL_RECEIVER")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_APP_PASSWORD"))
        smtp.send_message(msg)


