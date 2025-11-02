# autonomous/email_alert.py
import os
import ssl
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()  # loads .env in project root if present

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_FROM_NAME = os.getenv("ALERT_FROM_NAME", "Methane Monitor")
ALERT_TO = os.getenv("ALERT_TO")  # comma-separated list or single email
MAX_RETRIES = int(os.getenv("EMAIL_MAX_RETRIES", "4"))
RETRY_DELAY_SECONDS = float(os.getenv("EMAIL_RETRY_DELAY", "2.0"))

def _get_recipient_list(to_env_value):
    if not to_env_value:
        return []
    return [s.strip() for s in to_env_value.split(",") if s.strip()]

def send_email_alert(subject: str, plain_text_body: str, to_addrs: list[str] | None = None):
    """
    Sends a single email via Gmail SMTP SSL. Performs simple retry backoff.
    Raises RuntimeError on failure.
    """
    if to_addrs is None:
        to_addrs = _get_recipient_list(ALERT_TO)

    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_USER or GMAIL_APP_PASSWORD not set in environment (.env)")

    if not to_addrs:
        raise RuntimeError("No recipient addresses provided (ALERT_TO or to_addrs)")

    # Build message
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = f"{ALERT_FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(plain_text_body, "plain"))

    context = ssl.create_default_context()

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=30) as smtp:
                smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                smtp.sendmail(GMAIL_USER, to_addrs, msg.as_string())
            # success
            return True
        except Exception as e:
            last_exc = e
            wait = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            time.sleep(wait)
    # If we reach here, all retries failed
    raise RuntimeError(f"Failed to send email after {MAX_RETRIES} attempts. Last error: {last_exc}")
