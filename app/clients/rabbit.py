from faststream.rabbit import RabbitBroker
from faststream.security import BaseSecurity
import asyncio

from app.logger import logger
from app.exceptions.rabbit import RabbitBrokerNotStartedError

class RabbitProducerClient:
    def __init__(self, host: str, port: int, max_retries: int, backoff_sec: int):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.backoff_sec = backoff_sec

        try:
            self.broker = RabbitBroker(
                host=self.host,
                port=self.port,
            )
        except Exception as e:
            logger.error(f"Ошибка при подключении к RabbitMQ: {str(e)}")
            raise
        
        self._is_started = False

    async def start(self):
        if not self._is_started:
            try:
                await self.broker.start()
                self._is_started = True
            except Exception as e:
                logger.exception(f"Ошибка при старте RabbitBroker: {e}")
                raise
    
    async def stop(self):
        if self._is_started:
            await self.broker.stop()
            self._is_started = False

    async def check(self):
        if not self._is_started:
            logger.error("Ошибка при RabbitProducerClient health-check: брокер не запущен")
            raise RabbitBrokerNotStartedError
        try:
            await self.broker.ping(timeout=5.0)
            return True
        except Exception as e:
            logger.error(f"Ошибка при health-check RabbitProducerClient: {str(e)}")
            return False

    async def send(self, message: dict, queue: str):
        if not self._is_started:
            logger.error("Ошибка при RabbitProducerClient send: брокер не запущен")
            raise RabbitBrokerNotStartedError
        
        for attempt in range(1, self.max_retries + 1):
            try:
                await self.broker.publish(
                    queue=queue,
                    message=message)
                logger.info(f"Отправлено сообщение {message} в queue {queue}")
                break
            except Exception as e:
                logger.warning(f"Ошибка при попытке отправки сообщения {message} в queue {queue} RabbitProducerClient: {str(e)}")
                
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_sec)
                else:
                    logger.error(f"Не удалось отправить сообщение {message} в queue {queue} после {self.max_retries} попыток")
                    raise