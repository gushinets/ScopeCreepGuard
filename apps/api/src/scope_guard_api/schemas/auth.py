from typing import Literal
from uuid import UUID

from pydantic import StrictStr

from scope_guard_api.schemas.shared import WireModel


class UserResponse(WireModel):
    id: UUID
    email: StrictStr

    workspace_access: Literal["allowed", "email_confirmation_required"]
