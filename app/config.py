from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pixelwave Radio"
    database_url: str = "postgres://pradio@localhost:5432/pradio"
    jamendo_client_id: str
    audius_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webhook_secret: str = ""
    public_base_url: str = "https://pixelwave.dev"
    secret_key: str
    admin_username: str = "admin"
    admin_password: str
    track_cache_target: int = 1000
    jamendo_page_size: int = 200
    refresh_pages: int = 1
    track_cache_ttl_hours: int = 24

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
