import asyncio
from typing import Optional
import httpx

from app.origin_clients.base_client import BaseOriginClient
from app.metrics import metrics_middleware, get_token_suffix
from app.enums.polling_workers import OriginType
from app.logger import logger
from app.schemas.message import MessageSchema


class TamTamClient(BaseOriginClient):
    def __init__(self, token):
        self.token = token

        self.token_suffix = get_token_suffix(self.token)
        self.origin_type = OriginType.TAMTAM

        self.base_url = "https://botapi.tamtam.chat/"

        # Состояние сервиса
        self.is_running = False
        self.marker: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None

        self.get_updates = metrics_middleware(
            origin_type=self.origin_type, token_suffix=self.token_suffix
        )(self._get_updates)

    async def create_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient()
            logger.info("Клиент создан")

    async def close_client(self):
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("HTTPX клиент закрыт")

    async def _get_updates(self, limit=1, timeout=1):
        """Выполнение запроса к TamTam API"""
        method = "updates"
        params = {
            "access_token": self.token,
            "timeout": timeout,
            "limit": limit,
            "marker": self.marker,
            "types": None,
        }

        # Удаляем None значения из params
        params = {k: v for k, v in params.items() if v is not None}

        try:
            response = await self.client.get(
                self.base_url + method, params=params, timeout=60
            )
            response.raise_for_status()
            update = response.json()
        except Exception as e:
            logger.error(f"Error in get_updates: {str(e)}")
            raise

        if "updates" in update.keys():
            if len(update["updates"]) != 0:
                chat_id = self.get_chat_id_from_update(update)
                if chat_id:
                    await self.mark_seen(chat_id)
            else:
                return None
        else:
            return None

        if update and "marker" in update:
            self.marker = update["marker"]

        return MessageSchema(
            chat_id=chat_id,
            text=self.get_text(update),
            chat_user_name=self.get_name(update),
        )

    def get_chat_id_from_update(self, update):
        """Извлекает chat_id из update"""
        try:
            if "updates" in update and len(update["updates"]) > 0:
                message = update["updates"][0].get("message", {})
                return message.get("recipient", {}).get("chat_id")
        except Exception as e:
            logger.error(f"Error getting chat_id from update: {e}")
        return None

    def get_update_type(self, update):
        """
        Метод получения типа события произошедшего с ботом
        API = subscriptions/Get updates/[updates][0][update_type]
        :param update = результат работы метода get_update
        :return: возвращает значение поля 'update_type', при неудаче = None
        """
        upd_type = None
        if update:
            if "updates" in update.keys():
                if len(update["updates"]) > 0:
                    upd = update["updates"][0]
                    upd_type = upd.get("update_type")
            else:
                upd_type = update.get("update_type")
        return upd_type

    def get_marker(self, update):
        """Метод получения маркера события"""
        marker = None
        if update and "marker" in update:
            marker = update["marker"]
        return marker

    async def mark_seen(self, chat_id):
        """Отправка маркера о прочтении сообщения"""
        method_ntf = f"chats/{chat_id}/actions"
        params = {"action": "mark_seen"}
        try:
            await self.client.post(
                self.base_url + method_ntf + f"?access_token={self.token}", json=params
            )
        except Exception as e:
            logger.error(f"Error in mark_seen: {e}")

    async def get_chat_id(self, update=None):
        """Получение id чата"""
        if update is not None:
            return self.get_chat_id_from_update(update)

        # Если update не передан, получаем список чатов
        method = "chats"
        params = {"access_token": self.token}
        try:
            response = await self.client.get(self.base_url + method, params=params)
            if response.status_code == 200:
                chats_data = response.json()
                if "chats" in chats_data.keys() and len(chats_data["chats"]) > 0:
                    return chats_data["chats"][0].get("chat_id")
            else:
                logger.error("Error get_chat_id: Non-200 response")
        except Exception as e:
            logger.error(f"Error connect get_chat_id: {e}")
        return None

    def get_text(self, update):
        """
        Получение текста отправленного или пересланного боту в том числе в режиме конструктора
        :param update: результат работы метода get_updates()
        :return: возвращает, если это возможно, значение поля 'text' созданного или пересланного сообщения
                 из 'body' или 'link'-'forward' соответственно, при неудаче 'text' = None
        """
        text = None
        if update:
            update_type = self.get_update_type(update)

            if "updates" in update.keys() and len(update["updates"]) > 0:
                update_data = update["updates"][0]
            else:
                update_data = update

            if update_type in [
                "message_edited",
                "message_callback",
                "message_created",
                "message_constructed",
            ]:
                try:
                    message = update_data.get("message", {})
                    text = message.get("body", {}).get("text")
                    if not text:
                        text = message.get("link", {}).get("message", {}).get("text")
                except Exception as e:
                    logger.error(f"Error getting text from message: {e}")

            elif update_type == "message_construction_request":
                try:
                    input_data = update_data.get("input", {})
                    if "messages" in input_data and len(input_data["messages"]) > 0:
                        text = input_data["messages"][0].get("text")
                except Exception as e:
                    logger.error(f"Error getting text from construction request: {e}")

            elif update_type == "message_chat_created":
                try:
                    chat_data = update_data.get("chat", {})
                    if "pinned_message" in chat_data:
                        pinned_msg = chat_data["pinned_message"]
                        text = pinned_msg.get("body", {}).get("text")
                        if not text:
                            text = (
                                pinned_msg.get("link", {})
                                .get("message", {})
                                .get("text")
                            )
                except Exception as e:
                    logger.error(f"Error getting text from chat created: {e}")

        return text

    def get_name(self, update):
        """
        Получение имени пользователя, инициировавшего событие, в том числе нажатие кнопки
        :param update: результат работы метода get_update
        :return: возвращает, если это возможно, значение поля 'name' не зависимо от события, произошедшего с ботом
                 если событие - "удаление сообщения", то name = None
        """
        name = None
        if update:
            if "updates" in update.keys():
                upd = update["updates"][0]
            else:
                upd = update
            if "user" in upd.keys():
                name = upd["user"]["name"]
            elif "callback" in upd.keys():
                name = upd["callback"]["user"]["name"]
            elif "chat" in upd.keys():
                upd = upd["chat"]
                if "dialog_with_user" in upd.keys():
                    name = upd["dialog_with_user"]["name"]
            elif "message" in upd.keys():
                upd = upd["message"]
                if "sender" in upd.keys():
                    name = upd["sender"]["name"]
        return name

    async def run_polling(self):
        """Асинхронный метод для запуска поллинга"""
        await self.create_client()
        self.is_running = True

        try:
            while self.is_running:
                last_update = await self.get_updates()
                if last_update:
                    text = self.get_text(last_update)
                    chat_id = await self.get_chat_id(last_update)
                    logger.error(f"Received message: {text} in chat: {chat_id}")
                await asyncio.sleep(0.1)  # Небольшая пауза между запросами
        except KeyboardInterrupt:
            logger.error("Polling stopped by user")
        finally:
            await self.close_client()
