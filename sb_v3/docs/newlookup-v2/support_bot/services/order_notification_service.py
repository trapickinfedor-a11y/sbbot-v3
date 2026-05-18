"""
Сервис уведомлений воркеров о новых заказах
"""

import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Order, Worker
from support_bot.config import support_bot_config
from support_bot.constants.service_names import get_full_service_name

logger = logging.getLogger(__name__)


class OrderNotificationService:
    """Сервис уведомлений воркеров о новых заказах"""
    
    _bot: Optional[Bot] = None
    
    @classmethod
    def init(cls, bot: Bot):
        """Инициализация сервиса с ботом"""
        cls._bot = bot
    
    @classmethod
    async def notify_workers_about_new_order(
        cls, 
        session: AsyncSession, 
        order: Order
    ) -> bool:
        """
        Уведомить всех подходящих воркеров о новом заказе
        
        Args:
            session: Сессия БД
            order: Новый заказ
            
        Returns:
            bool: Успешность отправки уведомлений
        """
        if not cls._bot:
            logger.warning("Bot not initialized in OrderNotificationService")
            return False
        
        try:
            logger.info(
                "Searching workers for order %s: category='%s', service_name='%s'",
                order.id,
                order.category,
                order.service_name,
            )

            result = await session.execute(
                select(Worker).where(
                    Worker.is_active == True,
                    Worker.is_suspended == False,
                )
            )
            all_workers = result.scalars().all()

            logger.info("Found %s active workers to check", len(all_workers))

            # Импортируем функцию проверки доступа
            from support_bot.services.order_service import can_worker_access_order
            
            # Фильтруем воркеров по конкретным сервисам
            workers = []
            for worker in all_workers:
                logger.info(f"Checking worker {worker.id} (telegram_id={worker.telegram_id}, username={worker.username})")
                
                # Если у воркера не указаны services или список пуст, пропускаем его
                if not worker.services or len(worker.services) == 0:
                    logger.info(f"❌ Worker {worker.id} ({worker.username}) has no services configured, skipping")
                    continue
                
                logger.info(f"Worker {worker.id} ({worker.username}) has services: {worker.services}")
                
                # Используем гибкую проверку доступа
                if can_worker_access_order(worker.categories, worker.services, order.category, order.service_name):
                    workers.append(worker)
                    logger.info(f"✅✅✅ Worker {worker.id} ({worker.username}) WILL RECEIVE notification for service {order.service_name}")
                else:
                    logger.info(f"❌❌❌ Worker {worker.id} ({worker.username}) will NOT receive notification. Order service '{order.service_name}' not accessible with worker services: {worker.services}")
            
            if not workers:
                logger.info(f"No workers found for category '{order.category}' and service '{order.service_name}' for order {order.id}")
                return False
            
            # Формируем сообщение
            order_type = "BULK" if order.is_bulk else "Single"
            bulk_info = f" ({order.bulk_count} items)" if order.is_bulk else ""
            
            message_text = f"""🔔 <b>NEW ORDER AVAILABLE!</b>

📦 <b>Order #{order.id}</b> ({order_type}{bulk_info})
🔧 <b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}
📂 <b>Category:</b> {order.category}

⏰ <b>Created:</b> {order.created_at.strftime('%H:%M:%S')}

🎯 <b>Ready to take this order?</b>
Open Worker Bot to view details and take the order!

/start - Open Worker Bot"""
            
            # Отправляем уведомления всем подходящим воркерам
            from support_bot.keyboards.inline import notification_keyboard
            
            success_count = 0
            for worker in workers:
                try:
                    await cls._bot.send_message(
                        chat_id=worker.telegram_id,
                        text=message_text,
                        reply_markup=notification_keyboard(order.id),
                        parse_mode=ParseMode.HTML
                    )
                    success_count += 1
                    logger.info(f"Order notification sent to worker {worker.id} ({worker.username})")
                    
                except Exception as e:
                    logger.error(f"Failed to notify worker {worker.id}: {e}")
            
            logger.info(f"Order {order.id} notifications sent to {success_count}/{len(workers)} workers")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to notify workers about order {order.id}: {e}")
            return False
    
    @classmethod
    async def notify_worker_order_taken(
        cls,
        session: AsyncSession,
        order: Order,
        taken_by_worker_id: int
    ) -> bool:
        """
        Уведомить других воркеров что заказ был взят
        
        Args:
            session: Сессия БД
            order: Заказ который был взят
            taken_by_worker_id: ID воркера который взял заказ
            
        Returns:
            bool: Успешность отправки уведомлений
        """
        if not cls._bot:
            logger.warning("Bot not initialized in OrderNotificationService")
            return False
        
        try:
            result = await session.execute(
                select(Worker).where(
                    Worker.is_active == True,
                    Worker.is_suspended == False,
                    Worker.id != taken_by_worker_id
                )
            )
            all_workers = result.scalars().all()

            from support_bot.services.order_service import can_worker_access_order

            # Используем ту же проверку, что и для выдачи/уведомления новых заказов
            workers = []
            for worker in all_workers:
                if not worker.services or len(worker.services) == 0:
                    continue

                if can_worker_access_order(
                    worker.categories,
                    worker.services,
                    order.category,
                    order.service_name,
                ):
                    workers.append(worker)
            
            if not workers:
                return True  # Нет других воркеров для уведомления
            
            # Получаем информацию о воркере который взял заказ
            taken_worker = await session.get(Worker, taken_by_worker_id)
            taken_worker_name = taken_worker.username if taken_worker else f"Worker #{taken_by_worker_id}"
            
            message_text = f"""⚠️ <b>ORDER TAKEN</b>

📦 <b>Order #{order.id}</b> has been taken by <b>{taken_worker_name}</b>

🔧 <b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}

This order is no longer available."""
            
            # Отправляем уведомления
            success_count = 0
            for worker in workers:
                try:
                    await cls._bot.send_message(
                        chat_id=worker.telegram_id,
                        text=message_text,
                        parse_mode=ParseMode.HTML
                    )
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to notify worker {worker.id} about taken order: {e}")
            
            logger.info(f"Order taken notifications sent to {success_count}/{len(workers)} workers")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to notify workers about taken order {order.id}: {e}")
            return False
    
    @classmethod
    async def send_order_to_channel(cls, order: Order) -> bool:
        """
        Публичная отправка заказов в каналы отключена.
        
        Args:
            order: Заказ для отправки
            
        Returns:
            bool: Успешность отправки
        """
        logger.info("Skipping public channel notification for order %s", order.id)
        return False
