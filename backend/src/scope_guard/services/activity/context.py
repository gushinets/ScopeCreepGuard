"""Per-request trusted browser identity; never an authentication credential."""

from contextvars import ContextVar

browser_key: ContextVar[str | None] = ContextVar("product_browser_key", default=None)
