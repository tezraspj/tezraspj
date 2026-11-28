"""Application settings. All secrets come from environment variables (.env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tezraspj API"
    environment: str = "development"

    # Database (SQLite for local development, PostgreSQL for production)
    database_url: str = "sqlite:///./delivery.db"

    # Delivery pricing (смн)
    delivery_fee: float = 5.0
    free_delivery_threshold: float = 100.0

    # Admin security
    admin_api_token: str = ""
    secret_key: str = ""

    # Telegram notifications (optional)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_api: int = 120        # requests per minute per IP
    rate_limit_orders: int = 10      # POST /api/orders per minute per IP

    # CORS (frontend origins)
    cors_origins: str = "http://localhost:8765,http://localhost:8000,http://127.0.0.1:8765"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
