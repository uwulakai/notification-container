# Telegram Bot, TamTam Bot, WhatsApp и так далее - всё это http сервисы и у них есть много общего. Это надо вынести в отдельный http-класс
# особенности уже в отдельных файлах
# эл. почта - не http сервис, там отдельные протоколы
import asyncio
from typing import Dict, List, Optional, Any, Callable
import httpx
# from app.logger import logger


class PollingConfig:
    timeout: int            
    limit: int
    retry_delay: int        # Задержка при ошибках
    max_retries: int
    base_delay: float       # Базоавя задержка между циклами
    max_poling: int         # Максимальное кол-во запросов
    
class PollingMessage:
    """Универсальное представление сообщения от любого мессенджера"""
    text: Optional[str]      # Текст сообщения
    platform: str            # Платформа (tamtam, telegram и т.д.)
    timestamp: float         # Временная метка


class HTTPPollingService:
    def __init__(self, service_name: str, config: PollingConfig = None):
        self.service_name = service_name
        self.config = config or PollingConfig()
        self.client = httpx.AsyncClient

        # Состояние системы
        self.is_running = False
        self.marker = Optional[str] = None
        
        # Обработчики
        self.message_handlers = List[Callable] = []
        self.error_handlers = List[Callable] = []
    
        self.metrics = {
            'message_count': 0,
            'errors_count': 0,
            'time_of_start': None
        }
        