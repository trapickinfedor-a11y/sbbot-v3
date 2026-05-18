"""
HTTP сервер для main_bot для приема уведомлений от support_bot
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from main_bot.app.api.notifications import app as notifications_app
from main_bot.app.api.bot_management import app as bot_management_app
from main_bot.app.api.user_orders import app as user_orders_app

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HTTP API server starting...")
    yield
    logger.info("HTTP API server shutting down...")

# Создаем основное приложение FastAPI
app = FastAPI(
    title="Main Bot API",
    description="API для приема уведомлений от Support Bot",
    version="1.0.0",
    lifespan=lifespan
)

# Монтируем приложения
app.mount("/api/v1", user_orders_app)
app.mount("/api", notifications_app)
app.mount("", bot_management_app)

async def start_http_server():
    """Запустить HTTP сервер"""
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=int(os.environ.get("MAIN_BOT_API_PORT", "8080")),
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except Exception as e:
        logger.error(f"HTTP server error: {e}")

if __name__ == "__main__":
    asyncio.run(start_http_server())
