FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY ./app /app/app

# Запуск
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${SERVICE_PORT:-8000}", "--log-level", "info"]