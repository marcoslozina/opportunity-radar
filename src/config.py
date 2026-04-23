from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./opportunity_radar.db"
    anthropic_api_key: str = ""
    pipeline_schedule: str = "0 8 * * 1"  # lunes 08:00 UTC (cron)

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "opportunity-radar/0.1"

    youtube_api_key: str = ""
    serp_api_key: str = ""
    product_hunt_token: str = ""


settings = Settings()
