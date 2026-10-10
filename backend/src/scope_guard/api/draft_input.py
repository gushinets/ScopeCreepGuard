"""Ordered compatibility parsers; decoded JSON never crosses the use-case port."""

from dataclasses import dataclass
from uuid import UUID

from scope_guard.core.js_compat import date_parse_finite, js_string, stringify, trim, utf16_length
from scope_guard.infrastructure.auth.draft_proofs import UUID_PATTERN
from scope_guard.infrastructure.llm.language import normalize_language
from scope_guard.modules.analysis.domain import ABSENT, Absent, DraftProofClaims, Replies, thaw
from scope_guard.modules.analysis.normalization import labels, parse_materials, parse_snapshot
from scope_guard.modules.analysis.serialization import analysis_to_wire
from scope_guard.modules.drafts.domain import PROTECTED_FIELDS
from scope_guard.modules.drafts.serialization import EDITOR_FIELDS
from scope_guard.modules.drafts.values import (
    CreateDraft,
    DraftDocument,
    EditableChangeOrder,
    JsonObject,
    ProjectDetails,
    ReplyDocument,
    freeze_json,
    freeze_object,
    thaw_json,
)

MAX_DRAFT_BYTES = 1_000_000


def size(value: object) -> None:
    if len(stringify(value).encode("utf-8")) > MAX_DRAFT_BYTES:
        raise ValueError("invalid_draft_document")


def obj(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("invalid_draft_document")
    return value


def text(value: object, empty: bool = True) -> str:
    if (
        not isinstance(value, str)
        or utf16_length(value) > 100_000
        or (not empty and not trim(value))
    ):
        raise ValueError("invalid_draft_document")
    return value


@dataclass(frozen=True, slots=True)
class DraftEnvelope:
    project_id: str
    idempotency_key: str
    request: str
    locale: str


def parse_envelope(value: object) -> DraftEnvelope:
    size(value)
    raw = obj(value)
    for key in ("projectId", "idempotencyKey"):
        if not isinstance(raw.get(key), str) or not UUID_PATTERN.fullmatch(raw[key]):
            raise ValueError("invalid_draft_document")
    if raw.get("locale") not in ("en", "ru"):
        raise ValueError("invalid_draft_document")
    return DraftEnvelope(
        raw["projectId"],
        raw["idempotencyKey"],
        trim(text(raw.get("request"), False)),
        raw["locale"],
    )


def parse_editor(value: object) -> EditableChangeOrder:
    raw = obj(value)
    language = normalize_language(raw.get("language"))
    translated = labels(raw.get("changeOrderLabels"))
    if (
        not language
        or ("changeOrderLabels" in raw and translated == ABSENT)
        or (language.split("-")[0] not in ("ru", "en", "es") and translated == ABSENT)
    ):
        raise ValueError("invalid_draft_document")
    if (
        js_string(raw.get("currency", ABSENT)) not in ("", "RUB", "USD", "EUR")
        or type(raw.get("noAdditionalCharge")) is not bool
    ):
        raise ValueError("invalid_draft_document")
    fields = {field: text(raw.get(key)) for key, field in EDITOR_FIELDS}
    if not date_parse_finite(fields["created_at"]):
        raise ValueError("invalid_draft_document")
    ai_values: tuple[tuple[str, str], ...] | Absent = ABSENT
    if "aiValues" in raw:
        values = obj(raw["aiValues"])
        if any(
            key
            not in (
                "description",
                "estimatedHours",
                "additionalCost",
                "currency",
                "timelineImpact",
                "rationale",
                "note",
            )
            for key in values
        ):
            raise ValueError("invalid_draft_document")
        ai_values = tuple((key, text(value)) for key, value in values.items())
    return EditableChangeOrder(
        **fields,
        language=language,
        currency=freeze_json(raw["currency"]),
        no_additional_charge=raw["noAdditionalCharge"],
        reference=text(raw["reference"]) if "reference" in raw else ABSENT,
        labels=translated,
        ai_values=ai_values,
    )


def parse_document(value: object, locale: str, snapshot: JsonObject) -> DraftDocument:
    size(value)
    raw = obj(value)
    if type(raw.get("version")) not in (int, float) or raw["version"] != 1:
        raise ValueError("invalid_draft_document")
    result = parse_snapshot(raw.get("result"), locale)
    candidate, original = analysis_to_wire(result), thaw_json(snapshot)
    for field in PROTECTED_FIELDS:
        if (field in candidate) != (field in original) or (
            field in candidate and stringify(candidate[field]) != stringify(original[field])
        ):
            raise ValueError("immutable_analysis")
    reply, details = obj(raw.get("reply")), obj(raw.get("projectDetails"))
    if js_string(reply.get("tone", ABSENT)) not in ("warm", "neutral", "firm"):
        raise ValueError("invalid_draft_document")
    generated = obj(reply.get("generated"))
    if "clientMaterials" not in raw or "changeOrder" not in raw:
        raise ValueError("invalid_draft_document")
    return DraftDocument(
        result,
        parse_materials(raw["clientMaterials"]) if raw["clientMaterials"] is not None else None,
        parse_editor(raw["changeOrder"]) if raw["changeOrder"] is not None else None,
        ReplyDocument(
            freeze_json(reply["tone"]),
            text(reply.get("text")),
            Replies(*(text(generated.get(tone)) for tone in ("warm", "neutral", "firm"))),
        ),
        ProjectDetails(
            *(text(details.get(key)) for key in ("clientName", "clientEmail", "endDate"))
        ),
    )


def verified_command(
    envelope: DraftEnvelope, document: object, claims: DraftProofClaims
) -> CreateDraft:
    snapshot = freeze_object(analysis_to_wire(claims.analysis_snapshot))
    return CreateDraft(
        UUID(envelope.project_id),
        UUID(envelope.idempotency_key),
        envelope.request,
        envelope.locale,
        snapshot,
        freeze_object(thaw(claims.project_snapshot)),
        parse_document(document, envelope.locale, snapshot),
    )
