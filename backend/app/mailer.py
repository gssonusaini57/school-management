"""Minimal SMTP mailer for transactional email (Zoho Mail).

Stdlib-only (smtplib + email) — no extra dependency. Sends a multipart
text+HTML message. Designed to fail loudly in logs but never to leak SMTP
internals to the API caller (the forgot-password route returns a generic
response regardless of send outcome).
"""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from .config import settings
from .logging_config import get_logger

log = get_logger("app.mailer")


class EmailNotConfigured(RuntimeError):
    """Raised when an email send is attempted but SMTP isn't configured."""


def send_email(*, to: str, subject: str, html: str, text: str | None = None) -> None:
    """Send one email. Raises on hard failure; caller decides how to handle.

    `text` is a plaintext fallback; if omitted a crude one is derived so every
    message is multipart (better deliverability than HTML-only).
    """
    if not settings.email_enabled:
        raise EmailNotConfigured(
            "SMTP not configured (set SMTP_HOST / SMTP_USER / SMTP_PASSWORD)"
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.smtp_from_address))
    msg["To"] = to
    msg.set_content(text or "Please view this message in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")

    if settings.SMTP_USE_SSL:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=20) as s:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            s.ehlo()
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)

    log.info("email sent", extra={"event": "email_sent", "subject": subject})
