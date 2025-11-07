import asyncio
import time
from typing import Optional
import aioredis

class RedisRateLimiter:
    def __init__(self, redis_url: str, max_requests: int, time_window: int):
        self.redis = aioredis.from_url(redis_url)
        self.max_requests = max_requests
        self.time_window = time_window
        self.key = 'rate_limiter:requests'
            
    async def acquire(self) -> bool:
        current_time = int(time.time())
        window_start = current_time - self.time_window
        
        # Удаляем выолненные запросы
        await self.redis.zremrangebyscore(self.key, 0, window_start)
        
        # Считаем текущие запросы
        current_requests = await self.redis.zcard(self.key)
        
        if current_requests < self.max_requests:
            # Добавляем новый запрос
            self.redis.zadd(self.key, {str(current_time): current_time})
            self.redis.expire(self.key, self.time_window)
            return True
        return False
    
    async def wait_unavailable(self):
        while not await self.acquire():
            self.sleep(0.1)
            
    
            