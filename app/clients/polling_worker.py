import asyncio

from app.polling_clients.base_client import BasePollingClient
from app.clients.rabbit import RabbitProducerClient


class PollingWorker:
    def __init__(
        self,
        client: BasePollingClient,
        publisher: RabbitProducerClient,
        update_queue: str,
        backoff_sec: float,
    ):
        self.client = client
        self.publisher = publisher
        self.is_running = False
        self.update_queue = update_queue
        self.backoff_sec = backoff_sec

    async def start(self):
        self.is_running = True
        await self.client.create_client()

        try:
            while self.is_running:
                update = await self.client.get_updates()
                if update:
                    await self.publisher.send(update, self.update_queue)
                await asyncio.sleep(self.backoff_sec)
        except asyncio.CancelledError:
            pass
        finally:
            await self.client.close_client()
