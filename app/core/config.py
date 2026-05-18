"""
NexusIoT Platform Configuration
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    SECRET_KEY: str = "nexusiot-secret-change-in-production-please"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nexusiot.db"
    # For production PostgreSQL: postgresql+asyncpg://user:pass@localhost/nexusiot

    # MQTT
    MQTT_ENABLED: bool = True
    MQTT_BROKER_HOST: str = "9728affa3bc64fcc98b13435c136926c.s1.eu.hivemq.cloud"
    MQTT_BROKER_PORT: int = 8883
    MQTT_USERNAME: str = "esp32"
    MQTT_PASSWORD: str = "Maiducvan112@##"
    MQTT_KEEPALIVE: int = 60
    MQTT_CLOUD: str = "https://console.hivemq.cloud/clusters/9728affa3bc64fcc98b13435c136926c?cta_button=serverless&cta_ref=broker_product_page&_gl=1*h4glu1*_ga*MTgyOTM0NjQ4OC4xNzc5MDg3Nzcx*_ga_P96XGQCLE4*czE3NzkwODc3NjgkbzEkZzAkdDE3NzkwODc3NjgkajYwJGwwJGgw*_ga_BNBV6WH6Q5*czE3NzkwODc3NjgkbzEkZzAkdDE3NzkwODc3NjgkajYwJGwwJGgw&__hstc=184124345.7ed5ceff92732fd378faf6007d687a97.1779087771908.1779087771908.1779087771908.1&__hssc=184124345.1.1779087771908&__hsfp=d99741a6eca678a13d14d608e19ce819"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",   # React frontend
        "http://localhost:8080",   # Vue frontend
        "http://localhost:8000",   # Self
        "*",                       # Allow all for dev — restrict in prod!
    ]

    # Data retention
    DATA_RETENTION_DAYS: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
