FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt /app/shared/requirements.txt
COPY worker_bot/requirements.txt /app/worker_bot/requirements.txt

RUN pip install --no-cache-dir -r /app/shared/requirements.txt
RUN pip install --no-cache-dir -r /app/worker_bot/requirements.txt

COPY shared/ /app/shared/
COPY support_bot/ /app/support_bot/
COPY worker_bot/ /app/worker_bot/

RUN mkdir -p /app/uploads/telegram /app/uploads/admin

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "worker_bot.run"]
