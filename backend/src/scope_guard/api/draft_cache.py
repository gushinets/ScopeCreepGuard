from starlette.types import ASGIApp, Message, Receive, Scope, Send


class DraftReadCacheMiddleware:
    """Also covers authentication/dependency failures and generic error responses."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        private = (
            scope["type"] == "http"
            and scope["method"] == "GET"
            and (path == "/api/drafts" or path.startswith("/api/drafts/"))
        )

        async def output(message: Message) -> None:
            if private and message["type"] == "http.response.start":
                message = {
                    **message,
                    "headers": [
                        (key, value)
                        for key, value in message["headers"]
                        if key.lower() != b"cache-control"
                    ]
                    + [(b"cache-control", b"private, no-store")],
                }
            await send(message)

        await self.app(scope, receive, output)
