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
    
    # Resend Notifications
    resend_api_key: str = ""
    notification_email: str = "onboarding@resend.dev"  # Default test email for Resend

    # Niche Keywords
    real_estate_keywords_ar: list[str] = [
        "crédito hipotecario Argentina",
        "invertir en propiedades Argentina",
        "comprar departamento Misiones",
        "alquiler vs compra Argentina",
        "UVA hipotecario 2025",
        "propiedades en Posadas Misiones",
        "calculadora crédito hipotecario",
        "ROI inmobiliario Argentina",
        "Banco Nación hipotecario",
        "cómo invertir en inmuebles con poco capital",
    ]

    esg_keywords_latam: list[str] = [
        "NIS30 Mexico empresas",
        "SFDR compliance latinoamerica",
        "CBAM carbon border adjustment Mexico",
        "CVM 193 Brasil ESG",
        "reporte de sostenibilidad obligatorio Argentina",
        "calculadora huella de carbono empresa",
        "como medir scope 1 scope 2 scope 3",
        "software ESG pymes latinoamerica",
        "herramienta ESG en español",
        "reporte ESG sin consultora",
    ]


settings = Settings()
