from __future__ import annotations

"""
API для управления рассылками
ВАЖНО: Рассылки с файлами используют временное хранение на сервере!
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from sqlalchemy import delete, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezon, timezone
from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
import os
import uuid
import logging
import asyncio

from web_panel.auth import require_page_access
from web_panel.database import get_db
from shared.database.models import Broadcast, BroadcastTranslation, Marketer, MirrorBot, Seller, User, Worker
from web_panel.services.audit_service import log_action

router = APIRouter()
logger = logging.getLogger(__name__)
SUPPORTED_BROADCAST_LANGUAGES = ("en", "ru", "zh", "es")
SUPPORTED_AUDIENCES = {"users", "workers", "sellers", "marketers", "all"}


class BroadcastCreate(BaseModel):
    mirror_bot_id: Optional[int] = None  # None = всем ботам
    bot_type: Optional[str] = None  # admin/marketer/user (filter bots by type)
    audience: str = "users"
    seller_type: Optional[str] = None  # internal / external (only for audience=sellers)
    message_text: Optional[str] = None
    translations: Optional[Dict[str, str]] = None
    files: Optional[List[dict]] = None
    buttons: Optional[List[dict]] = None  # [{text, url}] inline keyboard buttons
    scheduled_at: Optional[datetime] = None  # Если задано — отправить в это время
    notify_team: bool = False  # Отправить уведомление команде (админам)


class BroadcastResponse(BaseModel):
    id: int
    mirror_bot_id: Optional[int]
    bot_type: Optional[str]  # admin/marketer/user
    audience: str
    message_text: str
    translations: Dict[str, str] = Field(default_factory=dict)
    languages: List[str] = Field(default_factory=list)
    files: Optional[List[dict]]
    buttons: Optional[List[dict]] = None
    status: str
    scheduled_at: Optional[datetime]
    total_users: int
    sent_count: int
    failed_count: int
    created_by: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


def normalize_broadcast_translations(
    message_text: Optional[str],
    translations: Optional[Dict[str, str]],
) -> Dict[str, str]:
    """Normalize multilingual broadcast payload and keep only supported languages."""
    cleaned: Dict[str, str] = {}
    if translations:
        for language, text in translations.items():
            language_code = (language or "").strip().lower()
            normalized_text = (text or "").strip()
            if language_code in SUPPORTED_BROADCAST_LANGUAGES and normalized_text:
                cleaned[language_code] = normalized_text

    fallback_text = (message_text or "").strip()
    if fallback_text and "en" not in cleaned:
        cleaned["en"] = fallback_text

    if not cleaned:
        raise HTTPException(status_code=400, detail="At least one broadcast text is required")

    return cleaned


def build_broadcast_response(broadcast: Broadcast, translations: Dict[str, str]) -> BroadcastResponse:
    message_text = translations.get("en") or broadcast.message_text
    scheduled_at = broadcast.scheduled_at
    if scheduled_at and scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    return BroadcastResponse(
        id=broadcast.id,
        mirror_bot_id=broadcast.mirror_bot_id,
        bot_type=getattr(broadcast, "bot_type", None),
        audience=getattr(broadcast, "audience", "users"),
        message_text=message_text,
        translations=translations,
        languages=sorted(translations.keys()),
        files=broadcast.files,
        buttons=getattr(broadcast, "buttons", None),
        status=broadcast.status,
        scheduled_at=scheduled_at,
        total_users=broadcast.total_users,
        sent_count=broadcast.sent_count,
        failed_count=broadcast.failed_count,
        created_by=broadcast.created_by,
        created_at=broadcast.created_at,
        started_at=broadcast.started_at,
        completed_at=broadcast.completed_at,
    )


def normalize_audience(audience: Optional[str]) -> str:
    normalized = (audience or "users").strip().lower()
    if normalized not in SUPPORTED_AUDIENCES:
        raise HTTPException(status_code=400, detail=f"Unsupported audience: {audience}")
    return normalized


async def count_broadcast_targets(
    session: AsyncSession,
    audience: str,
    mirror_bot_id: Optional[int],
    bot_type: Optional[str] = None,  # New: filter by bot type
) -> int:
    total = 0
    if audience in {"users", "all"}:
        if mirror_bot_id:
            stmt = select(func.count(User.id)).where(and_(User.mirror_bot_id == mirror_bot_id, User.is_banned == False))
        elif bot_type:
            # Filter users by bot type
            stmt = select(func.count(User.id)).join(MirrorBot, User.mirror_bot_id == MirrorBot.id).where(
                and_(MirrorBot.bot_type == bot_type, User.is_banned == False)
            )
        else:
            stmt = select(func.count(User.id)).where(User.is_banned == False)
        total += (await session.execute(stmt)).scalar_one() or 0
    if audience in {"workers", "all"}:
        total += (await session.execute(select(func.count(Worker.id)).where(Worker.is_active == True))).scalar_one() or 0
    if audience in {"sellers", "all"}:
        total += (await session.execute(select(func.count(Seller.id)).where(Seller.is_active == True))).scalar_one() or 0
    if audience in {"marketers", "all"}:
        total += (await session.execute(select(func.count(Marketer.id)).where(Marketer.is_active == True))).scalar_one() or 0
    return total


async def load_broadcast_targets(
    session: AsyncSession,
    *,
    audience: str,
    mirror_bot_id: Optional[int],
    bot_type: Optional[str] = None,  # New: filter by bot type
) -> list[dict]:
    targets: list[dict] = []
    seen: set[tuple[str, int]] = set()

    def _append_target(token: str | None, chat_id: int | None, language: str | None = None) -> None:
        normalized_token = (token or "").strip()
        if not normalized_token or not chat_id:
            return
        key = (normalized_token, int(chat_id))
        if key in seen:
            return
        seen.add(key)
        targets.append({"token": normalized_token, "chat_id": int(chat_id), "language": (language or "en").lower()})

    if audience in {"users", "all"}:
        if mirror_bot_id:
            bot_rows = [await session.scalar(select(MirrorBot).where(MirrorBot.id == mirror_bot_id))]
        elif bot_type:
            # Filter bots by type
            bot_rows = list((await session.execute(select(MirrorBot).where(and_(MirrorBot.is_active == True, MirrorBot.bot_type == bot_type)))).scalars().all())
        else:
            bot_rows = list((await session.execute(select(MirrorBot).where(MirrorBot.is_active == True))).scalars().all())
        for mirror_bot in bot_rows:
            if not mirror_bot:
                continue
            users = list((await session.execute(select(User).where(and_(User.mirror_bot_id == mirror_bot.id, User.is_banned == False)))).scalars().all())
            for user in users:
                _append_target(mirror_bot.bot_token, user.user_id, getattr(user, "language", "en"))

    if audience in {"workers", "all"}:
        worker_token = os.getenv("WORKER_BOT_TOKEN", "").strip()
        workers = list((await session.execute(select(Worker).where(Worker.is_active == True))).scalars().all())
        for worker in workers:
            _append_target(worker_token, worker.telegram_id, "en")

    if audience in {"sellers", "all"}:
        seller_token = os.getenv("SELLER_BOT_TOKEN", "").strip()
        sellers = list((await session.execute(select(Seller).where(Seller.is_active == True))).scalars().all())
        for seller in sellers:
            _append_target(seller_token, seller.telegram_id, getattr(seller, "language", "en"))

    if audience in {"marketers", "all"}:
        marketer_token = os.getenv("MARKETER_BOT_TOKEN", "").strip()
        marketers = list((await session.execute(select(Marketer).where(Marketer.is_active == True))).scalars().all())
        for marketer in marketers:
            _append_target(marketer_token, marketer.telegram_id, "en")

    return targets


def _build_reply_markup(buttons: Optional[list]) -> Optional[object]:
    """Собирает InlineKeyboardMarkup из списка [{text, url}]."""
    if not buttons:
        return None
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb_buttons = []
        for btn in buttons:
            text = (btn.get("text") or "").strip()
            url = (btn.get("url") or "").strip()
            if text and url:
                kb_buttons.append([InlineKeyboardButton(text=text, url=url)])
        if not kb_buttons:
            return None
        return InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    except Exception:
        return None


async def send_with_rate_limit(
    bot: Bot,
    user_id: int,
    text: str,
    max_retries: int = 3,
    reply_markup=None,
) -> bool:
    """
    Отправка сообщения с учетом Telegram rate limits
    
    Args:
        bot: Bot экземпляр
        user_id: ID пользователя
        text: Текст сообщения
        max_retries: Максимальное количество попыток
        
    Returns:
        True если успешно, False otherwise
    """
    for attempt in range(max_retries):
        try:
            await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=reply_markup)
            await asyncio.sleep(0.05)  # 20 msg/sec (безопасно)
            return True
        
        except TelegramRetryAfter as e:
            # Telegram просит подождать
            logger.warning(f"Rate limit hit, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
        
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            logger.info(f"User {user_id} blocked the bot")
            return False
        
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            if attempt == max_retries - 1:
                return False
            await asyncio.sleep(1)
    
    return False


async def send_file_with_rate_limit(
    bot: Bot,
    user_id: int,
    file_path: str,
    file_type: str,
    max_retries: int = 3
) -> bool:
    """
    Отправка файла с учетом Telegram rate limits
    
    Args:
        bot: Bot экземпляр
        user_id: ID пользователя
        file_path: Путь к файлу
        file_type: Тип файла (photo/video/document)
        max_retries: Максимальное количество попыток
        
    Returns:
        True если успешно, False otherwise
    """
    for attempt in range(max_retries):
        try:
            if file_type == "photo":
                await bot.send_photo(user_id, photo=FSInputFile(file_path))
            elif file_type == "video":
                await bot.send_video(user_id, video=FSInputFile(file_path))
            else:  # document
                await bot.send_document(user_id, document=FSInputFile(file_path))
            
            await asyncio.sleep(0.05)  # 20 msg/sec (безопасно)
            return True
        
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limit hit, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
        
        except TelegramForbiddenError:
            logger.info(f"User {user_id} blocked the bot")
            return False
        
        except Exception as e:
            logger.error(f"Failed to send file to {user_id}: {e}")
            if attempt == max_retries - 1:
                return False
            await asyncio.sleep(1)
    
    return False


async def download_broadcast_file(file_info: dict, session) -> Optional[str]:
    """
    Скачать файл из Telegram для рассылки
    
    Args:
        file_info: Информация о файле с file_id
        session: Сессия БД
        
    Returns:
        Путь к временному файлу или None
    """
    try:
        # Берем любой активный бот для скачивания
        bot_result = await session.execute(
            select(MirrorBot).where(MirrorBot.is_active == True).limit(1)
        )
        any_bot = bot_result.scalar_one_or_none()
        
        if not any_bot:
            logger.error("No active bots found for downloading broadcast file")
            return None
        
        bot = Bot(token=any_bot.bot_token)
        
        try:
            file_id = file_info.get("file_id")
            if not file_id:
                return None
            
            # Получаем файл из Telegram
            file = await bot.get_file(file_id)
            
            # Скачиваем в /tmp/
            ext = os.path.splitext(file.file_path)[1] or ".tmp"
            temp_path = f"/tmp/broadcast_{uuid.uuid4()}{ext}"
            
            await bot.download_file(file.file_path, temp_path)
            
            logger.info(f"Downloaded broadcast file to {temp_path}")
            return temp_path
        
        finally:
            await bot.session.close()
    
    except Exception as e:
        logger.error(f"Failed to download broadcast file: {e}")
        return None


async def send_broadcast_task(broadcast_id: int, db_url: str):
    """
    Фоновая задача для отправки рассылки.
    Файлы скачиваются ОДИН РАЗ, затем отправляются через каждый Mirror Bot.
    Движок явно закрывается после завершения, чтобы не было утечки соединений.
    """
    from shared.database.session import async_session_maker
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession as AS

    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_maker = sessionmaker(engine, class_=AS, expire_on_commit=False)
    try:
        async with session_maker() as session:
            # Получаем рассылку
            result = await session.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()

            if not broadcast:
                return

            # Обновляем статус
            broadcast.status = "in_progress"
            broadcast.started_at = datetime.now(timezone.utc)
            await session.commit()

            translations_result = await session.execute(
                select(BroadcastTranslation).where(BroadcastTranslation.broadcast_id == broadcast.id)
            )
            translation_rows = translations_result.scalars().all()
            translations = {
                row.language: row.message_text
                for row in translation_rows
                if row.language in SUPPORTED_BROADCAST_LANGUAGES and row.message_text
            }
            fallback_message = translations.get("en") or broadcast.message_text

            audience = normalize_audience(getattr(broadcast, "audience", "users"))
            # Pass bot_type to load function for filtering
            targets = await load_broadcast_targets(
                session,
                audience=audience,
                mirror_bot_id=broadcast.mirror_bot_id,
                bot_type=getattr(broadcast, "bot_type", None),
            )
            if not targets:
                broadcast.status = "failed"
                broadcast.completed_at = datetime.now(timezone.utc)
                await session.commit()
                return

            sent_count = 0
            failed_count = 0
            checkpoint_size = 100  # Checkpoint каждые 100 сообщений

            # Скачать файлы ОДИН РАЗ перед отправкой
            temp_files = []
            if broadcast.files:
                logger.info(f"Downloading {len(broadcast.files)} files for broadcast {broadcast_id}")
                for file_info in broadcast.files:
                    try:
                        temp_path = await download_broadcast_file(file_info, session)
                        if temp_path:
                            temp_files.append({
                                "path": temp_path,
                                "type": file_info.get("type", "document")
                            })
                            logger.info(f"Downloaded file: {temp_path}")
                        else:
                            logger.warning(f"Failed to download file: {file_info}")
                    except Exception as e:
                        logger.error(f"Error downloading file: {e}")

            reply_markup = _build_reply_markup(getattr(broadcast, "buttons", None))
            bot_cache: Dict[str, Bot] = {}
            try:
                for target in targets:
                    token = target["token"]
                    if token not in bot_cache:
                        bot_cache[token] = Bot(token=token)
                    bot = bot_cache[token]

                    broadcast_text = translations.get(target["language"]) or fallback_message
                    if not broadcast_text:
                        failed_count += 1
                        continue

                    success = await send_with_rate_limit(
                        bot, target["chat_id"], broadcast_text, reply_markup=reply_markup
                    )
                    if success:
                        files_success = True
                        if temp_files:
                            for temp_file in temp_files:
                                file_sent = await send_file_with_rate_limit(
                                    bot,
                                    target["chat_id"],
                                    temp_file["path"],
                                    temp_file["type"]
                                )
                                if not file_sent:
                                    files_success = False
                        if files_success:
                            sent_count += 1
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1

                    if (sent_count + failed_count) % checkpoint_size == 0:
                        broadcast.sent_count = sent_count
                        broadcast.failed_count = failed_count
                        await session.commit()
                        logger.info(
                            "Broadcast %s: %s/%s processed (%s sent, %s failed)",
                            broadcast_id,
                            sent_count + failed_count,
                            len(targets),
                            sent_count,
                            failed_count,
                        )
                        await asyncio.sleep(0.1)
            finally:
                for bot in bot_cache.values():
                    await bot.session.close()

            # Удалить временные файлы после всех отправок
            for temp_file in temp_files:
                try:
                    file_path = temp_file["path"]
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted temp file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete temp file {temp_file['path']}: {e}")

            # Обновляем итоговую статистику
            broadcast.sent_count = sent_count
            broadcast.failed_count = failed_count
            broadcast.status = "failed-partial" if failed_count else "completed"
            broadcast.completed_at = datetime.now(timezone.utc)

            await session.commit()
    finally:
        # Явно освобождаем пул соединений, чтобы не было утечки
        await engine.dispose()


@router.post("/", response_model=BroadcastResponse)
async def create_broadcast(
    broadcast_data: BroadcastCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("broadcasts"))
):
    """Создать рассылку (сразу или по таймеру)"""
    translations = normalize_broadcast_translations(
        broadcast_data.message_text,
        broadcast_data.translations,
    )
    audience = normalize_audience(broadcast_data.audience)
    # Pass bot_type to count function for filtering
    total_users = await count_broadcast_targets(db, audience, broadcast_data.mirror_bot_id, broadcast_data.bot_type)
    
    scheduled_at = broadcast_data.scheduled_at
    if scheduled_at and scheduled_at.tzinfo is not None:
        scheduled_at = scheduled_at.astimezone(timezone.utc).replace(tzinfo=None)

    now = datetime.now(timezone.utc)
    is_scheduled = (
        scheduled_at is not None
        and scheduled_at > now
    )
    status = "scheduled" if is_scheduled else "pending"
    
    broadcast = Broadcast(
        mirror_bot_id=broadcast_data.mirror_bot_id,
        bot_type=broadcast_data.bot_type,  # Store bot_type filter
        audience=audience,
        message_text=translations.get("en") or next(iter(translations.values())),
        files=broadcast_data.files,
        buttons=broadcast_data.buttons,
        status=status,
        scheduled_at=scheduled_at if is_scheduled else None,
        total_users=total_users,
        sent_count=0,
        failed_count=0,
        created_by=current_user.get("telegram_id") or current_user.get("admin_id") or 0
    )
    
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)

    for language, text in translations.items():
        db.add(
            BroadcastTranslation(
                broadcast_id=broadcast.id,
                language=language,
                message_text=text,
            )
        )

    await log_action(
        db,
        current_user.get("admin_id"),
        "broadcast_create",
        "broadcast",
        broadcast.id,
        {
            "mirror_bot_id": broadcast.mirror_bot_id,
            "audience": audience,
            "scheduled_at": broadcast.scheduled_at.isoformat() if broadcast.scheduled_at else None,
            "languages": sorted(translations.keys()),
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    
    from web_panel.config import web_panel_config
    
    # Send notification to team if requested
    if broadcast_data.notify_team:
        from shared.services.admin_notification_service import AdminNotificationService
        bot_name = "All Bots"
        if broadcast_data.mirror_bot_id:
            bot_result = await db.execute(select(MirrorBot).where(MirrorBot.id == broadcast_data.mirror_bot_id))
            bot = bot_result.scalar_one_or_none()
            if bot:
                bot_name = bot.bot_username or f"Bot #{bot.id}"
        
        schedule_info = f"📅 Scheduled for: {broadcast.scheduled_at.strftime('%Y-%m-%d %H:%M UTC')}" if broadcast.scheduled_at else "🚀 Sending immediately"
        
        await AdminNotificationService.notify_admin_action(
            title="📢 New Broadcast Created",
            lines=[
                f"Bot: {bot_name}",
                f"Audience: {audience} ({total_users} users)",
                f"Languages: {', '.join(sorted(translations.keys()))}",
                schedule_info,
                f"Message preview: {broadcast.message_text[:100]}..." if len(broadcast.message_text) > 100 else f"Message: {broadcast.message_text}",
                f"Created by: {current_user.get('username', 'Unknown')}",
            ],
            event_type="broadcast_created",
        )
    
    if not is_scheduled:
        background_tasks.add_task(send_broadcast_task, broadcast.id, web_panel_config.database_url)
    
    return build_broadcast_response(broadcast, translations)


@router.get("/", response_model=List[BroadcastResponse])
async def get_broadcasts(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("broadcasts"))
):
    """Получить список рассылок"""
    
    stmt = select(Broadcast)
    
    if status:
        stmt = stmt.where(Broadcast.status == status)
    
    stmt = stmt.order_by(Broadcast.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    broadcasts = result.scalars().all()

    broadcast_ids = [broadcast.id for broadcast in broadcasts]
    translations_map: Dict[int, Dict[str, str]] = {}
    if broadcast_ids:
        translations_result = await db.execute(
            select(BroadcastTranslation).where(BroadcastTranslation.broadcast_id.in_(broadcast_ids))
        )
        for row in translations_result.scalars().all():
            translations_map.setdefault(row.broadcast_id, {})[row.language] = row.message_text

    return [
        build_broadcast_response(broadcast, translations_map.get(broadcast.id, {}))
        for broadcast in broadcasts
    ]


@router.get("/{broadcast_id}", response_model=BroadcastResponse)
async def get_broadcast(
    broadcast_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("broadcasts"))
):
    """Получить детали рассылки"""
    
    stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
    result = await db.execute(stmt)
    broadcast = result.scalar_one_or_none()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    translations_result = await db.execute(
        select(BroadcastTranslation).where(BroadcastTranslation.broadcast_id == broadcast.id)
    )
    translations = {
        row.language: row.message_text
        for row in translations_result.scalars().all()
    }
    return build_broadcast_response(broadcast, translations)


@router.post("/{broadcast_id}/cancel")
async def cancel_scheduled_broadcast(
    broadcast_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("broadcasts"))
):
    """Отменить запланированную рассылку"""
    stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
    result = await db.execute(stmt)
    broadcast = result.scalar_one_or_none()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if broadcast.status != "scheduled":
        raise HTTPException(status_code=400, detail="Can only cancel scheduled broadcasts")
    translations_result = await db.execute(
        select(BroadcastTranslation.language).where(BroadcastTranslation.broadcast_id == broadcast.id)
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "broadcast_cancel",
        "broadcast",
        broadcast.id,
        {
            "languages": [row[0] for row in translations_result.all()],
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.execute(
        delete(BroadcastTranslation).where(BroadcastTranslation.broadcast_id == broadcast.id)
    )
    await db.delete(broadcast)
    await db.commit()
    return {"success": True, "message": "Scheduled broadcast cancelled"}


@router.delete("/{broadcast_id}")
async def delete_broadcast(
    broadcast_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("broadcasts"))
):
    """Удалить рассылку"""
    
    stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
    result = await db.execute(stmt)
    broadcast = result.scalar_one_or_none()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    # Можно удалять только completed, failed или scheduled
    if broadcast.status in ["pending", "in_progress"]:
        raise HTTPException(status_code=400, detail="Cannot delete active broadcast")
    translations_result = await db.execute(
        select(BroadcastTranslation.language).where(BroadcastTranslation.broadcast_id == broadcast.id)
    )
    
    await log_action(
        db,
        current_user.get("admin_id"),
        "broadcast_delete",
        "broadcast",
        broadcast.id,
        {
            "status": broadcast.status,
            "languages": [row[0] for row in translations_result.all()],
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.execute(
        delete(BroadcastTranslation).where(BroadcastTranslation.broadcast_id == broadcast.id)
    )
    await db.delete(broadcast)
    await db.commit()
    
    return {"success": True, "message": "Broadcast deleted"}

