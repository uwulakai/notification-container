import asyncio
import json
import os
from typing import Optional, Dict, Any
import time
import httpx

# Если http_worker находится в том же каталоге
try:
    from http_worker import PollingConfig, PollingMessage
except ImportError:
    # Для случая, если это отдельный файл
    pass

class TamTamPollingService():
    def __init__(self, token):
        self.token = token
        self.base_url = 'https://botapi.tamtam.chat/'
        
        # Состояние сервиса
        self.is_running = False
        self.marker: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None
        
        # Метрики

    async def create_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient()
            print('Клиент создан')
        
    async def close_client(self):
        if self.client:
            await self.client.aclose()
            self.client = None
            print('HTTPX клиент закрыт')
             
    async def get_updates(self, limit=1, timeout=45):
        '''Выполнение запроса к TamTam API'''
        method = 'updates'
        params = {
            'access_token': self.token,
            'timeout': timeout,
            'limit': limit,
            'marker': self.marker,
            'types': None
        }
        
        # Удаляем None значения из params
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = await self.client.get(self.base_url + method, params=params, timeout=60)
            update = response.json()
        except Exception as e:
            print(f"Error in get_updates: {str(e)}")
            return None
        
        if 'updates' in update.keys():
            if len(update['updates']) != 0:
                # Получаем chat_id для mark_seen
                chat_id = self.get_chat_id_from_update(update)
                if chat_id:
                    await self.mark_seen(chat_id)
            else:
                update = None
        else:
            update = None
            
        if update and 'marker' in update:
            self.marker = update['marker']
            
        return update
    
    def get_chat_id_from_update(self, update):
        """Извлекает chat_id из update"""
        try:
            if 'updates' in update and len(update['updates']) > 0:
                message = update['updates'][0].get('message', {})
                return message.get('recipient', {}).get('chat_id')
        except Exception as e:
            print(f"Error getting chat_id from update: {e}")
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
            if 'updates' in update.keys():
                if len(update['updates']) > 0:
                    upd = update['updates'][0]
                    upd_type = upd.get('update_type')
            else:
                upd_type = update.get('update_type')
        return upd_type
            
    async def get_bot_user_id(self):
        '''
        Возвращает айди текущего бота.
        '''
        method = 'me'
        params = {'access_token': self.token}
        try:
            response = await self.client.get(self.base_url + method, params=params)
            bot_info = response.json()
            return bot_info.get('user_id')
        except Exception as e:
            print(f"Error getting bot user id: {e}")
            return None
            
    def get_marker(self, update):
        '''Метод получения маркера события'''
        marker = None
        if update and 'marker' in update:
            marker = update['marker']
        return marker
                    
    async def mark_seen(self, chat_id):
        '''Отправка маркера о прочтении сообщения'''
        method_ntf = f'chats/{chat_id}/actions'
        params = {'action': 'mark_seen'}
        try:
            await self.client.post(
                self.base_url + method_ntf + f'?access_token={self.token}',
                json=params
            )
        except Exception as e:
            print(f'Error in mark_seen: {e}')
            
    async def get_chat_id(self, update=None):
        '''Получение id чата'''
        if update is not None:
            return self.get_chat_id_from_update(update)
        
        # Если update не передан, получаем список чатов
        method = 'chats'
        params = {"access_token": self.token}
        try:
            response = await self.client.get(self.base_url + method, params=params)
            if response.status_code == 200:
                chats_data = response.json()
                if 'chats' in chats_data.keys() and len(chats_data['chats']) > 0:
                    return chats_data['chats'][0].get('chat_id')
            else:
                print("Error get_chat_id: Non-200 response")
        except Exception as e:
            print(f"Error connect get_chat_id: {e}")
        return None

    def get_text(self, update):
        '''
        Получение текста отправленного или пересланного боту в том числе в режиме конструктора
        :param update: результат работы метода get_updates()
        :return: возвращает, если это возможно, значение поля 'text' созданного или пересланного сообщения
                 из 'body' или 'link'-'forward' соответственно, при неудаче 'text' = None
        '''
        text = None
        if update:
            update_type = self.get_update_type(update)
            
            if 'updates' in update.keys() and len(update['updates']) > 0:
                update_data = update['updates'][0]
            else:
                update_data = update
                
            if update_type in ['message_edited', 'message_callback', 'message_created', 'message_constructed']:
                try:
                    message = update_data.get('message', {})
                    text = message.get('body', {}).get('text')
                    if not text:
                        text = message.get('link', {}).get('message', {}).get('text')
                except Exception as e:
                    print(f"Error getting text from message: {e}")
                    
            elif update_type == 'message_construction_request':
                try:
                    input_data = update_data.get('input', {})
                    if 'messages' in input_data and len(input_data['messages']) > 0:
                        text = input_data['messages'][0].get('text')
                except Exception as e:
                    print(f"Error getting text from construction request: {e}")
                    
            elif update_type == 'message_chat_created':
                try:
                    chat_data = update_data.get('chat', {})
                    if 'pinned_message' in chat_data:
                        pinned_msg = chat_data['pinned_message']
                        text = pinned_msg.get('body', {}).get('text')
                        if not text:
                            text = pinned_msg.get('link', {}).get('message', {}).get('text')
                except Exception as e:
                    print(f"Error getting text from chat created: {e}")
                    
        return text

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
                    print(f"Received message: {text} in chat: {chat_id}")
                await asyncio.sleep(0.1)  # Небольшая пауза между запросами
        except KeyboardInterrupt:
            print("Polling stopped by user")
        finally:
            await self.close_client()


token = 'f9LHodD0cOJRTu4s2iVULPeZJvraecOmP1NkkMNjD_BPegBMLBbd1Tn1Oe0v8eIeP1wjd8gu0jlOmTp96rdcmQ'

async def main():
    bot = TamTamPollingService(token)
    await bot.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user")