import asyncio
from app.config import Settings
from app.polling_clients.tamtam import TamTamPollingService
from app.clients.rabbit import RabbitProducerClient
from app.clients.polling_worker import PollingWorker


async def start_all_workers():
    settings = Settings()
    publisher = RabbitProducerClient(settings.rabbit.RABBIT_URL.get_secret_value())
    await publisher.start()

    tasks = []
    for token in settings.tam_tam.TAM_TAM_TOKENS:
        client = TamTamPollingService(token.get_secret_value())
        worker = PollingWorker(
            client,
            publisher,
            settings.rabbit.RABBITMQ_NOTIFICATIONS_QUEUE,
            settings.rabbit.RABBITMQ_BACKOFF_SEC,
        )
        tasks.append(asyncio.create_task(worker.start()))

    await asyncio.gather(*tasks)
