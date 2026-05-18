"""
API для управления ботами
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os
import uuid
import aiofiles
from aiogram.types import FSInputFile
# Локальные константы заменены на мультиязычные функции

from web_panel.auth import get_current_user, require_page_access, require_role, ROLE_SUPER_ADMIN, ROLE_OWNER
from web_panel.database import get_db
from web_panel.utils.multilang import get_user_admin_message_prefix, get_user_admin_broadcast_prefix
from shared.security.internal_api import build_internal_api_headers

logger = logging.getLogger(__name__)
from shared.database.models import MirrorBot, User, Order, MarketerOwnBot
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
import asyncio

router = APIRouter()

BOT_TYPE_LABELS = {
    "admin": "Мой",
    "user": "Пользователь",
    "marketer": "Маркетолог",
}


class BotResponse(BaseModel):
    id: int
    bot_token: str
    bot_username: Optional[str]
    owner_user_id: int
    bot_type: str = "user"
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BotBroadcastRequest(BaseModel):
    message: str
    include_photo: Optional[str] = None


class BotUpdate(BaseModel):
    is_active: Optional[bool] = None
    bot_type: Optional[str] = None


def _mask_bot_token(token: Optional[str]) -> str:
    if not token:
        return ""
    if len(token) <= 12:
        return "*" * len(token)
    return f"{token[:6]}...{token[-4:]}"


@router.get("/")
async def get_bots(
    is_active: Optional[bool] = None,
    bot_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("bots"))
):
    """Получить список всех ботов с пагинацией"""

    stmt = select(MirrorBot)

    if is_active is not None:
        stmt = stmt.where(MirrorBot.is_active == is_active)

    if bot_type is not None and bot_type in ("admin", "user", "marketer"):
        stmt = stmt.where(MirrorBot.bot_type == bot_type)

    stmt = stmt.order_by(MirrorBot.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    bots = result.scalars().all()

    marketer_tokens_result = await db.execute(select(MarketerOwnBot.bot_token))
    marketer_tokens = {row[0] for row in marketer_tokens_result.all()}

    bots_with_stats = []
    for bot in bots:
        user_count_stmt = select(func.count(User.id)).where(User.mirror_bot_id == bot.id)
        user_count_result = await db.execute(user_count_stmt)
        user_count = user_count_result.scalar_one()

        resolved_type = bot.bot_type or "user"
        if resolved_type == "user" and bot.bot_token in marketer_tokens:
            resolved_type = "marketer"

        bots_with_stats.append({
            "id": bot.id,
            "bot_token": bot.bot_token if current_user.get("role") in (ROLE_SUPER_ADMIN, ROLE_OWNER) else _mask_bot_token(bot.bot_token),
            "bot_username": bot.bot_username,
            "owner_user_id": bot.owner_user_id,
            "owner_telegram_id": bot.owner_user_id,
            "bot_type": resolved_type,
            "bot_type_label": BOT_TYPE_LABELS.get(resolved_type, resolved_type),
            "is_active": bot.is_active,
            "created_at": bot.created_at,
            "users_count": user_count
        })

    return {
        "items": bots_with_stats,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{bot_id}")
async def get_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("bots"))
):
    """Получить информацию о боте"""
    
    stmt = select(MirrorBot).where(MirrorBot.id == bot_id)
    result = await db.execute(stmt)
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    resolved_type = bot.bot_type or "user"
    if resolved_type == "user":
        mkt = await db.execute(
            select(MarketerOwnBot.id).where(MarketerOwnBot.bot_token == bot.bot_token).limit(1)
        )
        if mkt.scalar_one_or_none():
            resolved_type = "marketer"

    return {
        "id": bot.id,
        "bot_token": bot.bot_token if current_user.get("role") == ROLE_SUPER_ADMIN else _mask_bot_token(bot.bot_token),
        "bot_username": bot.bot_username,
        "owner_user_id": bot.owner_user_id,
        "bot_type": resolved_type,
        "bot_type_label": BOT_TYPE_LABELS.get(resolved_type, resolved_type),
        "is_active": bot.is_active,
        "created_at": bot.created_at,
    }


@router.put("/{bot_id}")
async def update_bot(
    bot_id: int,
    data: BotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("bots"))
):
    """Обновить бота"""

    stmt = select(MirrorBot).where(MirrorBot.id == bot_id)
    result = await db.execute(stmt)
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if data.bot_type is not None and data.bot_type in ("admin", "user", "marketer"):
        bot.bot_type = data.bot_type

    if data.is_active is not None:
        bot.is_active = data.is_active

    # Если изменился статус активности, сначала уведомляем main_bot,
    # и только при успехе сохраняем изменения в БД
    if data.is_active is not None:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    os.getenv("MAIN_BOT_API_URL", "http://main_bot:8080") + "/bot/toggle",
                    json={
                        "bot_id": bot_id,
                        "is_active": data.is_active
                    },
                    headers=build_internal_api_headers(),
                    timeout=10.0
                )
                if response.status_code != 200:
                    await db.rollback()
                    raise HTTPException(
                        status_code=502,
                        detail=f"main_bot rejected toggle: {response.text}"
                    )
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error notifying main_bot about bot {bot_id} status change: {e}")
            raise HTTPException(
                status_code=502,
                detail="Failed to reach main_bot service; bot status unchanged."
            )

    await db.commit()
    await db.refresh(bot)

    return {
        "message": "Bot updated successfully",
        "bot_id": bot_id,
        "is_active": bot.is_active
    }


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role(ROLE_SUPER_ADMIN))
):
    """Удалить бота"""
    
    stmt = select(MirrorBot).where(MirrorBot.id == bot_id)
    result = await db.execute(stmt)
    bot = result.scalar_one_or_none()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    users_count_result = await db.execute(
        select(func.count(User.id)).where(User.mirror_bot_id == bot_id)
    )
    users_count = users_count_result.scalar_one()

    orders_count_result = await db.execute(
        select(func.count(Order.id)).where(Order.mirror_bot_id == bot_id)
    )
    orders_count = orders_count_result.scalar_one()

    if users_count or orders_count:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot delete bot with linked data. "
                f"Users: {users_count}, orders: {orders_count}. "
                "Deactivate it instead or migrate related records first."
            ),
        )

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                os.getenv("MAIN_BOT_API_URL", "http://main_bot:8080") + "/bot/toggle",
                json={
                    "bot_id": bot_id,
                    "is_active": False,
                },
                headers=build_internal_api_headers(),
                timeout=10.0,
            )
            if response.status_code != 200:
                logger.warning(
                    "Failed to stop bot %s before deletion: %s",
                    bot_id,
                    response.text,
                )
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id} before deletion: {e}")

    await db.delete(bot)
    await db.commit()
    
    return {"message": "Bot deleted successfully"}


@router.get("/{bot_id}/users")
async def get_bot_users(
    bot_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить пользователей бота"""
    
    stmt = select(User).where(User.mirror_bot_id == bot_id).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "balance": float(user.balance),
            "is_banned": user.is_banned,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.get("/{bot_id}/stats")
