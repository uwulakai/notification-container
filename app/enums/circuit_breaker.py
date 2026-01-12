from enum import Enum


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerClientEnum(str, Enum):
    RABBITMQ = "RABBITMQ"
