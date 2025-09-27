from dishka import Provider, Scope, provide
from faststream.security import BaseSecurity

from app.clients.rabbit import RabbitProducerClient
from app.config import settings
from app.logger import logger

class RabbitProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_rabbit_client(self) -> RabbitProducerClient:
        try:
            client = RabbitProducerClient(
                host=settings.rabbit.RABBITMQ_HOST,
                port=settings.rabbit.RABBITMQ_PORT,
                max_retries=settings.rabbit.RABBITMQ_MAX_RETRIES,
                backoff_sec=settings.rabbit.RABBITMQ_BACKOFF_SEC
            )

            await client.start()
            return client
        except Exception as e:
            logger.error(f"Не удалось подключится к RabbitMQ через RabbitProducerClient: {str(e)}")
            raise