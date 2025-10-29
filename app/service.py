import asyncio
from app.config import Settings
from app.origin_clients.tamtam import TamTamClient
from app.clients.rabbit.provide import get_rabbit_client
from app.clients.polling_worker import PollingWorker

from app.logger import logger


async def start_all_workers():
    settings = Settings()

    tasks = []
    for token in settings.tam_tam.TAM_TAM_TOKENS:
        client = TamTamClient(token.get_secret_value())
        publisher = await get_rabbit_client()
        worker = PollingWorker(
            client,
            publisher,
            settings.rabbit.RABBITMQ_NOTIFICATIONS_QUEUE,
            settings.tam_tam.TAM_TAM_BACKOFF_SEC,
        )
        tasks.append(asyncio.create_task(worker.start()))

    await asyncio.gather(*tasks)
