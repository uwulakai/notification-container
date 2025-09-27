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
