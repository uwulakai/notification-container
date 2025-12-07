import asyncio
import time
from typing import Optional, Tuple
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.metrics import (
    REDIS_OPERATIONS,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WAIT_TIME,
    CONNECTION_STATUS,
)
from app.enums.polling_workers import OriginType
from app.logger import logger


class RedisRateLimiter:
    def __init__(
        self,
        redis_url: str,
        max_requests_per_service: int,
        origin_type: OriginType,
        window_seconds: int = 1,
    ):
        self.redis_url = redis_url
        self.max_requests_per_service = (
            max_requests_per_service  # Общий лимит для сервиса (IP)
        )
        self.window_seconds = window_seconds
        self.key_prefix = "rate_limiter"
        self.redis: Optional[redis.Redis] = None
        self._script_sha: Optional[str] = None

        self.origin_type = origin_type

    async def connect(self):
        """Создаёт соединение с Redis и загружает Lua-скрипт."""
        if not self.redis:
            try:
                self.redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                await self._load_lua_script()
                CONNECTION_STATUS.labels(
                    origin_type=self.origin_type, service="redis"
                ).set(1)
                REDIS_OPERATIONS.labels(
                    origin_type=self.origin_type, operation="connect", status="success"
                ).inc()
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                CONNECTION_STATUS.labels(
                    origin_type=self.origin_type, service="redis"
                ).set(0)
                REDIS_OPERATIONS.labels(
                    origin_type=self.origin_type, operation="connect", status="error"
                ).inc()
                raise

    async def _load_lua_script(self):
        """Загружает Lua-скрипт для атомарного rate limiting по сервису."""
        lua_script = """
        local key = KEYS[1]
        local max_requests = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        
        -- Удаляем старые записи вне временного окна
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
        
        -- Получаем текущее количество запросов
        local current = redis.call('ZCARD', key)
        
        if current < max_requests then
            -- Добавляем новый запрос с временной меткой
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window)
            return {1, max_requests - current - 1}  -- allowed, remaining
        else
            -- Получаем время самого старого запроса для расчета времени ожидания
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            if oldest and #oldest >= 2 then
                local wait_time = window - (now - tonumber(oldest[2]))
                return {0, math.ceil(wait_time)}  -- denied, wait_time
            else
                return {0, window}  -- denied, fallback wait time
            end
        end
        """

        try:
            self._script_sha = await self.redis.script_load(lua_script)
            logger.info("Lua script loaded successfully")
        except RedisError as e:
            logger.error(f"Failed to load Lua script: {e}")
            self._script_sha = None

    async def acquire_for_service(self, service: str) -> Tuple[bool, int]:
        """
        Rate limiting для конкретного сервиса (tamtam, telegram, etc).
        Все боты одного сервиса делят общий лимит.

        Returns:
            Tuple[bool, int]: (allowed, remaining_requests_or_wait_time)
        """
        RATE_LIMIT_REQUESTS.labels(origin_type=self.origin_type, action="acquire").inc()
        if not self.redis:
            await self.connect()

        key = f"{self.key_prefix}:service:{service}"
        current_time = time.time()

        try:
            if self._script_sha:
                result = await self.redis.evalsha(
                    self._script_sha,
                    1,  # количество ключей
                    key,
                    self.max_requests_per_service,
                    self.window_seconds,
                    current_time,
                )
                allowed, remaining = bool(result[0]), int(result[1])
                REDIS_OPERATIONS.labels(
                    origin_type=self.origin_type,
                    operation="rate_limit_check",
                    status="success",
                ).inc()
                return allowed, remaining
            else:
                return await self._acquire_fallback(key, current_time)

        except RedisError as e:
            logger.error(f"Redis error in acquire_for_service: {e}")
            REDIS_OPERATIONS.labels(
                origin_type=self.origin_type,
                operation="rate_limit_check",
                status="error",
            ).inc()
            return True, self.max_requests_per_service - 1
        finally:
            duration = time.time() - current_time
            RATE_LIMIT_WAIT_TIME.labels(origin_type=self.origin_type).observe(duration)

    async def _acquire_fallback(
        self, key: str, current_time: float
    ) -> Tuple[bool, int]:
        """Fallback реализация через pipeline"""
        async with self.redis.pipeline(transaction=True) as pipe:
            try:
                pipe.zremrangebyscore(key, 0, current_time - self.window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.expire(key, self.window_seconds)

                results = await pipe.execute()
                current_count = results[1]

                if current_count <= self.max_requests_per_service:
                    return True, self.max_requests_per_service - current_count - 1
                else:
                    oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        wait_time = self.window_seconds - (current_time - oldest[0][1])
                        return False, max(1, int(wait_time))
                    return False, self.window_seconds

            except RedisError as e:
                logger.error(f"Fallback rate limit error: {e}")
                return True, self.max_requests_per_service - 1

    async def wait_for_service(self, service: str):
        """
        Умное ожидание для конкретного сервиса.
        Все боты этого сервиса будут ждать вместе когда освободится место в общем лимите.
        """
        RATE_LIMIT_REQUESTS.labels(origin_type=self.origin_type, action="wait").inc()
        total_wait_time = 0
        max_total_wait = 30.0
        wait_start = time.time()

        while total_wait_time < max_total_wait:
            allowed, remaining_or_wait = await self.acquire_for_service(service)

            if allowed:
                logger.debug(
                    f"Service rate limit acquired for {service}, remaining: {remaining_or_wait}"
                )
                break

            # Добавляем jitter для избежания synchronized retries
            wait_time = remaining_or_wait
            jitter = wait_time * 0.1  # 10% jitter
            actual_wait = min(wait_time + jitter, max_total_wait - total_wait_time)

            logger.info(
                f"Service rate limit exceeded for {service}. "
                f"Waiting {actual_wait:.2f}s (total: {total_wait_time:.2f}s)"
            )

            await asyncio.sleep(actual_wait)
            total_wait_time += actual_wait
        else:
            logger.warning(
                f"Service rate limit timeout for {service} after {total_wait_time}s"
            )
        total_duration = time.time() - wait_start
        RATE_LIMIT_WAIT_TIME.labels(origin_type=self.origin_type).observe(
            total_duration
        )

    async def get_service_metrics(self, service: str) -> dict:
        """Возвращает метрики текущего состояния rate limiter для сервиса."""
        if not self.redis:
            await self.connect()

        key = f"{self.key_prefix}:service:{service}"
        current_time = time.time()

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, current_time - self.window_seconds)
                pipe.zcard(key)
                pipe.ttl(key)

                results = await pipe.execute()
                current_count, ttl = results[1], results[2]

                return {
                    "service": service,
                    "current_requests": current_count,
                    "max_requests": self.max_requests_per_service,
                    "remaining": max(0, self.max_requests_per_service - current_count),
                    "window_seconds": self.window_seconds,
                    "ttl": ttl,
                    "utilization_percent": (
                        current_count / self.max_requests_per_service
                    )
                    * 100,
                }
        except RedisError as e:
            logger.error(f"Error getting service metrics: {e}")
            return {}

    async def disconnect(self):
        """Закрывает соединение."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self._script_sha = None
