from app.utils.circuit_breaker.base import CircuitBreakerBaseClient
from app.enums.circuit_breaker import CircuitBreakerClientEnum


class CircuitBreakerRedisClient(CircuitBreakerBaseClient):
    def __init__(self, max_failures=3, reset_timeout_sec=60, half_open_max_attempts=2):
        super().__init__(
            CircuitBreakerClientEnum.REDIS,
            max_failures,
            reset_timeout_sec,
            half_open_max_attempts,
        )
