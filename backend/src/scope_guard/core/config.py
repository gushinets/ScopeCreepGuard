from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCOPE_GUARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    allowed_origins: tuple[str, ...] = ()
    auth_secret: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SCOPE_GUARD_AUTH_SECRET", "AUTH_SECRET")
    )
    production: bool = False
    workflow_v2: bool = False
    llm_workflow: bool = False
    worker_role: Literal["exports", "llm"] = "exports"
    llm_max_cost: Decimal = Field(default=Decimal("1.00"), gt=0, le=100)
    llm_input_rate_bound: Decimal | None = Field(default=None, gt=0)
    llm_output_rate_bound: Decimal | None = Field(default=None, gt=0)
    export_bucket: str | None = None
    export_endpoint: str | None = None
    export_region: str = "us-east-1"
    export_retention_days: int | None = Field(default=None, ge=1)
    export_access_key: SecretStr | None = None
    export_secret_key: SecretStr | None = None
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SCOPE_GUARD_OPENAI_API_KEY", "OPENAI_API_KEY")
    )
    openai_model: str = Field(
        default="gpt-6-luna",
        validation_alias=AliasChoices("SCOPE_GUARD_OPENAI_MODEL", "OPENAI_MODEL"),
    )

    @field_validator("openai_model")
    @classmethod
    def validate_openai_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("openai_model must not be empty or whitespace-only")
        return value

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or value != f"{parsed.scheme}://{parsed.netloc}"
            ):
                raise ValueError("invalid_allowed_origin")
        return values

    database_url: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SCOPE_GUARD_DATABASE_URL", "DATABASE_URL")
    )

    public_app_url: str | None = None

    @model_validator(mode="after")
    def validate_public_app_url(self):
        if self.public_app_url is None:
            return self
        url = urlsplit(self.public_app_url)
        _ = url.port  # Reject malformed and out-of-range ports at configuration time.
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
            or any(ord(c) < 33 for c in self.public_app_url)
            or (url.scheme == "http" and (self.production or not local))
        ):
            raise ValueError("invalid_public_app_url")
        self.public_app_url = self.public_app_url.rstrip("/")
        return self

    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_sender_address: str = "no-reply-scopecreepguard@mail.com"
    smtp_sender_name: str | None = "ScopeCreepGuard"
    smtp_transport: Literal["none", "starttls", "tls"] = "none"
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_timeout: float = Field(default=10, gt=0, le=120, allow_inf_nan=False)
    smtp_deadline: float = Field(default=30, gt=0, le=300, allow_inf_nan=False)
