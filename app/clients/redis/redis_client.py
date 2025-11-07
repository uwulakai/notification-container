import asyncio
from typing import Optional
import redis.asyncio as redis


class RedisRateLimiter:
    def __init__(self, redis_url: str, max_requests: int):
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.key = "rate_limiter:requests"
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Создаёт соединение с Redis (однократно)."""
        if not self.redis:
            self.redis = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

    async def disconnect(self):
        """Закрывает соединение."""
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def acquire(self) -> bool:
        if not self.redis:
            await self.connect()

        # атомарно увеличиваем и получаем новое значение
        count = await self.redis.incr(self.key)

        # если ключ только что создан — задаём TTL
        if count == 1:
            await self.redis.expire(self.key, 1)  # 1 - одна секунда

        # если превышен лимит, отказываем
        return count <= self.max_requests

    async def wait_unavailable(self):
        """Блокирует выполнение, пока не освободится место в лимите."""
        while not await self.acquire():
            await asyncio.sleep(0.1)
