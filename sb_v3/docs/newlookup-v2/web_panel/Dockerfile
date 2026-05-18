FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY shared/requirements.txt /app/shared/requirements.txt
COPY web_panel/requirements.txt /app/web_panel/requirements.txt
COPY mirror_bot/requirements.txt /app/mirror_bot/requirements.txt
COPY seller_bot/requirements.txt /app/seller_bot/requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r /app/shared/requirements.txt
RUN pip install --no-cache-dir -r /app/web_panel/requirements.txt
RUN pip install --no-cache-dir -r /app/mirror_bot/requirements.txt
RUN pip install --no-cache-dir -r /app/seller_bot/requirements.txt

# Копируем код
COPY shared/ /app/shared/
COPY web_panel/ /app/web_panel/
COPY mirror_bot/ /app/mirror_bot/
COPY seller_bot/ /app/seller_bot/

# Создаем директории для данных и файлов
RUN mkdir -p /app/data/uploads /app/uploads/telegram /app/uploads/admin

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Порт
EXPOSE 8000

# Запуск
CMD ["python", "-m", "web_panel.run"]

