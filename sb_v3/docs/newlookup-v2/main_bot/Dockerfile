FROM python:3.11-slim

WORKDIR /app

COPY main_bot/requirements.txt /app/main_bot/requirements.txt
COPY shared/requirements.txt /app/shared/requirements.txt
COPY mirror_bot/requirements.txt /app/mirror_bot/requirements.txt

RUN pip install --no-cache-dir -r main_bot/requirements.txt
RUN pip install --no-cache-dir -r shared/requirements.txt
RUN pip install --no-cache-dir -r mirror_bot/requirements.txt

COPY main_bot /app/main_bot
COPY shared /app/shared
COPY mirror_bot /app/mirror_bot

# Создаем директории для файлов
RUN mkdir -p /app/uploads/telegram /app/uploads/admin

CMD ["python", "-m", "main_bot.app.main"]

