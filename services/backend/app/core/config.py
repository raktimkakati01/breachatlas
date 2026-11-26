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

    # --- Admin sessions ---
    SESSION_COOKIE_NAME: str = "ba_session"
    SESSION_TTL_HOURS: int = 12
    # Login attempts allowed per minute per client IP.
    LOGIN_RATE_LIMIT: str = "10/minute"

    # --- Ingestion (Phase 4) ---
    # The worker calls the isolated fetcher service; it never fetches URLs itself.
    FETCHER_URL: str = "http://fetcher:8001"
    EDGAR_INTERVAL_HOURS: int = 24

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cookie_secure(self) -> bool:
        # Secure cookies require HTTPS; disable only outside production (local http dev).
        return self.APP_ENV == "production"


settings = Settings()
