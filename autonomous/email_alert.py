# autonomous/email_alert.py
import os
import ssl
import time
import socket
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import requests

load_dotenv()

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_FROM_NAME = os.getenv("ALERT_FROM_NAME", "Methane Monitor")
ALERT_TO = os.getenv("ALERT_TO", "")
MAX_RETRIES = int(os.getenv("EMAIL_MAX_RETRIES", "4"))
RETRY_DELAY_SECONDS = float(os.getenv("EMAIL_RETRY_DELAY", "2.0"))

# SendGrid fallback
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM = os.getenv("SENDGRID_FROM", GMAIL_USER)

def _get_recipient_list(to_env_value):
    if not to_env_value:
        return []
    return [s.strip() for s in to_env_value.split(",") if s.strip()]

def _check_port(host: str, port: int, timeout: float = 6.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def _try_smtp_ssl(subject: str, body: str, to_addrs: list[str]) -> bool:
    context = ssl.create_default_context()
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            LOG.debug("Attempt %d to send via SMTP SSL (465)", attempt)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=20) as smtp:
                smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                msg = MIMEMultipart()
                msg["Subject"] = subject
                msg["From"] = f"{ALERT_FROM_NAME} <{GMAIL_USER}>"
                msg["To"] = ", ".join(to_addrs)
                msg.attach(MIMEText(body, "plain"))
                smtp.sendmail(GMAIL_USER, to_addrs, msg.as_string())
            return True
        except Exception as e:
            LOG.debug("SMTP SSL attempt %d failed: %s", attempt, e, exc_info=True)
            last_exc = e
            time.sleep(RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))
    LOG.warning("SMTP_SSL failed after %d attempts: %s", MAX_RETRIES, last_exc)
    return False

def _try_smtp_starttls(subject: str, body: str, to_addrs: list[str]) -> bool:
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            LOG.debug("Attempt %d to send via SMTP STARTTLS (587)", attempt)
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                msg = MIMEMultipart()
                msg["Subject"] = subject
                msg["From"] = f"{ALERT_FROM_NAME} <{GMAIL_USER}>"
                msg["To"] = ", ".join(to_addrs)
                msg.attach(MIMEText(body, "plain"))
                smtp.sendmail(GMAIL_USER, to_addrs, msg.as_string())
            return True
        except Exception as e:
            LOG.debug("SMTP STARTTLS attempt %d failed: %s", attempt, e, exc_info=True)
            last_exc = e
            time.sleep(RETRY_DELAY_SECONDS * (2 ** (attempt - 1)))
    LOG.warning("SMTP STARTTLS failed after %d attempts: %s", MAX_RETRIES, last_exc)
    return False

def _send_via_sendgrid(subject: str, body: str, to_addrs: list[str]) -> bool:
    if not SENDGRID_API_KEY or not SENDGRID_FROM:
        LOG.error("SendGrid not configured.")
        return False
    url = "https://api.sendgrid.com/v3/mail/send"
    payload = {
        "personalizations": [{"to": [{"email": e} for e in to_addrs]}],
        "from": {"email": SENDGRID_FROM},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}]
    }
    headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        LOG.debug("SendGrid sent message successfully.")
        return True
    except Exception as e:
        LOG.exception("SendGrid send failed: %s", e)
        return False

def send_email_alert(subject: str, plain_text_body: str, to_addrs: list[str] | None = None) -> bool:
    if to_addrs is None:
        to_addrs = _get_recipient_list(ALERT_TO)

    if not to_addrs:
        raise RuntimeError("No recipient addresses provided (ALERT_TO or to_addrs)")

    # Basic validation of Gmail creds
    has_gmail_creds = bool(GMAIL_USER and GMAIL_APP_PASSWORD)

    # Quick connectivity test
    smtp465_ok = _check_port("smtp.gmail.com", 465)
    smtp587_ok = _check_port("smtp.gmail.com", 587)
    LOG.debug("Connectivity: 465:%s 587:%s", smtp465_ok, smtp587_ok)

    if has_gmail_creds and (smtp465_ok or smtp587_ok):
        if smtp465_ok:
            ok = _try_smtp_ssl(subject, plain_text_body, to_addrs)
            if ok:
                return True
        if smtp587_ok:
            ok = _try_smtp_starttls(subject, plain_text_body, to_addrs)
            if ok:
                return True

    # If SMTP unreachable or creds missing/failed, try SendGrid fallback (HTTPS)
    if SENDGRID_API_KEY:
        LOG.info("Attempting SendGrid fallback")
        if _send_via_sendgrid(subject, plain_text_body, to_addrs):
            return True

    raise RuntimeError("Failed to send email via SMTP and no successful fallback.")
