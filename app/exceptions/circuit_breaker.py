class BaseCircuitBreakerOpenError(Exception):
    """Автоматический выключатель открыт, соедение с клиентом отозвано"""


class RabbitMQCircuitBreakerOpenError(Exception):
    """Соединение с RabbitMQ клиентом отозвано"""


class RedisCircuitBreakerOpenError(Exception):
    """Соединение с Redis клиентом отозвано"""
