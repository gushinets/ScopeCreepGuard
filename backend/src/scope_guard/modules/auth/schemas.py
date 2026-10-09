from uuid import UUID

from pydantic import StrictStr

from scope_guard.core.contracts import WireModel


class UserResponse(WireModel):
    id: UUID
    email: StrictStr
