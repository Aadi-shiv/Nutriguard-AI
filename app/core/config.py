"""
app/core/config.py
Central configuration loader for NutriGuard AI.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_ENV: str = Field(default="development")
    APP_VERSION: str = Field(default="0.1.0")
    LOG_LEVEL: str = Field(default="INFO")
    GROQ_API_KEY: str = Field(...)
    ANTHROPIC_API_KEY: str = Field(default="not_used")
    GEMINI_API_KEY: str = Field(default="not_used")
    RATE_LIMIT_PER_MINUTE: int = Field(default=10)
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_db")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()