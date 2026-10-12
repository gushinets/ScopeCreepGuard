from uuid import UUID

from pydantic import StrictStr

from scope_guard_api.schemas.shared import WireModel


class UserResponse(WireModel):
    id: UUID
    email: StrictStr
