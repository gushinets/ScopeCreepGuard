import importlib.util
from pathlib import Path

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/verify_docker_startup.py"
spec = importlib.util.spec_from_file_location("startup_confirmation", SCRIPT)
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)

ORIGIN = "http://127.0.0.1:34567"
OWNER = "10000000-0000-4000-8000-000000000001"
TOKEN = "synthetic-confirmation-token-for-startup"


def test_mail_poll_waits_for_matching_recipient_and_preserves_fragment_token():
    elapsed = [0.0]
    polls = []

    def handle(request):
        polls.append(request.url.path)
        if request.url.path == "/api/v1/messages":
            messages = (
                []
                if elapsed[0] == 0
                else [
                    {"ID": "unrelated", "To": [{"Address": "other@example.test"}]},
                    {"ID": "confirmation", "To": [{"Address": "startup@example.test"}]},
                ]
            )
            return httpx.Response(200, json={"messages": messages})
        assert request.url.path == "/api/v1/message/confirmation"
        return httpx.Response(
            200, json={"Text": f"Confirm\n{ORIGIN}/confirm-email#userId={OWNER}&token={TOKEN}\n"}
        )

    with httpx.Client(transport=httpx.MockTransport(handle), base_url="http://mailpit") as client:
        result = startup.wait_for_confirmation(
            client,
            "startup@example.test",
            ORIGIN,
            OWNER,
            clock=lambda: elapsed[0],
            sleep=lambda value: elapsed.__setitem__(0, elapsed[0] + value),
        )
    assert result == {"userId": OWNER, "token": TOKEN}
    assert polls == ["/api/v1/messages", "/api/v1/messages", "/api/v1/message/confirmation"]


def test_mail_poll_has_a_deadline_without_leaking_message_contents():
    elapsed = [0.0]
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"messages": []})),
        base_url="http://mailpit",
    ) as client:
        with pytest.raises(AssertionError, match="Confirmation email did not arrive"):
            startup.wait_for_confirmation(
                client,
                "startup@example.test",
                ORIGIN,
                OWNER,
                timeout=1,
                clock=lambda: elapsed[0],
                sleep=lambda value: elapsed.__setitem__(0, elapsed[0] + value),
            )
    assert elapsed[0] == pytest.approx(1)


@pytest.mark.parametrize(
    "link",
    [
        f"https://evil.test/confirm-email#userId={OWNER}&token={TOKEN}",
        f"{ORIGIN}/confirm-email?userId={OWNER}&token={TOKEN}",
        f"{ORIGIN}/confirm-email#userId=20000000-0000-4000-8000-000000000002&token={TOKEN}",
    ],
)
def test_mail_link_requires_the_expected_origin_fragment_and_owner(link):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "messages": [
                        {"ID": "confirmation", "To": [{"Address": "startup@example.test"}]}
                    ]
                }
                if request.url.path.endswith("messages")
                else {"Text": link},
            )
        ),
        base_url="http://mailpit",
    ) as client:
        with pytest.raises(AssertionError, match="Invalid confirmation email link") as error:
            startup.wait_for_confirmation(client, "startup@example.test", ORIGIN, OWNER)
    assert TOKEN not in str(error.value)
