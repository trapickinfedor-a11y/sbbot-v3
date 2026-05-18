"""
Утилита для отправки уведомлений саппортам о новых заказах
Используется из Mirror Bot
"""

import logging
import asyncio
from typing import Optional
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Order
from support_bot.config import support_bot_config

logger = logging.getLogger(__name__)


async def notify_workers_about_new_order(order: Order, session: AsyncSession):
    """
    Отправить уведомление саппортам о новом заказе
    
    Эта функция вызывается из Mirror Bot когда создается новый заказ
    
    Args:
        order: Новый заказ
        session: Database session
    """
    try:
        # Инициализируем бота Support Bot
        support_bot = Bot(token=support_bot_config.bot_token)
        
        # Импортируем сервис
        from support_bot.services.worker_notification_service import WorkerNotificationService
        
        # Инициализируем сервис если еще не инициализирован
        if not WorkerNotificationService._bot:
            WorkerNotificationService.init(support_bot)
        
        # Отправляем уведомление
        await WorkerNotificationService.notify_new_order(session, order)
        
        # Закрываем сессию бота
        await support_bot.session.close()
        
        logger.info(f"Workers notified about order #{order.id}")
    
    except Exception as e:
        logger.error(f"Failed to notify workers about order {order.id}: {e}")


def schedule_worker_notification(order: Order, session: AsyncSession):
    """
    Запланировать уведомление саппортов (для синхронного кода)
    
    Args:
        order: Новый заказ
        session: Database session
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Если event loop уже запущен, создаем задачу
        asyncio.create_task(notify_workers_about_new_order(order, session))
    else:
        # Иначе запускаем синхронно
        loop.run_until_complete(notify_workers_about_new_order(order, session))

