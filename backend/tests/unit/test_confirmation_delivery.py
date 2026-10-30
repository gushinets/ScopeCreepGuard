import asyncio
from uuid import uuid4

import pytest

from scope_guard.services.email.contracts import EmailError


@pytest.mark.parametrize(
    "failure,expected", [(None, "accepted"), ("rejected", "failed"), ("ambiguous", "unknown")]
)
def test_delivery_outcomes_preserve_pending_account(failure, expected):
    from scope_guard.services.auth.confirmation import ConfirmationService

    events = []

    class Attempts:
        async def reserve(self, user_id, source):
            events.append("committed_reservation")
            return uuid4()

        async def finish(self, attempt, status):
            events.append(status)

        async def status(self, user_id, source=None):
            return {"status": expected, "retryAfter": 60}

    class Tokens:
        async def issue_pending_confirmation(self, user_id):
            from datetime import UTC, datetime

            from scope_guard.domain.auth.tokens import IssuedAuthToken

            events.append("committed_token")
            return IssuedAuthToken("secret-token", datetime.now(UTC))

    class Email:
        async def send_confirmation(self, recipient, url, locale):
            assert events == ["committed_reservation", "committed_token"]
            assert "#userId=" in url and "&token=secret-token" in url
            assert locale == "ru"
            if failure:
                raise EmailError(failure)

    result = asyncio.run(
        ConfirmationService(Attempts(), Tokens(), Email(), "http://localhost:3000").send(
            {"id": str(uuid4()), "email": "a@example.test"}, "ru", "source"
        )
    )
    assert result["status"] == expected
    assert events[-1] == expected
