"""
FastAPI сервер для Worker Bot API
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from worker_bot.api.notifications import router as notifications_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Worker Bot API starting...")
    yield
    logger.info("Worker Bot API shutting down...")


app = FastAPI(
    title="Worker Bot API",
    description="API для получения уведомлений о заказах воркеров",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(notifications_router)


@app.get("/health")
async def health_check():
    """Проверка здоровья API"""
    return {"status": "healthy", "service": "worker_bot_api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "worker_bot.api_server:app",
        host="0.0.0.0",
        port=8181,
        log_level="info",
    )
