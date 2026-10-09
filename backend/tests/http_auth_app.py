"""Test-only HTTP application with the frozen compatibility clock."""

import os
import time

from scope_guard.core.config import Settings
from scope_guard.main import create_app

app = create_app(
    Settings(_env_file=None),
    clock=time.time if os.environ.get("SCG_AUTH_REALTIME") == "1" else lambda: 1791622800,
)

if __name__ == "__main__":
    import sys

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(sys.argv[1]),
        loop="scope_guard.infrastructure.database.session:event_loop",
    )
