import time
from typing import Callable, Any

from app.logger import logger
from app.enums.circuit_breaker import CircuitBreakerState, CircuitBreakerClientEnum
from app.exceptions.circuit_breaker import (
    BaseCircuitBreakerOpenError,
    RabbitMQCircuitBreakerOpenError,
    RedisCircuitBreakerOpenError,
)


class CircuitBreakerBaseClient:
    def __init__(
        self,
        client: CircuitBreakerClientEnum,
        max_failures: int = 3,
        reset_timeout_sec: int = 60,
        half_open_max_attempts: int = 1,
    ):
        self.client = client
        self.max_failures = max_failures
        self.reset_timeout_sec = reset_timeout_sec
        self.half_open_max_attempts = half_open_max_attempts
        self.failures = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = 0
        self.half_open_max_attempts = 0

    def _get_exception_class(self):
        exception_mapping = {
            CircuitBreakerClientEnum.RABBITMQ: RabbitMQCircuitBreakerOpenError,
            CircuitBreakerClientEnum.REDIS: RedisCircuitBreakerOpenError,
        }
        return exception_mapping.get(self.client, BaseCircuitBreakerOpenError)

    def _open(self):
        self.state = CircuitBreakerState.OPEN
        self.last_failure_time = time.time()
        logger.warning(f"CircuitBreaker {self.client} изменил состояние на OPEN")

    def _half_open(self):
        self.state = CircuitBreakerState.HALF_OPEN
        logger.info(f"CircuitBreaker {self.client} изменил состояние на HALF_OPEN")

    def _close(self):
        self.state = CircuitBreakerState.CLOSED
        self.failures = 0
        logger.info(f"CircuitBreaker {self.client} изменил состояние на CLOSED")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitBreakerState.OPEN:
            if (time.time() - self.last_failure_time) >= self.reset_timeout_sec:
                self._half_open()
            else:
                logger.warning(
                    f"CircuitBreaker {self.client} в состоянии OPEN — пропускаем запрос"
                )
                raise self._get_exception_class()

        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"CircuitBreaker {self.client}: ошибка вызова - {str(e)}")

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_attempts += 1
                logger.warning(
                    f"CircuitBreaker {self.client}: HALF_OPEN попытка #{self.half_open_attempts} неуспешна"
                )

                if self.half_open_attempts >= self.half_open_max_attempts:
                    logger.warning(
                        f"CircuitBreaker {self.client}: HALF_OPEN -> OPEN "
                        f"(достигнут лимит {self.half_open_max_attempts} попыток)"
                    )
                    self._open()
                else:
                    logger.info(
                        f"CircuitBreaker {self.client}: остаемся в HALF_OPEN "
                        f"(попытка {self.half_open_attempts}/{self.half_open_max_attempts})"
                    )
            else:
                self.failures += 1
                logger.debug(f"CircuitBreaker {self.client}: неудача #{self.failures}")
                if self.failures >= self.max_failures:
                    logger.warning(
                        f"CircuitBreaker {self.client}: CLOSED -> OPEN "
                        f"(достигнут max_failures={self.max_failures})"
                    )
                    self._open()
            raise
        else:
            if self.state == CircuitBreakerState.HALF_OPEN:
                logger.info(
                    f"CircuitBreaker {self.client}: HALF_OPEN попытка успешна -> CLOSED"
                )
                self._close()
                self.half_open_attempts = 0
            self.failures = 0
            return result
