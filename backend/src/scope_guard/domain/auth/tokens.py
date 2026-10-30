from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Purpose = Literal["verify_email", "reset_password"]


class InvalidAuthToken(Exception):
    def __init__(self):
        super().__init__("invalid_auth_token")


@dataclass(frozen=True)
class IssuedAuthToken:
    raw: str = field(repr=False)
    expires_at: datetime
