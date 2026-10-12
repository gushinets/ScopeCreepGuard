from collections.abc import Callable

from scope_guard.domain.analysis.domain import DraftProofBinding, DraftProofClaims
from scope_guard.services.analysis.ports import DraftProofPort


class DraftProofService:
    def __init__(self, factory: Callable[[], DraftProofPort]):
        self.factory = factory

    def verify(self, token: object, binding: DraftProofBinding) -> DraftProofClaims:
        return self.factory().verify(token, binding)
