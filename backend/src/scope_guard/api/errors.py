"""HTTP compatibility boundary. Business modules must not return HTTP responses."""

import json
import logging
from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ErrorCode(StrEnum):
    request_body_invalid = "errors.requestBodyInvalid"
    request_failed = "errors.requestFailed"
    auth_required = "errors.authRequired"
    email_required = "errors.emailRequired"
    password_required = "errors.passwordRequired"
    invalid_email = "errors.invalidEmail"
    password_too_short = "errors.passwordTooShort"
    duplicate_email = "errors.duplicateEmail"
    invalid_credentials = "errors.invalidCredentials"
    project_not_found = "errors.projectNotFound"
    project_name_required = "errors.projectNameRequired"
    scope_required = "errors.scopeRequired"
    industry_invalid = "errors.industryInvalid"
    client_invalid = "errors.clientInvalid"
    start_date_invalid = "errors.startDateInvalid"
    pricing_model_invalid = "errors.pricingModelInvalid"
    currency_invalid = "errors.currencyInvalid"
    hourly_rate_invalid = "errors.hourlyRateInvalid"
    fixed_price_invalid = "errors.fixedPriceInvalid"
    history_date_invalid = "errors.historyDateInvalid"
    request_required = "errors.requestRequired"
    verdict_invalid = "errors.verdictInvalid"
    summary_required = "errors.summaryRequired"
    locale_invalid = "errors.localeInvalid"
    client_language_unsupported = "errors.clientLanguageUnsupported"
    analysis_unavailable = "errors.analysisUnavailable"
    analysis_failed = "errors.analysisFailed"
    analysis_invalid = "errors.analysisInvalid"
    analysis_input_too_large = "errors.analysisInputTooLarge"
    analysis_rate_limited = "errors.analysisRateLimited"
    draft_proof_invalid = "errors.draftProofInvalid"
    draft_not_found = "errors.draftNotFound"
    draft_save_failed = "errors.draftSaveFailed"
    draft_load_failed = "errors.draftLoadFailed"
    evaluation_reasoning_required = "errors.evaluationReasoningRequired"
    evaluation_label_invalid = "errors.evaluationLabelInvalid"
    evaluation_history_not_found = "errors.evaluationHistoryNotFound"


class ApiError(Exception):
    def __init__(self, code: ErrorCode, status: int = 400):
        super().__init__(code.value)
        self.code, self.status = code, status


async def read_json_object(request: Request) -> dict:
    try:
        # Python's JSON decoder otherwise accepts NaN/Infinity unlike JSON.parse.
        value = json.loads(await request.body(), parse_constant=_invalid_constant)
    except (ValueError, UnicodeError):
        raise ApiError(ErrorCode.request_body_invalid) from None
    if not isinstance(value, dict):
        raise ApiError(ErrorCode.request_body_invalid)
    return value


def _invalid_constant(_value: str):
    raise ValueError("invalid_json_constant")


def json_error(code: ErrorCode, status: int) -> JSONResponse:
    return JSONResponse({"error": code.value}, status_code=status)


def log_unexpected(error: Exception) -> None:
    logging.getLogger("scope_guard").error(
        "api_unhandled_exception", extra={"exception_type": type(error).__name__}
    )


class UnhandledErrorMiddleware:
    """Catch before Starlette re-raises to the server's raw traceback logger."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracked_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception as error:
            log_unexpected(error)
            if started:
                # Headers already sent: terminate the stream with a sanitized failure.
                raise RuntimeError("api_response_failed") from None
            await json_error(ErrorCode.request_failed, 500)(scope, receive, send)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_request: Request, error: ApiError):
        return json_error(error.code, error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _error: RequestValidationError):
        # Route-specific parsers select the more precise legacy codes/precedence.
        return json_error(ErrorCode.request_body_invalid, 400)

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, error: Exception):
        # Never log exception messages, tracebacks, request bodies or query parameters.
        log_unexpected(error)
        return json_error(ErrorCode.request_failed, 500)
