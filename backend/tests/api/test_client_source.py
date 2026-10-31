import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from scope_guard.core.config import Settings


@pytest.mark.parametrize(
    "peer,header,expected",
    [
        ("192.0.2.10", "198.51.100.1", "198.51.100.1"),
        ("192.0.2.10", "198.51.100.2", "198.51.100.2"),
        ("192.0.2.11", "198.51.100.1", "192.0.2.11"),
        ("192.0.2.10", "bad", "192.0.2.10"),
        ("192.0.2.10", "198.51.100.1, 198.51.100.2", "192.0.2.10"),
        ("192.0.2.10", "", "192.0.2.10"),
    ],
)
def test_only_explicit_proxy_peer_can_supply_one_address(peer, header, expected):
    from scope_guard_api.client_source import client_source

    settings = Settings(_env_file=None, trusted_proxy_hosts=("192.0.2.10",))
    request = Request(
        {
            "type": "http",
            "client": (peer, 1234),
            "headers": [
                (b"x-scope-guard-client-ip", header.encode()),
                (b"x-forwarded-for", b"203.0.113.99"),
            ],
            "app": SimpleNamespace(state=SimpleNamespace(settings=settings)),
        }
    )
    assert asyncio.run(client_source(request)) == expected


def test_default_direct_access_ignores_forwarded_addresses():
    from scope_guard_api.client_source import client_source

    request = Request(
        {
            "type": "http",
            "client": ("192.0.2.10", 1234),
            "headers": [(b"x-scope-guard-client-ip", b"203.0.113.99")],
            "app": SimpleNamespace(state=SimpleNamespace(settings=Settings(_env_file=None))),
        }
    )
    assert asyncio.run(client_source(request)) == "192.0.2.10"


def test_proxy_dns_refresh_and_failure_do_not_keep_stale_trust(monkeypatch):
    from scope_guard_api.client_source import client_source

    async def run():
        request = Request(
            {
                "type": "http",
                "client": ("192.0.2.10", 1234),
                "headers": [(b"x-scope-guard-client-ip", b"198.51.100.1")],
                "app": SimpleNamespace(
                    state=SimpleNamespace(
                        settings=Settings(_env_file=None, trusted_proxy_hosts=("app",))
                    )
                ),
            }
        )
        current = "192.0.2.10"

        async def lookup(*args, **kwargs):
            if current is None:
                raise OSError("synthetic DNS failure")
            return [(2, 1, 6, "", (current, 0))]

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", lookup)
        assert await client_source(request) == "198.51.100.1"
        current = "192.0.2.11"
        assert await client_source(request) == "192.0.2.10"
        current = None
        assert await client_source(request) == "192.0.2.10"

    asyncio.run(run())
