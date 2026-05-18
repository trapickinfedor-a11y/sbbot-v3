"""
Главный файл для запуска Telegram-бота.

Что делает:
  1. Применяет asyncio policy fix для uvloop.
  2. Загружает конфиг из .env.
  3. Инициализирует aiogram Bot, Dispatcher и FSM storage.
  4. Инициализирует WorkerPool из cs_module.
  5. Регистрирует все хэндлеры (команды, FSM, колбэки).
  6. Настраивает graceful shutdown для пула воркеров.
"""

# 1. ФИКС ДЛЯ ASYNCIO POLICY (ОБЯЗАТЕЛЬНО ПЕРВЫМ)
# Это решает конфликт между uvloop (который ставит aiogram) и Playwright
import sys
try:
    if "linux" in sys.platform.lower():
        import uvloop
        uvloop.install()
        print("[INFO] uvloop policy installed.")
except ImportError:
    pass # uvloop не обязателен, но рекомендуется на Linux

# 2. Остальные импорты
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.handlers import register_handlers
from app.services.worker_pool import pool, start_worker_pool, stop_worker_pool


async def main():
    """Точка входа в приложение."""
    # Настройка логирования
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Инициализация
    storage = MemoryStorage()
    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=storage)

    # Регистрация хэндлеров
    register_handlers(dp)

    # Регистрация lifecycle-хуков для пула воркеров
    dp.startup.register(start_worker_pool)
    dp.shutdown.register(stop_worker_pool)

    logger.info("Starting bot...")

    try:
        # Удаляем вебхук, если он был установлен
        await bot.delete_webhook(drop_pending_updates=True)
        # Запускаем polling
        await dp.start_polling(bot)
    finally:
        logger.info("Stopping bot...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped manually")
