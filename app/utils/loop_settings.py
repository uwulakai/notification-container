import asyncio

from app.logger import logger

import sys


def handle_sync_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.exception(
        "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
    )


sys.excepthook = handle_sync_exception


def handle_async_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.exception(f"Unhandled exception in event loop: {msg}")


def safe_create_task(coro, name=None):
    task = asyncio.create_task(coro, name=name)

    def _handle_task_result(task):
        try:
            task.result()
        except asyncio.CancelledError:
            logger.warning(f"Task {name or task.get_name()} was cancelled.")
        except Exception as e:
            logger.exception(f"Task {name or task.get_name()} crashed: {e}")

    task.add_done_callback(_handle_task_result)
    return task
