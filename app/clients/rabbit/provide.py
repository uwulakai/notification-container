from app.config import settings
from app.clients.rabbit.client import RabbitProducerClient


async def get_rabbit_client() -> RabbitProducerClient:
    client = RabbitProducerClient(
        url=settings.rabbit.RABBIT_URL.get_secret_value(),
        max_retries=settings.rabbit.RABBITMQ_MAX_RETRIES,
        backoff_sec=settings.rabbit.RABBITMQ_BACKOFF_SEC,
    )
    await client.start()
    return client
