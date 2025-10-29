from app.clients.rabbit.provide import get_rabbit_client
from app.clients.rabbit.create_queues import create_queues


async def on_startup():
    client = await get_rabbit_client()
    await create_queues(client)
