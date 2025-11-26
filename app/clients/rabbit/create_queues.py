from faststream.rabbit import RabbitQueue

from app.clients.rabbit.client import RabbitProducerClient
from app.logger import logger
from app.config import settings


async def create_queues(rabbit_client: RabbitProducerClient):
    logger.info("Инициализация очередей в RabbitMQ...")
    queues = [
        RabbitQueue(settings.rabbit.RABBITMQ_NOTIFICATIONS_QUEUE, durable=True),
    ]

    for q in queues:
        await rabbit_client.broker.declare_queue(q)
        logger.info(f"Очередь {q.name} объявлена")
