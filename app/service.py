import asyncio

from app.clients.polling_worker import PollingWorker
from app.clients.rabbit.provide import get_rabbit_client
from app.config import Settings
from app.origin_clients.tamtam import TamTamClient
from app.clients.redis.redis_client import RedisRateLimiter


async def start_all_workers():
    settings = Settings()

    tasks = []
    for token in settings.tam_tam.TAM_TAM_TOKENS:
        client = TamTamClient(token.get_secret_value())
        publisher = await get_rabbit_client()
        redis_client = RedisRateLimiter(
            settings.redis.REDIS_URL.get_secret_value(), 2, client.origin_type
        )
        await redis_client.connect()
        worker = PollingWorker(
            client,
            publisher,
            redis_client,
            settings.rabbit.RABBITMQ_NOTIFICATIONS_QUEUE,
        )
        tasks.append(asyncio.create_task(worker.start()))

    await asyncio.gather(*tasks)
