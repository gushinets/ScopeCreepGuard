from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class WorkflowBoundary(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled=False, llm_enabled=False):
        super().__init__(app)
        self.enabled = enabled
        self.llm_enabled = llm_enabled

    async def dispatch(self, request, call_next):
        path = request.url.path
        headers = {"Cache-Control": "private, no-store"}
        if (
            self.enabled
            and path.startswith("/api/")
            and not path.startswith(("/api/v2/", "/api/auth/"))
            and path not in ("/api/locale", "/api/scope/extract", "/api/evaluations/export")
            and not (
                self.llm_enabled
                and path
                in (
                    "/api/analyze",
                    "/api/replies/regenerate",
                    "/api/client-materials/language",
                    "/api/change-orders/estimate",
                )
            )
        ):
            return JSONResponse({"error": "errors.clientUpgradeRequired"}, 426, headers=headers)
        if path.startswith("/api/v2/") and not self.enabled:
            return JSONResponse({"error": "errors.workflowUnavailable"}, 503, headers=headers)
        response = await call_next(request)
        if path.startswith("/api/v2/"):
            response.headers.update(headers)
        return response
