from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StrictStr

from scope_guard_api.schemas.shared import WireModel

Name = Annotated[StrictStr, Field(max_length=250)]


class ProfilePreferences(WireModel):
    model_config = ConfigDict(extra="forbid")
    locale: Literal["ru", "en"] | None = None
    timezone: Annotated[StrictStr, Field(max_length=100)] | None = None
    preferred_tone: Literal["warm", "neutral", "firm"] | None = None
    default_currency: Literal["RUB", "USD", "EUR"] | None = None


class ProfileChanges(WireModel):
    model_config = ConfigDict(extra="forbid")
    display_name: Name | None = None
    business_name: Name | None = None
    provider_name: Name | None = None
    profession: Name | None = None
    status: Literal["active", "inactive"] = "active"
    preferences: ProfilePreferences = Field(default_factory=ProfilePreferences)


class ProfileUpdate(WireModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    expected_revision: Annotated[StrictStr, Field(pattern=r"^[1-9][0-9]{0,18}$")]
    changes: ProfileChanges


class ProfileView(ProfileChanges):
    id: UUID
    revision: str
    created_at: str
    updated_at: str


class ProfileResponse(WireModel):
    profile: ProfileView
