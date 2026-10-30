"""Explicit baseline-only ASGI fixture; never imported by production composition."""

from historical_auth import HistoricalAuthUnitOfWork
from scope_guard_api import bootstrap
from scope_guard_api.main import create_app

from scope_guard.core.config import Settings


def install_historical_auth():
    bootstrap.AuthUnitOfWork = HistoricalAuthUnitOfWork


def create_historical_app():
    install_historical_auth()
    return create_app(Settings(_env_file=None))
