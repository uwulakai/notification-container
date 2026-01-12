import asyncio
import signal
from prometheus_client import start_http_server
from datetime import datetime

from app.config import settings
from app.logger import logger
from app.on_startup import on_startup
from app.service import start_all_workers
from app.utils.loop_settings import handle_async_exception, safe_create_task
from app.utils.rabbit_waiter import wait_for_rabbit
from app.metrics import registry, SERVICE_INFO


async def main():
    SERVICE_INFO.info(
        {
            "start_time": datetime.now().isoformat(),
        }
    )
    start_http_server(settings.prometheus.METRICS_PORT, registry=registry)

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_sigterm():
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
    loop.add_signal_handler(signal.SIGINT, handle_sigterm)
    loop.set_exception_handler(handle_async_exception)

    logger.info("Запускаем всех воркеров...")
    task = safe_create_task(start_all_workers(), name="start_all_workers")

    await stop_event.wait()
    logger.warning("Останавливаем всех воркеров...")
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


if __name__ == "__main__":
    logger.info(f"Все настройки инициализированы: {settings}")
    asyncio.run(wait_for_rabbit())
    asyncio.run(on_startup())
    asyncio.run(main())
