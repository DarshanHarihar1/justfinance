"""Application configuration loaded from environment variables.

All settings are validated by Pydantic at startup. ``get_settings`` is cached
so the rest of the app can call it cheaply.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@db:5432/finance",
        description="SQLAlchemy async URL. Prod uses Supavisor on :6543.",
    )
    database_is_pooled: bool = Field(
        default=False,
        description=(
            "True when DATABASE_URL points at Supavisor (or any external pgbouncer-like "
            "pooler). Causes the engine to use NullPool and disable prepared statements."
        ),
    )

    # ── Auth ───────────────────────────────────────────────────────────────
    app_password_hash: str = Field(
        default="$2b$12$replace_this_with_a_real_hash",
        description="bcrypt hash of the shared password. Required in prod.",
    )
    session_secret: str = Field(
        default="dev-only-not-secret-change-me",
        description="Key for signing session cookies. Must be >=32 chars in prod.",
    )
    session_max_age: int = Field(default=60 * 60 * 24 * 30, description="Seconds.")

    # ── OpenRouter ─────────────────────────────────────────────────────────
    openrouter_api_key: str = Field(default="", description="sk-or-v1-...")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_model_categorize: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free"
    )
    openrouter_model_insights: str = Field(default="deepseek/deepseek-r1:free")
    openrouter_app_name: str = Field(default="finance-tracker")
    openrouter_app_url: str = Field(default="http://localhost:5173")

    # ── HTTP ───────────────────────────────────────────────────────────────
    # ``NoDecode`` opts out of pydantic-settings' default JSON parsing for complex
    # types, so a comma-separated string in CORS_ORIGINS is split by the
    # validator below instead of being interpreted as JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"],
    )

    # ── Logging ────────────────────────────────────────────────────────────
    log_format: Literal["console", "json"] = Field(default="console")
    log_level: str = Field(default="INFO")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
