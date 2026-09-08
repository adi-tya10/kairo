from functools import lru_cache
from pathlib import Path

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
