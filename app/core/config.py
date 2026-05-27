from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://poc:poc@localhost:5432/poc_mqtt"

    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC: str = "machines/events"
    MQTT_CLIENT_ID: str = "poc-backend"
    MQTT_RECONNECT_DELAY: int = 5

    # Application
    LOG_LEVEL: str = "INFO"
    API_TITLE: str = "PoC MQTT FastAPI"
    API_VERSION: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

