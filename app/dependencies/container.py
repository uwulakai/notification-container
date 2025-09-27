from dishka import make_async_container
from app.dependencies.providers import get_providers

class ContainerManager:
    def __init__(self):
        self._container = None

    def init_container(self):
        providers = get_providers()
        self._container = make_async_container(*providers)
        return self._container
    
    def set_container(self, container):
        self._container = container
    
    def get_container(self):
        if self._container is None:
            raise RuntimeError("Container not initialized. Call init_container() first")
        return self._container
    
    async def close(self):
        if self._container:
            await self._container.close()
            self._container = None

container_manager = ContainerManager()

# при старте приложеня - init_container. Далее в любом месте импортим container_manager, получаем контейнер через get_container и получаем любую зависимость

"""Пример: 

/app/main.py:
from app.dependencies.container import container_manager

container_manager.init_container()

/app/worker.py:

from app.dependencies.container import container_manager
from app.clients.rabbit import RabbitProducerClient

container = container_manager.get_container()

rabbit_client = container.get(RabbitProducerClient)"""