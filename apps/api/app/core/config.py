import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(ROOT_ENV)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "KAIRO Engine API"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "kairo-development-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:1420", "tauri://localhost"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Support both JSON array syntax and comma-separated string from deployment environments."""
        if isinstance(v, str):
            trimmed = v.strip()
            if trimmed.startswith("[") and trimmed.endswith("]"):
                try:
                    parsed = json.loads(trimmed)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in trimmed.split(",") if origin.strip()]
        return v

    # Supabase / PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/kairo"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Neo4j Graph DB
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "kairo_password"

    # Redis Broker
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM API (Groq / Gemini / OpenAI)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gemini-1.5-pro"
    LLM_TEMPERATURE: float = 0.1

    # Webhook Secrets (HMAC)
    GITHUB_WEBHOOK_SECRET: str = "kairo_github_webhook_secret_local"
    JIRA_WEBHOOK_SECRET: str = "kairo_jira_webhook_secret_local"
    LINEAR_WEBHOOK_SECRET: str = "kairo_linear_webhook_secret_local"
    GITLAB_WEBHOOK_SECRET: str = "kairo_gitlab_webhook_secret_local"
    SLACK_WEBHOOK_URL: str = ""

    # SMTP / Transactional Email (Brevo / Gmail / Standard Relay)
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "adityaeeshan5230@gmail.com"
    SMTP_FROM_NAME: str = "KAIRO Team"
    WEB_APP_URL: str = "http://localhost:3000"

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """
        Enforces strict fail-fast validation in production mode:
        Rejects insecure default keys, wildcard CORS, or missing critical credentials.
        """
        if self.APP_ENV.lower() == "production":
            insecure_keys = [
                "kairo-development-secret-key-change-in-production",
                "secret",
                "changeme",
                "your-secret-key-change-this-in-prod",
            ]
            if self.SECRET_KEY in insecure_keys or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be a cryptographically secure random string (>=32 chars) in production.")

            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard '*' CORS_ORIGINS is forbidden in production.")

            if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_ROLE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required in production.")

            if not self.NEO4J_URI or not self.NEO4J_USER or not self.NEO4J_PASSWORD:
                raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD are required in production.")

            if self.NEO4J_PASSWORD == "kairo_password":
                raise ValueError("Insecure default NEO4J_PASSWORD is forbidden in production.")

            if not self.REDIS_URL:
                raise ValueError("REDIS_URL is required in production for rate limiting and Celery.")

            if self.GITHUB_WEBHOOK_SECRET == "kairo_github_webhook_secret_local":
                raise ValueError("Default GITHUB_WEBHOOK_SECRET is forbidden in production.")
            if self.JIRA_WEBHOOK_SECRET == "kairo_jira_webhook_secret_local":
                raise ValueError("Default JIRA_WEBHOOK_SECRET is forbidden in production.")
            if self.LINEAR_WEBHOOK_SECRET == "kairo_linear_webhook_secret_local":
                raise ValueError("Default LINEAR_WEBHOOK_SECRET is forbidden in production.")
            if self.GITLAB_WEBHOOK_SECRET == "kairo_gitlab_webhook_secret_local":
                raise ValueError("Default GITLAB_WEBHOOK_SECRET is forbidden in production.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
