import logging
from email.utils import make_msgid
from html import escape
from time import monotonic
from typing import Literal
from urllib.parse import urlsplit

from .contracts import EmailError, EmailMessage, Sender, header

logger = logging.getLogger("scope_guard.email")


class EmailService:
    def __init__(self, sender: Sender):
        self.sender = sender

    def prepare(
        self,
        kind: Literal["confirmation", "password_recovery"],
        recipient: str,
        action_url: str,
        locale: Literal["ru", "en"],
    ) -> EmailMessage:
        try:
            header(action_url)
            url = urlsplit(action_url)
            if (
                url.scheme not in ("http", "https")
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or any(c.isspace() for c in action_url)
            ):
                raise ValueError
            _ = url.port
        except ValueError:
            raise EmailError("invalid") from None
        if locale not in ("ru", "en") or kind not in ("confirmation", "password_recovery"):
            raise EmailError("invalid")
        subjects = {
            ("confirmation", "en"): "Confirm your email",
            ("confirmation", "ru"): "Подтвердите адрес электронной почты",
            ("password_recovery", "en"): "Reset your password",
            ("password_recovery", "ru"): "Восстановление пароля",
        }
        subject = subjects[kind, locale]
        expiry = (
            "Ссылка действительна 24 часа."
            if locale == "ru"
            else "This link is valid for 24 hours."
        )
        instruction = (
            (
                "Перейдите по ссылке, чтобы подтвердить адрес электронной почты."
                if kind == "confirmation"
                else "Перейдите по ссылке, чтобы задать новый пароль."
            )
            if locale == "ru"
            else (
                "Follow the link to confirm your email address."
                if kind == "confirmation"
                else "Follow the link to choose a new password."
            )
        )
        ignore = (
            "Если вы не запрашивали это письмо, проигнорируйте его."
            if locale == "ru"
            else "If you did not request this email, ignore it."
        )
        return EmailMessage(
            recipient,
            subject,
            f"{instruction}\n{action_url}\n{expiry}\n{ignore}",
            f'<p>{instruction}</p><p><a href="{escape(action_url, quote=True)}">'
            f"{escape(subject)}</a></p><p>{expiry}</p><p>{ignore}</p>",
            make_msgid(domain="scopecreepguard.local"),
            kind,
            locale,
        )

    async def send(self, message: EmailMessage) -> None:
        started = monotonic()
        category = "cancelled"
        try:
            await self.sender.send(message)
            category = "accepted"
        except EmailError as exc:
            category = exc.category
            raise
        finally:
            logger.info(
                "email_operation",
                extra={
                    "message_id": message.message_id,
                    "template_kind": message.kind,
                    "locale": message.locale,
                    "duration_ms": round((monotonic() - started) * 1000),
                    "category": category,
                },
            )

    async def send_confirmation(self, recipient: str, action_url: str, locale) -> EmailMessage:
        message = self.prepare("confirmation", recipient, action_url, locale)
        await self.send(message)
        return message

    async def send_password_recovery(self, recipient: str, action_url: str, locale) -> EmailMessage:
        message = self.prepare("password_recovery", recipient, action_url, locale)
        await self.send(message)
        return message
