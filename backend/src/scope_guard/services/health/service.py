from scope_guard.services.health.ports import DatabaseHealth, DatabaseUnavailableError


class HealthService:
    def __init__(self, database: DatabaseHealth | None):
        self.database = database

    async def ready(self) -> bool:
        if self.database is None:
            return False
        try:
            await self.database.check_connection()
            return True
        except DatabaseUnavailableError:
            return False
