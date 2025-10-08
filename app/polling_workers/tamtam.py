# тут уже особенности конкретного сервиса. Сначала всё делаем на TamTam ботах
# from app.polling_workers.http_worker import HTTPPollingService


# class TamTamPollingService(HTTPPollingService):
#     pass
from http_worker import PollingConfig, PollingMessage
import time


config = PollingConfig(timeout=10, limit=50)
message = PollingMessage(
    message_id="123",
    chat_id="chat_456", 
    user_id="user_789",
    user_name="John",
    text="Hello World",
    platform="tamtam",
    timestamp=time.time(),
    raw_data={"key": "value"}
)
print(message)