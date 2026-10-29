import asyncio

import pytest


def test_email_module_contract():
    from scope_guard.services.email.service import EmailService

    class Sender:
        async def send(self, message):
            self.message = message

    sender = Sender()
    service = EmailService(sender)
    for kind in ("confirmation", "password_recovery"):
        for locale in ("ru", "en"):
            message = service.prepare(
                kind, "test@example.com", "http://localhost/action?a=1&b=2", locale
            )
            assert message.subject
            assert ("24 часа" if locale == "ru" else "24 hours") in message.text
            assert "&amp;b=2" in message.html
            asyncio.run(service.send(message))
            assert sender.message == message


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "https:///bad", "http://user:pass@host/a", "https://host/\r\nx"]
)
def test_unsafe_urls(url):
    from scope_guard.services.email.contracts import EmailError
    from scope_guard.services.email.service import EmailService

    with pytest.raises(EmailError):
        EmailService(None).prepare("confirmation", "test@example.com", url, "en")


@pytest.mark.parametrize(
    "kind,locale,subject",
    [
        ("confirmation", "en", "Confirm your email"),
        ("confirmation", "ru", "Подтвердите адрес электронной почты"),
        ("password_recovery", "en", "Reset your password"),
        ("password_recovery", "ru", "Восстановление пароля"),
    ],
)
def test_mime(kind, locale, subject):
    from scope_guard.core.config import Settings
    from scope_guard.integrations.email.smtp import mime_message
    from scope_guard.services.email.service import EmailService

    message = EmailService(None).prepare(kind, "test@example.com", "https://example.com/a", locale)
    mime = mime_message(message, Settings(_env_file=None))
    assert mime["Subject"] == subject
    assert mime["Message-ID"] == message.message_id
    assert mime.get_content_type() == "multipart/alternative"
    assert mime.get_body(preferencelist=("plain",)).get_content().strip() == message.text
    assert mime.get_body(preferencelist=("html",)).get_content().strip() == message.html


@pytest.mark.parametrize(
    "field,value",
    [
        ("smtp_timeout", 0),
        ("smtp_deadline", 301),
        ("smtp_timeout", float("nan")),
        ("smtp_port", 0),
        ("smtp_transport", "auto"),
    ],
)
def test_bad_settings(field, value):
    from pydantic import ValidationError

    from scope_guard.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


@pytest.mark.parametrize("recipient,locale", [("a@b\r\nBcc:x@y", "en"), ("x@y", "de")])
def test_bad_headers_locale(recipient, locale):
    from scope_guard.services.email.contracts import EmailError
    from scope_guard.services.email.service import EmailService

    with pytest.raises(EmailError):
        EmailService(None).prepare("confirmation", recipient, "https://example.com", locale)


@pytest.mark.parametrize("mode", ["none", "starttls", "tls"])
@pytest.mark.parametrize("auth", [False, True])
def test_smtp_modes(monkeypatch, mode, auth):
    from scope_guard.core.config import Settings
    from scope_guard.integrations.email import smtp
    from scope_guard.services.email.service import EmailService

    captured = {}

    class Client:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def connect(self):
            pass

        async def login(self, username, password):
            captured["login"] = (username, password)

        async def send_message(self, message, **kwargs):
            captured["mime"] = message
            return {}, "accepted"

        def close(self):
            captured["closed"] = True

    monkeypatch.setattr(smtp.aiosmtplib, "SMTP", Client)
    settings = Settings(
        _env_file=None,
        smtp_transport=mode,
        smtp_username="user" if auth else None,
        smtp_password="secret" if auth else None,
    )
    service = EmailService(smtp.SMTPSender(settings))
    asyncio.run(service.send_confirmation("test@example.com", "https://example.com", "en"))
    assert captured["use_tls"] == (mode == "tls")
    assert captured["start_tls"] == (mode == "starttls")
    assert captured["validate_certs"] is True
    assert ("login" in captured) == auth
    assert captured["closed"]


