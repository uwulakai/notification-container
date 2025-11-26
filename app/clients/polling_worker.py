import asyncio

from app.origin_clients.base_client import BaseOriginClient
from app.clients.rabbit.client import RabbitProducerClient
from app.clients.redis.redis_client import RedisRateLimiter
from app.logger import logger


class PollingWorker:
    def __init__(
        self,
        client: BaseOriginClient,
        publisher: RabbitProducerClient,
        redis_client: RedisRateLimiter,
        update_queue: str,
        backoff_sec: float,
    ):
        self.client = client
        self.publisher = publisher
        self.redis_client = redis_client
        self.is_running = False
        self.update_queue = update_queue
        self.backoff_sec = backoff_sec

    async def start(self):
        self.is_running = True
        await self.client.create_client()

        try:
            while self.is_running:
                await self.redis_client.wait_for_service("tamtam")
                logger.info(f"Бот {self.client.token[-5:-1]} делает запрос...")
                update = await self.client.get_updates()
                if update:
                    await self.publisher.send(update, self.update_queue)
        except asyncio.CancelledError:
            pass
        finally:
            await self.client.close_client()
