import asyncio
# Disable uvloop
try:
    import uvloop; asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
except ImportError:
    pass
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from main_bot.app.config import config
from shared.config.env_utils import StartupValidationError, validate_startup_env
from main_bot.app.repository.base import BotRepository
from main_bot.app.repository.postgres import PostgresBotRepository
from main_bot.app.services.mirror_bot import MirrorBotService
from main_bot.app.handlers import start, token, owner_cabinet
from main_bot.app.middleware.logging import LoggingMiddleware
from main_bot.app.middleware.ban_check import MainBotBanCheckMiddleware
from main_bot.app.middleware.mirror_service import MirrorServiceMiddleware
from main_bot.app.middleware.error_handler import ErrorHandlerMiddleware
from main_bot.app.api.server import start_http_server
from shared.middlewares.error_logging import GlobalErrorLoggingMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _validate_main_bot_startup() -> None:
    warnings = validate_startup_env(
        "main_bot",
        required=["MAIN_BOT_TOKEN", "DATABASE_URL", "INTERNAL_API_TOKEN"],
        optional=["MAIN_BOT_USERNAME", "SUPPORT_BOT_TOKEN"],
    )
    for warning in warnings:
        logger.warning(warning)

def create_repository() -> BotRepository:
    return PostgresBotRepository()

async def start_bot_polling(mirror_service: MirrorBotService):
    """Запустить polling для main bot"""
    bot = Bot(
        token=config.main_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()
    
    dp.update.middleware(LoggingMiddleware())
    dp.update.middleware(ErrorHandlerMiddleware())
    dp.update.middleware(MirrorServiceMiddleware(mirror_service))
    dp.update.middleware(MainBotBanCheckMiddleware())
    dp.update.middleware(GlobalErrorLoggingMiddleware("main_bot"))
    
    dp["mirror_service"] = mirror_service
    
    dp.include_router(start.router)
    dp.include_router(token.router)
    dp.include_router(owner_cabinet.router)
    
    logger.info("Main bot polling starting...")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Main bot polling stopped")

async def main():
    try:
        _validate_main_bot_startup()
    except StartupValidationError as exc:
        logger.error(str(exc))
        raise SystemExit(1)

    repository = create_repository()
    await repository.init_db()
    logger.info(f"Database initialized: PostgreSQL")
    
    mirror_service = MirrorBotService(repository)
    await mirror_service.restore_all_bots()
    logger.info("Mirror bots restored from database")
    
    # Инициализируем API для управления ботами
    from main_bot.app.api.bot_management import set_mirror_bot_service
    set_mirror_bot_service(mirror_service)
    
    # Запускаем HTTP сервер и bot polling параллельно
    logger.info("Starting main bot services...")
    
    try:
        await asyncio.gather(
            start_http_server(),
            start_bot_polling(mirror_service)
        )
    finally:
        await mirror_service.shutdown_all()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

