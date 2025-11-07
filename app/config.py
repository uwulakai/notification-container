from typing import List

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    RABBITMQ_HOST: str = "polling_rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: SecretStr
    RABBITMQ_PASS: SecretStr

    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_BACKOFF_SEC: int = 5

    RABBITMQ_NOTIFICATIONS_QUEUE: str = "notifications"

    @computed_field
    @property
    def RABBIT_URL(self) -> SecretStr:
        return SecretStr(
            f"amqp://{self.RABBITMQ_USER.get_secret_value()}:{self.RABBITMQ_PASS.get_secret_value()}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
        )


class LoggingSettings(BaseSettingsConfig):
    """Настройки логирования"""

    LOGGING_LEVEL: LoggingLevel = LoggingLevel.INFO
    LOGGING_SERIALIZE: bool = True
    LOGGING_ENABLE_MODULES: str = " "
    LOGGING_DISABLE_MODULES: str = ""


class TamTamSettings(BaseSettingsConfig):
    """Настройки TamTam"""

    TAM_TAM_TOKENS_STR: SecretStr = ""
    TAM_TAM_MAX_POLLING_BOTS: int = 10
    TAM_TAM_BACKOFF_SEC: float = 0.05

    @computed_field
    @property
    def TAM_TAM_TOKENS(self) -> List[SecretStr]:
        return [
            SecretStr(token.strip())
            for token in self.TAM_TAM_TOKENS_STR.get_secret_value().split(",")
            if token.strip()
        ]


class RedisSettings(BaseSettingsConfig):
    """Настройки для подключения к Redis"""

    REDIS_URL: SecretStr


class Settings(BaseSettings):
    """Общий класс настроек"""

    rabbit: RabbitMQSettings = RabbitMQSettings()
    logging: LoggingSettings = LoggingSettings()
    tam_tam: TamTamSettings = TamTamSettings()
    redis: RedisSettings = RedisSettings()


settings = Settings()
