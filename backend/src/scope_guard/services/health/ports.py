from typing import Protocol


class DatabaseUnavailableError(Exception):
    def __init__(self):
        super().__init__("database_unavailable")


class DatabaseHealth(Protocol):
    async def check_connection(self) -> None: ...
