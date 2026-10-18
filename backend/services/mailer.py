"""
Outbound email via the founder's own SMTP account (e.g. Gmail with an app password).
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid
from typing import Any

SMTP_TIMEOUT_SECONDS = 20


class MailerError(Exception):
    pass


def _connect(settings: dict[str, Any]) -> smtplib.SMTP:
    host, port = settings["host"], int(settings["port"])
    context = ssl.create_default_context()
    try:
        if settings.get("use_ssl"):
            server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT_SECONDS, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS)
            server.ehlo()
            if server.has_extn("starttls"):
                server.starttls(context=context)
                server.ehlo()
        if settings.get("password"):
            server.login(settings["username"], settings["password"])
        return server
    except smtplib.SMTPAuthenticationError as exc:
        raise MailerError("SMTP login failed: check the username and app password") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise MailerError(f"Could not connect to {host}:{port}: {exc}") from exc


def test_smtp(settings: dict[str, Any]) -> tuple[bool, str]:
    try:
        server = _connect(settings)
    except MailerError as exc:
        return False, str(exc)
    try:
        server.quit()
    except smtplib.SMTPException:
        pass
    return True, f"Logged in to {settings['host']} as {settings['username']}"


def send_email(
    settings: dict[str, Any],
    *,
    to_email: str,
    subject: str,
    body: str,
    from_name: str | None = None,
) -> str:
    """Send a plain-text email and return its Message-ID."""
    msg = EmailMessage()
    from_email = settings["from_email"]
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    message_id = make_msgid(domain=from_email.split("@")[-1] or None)
    msg["Message-ID"] = message_id
    msg.set_content(body)
    server = _connect(settings)
    try:
        server.send_message(msg)
    except smtplib.SMTPException as exc:
        raise MailerError(f"SMTP server rejected the message: {exc}") from exc
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            pass
    return message_id
