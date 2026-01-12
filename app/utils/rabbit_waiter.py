from faststream.rabbit import RabbitBroker
import asyncio

from app.logger import logger
from app.config import settings

MAX_RETRIES = 10
RETRY_DELAY = 5


async def wait_for_rabbit():
    """Ждем, пока RabbitMQ станет доступен."""
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info("Ожидаем, пока RabbitMQ запустится и станет доступен...")
        try:
            broker = RabbitBroker(url=settings.rabbit.RABBIT_URL.get_secret_value())
            await broker.connect()
            logger.info("RabbitMQ доступен — продолжаем запуск приложения")
            await broker.stop()
            return
        except Exception as e:
            logger.warning(
                f"RabbitMQ недоступен (попытка {attempt}/{MAX_RETRIES}): {e}"
            )
            await asyncio.sleep(RETRY_DELAY)
    raise RuntimeError("Не удалось подключиться к RabbitMQ после нескольких попыток")
