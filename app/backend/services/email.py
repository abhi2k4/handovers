"""Send alert emails over SMTP, with the standard library only.

Port 465 uses implicit TLS, 587 STARTTLS, anything else plain SMTP (Mailpit on 1025 in
development). smtplib blocks, so each send runs in a worker thread.
"""

import asyncio
import smtplib
from email.message import EmailMessage

from core.config import Settings


class SendError(Exception):
    pass


def message(s: Settings, to: str, subject: str, body: str, link: str = "") -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"Handovers <{s.smtp_from}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(f"{body}\n\n{link}\n" if link else f"{body}\n")
    return msg


def _send(s: Settings, msg: EmailMessage) -> None:
    password = s.smtp_password.get_secret_value() if s.smtp_password else ""
    smtp_class = smtplib.SMTP_SSL if s.smtp_port == 465 else smtplib.SMTP
    with smtp_class(s.smtp_host, s.smtp_port, timeout=10) as smtp:
        if s.smtp_port == 587:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, password)
        smtp.send_message(msg)


async def send(s: Settings, to: str, subject: str, body: str, link: str = "") -> None:
    """Raises SendError with a reason an admin can read (never the password)."""
    if not s.email_enabled:
        raise SendError("Email is not set up")
    try:
        await asyncio.to_thread(_send, s, message(s, to, subject, body, link))
    except (OSError, smtplib.SMTPException) as exc:
        raise SendError(f"{s.smtp_host}:{s.smtp_port}: {exc}"[:300]) from exc
