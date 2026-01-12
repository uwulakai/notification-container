import time
from typing import Callable, Any

from app.logger import logger
from app.enums.circuit_breaker import CircuitBreakerState, CircuitBreakerClientEnum
from app.exceptions.circuit_breaker import (
    BaseCircuitBreakerOpenError,
    RabbitMQCircuitBreakerOpenError,
)


class CircuitBreakerBaseClient:
    def __init__(
        self,
        client: CircuitBreakerClientEnum,
        max_failures: int = 3,
        reset_timeout_sec: int = 60,
    ):
        self.client = client
        self.max_failures = max_failures
        self.reset_timeout_sec = reset_timeout_sec
        self.failures = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = 0

    def _get_exception_class(self):
        exception_mapping = {
            CircuitBreakerClientEnum.RABBITMQ: RabbitMQCircuitBreakerOpenError,
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
        except Exception:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._open()
            else:
                self.failures += 1
                if self.failures >= self.max_failures:
                    self._open()
            raise
        else:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._close()
            self.failures = 0
            return result
