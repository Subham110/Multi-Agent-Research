from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = "ResearchMesh AI"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    SECRET_KEY: str = "development-only-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALLOW_REGISTRATION: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    DATABASE_URL: str = "postgresql+psycopg://research:research@localhost:5432/research"
    REDIS_URL: str = "redis://localhost:6379/0"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    EMBEDDING_DIMENSION: Literal[768] = 768

    MAX_RESEARCH_SOURCES: int = Field(default=12, ge=3, le=30)
    MAX_PAPERS: int = Field(default=5, ge=0, le=10)
    MAX_PDF_BYTES: int = Field(default=15_000_000, ge=1_000_000, le=50_000_000)
    MAX_AGENT_REFLECTIONS: int = Field(default=2, ge=0, le=4)
    MAX_CRITIC_REVISIONS: int = Field(default=2, ge=0, le=4)
    DEFAULT_RESEARCH_DEPTH: Literal["quick", "standard", "deep"] = "standard"
    MAX_ACTIVE_JOBS_PER_USER: int = Field(default=3, ge=1, le=20)

    BOOTSTRAP_TENANT_SLUG: str = "default"
    BOOTSTRAP_TENANT_NAME: str = "Default Research Team"
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@example.com"
    BOOTSTRAP_ADMIN_PASSWORD: str = "Change-This-Password-Now"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def validate_production(self) -> None:
        if self.ENVIRONMENT != "production":
            return
        if self.SECRET_KEY in {"development-only-change-me", "change-me"} or len(self.SECRET_KEY) < 32:
            raise RuntimeError("A strong SECRET_KEY is required in production")
        if self.ALLOW_REGISTRATION:
            raise RuntimeError("ALLOW_REGISTRATION must be false in production")
        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required")
        if any("localhost" in origin for origin in self.CORS_ORIGINS):
            raise RuntimeError("Production CORS_ORIGINS cannot contain localhost")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings


settings = get_settings()
