import asyncio
from email.headerregistry import Address
from email.message import EmailMessage as MIMEMessage
from email.utils import formatdate

import aiosmtplib
from aiosmtplib import errors

from scope_guard.core.config import Settings
from scope_guard.services.email.contracts import (
    EmailError,
    EmailMessage,
    ErrorCategory,
    address,
    header,
)


def mime_message(message: EmailMessage, settings: Settings) -> MIMEMessage:
    address(settings.smtp_sender_address)
    if settings.smtp_sender_name:
        header(settings.smtp_sender_name)
    result = MIMEMessage()
    result["From"] = Address(
        settings.smtp_sender_name or "", addr_spec=settings.smtp_sender_address
    )
    result["To"] = address(message.recipient)
    result["Subject"] = header(message.subject)
    result["Message-ID"] = header(message.message_id)
    result["Date"] = formatdate(localtime=False, usegmt=True)
    result.set_content(message.text)
    result.add_alternative(message.html, subtype="html")
    return result


def response_category(code: int) -> ErrorCategory:
    return "temporary" if 400 <= code < 500 else "rejected"


class SMTPSender:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def send(self, message: EmailMessage) -> None:
        s = self.settings
        if (
            not s.smtp_host.strip()
            or bool(s.smtp_username) != bool(s.smtp_password)
            or (s.smtp_password is not None and not s.smtp_password.get_secret_value())
        ):
            raise EmailError("invalid")
        mime = mime_message(message, s)
        client = None
        try:
            client = aiosmtplib.SMTP(
                hostname=s.smtp_host,
                port=s.smtp_port,
                timeout=s.smtp_timeout,
                use_tls=s.smtp_transport == "tls",
                start_tls=s.smtp_transport == "starttls",
                validate_certs=True,
            )
            async with asyncio.timeout(s.smtp_deadline):
                await client.connect()
                if s.smtp_username and s.smtp_password:
                    await client.login(s.smtp_username, s.smtp_password.get_secret_value())
                refused, _ = await client.send_message(
                    mime,
                    sender=s.smtp_sender_address,
                    recipients=[message.recipient],
                )
                if refused:
                    raise EmailError(response_category(next(iter(refused.values())).code))
        except (TimeoutError, errors.SMTPTimeoutError):
            raise EmailError("ambiguous") from None
        except errors.SMTPAuthenticationError:
            raise EmailError("authentication") from None
        except errors.SMTPRecipientsRefused as exc:
            category: ErrorCategory = (
                "temporary" if all(400 <= r.code < 500 for r in exc.recipients) else "rejected"
            )
            raise EmailError(category) from None
        except errors.SMTPResponseException as exc:
            raise EmailError(response_category(exc.code)) from None
        except errors.SMTPConnectError:
            raise EmailError("temporary") from None
        except (errors.SMTPServerDisconnected, OSError):
            raise EmailError("ambiguous") from None
        except errors.SMTPNotSupported:
            raise EmailError("invalid") from None
        except errors.SMTPException:
            raise EmailError("temporary") from None
        except (ValueError, UnicodeError):
            raise EmailError("invalid") from None
        finally:
            # Synchronous transport close cannot wait for QUIT or mask cancellation/failure.
            if client is not None:
                client.close()
