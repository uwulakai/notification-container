from abc import ABC, abstractmethod


class BaseOriginClient(ABC):
    @abstractmethod
    async def create_client(self):
        pass

    @abstractmethod
    async def close_client(self):
        pass

    @abstractmethod
    async def get_updates(self):
        pass