@pytest.mark.parametrize(
    "failure,category",
    [
        ("temporary", "temporary"),
        ("permanent", "rejected"),
        ("auth", "authentication"),
        ("timeout", "ambiguous"),
        ("disconnect", "ambiguous"),
        ("refusal", "rejected"),
        ("cancel", None),
        ("connect", "temporary"),
    ],
)
def test_failures_no_retry_safe_logs(monkeypatch, caplog, failure, category):
    import logging

    from aiosmtplib import errors
    from aiosmtplib.response import SMTPResponse

    from scope_guard.core.config import Settings
    from scope_guard.integrations.email import smtp
    from scope_guard.services.email.contracts import EmailError
    from scope_guard.services.email.service import EmailService

    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def connect(self):
            if failure == "connect":
                raise errors.SMTPConnectError("sensitive")

        async def send_message(self, *args, **kwargs):
            calls.append("send")
            if failure == "refusal":
                return {"test@example.com": SMTPResponse(550, "sensitive")}, ""
            if failure == "timeout":
                await asyncio.sleep(1)
            if failure == "cancel":
                raise asyncio.CancelledError
            if failure == "disconnect":
                raise errors.SMTPServerDisconnected("sensitive")
            if failure == "auth":
                raise errors.SMTPAuthenticationError(535, "sensitive")
            raise errors.SMTPDataError(450 if failure == "temporary" else 550, "sensitive")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(smtp.aiosmtplib, "SMTP", Client)
    caplog.set_level(logging.INFO, logger="scope_guard.email")
    service = EmailService(smtp.SMTPSender(Settings(_env_file=None, smtp_deadline=0.01)))
    with pytest.raises(EmailError if category else asyncio.CancelledError) as caught:
        asyncio.run(
            service.send_confirmation("test@example.com", "https://example.com/token", "en")
        )
    if category:
        assert caught.value.category == category
    assert calls.count("send") <= 1
    assert calls[-1] == "close"
    data = str([r.__dict__ for r in caplog.records])
    for secret in ("test@example.com", "/token", "sensitive"):
        assert secret not in data


def test_incomplete_auth_is_lazy():
    from scope_guard.core.config import Settings
    from scope_guard.integrations.email.smtp import SMTPSender
    from scope_guard.services.email.contracts import EmailError
    from scope_guard.services.email.service import EmailService

    service = EmailService(SMTPSender(Settings(_env_file=None, smtp_username="user")))
    with pytest.raises(EmailError, match="invalid"):
        asyncio.run(service.send_confirmation("test@example.com", "http://localhost", "en"))


@pytest.mark.parametrize("code,category", [(450, "temporary"), (550, "rejected")])
def test_raised_recipient_refusal(monkeypatch, code, category):
    from aiosmtplib import errors

    from scope_guard.core.config import Settings
    from scope_guard.integrations.email import smtp
    from scope_guard.services.email.contracts import EmailError
    from scope_guard.services.email.service import EmailService

    class Client:
        def __init__(self, **kwargs):
            pass

        async def connect(self):
            pass

        async def send_message(self, *args, **kwargs):
            raise errors.SMTPRecipientsRefused(
                [errors.SMTPRecipientRefused(code, "private", "test@example.com")]
            )

        def close(self):
            pass

    monkeypatch.setattr(smtp.aiosmtplib, "SMTP", Client)
    service = EmailService(smtp.SMTPSender(Settings(_env_file=None)))
    with pytest.raises(EmailError) as caught:
        asyncio.run(service.send_confirmation("test@example.com", "https://example.com", "en"))
    assert caught.value.category == category


@pytest.mark.parametrize("field", ["subject", "message_id", "recipient"])
def test_message_header_injection(field):
    from dataclasses import replace

    from scope_guard.services.email.contracts import EmailError
    from scope_guard.services.email.service import EmailService

    message = EmailService(None).prepare(
        "confirmation", "test@example.com", "http://localhost", "en"
    )
    with pytest.raises(EmailError):
        replace(message, **{field: "a\r\nBcc: stolen@example.com"})
