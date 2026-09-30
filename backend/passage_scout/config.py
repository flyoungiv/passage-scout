from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    tavily_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-20b"
    live_access_token: SecretStr = SecretStr("")
    tavily_monthly_credits: int = Field(1000, gt=0)
    groq_requests_per_minute: int = Field(30, gt=0)
    groq_requests_per_day: int = Field(1000, gt=0)
    groq_tokens_per_minute: int = Field(8000, gt=0)
    groq_tokens_per_day: int = Field(200000, gt=0)
    max_document_chars: int = Field(100000, ge=1000, le=500000)
    max_upload_bytes: int = Field(5_000_000, ge=1000, le=10_000_000)
    max_pdf_pages: int = Field(30, ge=1, le=100)
    provider_timeout_seconds: float = Field(25, gt=0, le=60)

    @property
    def live_ready(self) -> bool:
        return bool(self.tavily_api_key.get_secret_value() and self.groq_api_key.get_secret_value())


@lru_cache
def settings() -> Settings:
    return Settings()
