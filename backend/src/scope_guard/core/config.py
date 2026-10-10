from typing import Literal
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator
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
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("SCOPE_GUARD_OPENAI_API_KEY", "OPENAI_API_KEY")
    )

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