async def get_bot_stats(
    bot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить статистику бота"""
    
    # Пользователи
    stmt = select(
        func.count(User.id).label("total_users"),
        func.sum(User.balance).label("total_balance")
    ).where(User.mirror_bot_id == bot_id)
    
    result = await db.execute(stmt)
    user_stats = result.first()
    
    # Заказы
    stmt = select(
        func.count(Order.id).label("total_orders"),
        func.sum(Order.price).label("total_revenue")
    ).where(Order.mirror_bot_id == bot_id)
    
    result = await db.execute(stmt)
    order_stats = result.first()
    
    return {
        "bot_id": bot_id,
        "total_users": user_stats.total_users or 0,
        "total_balance": float(user_stats.total_balance or 0),
        "total_orders": order_stats.total_orders or 0,
        "total_revenue": float(order_stats.total_revenue or 0)
    }


@router.post("/{bot_id}/broadcast")
async def broadcast_to_bot_users(
    bot_id: int,
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Рассылка сообщения всем пользователям бота с поддержкой файлов"""
    
    stmt = select(MirrorBot).where(MirrorBot.id == bot_id)
    result = await db.execute(stmt)
    mirror_bot = result.scalar_one_or_none()
    
    if not mirror_bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Получаем пользователей
    stmt = select(User).where(User.mirror_bot_id == bot_id)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    if not users:
        return {"message": "No users found", "sent": 0, "failed": 0}
    
    temp_file_path = None
    
    try:
        # Сохраняем файл если есть
        if file and file.size > 0:
            temp_dir = "/tmp/admin_broadcasts"
            os.makedirs(temp_dir, exist_ok=True)
            
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
            temp_filename = f"{uuid.uuid4()}{file_extension}"
            temp_file_path = os.path.join(temp_dir, temp_filename)
            
            async with aiofiles.open(temp_file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        
        bot = Bot(token=mirror_bot.bot_token)
        sent = 0
        failed = 0
        content_type = (file.content_type or "") if file else ""

        try:
            for user in users:
                try:
                    admin_prefix = await get_user_admin_message_prefix(db, user.user_id, bot_id)
                    if temp_file_path:
                        if content_type.startswith('image/'):
                            await bot.send_photo(chat_id=user.user_id, photo=FSInputFile(temp_file_path), caption=f"{admin_prefix}{message}", parse_mode="HTML")
                        elif content_type.startswith('video/'):
                            await bot.send_video(chat_id=user.user_id, video=FSInputFile(temp_file_path), caption=f"{admin_prefix}{message}", parse_mode="HTML")
                        else:
                            await bot.send_document(chat_id=user.user_id, document=FSInputFile(temp_file_path), caption=f"{admin_prefix}{message}", parse_mode="HTML")
                    else:
                        await bot.send_message(chat_id=user.user_id, text=f"{admin_prefix}{message}", parse_mode="HTML")
                    sent += 1
                    await asyncio.sleep(0.05)  # 20 msg/sec — Telegram rate limit
                except TelegramRetryAfter as e:
                    logger.warning("Broadcast rate limit, sleeping %s s", e.retry_after)
                    await asyncio.sleep(e.retry_after)
                    failed += 1
                except TelegramForbiddenError:
                    failed += 1  # пользователь заблокировал бота
                except Exception as e:
                    logger.error("Failed to send broadcast to user %s: %s", user.user_id, e)
                    failed += 1
        finally:
            await bot.session.close()

        return {
            "message": "Broadcast completed",
            "sent": sent,
            "failed": failed,
            "total": len(users)
        }

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error("Failed to delete temp file %s: %s", temp_file_path, e)


@router.post("/broadcast-all")
async def broadcast_to_all_bots(
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Рассылка сообщения всем пользователям всех ботов с поддержкой файлов"""
    
    stmt = select(MirrorBot).where(MirrorBot.is_active == True)
    result = await db.execute(stmt)
    bots = result.scalars().all()
    
    temp_file_path = None
    
    try:
        # Сохраняем файл если есть
        if file and file.size > 0:
            temp_dir = "/tmp/admin_broadcasts"
            os.makedirs(temp_dir, exist_ok=True)
            
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
            temp_filename = f"{uuid.uuid4()}{file_extension}"
            temp_file_path = os.path.join(temp_dir, temp_filename)
            
            async with aiofiles.open(temp_file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        
        total_sent = 0
        total_failed = 0
        
        ct = (file.content_type or "") if file else ""
        for mirror_bot in bots:
            stmt = select(User).where(User.mirror_bot_id == mirror_bot.id)
            result = await db.execute(stmt)
            users = result.scalars().all()

            bot = Bot(token=mirror_bot.bot_token)
            try:
                for user in users:
                    try:
                        broadcast_prefix = await get_user_admin_broadcast_prefix(db, user.user_id, mirror_bot.id)
                        if temp_file_path:
                            if ct.startswith('image/'):
                                await bot.send_photo(chat_id=user.user_id, photo=FSInputFile(temp_file_path), caption=f"{broadcast_prefix}{message}", parse_mode="HTML")
                            elif ct.startswith('video/'):
                                await bot.send_video(chat_id=user.user_id, video=FSInputFile(temp_file_path), caption=f"{broadcast_prefix}{message}", parse_mode="HTML")
                            else:
                                await bot.send_document(chat_id=user.user_id, document=FSInputFile(temp_file_path), caption=f"{broadcast_prefix}{message}", parse_mode="HTML")
                        else:
                            await bot.send_message(chat_id=user.user_id, text=f"{broadcast_prefix}{message}", parse_mode="HTML")
                        total_sent += 1
                        await asyncio.sleep(0.05)  # 20 msg/sec
                    except TelegramRetryAfter as e:
                        logger.warning("All-bots broadcast rate limit, sleeping %s s", e.retry_after)
                        await asyncio.sleep(e.retry_after)
                        total_failed += 1
                    except TelegramForbiddenError:
                        total_failed += 1
                    except Exception as e:
                        logger.error("Failed to send broadcast to user %s via bot %s: %s", user.user_id, mirror_bot.id, e)
                        total_failed += 1
            finally:
                await bot.session.close()
        
        return {
            "message": "Broadcast to all bots completed",
            "sent": total_sent,
            "failed": total_failed,
            "bots_count": len(bots)
        }
    
    finally:
        # Удаляем временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error("Failed to delete temp file %s: %s", temp_file_path, e)


@router.post("/update-usernames")
async def update_bot_usernames(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновить username для всех ботов"""
    
    stmt = select(MirrorBot)
    result = await db.execute(stmt)
    bots = result.scalars().all()
    
    updated = 0
    failed = 0
    results = []
    
    for mirror_bot in bots:
        try:
            # Создаем экземпляр бота
            bot = Bot(token=mirror_bot.bot_token)
            
            # Получаем информацию о боте
            bot_info = await bot.get_me()
            
            # Обновляем username
            old_username = mirror_bot.bot_username
            mirror_bot.bot_username = bot_info.username
            
            results.append({
                "bot_id": mirror_bot.id,
                "old_username": old_username,
                "new_username": bot_info.username,
                "status": "success"
            })
            
            await bot.session.close()
            updated += 1
            
        except Exception as e:
            results.append({
                "bot_id": mirror_bot.id,
                "old_username": mirror_bot.bot_username,
                "new_username": None,
                "status": "error",
                "error": str(e)
            })
            failed += 1
    
    # Сохраняем изменения
    await db.commit()
    
    return {
        "message": "Username update completed",
        "updated": updated,
        "failed": failed,
        "results": results
    }

