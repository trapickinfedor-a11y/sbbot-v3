FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY shared/requirements.txt /app/shared/requirements.txt
COPY support_bot/requirements.txt /app/support_bot/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r /app/shared/requirements.txt
RUN pip install --no-cache-dir -r /app/support_bot/requirements.txt

# Копируем код
COPY shared/ /app/shared/
COPY support_bot/ /app/support_bot/

# Создаем директории для файлов
RUN mkdir -p /app/uploads/telegram /app/uploads/admin

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Запуск
CMD ["python", "-m", "support_bot.run"]

