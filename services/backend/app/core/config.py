"""Application settings, loaded from environment / .env (12-factor, no secrets in code)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Default is a local SQLite file so the app/tests run with zero infra.
    # docker compose overrides this with the PostgreSQL URL.
    DATABASE_URL: str = "sqlite+pysqlite:///./breachatlas.db"

    # Comma-separated allowed CORS origins.
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    # Public read API rate limit (requests per minute per client IP).
    API_RATE_LIMIT: int = 60

    # local | ci | production
    APP_ENV: str = "local"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
