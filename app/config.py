from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from pathlib import Path

from app.enums.logging import LoggingLevel

class BaseSettingsConfig(BaseSettings):
    """Базовые настройки конфигов"""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

class RabbitMQSettings(BaseSettingsConfig):
    """Настройки для подключения к RabbitMQ"""
    RABBITMQ_HOST: str = "rabbit"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: SecretStr
    RABBITMQ_PASSWORD: SecretStr

    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_BACKOFF_SEC: int = 5

class LoggingSettings(BaseSettingsConfig):
    """Настройки логирования"""

    LOGGING_LEVEL: LoggingLevel = LoggingLevel.INFO
    LOGGING_SERIALIZE: bool = True
    LOGGING_ENABLE_MODULES: str = " "
    LOGGING_DISABLE_MODULES: str = ""
    
class Settings(BaseSettings):
    """Общий класс настроек"""

    rabbit: RabbitMQSettings = RabbitMQSettings()
    logging: LoggingSettings = LoggingSettings()

settings = Settings()