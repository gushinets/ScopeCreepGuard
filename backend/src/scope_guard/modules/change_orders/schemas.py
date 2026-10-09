import re
from datetime import datetime
from typing import Literal

from langcodes import Language
from pydantic import StrictBool, StrictStr, create_model, field_validator, model_validator

from scope_guard.core.contracts import Currency, Text, WireModel, language_tag

LABEL_KEYS = (
    "title",
    "draft",
    "documentNumber",
    "created",
    "project",
    "provider",
    "client",
    "clientEmail",
    "requestedChange",
    "commercialTerms",
    "estimatedEffort",
    "additionalFee",
    "noAdditionalCharge",
    "scheduleImpact",
    "additionalTerms",
    "approval",
    "approvedBy",
    "date",
    "draftFooter",
    "introduction",
    "outsideScopeFree",
    "endDate",
    "rationale",
    "terms",
    "note",
    "page",
    "hours",
)
SUPPORTED_LANGUAGES = {
    "ru",
    "en",
    "es",
    "de",
    "fr",
    "it",
    "nl",
    "pl",
    "pt",
    "tr",
    "uk",
    "bg",
    "el",
    "cs",
    "sk",
    "hr",
    "ro",
    "hu",
    "fi",
    "sv",
    "da",
    "nb",
    "et",
    "lv",
    "lt",
    "id",
}


class LabelBase(WireModel):
    @field_validator("*", mode="before")
    @classmethod
    def validate_label(cls, value):
        if not isinstance(value, str) or not value.strip() or len(value) > 1500:
            raise ValueError("invalid_labels")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value):
            raise ValueError("invalid_labels")
        return value.strip()


ChangeOrderLabels = create_model(
    "ChangeOrderLabels", __base__=LabelBase, **{key: (StrictStr, ...) for key in LABEL_KEYS}
)


class Replies(WireModel):
    warm: Text
    neutral: Text
    firm: Text


class ClientChangeOrderText(WireModel):
    description: Text
    timeline_impact: Text
    rationale: Text
    note: Text


class ClientMaterials(WireModel):
    client_language: StrictStr
    replies: Replies
    change_order: ClientChangeOrderText | None = None
    change_order_labels: ChangeOrderLabels | None = None

    @field_validator("client_language")
    @classmethod
    def supported_tag(cls, value):
        # Keep explicit script subtags; standardize_tag would remove defaults.
        # This normalizes casing and registered aliases before font restrictions.
        raw = language_tag(value)
        value = Language.get(raw).to_tag()
        match = re.fullmatch(r"([a-z]{2,3})(?:-([A-Z][a-z]{3}))?(?:-[A-Z]{2}|-\d{3})?", value)
        if not match or match[1] not in SUPPORTED_LANGUAGES:
            raise ValueError("unsupported_language")
        script = (
            "Cyrl" if match[1] in {"ru", "uk", "bg"} else "Grek" if match[1] == "el" else "Latn"
        )
        if match[2] and match[2] != script:
            raise ValueError("unsupported_language")
        # Intl/CLDR selects successors of these obsolete regions by language.
        # Langcodes uses RU universally; retain the frontend's supported subset.
        old_region = raw.rsplit("-", 1)[-1].upper()
        if old_region in {"SU", "810", "172"}:
            successors = {"uk": "UA"}
            if old_region != "172":
                successors.update(et="EE", lv="LV", lt="LT")
            value = value.rsplit("-", 1)[0] + "-" + successors.get(match[1], "RU")
        return value

    @model_validator(mode="after")
    def validate_materials(self):
        if (
            self.client_language.split("-")[0] not in {"en", "ru", "es"}
            and not self.change_order_labels
        ):
            raise ValueError("labels_required")
        if any(not value.strip() for value in self.replies.model_dump().values()):
            raise ValueError("empty_reply")
        if self.change_order and any(
            not value.strip()
            for key, value in self.change_order.model_dump().items()
            if key != "rationale"
        ):
            raise ValueError("empty_client_text")
        return self


class EditableChangeOrder(WireModel):
    reference: Text | None = None
    created_at: Text
    language: StrictStr
    change_order_labels: ChangeOrderLabels | None = None
    project_name: Text
    description: Text
    estimated_hours: Text
    additional_cost: Text
    currency: Currency | Literal[""]
    timeline_impact: Text
    rationale: Text
    note: Text
    provider_name: Text
    client_name: Text
    client_email: Text
    end_date: Text
    additional_terms: Text
    client_approver_name: Text
    approval_date: Text
    no_additional_charge: StrictBool
    ai_values: (
        dict[
            Literal[
                "description",
                "estimatedHours",
                "additionalCost",
                "currency",
                "timelineImpact",
                "rationale",
                "note",
            ],
            Text,
        ]
        | None
    ) = None

    @field_validator("created_at")
    @classmethod
    def timestamp(cls, value):
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @field_validator("language")
    @classmethod
    def tag(cls, value):
        return language_tag(value)

    @model_validator(mode="after")
    def labels_for_language(self):
        if self.language.split("-")[0] not in {"ru", "en", "es"} and not self.change_order_labels:
            raise ValueError("labels_required")
        return self
