from app.dependencies.providers.rabbit import RabbitProvider

def get_providers():
    return [
        RabbitProvider(),
    ]