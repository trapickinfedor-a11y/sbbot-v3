from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from main_bot.app.repository.base import BotRepository
from main_bot.app.domain.entities import MirrorBot as MirrorBotEntity
from shared.database.models import MirrorBot as MirrorBotModel
from shared.database.session import async_session_maker, init_db


class PostgresBotRepository(BotRepository):
    """PostgreSQL репозиторий для управления зеркальными ботами"""

    async def init_db(self):
        """Инициализация БД (создание таблиц)"""
        await init_db()

    async def create(self, bot: MirrorBotEntity) -> MirrorBotEntity:
        """Создать нового бота"""
        async with async_session_maker() as session:
            db_bot = MirrorBotModel(
                bot_token=bot.bot_token,
                bot_username=bot.bot_username,
                owner_user_id=bot.user_id,
                is_active=True,
                created_at=bot.created_at
            )
            session.add(db_bot)
            await session.commit()
            await session.refresh(db_bot)

            bot.id = db_bot.id
            return bot

    async def get_by_token(self, bot_token: str) -> Optional[MirrorBotEntity]:
        """Получить активного бота по токену"""
        async with async_session_maker() as session:
            stmt = select(MirrorBotModel).where(
                MirrorBotModel.bot_token == bot_token,
                MirrorBotModel.is_active == True
            )
            result = await session.execute(stmt)
            db_bot = result.scalar_one_or_none()

            if db_bot:
                return MirrorBotEntity(
                    id=db_bot.id,
                    user_id=db_bot.owner_user_id,
                    bot_token=db_bot.bot_token,
                    bot_username=db_bot.bot_username or "",
                    created_at=db_bot.created_at
                )
            return None

    async def get_by_user_id(self, user_id: int) -> Optional[MirrorBotEntity]:
        """Получить первого активного бота по user_id"""
        bots = await self.get_all_by_user_id(user_id)
        return bots[0] if bots else None

    async def get_all_by_user_id(self, user_id: int) -> List[MirrorBotEntity]:
        """Получить все активные боты владельца"""
        async with async_session_maker() as session:
            stmt = select(MirrorBotModel).where(
                MirrorBotModel.owner_user_id == user_id,
                MirrorBotModel.is_active == True
            ).order_by(MirrorBotModel.id)
            result = await session.execute(stmt)
            db_bots = result.scalars().all()
            return [
                MirrorBotEntity(
                    id=db_bot.id,
                    user_id=db_bot.owner_user_id,
                    bot_token=db_bot.bot_token,
                    bot_username=db_bot.bot_username or "",
                    created_at=db_bot.created_at
                )
                for db_bot in db_bots
            ]

    async def get_by_id(self, bot_id: int) -> Optional[MirrorBotEntity]:
        """Получить бота по ID"""
        async with async_session_maker() as session:
            stmt = select(MirrorBotModel).where(MirrorBotModel.id == bot_id)
            result = await session.execute(stmt)
            db_bot = result.scalar_one_or_none()

            if db_bot:
                return MirrorBotEntity(
                    id=db_bot.id,
                    user_id=db_bot.owner_user_id,
                    bot_token=db_bot.bot_token,
                    bot_username=db_bot.bot_username or "",
                    created_at=db_bot.created_at
                )
            return None

    async def get_all(self) -> List[MirrorBotEntity]:
        """Получить все активные боты"""
        async with async_session_maker() as session:
            stmt = select(MirrorBotModel).where(MirrorBotModel.is_active == True)
            result = await session.execute(stmt)
            db_bots = result.scalars().all()

            return [
                MirrorBotEntity(
                    id=db_bot.id,
                    user_id=db_bot.owner_user_id,
                    bot_token=db_bot.bot_token,
                    bot_username=db_bot.bot_username or "",
                    created_at=db_bot.created_at
                )
                for db_bot in db_bots
            ]

    async def reactivate(self, bot_id: int, bot_username: Optional[str] = None) -> bool:
        """Реактивировать бота"""
        async with async_session_maker() as session:
            stmt = select(MirrorBotModel).where(MirrorBotModel.id == bot_id)
            result = await session.execute(stmt)
            db_bot = result.scalar_one_or_none()

            if db_bot:
                db_bot.is_active = True
                if bot_username:
                    db_bot.bot_username = bot_username
                await session.commit()
                return True
            return False

    async def delete_by_user_id(self, user_id: int) -> bool:
        """Деактивировать все боты пользователя (мягкое удаление)"""
        async with async_session_maker() as session:
            stmt = select(MirrorBotModel).where(
                MirrorBotModel.owner_user_id == user_id,
                MirrorBotModel.is_active == True
            )
            result = await session.execute(stmt)
            db_bots = result.scalars().all()

            if not db_bots:
                return False
            for db_bot in db_bots:
                db_bot.is_active = False
            await session.commit()
            return True
