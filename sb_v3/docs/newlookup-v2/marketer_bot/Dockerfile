FROM python:3.11-slim

WORKDIR /app

COPY shared/requirements.txt /app/shared/requirements.txt
COPY marketer_bot/requirements.txt /app/marketer_bot/requirements.txt

RUN pip install --no-cache-dir -r /app/shared/requirements.txt
RUN pip install --no-cache-dir -r /app/marketer_bot/requirements.txt

COPY shared/ /app/shared/
COPY marketer_bot/ /app/marketer_bot/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "marketer_bot.bot"]
