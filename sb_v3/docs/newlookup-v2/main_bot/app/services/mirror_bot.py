import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError, TelegramBadRequest
from main_bot.app.domain.entities import MirrorBot
from main_bot.app.repository.base import BotRepository
from main_bot.app.constants.texts import BotTexts

logger = logging.getLogger(__name__)

class MirrorBotService:

    def __init__(self, repository: BotRepository):
        self.repository = repository
        self.running_bots: Dict[int, Tuple[Bot, Dispatcher, asyncio.Task]] = {}

    async def validate_token(self, token: str) -> Optional[dict]:
        try:
            bot = Bot(token=token)
            bot_info = await bot.get_me()
            await bot.session.close()
            return {
                "username": bot_info.username,
                "id": bot_info.id
            }
        except (TelegramUnauthorizedError, TelegramBadRequest):
            return None

    async def start_mirror_bot(self, user_id: int, bot_token: str) -> Tuple[bool, str]:
        # Проверяем, есть ли неактивный бот с таким токеном
        existing_token_bot = await self.repository.get_by_token(bot_token)
        if existing_token_bot:
            if existing_token_bot.user_id != user_id:
                return False, "This token belongs to another user."
            # Реактивируем существующего бота того же пользователя
            bot_info = await self.validate_token(bot_token)
            if not bot_info:
                return False, BotTexts.ERROR_INVALID_TOKEN
            success = await self.repository.reactivate(existing_token_bot.id, bot_info["username"])
            if success:
                if existing_token_bot.id not in self.running_bots:
                    await self._launch_bot(existing_token_bot)
                return True, bot_info["username"]

        bot_info = await self.validate_token(bot_token)
        if not bot_info:
            return False, BotTexts.ERROR_INVALID_TOKEN

        mirror_bot = MirrorBot.create(
            user_id=user_id,
            bot_token=bot_token,
            bot_username=bot_info["username"]
        )
        await self.repository.create(mirror_bot)

        await self._launch_bot(mirror_bot)

        return True, bot_info["username"]

    async def _launch_bot(self, mirror_bot: MirrorBot):
        from mirror_bot.bot import create_mirror_bot
        from mirror_bot.handlers.payment import init_payment_manager, init_cryptomus_manager
        from mirror_bot.config import mirror_bot_config

        bot, dp = create_mirror_bot(mirror_bot.bot_token, mirror_bot.id)

        # Инициализация платежных менеджеров
        if mirror_bot_config.crypto_pay_token:
            init_payment_manager(
                mirror_bot_config.crypto_pay_token,
                mirror_bot_config.crypto_pay_testnet
            )

        if mirror_bot_config.cryptomus_merchant_id and mirror_bot_config.cryptomus_payment_key:
            init_cryptomus_manager(
                mirror_bot_config.cryptomus_merchant_id,
                mirror_bot_config.cryptomus_payment_key,
                mirror_bot_config.cryptomus_payout_key
            )

        task = asyncio.create_task(self._run_polling(dp, bot, mirror_bot.id))
        self.running_bots[mirror_bot.id] = (bot, dp, task)

    async def _run_polling(self, dp: Dispatcher, bot: Bot, bot_id: int):
        retry_delay = 5
        max_delay = 120
        while bot_id in self.running_bots:
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
                logger.info("Mirror bot %s polling ended normally", bot_id)
                break
            except (TelegramUnauthorizedError, TelegramBadRequest) as e:
                logger.error("Mirror bot %s invalid token, stopping: %s", bot_id, e)
                break
            except Exception as e:
                if bot_id not in self.running_bots:
                    break
                logger.warning(
                    "Mirror bot %s polling crashed (%s), retrying in %ss...",
                    bot_id, e, retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
                continue
        self.running_bots.pop(bot_id, None)
        try:
            await bot.session.close()
        except Exception:
            pass

    async def stop_mirror_bot(self, user_id: int) -> bool:
        existing_bot = await self.repository.get_by_user_id(user_id)
        if existing_bot and existing_bot.id in self.running_bots:
            bot, dp, task = self.running_bots[existing_bot.id]

            await dp.stop_polling()

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            await bot.session.close()
            del self.running_bots[existing_bot.id]

        return await self.repository.delete_by_user_id(user_id)

    async def restore_all_bots(self):
        bots = await self.repository.get_all()
        logger.info("restore_all_bots: found %d active mirror bots", len(bots))
        for mirror_bot in bots:
            if mirror_bot.id not in self.running_bots:
                try:
                    await self._launch_bot(mirror_bot)
                    logger.info("Launched mirror bot id=%s @%s", mirror_bot.id, mirror_bot.bot_username)
                except Exception as e:
                    logger.error("Failed to launch mirror bot id=%s: %s", mirror_bot.id, e)

    async def get_user_bot(self, user_id: int) -> Optional[MirrorBot]:
        return await self.repository.get_by_user_id(user_id)

    async def get_user_bots(self, user_id: int) -> List[MirrorBot]:
        if hasattr(self.repository, "get_all_by_user_id"):
            return await self.repository.get_all_by_user_id(user_id)
        bot = await self.repository.get_by_user_id(user_id)
        return [bot] if bot else []

    async def shutdown_all(self):
        """Stop all running mirror bots safely (single-pass snapshot to avoid race)."""
        snapshot = list(self.running_bots.items())
        for bot_id, (bot, dp, task) in snapshot:
            try:
                await dp.stop_polling()
            except Exception:
                pass
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            try:
                await bot.session.close()
            except Exception:
                pass

        self.running_bots.clear()

    async def update_bot_username(self, bot_id: int, bot_username: str) -> bool:
        """Обновить username конкретного бота в базе данных по bot_id"""
        try:
            from shared.database.session import async_session_maker
            from shared.database.models import MirrorBot as MirrorBotModel
            from sqlalchemy import update

            async with async_session_maker() as session:
                stmt = update(MirrorBotModel).where(
                    MirrorBotModel.id == bot_id
                ).values(bot_username=bot_username)
                await session.execute(stmt)
                await session.commit()

            return True
        except Exception:
            return False

    async def start_bot_by_id(self, bot_id: int) -> bool:
        """Запустить бота по ID"""
        try:
            mirror_bot = await self.repository.get_by_id(bot_id)
            if not mirror_bot:
                logger.warning("start_bot_by_id: bot %s not found in DB", bot_id)
                return False

            if mirror_bot.id in self.running_bots:
                logger.info("start_bot_by_id: bot %s already running", bot_id)
                return True

            await self._launch_bot(mirror_bot)
            logger.info("start_bot_by_id: bot %s (@%s) launched", bot_id, mirror_bot.bot_username)
            return True

        except Exception as e:
            logger.error("Error starting bot by ID %s: %s", bot_id, e, exc_info=True)
            return False

    async def stop_bot_by_id(self, bot_id: int) -> bool:
        """Остановить бота по ID"""
        try:
            mirror_bot = await self.repository.get_by_id(bot_id)
            if not mirror_bot:
                return False

            if mirror_bot.id in self.running_bots:
                bot, dp, task = self.running_bots[mirror_bot.id]

                await dp.stop_polling()

                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                await bot.session.close()
                del self.running_bots[mirror_bot.id]

            return True

        except Exception as e:
            logger.error("Error stopping bot by ID %s: %s", bot_id, e)
            return False

    async def is_bot_running(self, bot_id: int) -> bool:
        """Проверить, запущен ли бот"""
        try:
            mirror_bot = await self.repository.get_by_id(bot_id)
            if not mirror_bot:
                return False

            return mirror_bot.id in self.running_bots

        except Exception as e:
            logger.error("Error checking bot status %s: %s", bot_id, e)
            return False
