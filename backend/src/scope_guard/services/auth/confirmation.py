"""Delivery orchestration; each port finishes its transaction before returning."""

from uuid import UUID

from scope_guard.domain.auth.validation import AuthError
from scope_guard.services.email.contracts import EmailError


class ResendLimited(AuthError):
    def __init__(self, retry_after: int):
        super().__init__("errors.emailResendLimited", 429)
        self.retry_after = retry_after


class ConfirmationService:
    def __init__(self, attempts, tokens, email, public_url: str):
        self.attempts, self.tokens, self.email = attempts, tokens, email
        self.public_url = public_url

    async def send(self, user: dict, locale: str, source: str) -> dict:
        if not self.public_url:
            raise AuthError("errors.requestFailed", 503)
        user_id = UUID(user["id"])
        attempt = await self.attempts.reserve(user_id, source)
        # Reserved attempts default to unknown: cancellation or process death is
        # recoverable and cannot assert non-delivery or free another attempt.
        status = "unknown"
        try:
            token = await self.tokens.issue_pending_confirmation(user_id)
            url = f"{self.public_url}/confirm-email#userId={user_id}&token={token.raw}"
            await self.email.send_confirmation(user["email"], url, locale)
            status = "accepted"
        except EmailError as error:
            status = "unknown" if error.category == "ambiguous" else "failed"
        await self.attempts.finish(attempt, status)
        return await self.attempts.status(user_id, source)
