from abc import ABC, abstractmethod

from app.enums.polling_workers import OriginType


class BaseOriginClient(ABC):
    token: str
    token_suffix: str
    origin_type: OriginType

    @abstractmethod
    async def create_client(self):
        pass

    @abstractmethod
    async def close_client(self):
        pass
