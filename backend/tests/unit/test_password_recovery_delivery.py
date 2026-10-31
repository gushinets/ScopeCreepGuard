import asyncio

import pytest

from scope_guard.services.email.contracts import EmailError
from scope_guard.services.email.service import EmailService


@pytest.mark.parametrize("locale", ["ru", "en"])
def test_password_change_notification_contains_no_action_secret(locale):
    delivered = []

    class Sender:
        async def send(self, message):
            delivered.append(message)

    asyncio.run(EmailService(Sender()).send_password_changed("owner@example.test", locale))
    message = delivered[0]
    assert message.recipient == "owner@example.test"
    assert message.locale == locale
    assert message.kind == "password_changed"
    assert (
        "password" in message.subject.lower()
        if locale == "en"
        else "парол" in message.subject.lower()
    )
    assert "token=" not in message.text + message.html
    assert "#" not in message.text


def test_notification_failure_retains_safe_category():
    class Sender:
        async def send(self, message):
            raise EmailError("ambiguous")

    with pytest.raises(EmailError) as failure:
        asyncio.run(EmailService(Sender()).send_password_changed("owner@example.test", "en"))
    assert failure.value.category == "ambiguous"
