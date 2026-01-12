import asyncio

from app.origin_clients.base_client import BaseOriginClient
from app.clients.rabbit.client import RabbitProducerClient
from app.clients.redis.redis_client import RedisRateLimiter
from app.metrics import (
    get_token_suffix,
    RABBITMQ_MESSAGES_SENT,
    RABBITMQ_MESSAGES_ERROR,
)
from app.logger import logger

from app.utils.circuit_breaker.rabbit import CircuitBreakerRabbitClient
from app.utils.circuit_breaker.redis import CircuitBreakerRedisClient
from app.exceptions.circuit_breaker import (
    RabbitMQCircuitBreakerOpenError,
    RedisCircuitBreakerOpenError,
)


class PollingWorker:
    def __init__(
        self,
        client: BaseOriginClient,
        publisher: RabbitProducerClient,
        redis_client: RedisRateLimiter,
        publisher_cb: CircuitBreakerRabbitClient,
        redis_cb: CircuitBreakerRedisClient,
        update_queue: str,
    ):
        self.client = client
        self.origin_type = client.origin_type
        self.publisher = publisher
        self.redis_client = redis_client
        self.is_running = False
        self.update_queue = update_queue

        self.publisher_cb = publisher_cb
        self.redis_cb = redis_cb

    async def start(self):
        self.is_running = True
        await self.client.create_client()

        try:
            while self.is_running:
                try:
                    await self.redis_cb.call(
                        self.redis_client.wait_for_service, self.client.origin_type
                    )
                except RedisCircuitBreakerOpenError:
                    logger.warning(
                        f"Redis недоступен -> бот {get_token_suffix(self.client.token)} пропускает запрос"
                    )
                    await asyncio.sleep(2)
                    continue
                except Exception as e:
                    logger.error(
                        f"Бот {get_token_suffix(self.client.token)}. Ошибка при обращении к Redis: {str(e)}"
                    )
                    await asyncio.sleep(2)
                    continue
                logger.info(
                    f"Бот {get_token_suffix(self.client.token)} делает запрос..."
                )
                update = await self.client.get_updates()
                if update:
                    try:
                        await self.publisher_cb.call(
                            self.publisher.send, update, self.update_queue
                        )
                        RABBITMQ_MESSAGES_SENT.labels(
                            origin_type=self.origin_type,
                            token_suffix=self.client.token_suffix,
                        ).inc()
                    except Exception as e:
                        logger.error(
                            f"Ошибка отправки в RabbitMQ. Origin_type: {self.origin_type}, token_suffix: {self.client.token_suffix}. Ошибка: {e}"
                        )
                        RABBITMQ_MESSAGES_ERROR.labels(
                            origin_type=self.origin_type,
                            token_suffix=self.client.token_suffix,
                        ).inc()
        except asyncio.CancelledError:
            pass
        finally:
            await self.client.close_client()
