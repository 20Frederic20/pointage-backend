"""SMTP adapter for the :class:`EmailSender` port — stdlib ``smtplib``.

``smtplib`` blocks, so each send runs in a worker thread and never stalls
the event loop. One connection per email: login codes are a trickle, a
connection pool would buy nothing.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from core.settings import MailSettings

from ..application.dtos import OutgoingEmailDTO
from ..application.ports import EmailSender

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


class SmtpEmailSender(EmailSender):
    __slots__ = ("_settings",)

    def __init__(self, settings: MailSettings) -> None:
        self._settings = settings

    async def send(self, email: OutgoingEmailDTO) -> None:
        try:
            await asyncio.to_thread(self._send_blocking, email)
        except Exception:
            # Runs after the response is sent: nobody to report to but the
            # logs. The user asks for a new code after the resend cooldown.
            logger.exception("mail: could not send %r to %s", email.subject, email.to)

    def _send_blocking(self, email: OutgoingEmailDTO) -> None:
        message = EmailMessage()
        message["From"] = self._settings.mail_from
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=_TIMEOUT_SECONDS) as smtp:
            if self._settings.smtp_starttls:
                smtp.starttls()
            if self._settings.smtp_username:
                smtp.login(self._settings.smtp_username, self._settings.smtp_password or "")
            smtp.send_message(message)
