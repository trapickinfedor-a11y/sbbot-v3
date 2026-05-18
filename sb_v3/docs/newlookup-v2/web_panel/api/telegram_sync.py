"""
API для синхронизации данных с Telegram
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from web_panel.database import get_db
from web_panel.auth import get_current_user
from web_panel.services.telegram_info import TelegramInfoService
from shared.database.models import MirrorBot, User
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sync/bot-usernames")
async def sync_bot_usernames(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Синхронизирует username всех ботов с Telegram API"""
    try:
        # Получаем всех ботов из базы данных
        stmt = select(MirrorBot.id, MirrorBot.bot_token).where(MirrorBot.is_active == True)
        result = await db.execute(stmt)
        bots = result.fetchall()
        
        if not bots:
            return {"message": "Активные боты не найдены", "updated_count": 0}
        
        # Создаем словарь {bot_id: bot_token}
        bot_tokens = {bot.id: bot.bot_token for bot in bots}
        
        # Обновляем username'ы
        updated_count = await TelegramInfoService.update_bot_usernames(db, bot_tokens)
        
        return {
            "message": f"Обновлено {updated_count} из {len(bots)} ботов",
            "updated_count": updated_count,
            "total_bots": len(bots)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при синхронизации username ботов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")


@router.post("/sync/user-usernames")
async def sync_user_usernames(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Синхронизирует username пользователей с Telegram API (ограниченное количество)"""
    try:
        # Получаем пользователей без username и их ботов
        stmt = select(
            User.id,
            User.user_id,
            MirrorBot.bot_token
        ).join(
            MirrorBot, User.mirror_bot_id == MirrorBot.id
        ).where(
            User.username.is_(None),
            MirrorBot.is_active == True
        ).limit(limit)
        
        result = await db.execute(stmt)
        users = result.fetchall()
        
        if not users:
            return {"message": "Пользователи без username не найдены", "updated_count": 0}
        
        # Создаем список данных для обновления
        user_data = [(user.id, user.user_id, user.bot_token) for user in users]
        
        # Обновляем username'ы
        updated_count = await TelegramInfoService.update_user_usernames(db, user_data)
        
        return {
            "message": f"Обновлено {updated_count} из {len(users)} пользователей",
            "updated_count": updated_count,
            "total_processed": len(users)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при синхронизации username пользователей: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")


@router.get("/sync/status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получает статус синхронизации (сколько ботов и пользователей без username)"""
    try:
        # Считаем ботов без username
        bots_without_username_stmt = select(MirrorBot.id).where(
            MirrorBot.bot_username.is_(None),
            MirrorBot.is_active == True
        )
        bots_result = await db.execute(bots_without_username_stmt)
        bots_without_username = len(bots_result.fetchall())
        
        # Считаем пользователей без username
        users_without_username_stmt = select(User.id).where(User.username.is_(None))
        users_result = await db.execute(users_without_username_stmt)
        users_without_username = len(users_result.fetchall())
        
        # Общее количество
        total_bots_stmt = select(MirrorBot.id).where(MirrorBot.is_active == True)
        total_bots_result = await db.execute(total_bots_stmt)
        total_bots = len(total_bots_result.fetchall())
        
        total_users_stmt = select(User.id)
        total_users_result = await db.execute(total_users_stmt)
        total_users = len(total_users_result.fetchall())
        
        return {
            "bots": {
                "total": total_bots,
                "without_username": bots_without_username,
                "with_username": total_bots - bots_without_username
            },
            "users": {
                "total": total_users,
                "without_username": users_without_username,
                "with_username": total_users - users_without_username
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статуса синхронизации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса: {str(e)}")
