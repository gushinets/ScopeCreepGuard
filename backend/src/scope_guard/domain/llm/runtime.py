import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

PROMPT_VERSION = "workflow-v3"


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, default=str)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


@dataclass(frozen=True)
class Binding:
    operation_id: UUID
    step_id: UUID
    epoch: int
    model: str
    effort: str
    semantic_start: int = 0
    deadline: datetime | None = None
    transport_start: int = 0


@dataclass(frozen=True)
class ProviderRequest:
    binding: Binding
    semantic_attempt: int
    messages: list[dict]
    schema: dict
    schema_name: str
    timeout: float
    max_output_tokens: int = 4096


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model: str | None = None
    provider: str | None = None
    response_id: str | None = None
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None
    reported_cost: Decimal | None = None
    status: str = "completed"


class GatewayFailure(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
