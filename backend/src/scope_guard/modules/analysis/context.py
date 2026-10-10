from uuid import UUID

from scope_guard.modules.analysis.domain import (
    ABSENT,
    DraftProofBinding,
    GenerationContext,
    GenerationError,
    HistoricalSelector,
    thaw,
)
from scope_guard.modules.drafts.generation_context import from_draft, overlay


def project_context(project) -> GenerationContext:
    card = project.card
    terms = card.pricing
    return GenerationContext(
        str(project.id),
        card.name,
        card.client.value if card.client.supplied else ABSENT,
        str(card.industry),
        card.scope.text,
        card.dates.start.value if card.dates.start else None,
        str(terms.model) if terms.model else None,
        str(terms.currency) if terms.currency else None,
        format(terms.hourly_rate, ".2f") if terms.hourly_rate is not None else None,
        format(terms.fixed_price, ".2f") if terms.fixed_price is not None else None,
    )


async def historical_context(
    work,
    proofs,
    owner: str,
    current: GenerationContext,
    request: str,
    selector: HistoricalSelector,
    locale: str,
) -> GenerationContext:
    try:
        if selector.draft_id != ABSENT:
            if not isinstance(selector.draft_id, str):
                raise ValueError
            draft = await work.drafts.get_owned(UUID(owner), UUID(selector.draft_id))
            if draft is None or draft.project_id != current.project_id or draft.request != request:
                raise ValueError
            return from_draft(current, draft)
        if selector.proof != ABSENT:
            proof_locale = selector.locale if selector.locale in ("en", "ru") else locale
            claims = proofs.verify(
                selector.proof, DraftProofBinding(owner, current.project_id, request, proof_locale)
            )
            return overlay(
                current,
                claims.project_snapshot,
                thaw(claims.project_snapshot).get("clientName") or "",
            )
        return current
    except (ValueError, TypeError, AttributeError, KeyError):
        raise GenerationError("draftProofInvalid") from None
