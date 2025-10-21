# Dockerfile
FROM python:3.13-slim

# Poetry
RUN pip install --no-cache-dir poetry

# WORKDIR совпадает с томом
WORKDIR /app

# Копируем зависимости для кеша сборки
COPY pyproject.toml poetry.lock /app/

# Установим зависимости
RUN poetry install --no-root --no-interaction --no-ansi

# Копируем код приложения
COPY ./app /app/app
