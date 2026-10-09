"""Integration tests own their PostgreSQL server; application settings are never targets."""

import asyncio
import sys

import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def pytest_addoption(parser):
    parser.addoption(
        "--require-integration", action="store_true", help="Fail if integration cannot run"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--require-integration") and not any(
        item.get_closest_marker("integration") for item in items
    ):
        raise pytest.UsageError("--require-integration requires collected PostgreSQL tests")


@pytest.fixture(scope="session")
def postgres_server():
    from integration.support import DisposablePostgres

    with DisposablePostgres() as server:
        yield server


@pytest.fixture
def disposable_url(postgres_server):
    with postgres_server.database() as url:
        yield url
