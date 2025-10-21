import asyncio
import signal

from app.config import settings
from app.logger import logger
from app.service import start_all_workers


async def main():
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_sigterm():
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
    loop.add_signal_handler(signal.SIGINT, handle_sigterm)

    logger.info("Запускаем всех воркеров...")
    task = asyncio.create_task(start_all_workers())

    await stop_event.wait()
    logger.warning("Останавливаем всех воркеров...")
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


if __name__ == "__main__":
    logger.info(f"Все настройки инициализированы: {settings}")
    asyncio.run(main())
