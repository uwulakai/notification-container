from loguru import logger
import sys
import logging

from app.config import settings

logger.remove()
logger.add(
    sys.stdout,
    level=settings.logging.LOGGING_LEVEL,
    backtrace=True,
    diagnose=True,   # только для dev
    enqueue=True
)

# Логи INFO, DEBUG, WARNING - в отдельный файл
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="10 days",
    compression="zip",
    level="DEBUG",
    backtrace=True,
    diagnose=True,   # только для dev
    enqueue=True,
    filter=lambda record: record["level"].name in ["DEBUG", "INFO", "WARNING"],
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Логи ERROR и CRITICAL - в отдельный файл для ошибок
logger.add(
    "logs/error.log",
    rotation="5 MB",
    retention="30 days",
    compression="zip",
    level="ERROR",
    backtrace=True,
    diagnose=True,   # только для dev
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(exception=record.exc_info, depth=6).log(level, record.getMessage())

def setup_logging():
    """Перехватываем все логи Python и Uvicorn в Loguru"""
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False

    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
