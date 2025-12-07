from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    CollectorRegistry,
)
import asyncio
from functools import wraps

# Создаём свой registry для изоляции метрик
registry = CollectorRegistry()

# Общие метрики
REQUESTS_TOTAL = Counter(
    "origin_requests_total",
    "Общее количество запросов к API сервисов",
    ["origin_type", "token_suffix", "endpoint"],
    registry=registry,
)

REQUESTS_IN_PROGRESS = Gauge(
    "origin_requests_in_progress",
    "Количество запросов, обрабатываемых в данный момент",
    ["origin_type", "token_suffix"],
    registry=registry,
)

REQUESTS_DURATION = Histogram(
    "origin_requests_duration_seconds",
    "Длительность обработки запросов",
    ["origin_type", "token_suffix"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=registry,
)

REQUESTS_SUCCESS = Counter(
    "origin_requests_success_total",
    "Количество успешно обработанных запросов",
    ["origin_type", "token_suffix"],
    registry=registry,
)

REQUESTS_ERROR = Counter(
    "origin_requests_error_total",
    "Количество запросов, завершившихся с ошибкой",
    ["origin_type", "token_suffix"],
    registry=registry,
)

# Метрики состояния подключений
CONNECTION_STATUS = Gauge(
    "origin_connection_status",
    "Статус подключения к сервисам (1 = подключено, 0 = отключено)",
    ["origin_type", "service"],
    registry=registry,
)

# Метрики rate limiting
RATE_LIMIT_REQUESTS = Counter(
    "origin_rate_limit_requests_total",
    "Общее количество запросов к rate limiter",
    ["origin_type", "action"],
    registry=registry,
)

RATE_LIMIT_WAIT_TIME = Histogram(
    "origin_rate_limit_wait_seconds",
    "Время ожидания из-за rate limiting",
    ["origin_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=registry,
)

# Метрики очереди RabbitMQ
RABBITMQ_MESSAGES_SENT = Counter(
    "origin_rabbitmq_messages_sent_total",
    "Количество отправленных сообщений в RabbitMQ",
    ["origin_type", "token_suffix"],
    registry=registry,
)

RABBITMQ_MESSAGES_ERROR = Counter(
    "origin_rabbitmq_messages_error_total",
    "Количество ошибок при отправке в RabbitMQ",
    ["origin_type", "token_suffix"],
    registry=registry,
)

# Метрики Redis
REDIS_OPERATIONS = Counter(
    "origin_redis_operations_total",
    "Количество операций с Redis",
    ["origin_type", "operation", "status"],
    registry=registry,
)

SERVICE_INFO = Info("origin_service_info", "Информация о сервисе", registry=registry)

WORKER_INFO = Info(
    "origin_worker_info",
    "Информация о воркерах",
    ["origin_type", "token_suffix"],
    registry=registry,
)


def get_token_suffix(token: str) -> str:
    """Получает последние 4 символа токена для меток"""
    return token[-4:] if token and len(token) >= 4 else "unknown"


def metrics_middleware(origin_type: str, token_suffix: str):
    """Декоратор для сбора метрик запросов"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            endpoint = func.__name__

            # Увеличиваем счётчик активных запросов
            REQUESTS_IN_PROGRESS.labels(
                origin_type=origin_type, token_suffix=token_suffix
            ).inc()

            start_time = asyncio.get_event_loop().time()

            try:
                result = await func(*args, **kwargs)
                REQUESTS_SUCCESS.labels(
                    origin_type=origin_type,
                    token_suffix=token_suffix,
                ).inc()
                return result
            except Exception:
                REQUESTS_ERROR.labels(
                    origin_type=origin_type,
                    token_suffix=token_suffix,
                ).inc()
                raise
            finally:
                # Уменьшаем счётчик активных запросов
                REQUESTS_IN_PROGRESS.labels(
                    origin_type=origin_type, token_suffix=token_suffix
                ).dec()

                # Замеряем длительность
                duration = asyncio.get_event_loop().time() - start_time
                REQUESTS_DURATION.labels(
                    origin_type=origin_type, token_suffix=token_suffix
                ).observe(duration)

                # Общий счётчик запросов
                REQUESTS_TOTAL.labels(
                    origin_type=origin_type,
                    token_suffix=token_suffix,
                    endpoint=endpoint,
                ).inc()

        return wrapper

    return decorator
