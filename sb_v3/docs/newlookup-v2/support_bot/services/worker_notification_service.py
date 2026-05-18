"""
Сервис уведомлений саппортов о новых заказах
"""

import logging
from typing import Optional, List
from aiogram import Bot
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Order, Worker, BulkOrderItem
from support_bot.keyboards.inline import (
    order_notification_keyboard,
    bulk_order_notification_keyboard
)

logger = logging.getLogger(__name__)


class WorkerNotificationService:
    """Сервис для отправки уведомлений саппортам о новых заказах"""
    
    _bot: Optional[Bot] = None
    
    @classmethod
    def init(cls, bot: Bot):
        """Инициализация сервиса с ботом"""
        cls._bot = bot
        logger.info("WorkerNotificationService initialized")
    
    @classmethod
    async def notify_new_order(cls, session: AsyncSession, order: Order):
        """
        Отправка уведомления о новом заказе всем саппортам этой категории
        
        Args:
            session: Database session
            order: Новый заказ
        """
        if not cls._bot:
            logger.warning("Bot not initialized in WorkerNotificationService")
            return
        
        try:
            # Проверяем всех активных воркеров через общую логику доступа,
            # чтобы legacy-категории и alias-сервисы не выпадали из уведомлений.
            stmt = select(Worker).where(
                Worker.is_active == True,
                Worker.is_suspended == False,
            )
            result = await session.execute(stmt)
            all_workers = result.scalars().all()
            
            if not all_workers:
                logger.warning("No active workers found")
                return
            
            logger.info(f"Found {len(all_workers)} active workers")
            logger.info(f"[WorkerNotificationService] Order #{order.id} service_name: '{order.service_name}'")
            
            # Импортируем функцию проверки доступа
            from support_bot.services.order_service import can_worker_access_order
            
            # Фильтруем воркеров по конкретным сервисам
            workers = []
            for worker in all_workers:
                logger.info(f"[WorkerNotificationService] Checking worker {worker.id} (telegram_id={worker.telegram_id}, username={worker.username})")
                
                # Если у воркера не указаны services или список пуст, пропускаем его
                if not worker.services or len(worker.services) == 0:
                    logger.info(f"[WorkerNotificationService] ❌ Worker {worker.id} ({worker.username}) has no services configured, skipping")
                    continue
                
                logger.info(f"[WorkerNotificationService] Worker {worker.id} ({worker.username}) has services: {worker.services}")
                
                # Используем гибкую проверку доступа
                if can_worker_access_order(worker.categories, worker.services, order.category, order.service_name):
                    workers.append(worker)
                    logger.info(f"[WorkerNotificationService] ✅✅✅ Worker {worker.id} ({worker.username}) WILL RECEIVE notification for service {order.service_name}")
                else:
                    logger.info(f"[WorkerNotificationService] ❌❌❌ Worker {worker.id} ({worker.username}) will NOT receive notification. Order service '{order.service_name}' not accessible with worker services: {worker.services}")
            
            if not workers:
                logger.warning(f"No workers found for category '{order.category}' and service '{order.service_name}'")
                return
            
            logger.info(f"Sending order #{order.id} notifications to {len(workers)} workers with matching services")
            
            # Отправляем уведомление каждому воркеру
            for worker in workers:
                try:
                    if order.is_bulk:
                        # Bulk заказ - показываем кнопки для каждого элемента
                        await cls._send_bulk_order_notification(session, order, worker.telegram_id)
                    else:
                        # Single заказ
                        await cls._send_single_order_notification(order, worker.telegram_id)
                
                except Exception as e:
                    logger.error(f"Failed to notify worker {worker.telegram_id}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to notify workers about order {order.id}: {e}")
    
    @classmethod
    async def _send_single_order_notification(cls, order: Order, worker_telegram_id: int) -> Optional[int]:
        """
        Отправка уведомления о single заказе
        
        Returns:
            message_id или None
        """
        # Форматируем данные клиента
        customer_data = cls._format_customer_data(order.input_data)
        
        text = f"""🛒 <b>NEW ORDER #{order.id}</b>

🔧 <b>Service:</b> {order.service_name}
📂 <b>Category:</b> {order.category.upper()}

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        try:
            message = await cls._bot.send_message(
                chat_id=worker_telegram_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=order_notification_keyboard(order.id)
            )
            
            logger.info(f"Single order notification sent to {worker_telegram_id}, message_id={message.message_id}")
            return message.message_id
        
        except Exception as e:
            logger.error(f"Failed to send single order notification: {e}")
            return None
    
    @classmethod
    async def _send_bulk_order_notification(cls, session: AsyncSession, order: Order, worker_telegram_id: int):
        """
        Отправка уведомления о bulk заказе
        
        Для bulk заказов создаем кнопки "взять в работу" для каждого элемента
        """
        text = f"""📦 <b>NEW BULK ORDER #{order.id}</b>

🔧 <b>Service:</b> {order.service_name}
📂 <b>Category:</b> {order.category.upper()}
📊 <b>Items:</b> {order.bulk_count}

━━━━━━━━━━━━━━━━━━
⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}

👇 <b>Select items to work on:</b>
"""
        
        try:
            # Получаем элементы bulk заказа
            stmt = select(BulkOrderItem).where(
                BulkOrderItem.order_id == order.id
            ).order_by(BulkOrderItem.item_number)
            
            result = await session.execute(stmt)
            items = result.scalars().all()
            
            message = await cls._bot.send_message(
                chat_id=worker_telegram_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=bulk_order_notification_keyboard(order.id, items)
            )
            
            logger.info(f"Bulk order notification sent to {worker_telegram_id}, message_id={message.message_id}")
        
        except Exception as e:
            logger.error(f"Failed to send bulk order notification: {e}")
    
    @classmethod
    def _format_customer_data(cls, data: dict) -> str:
        """Форматирование данных клиента для отображения"""
        lines = []
        for key, value in data.items():
            # Красиво форматируем ключи
            key_formatted = key.replace("_", " ").title()
            lines.append(f"   • <b>{key_formatted}:</b> <code>{value}</code>")
        return "\n".join(lines)
    
    @classmethod
    async def notify_complaint_resolved(cls, worker_telegram_id: int, complaint_id: int, status: str, admin_response: str, action: str = None):
        """
        Уведомление воркера о решении жалобы
        
        Args:
            worker_telegram_id: Telegram ID воркера
            complaint_id: ID жалобы
            status: Статус жалобы (resolved/rejected)
            admin_response: Ответ администратора
            action: Действие (ban_user/warn_user/reject)
        """
        if not cls._bot:
            logger.warning("Bot not initialized in WorkerNotificationService")
            return
        
        try:
            status_emoji = {
                "resolved": "✅",
                "rejected": "❌"
            }
            
            action_text = ""
            if action == "ban_user":
                action_text = "\n🚫 <b>Action:</b> User has been banned"
            elif action == "warn_user":
                action_text = "\n⚠️ <b>Action:</b> User has been warned"
            elif action == "reject":
                action_text = "\n❌ <b>Action:</b> Complaint rejected"
            
            text = f"""{status_emoji.get(status, '❓')} <b>COMPLAINT UPDATE</b>

📋 <b>Complaint ID:</b> #{complaint_id}
📊 <b>Status:</b> {status.upper()}{action_text}

💬 <b>Admin Response:</b>
<i>{admin_response}</i>

━━━━━━━━━━━━━━━━━━
Thank you for your report! 🙏
"""
            
            await cls._bot.send_message(
                chat_id=worker_telegram_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Complaint resolution notification sent to worker {worker_telegram_id} for complaint #{complaint_id}")
        
        except Exception as e:
            logger.error(f"Failed to send complaint resolution notification: {e}")
    
    @classmethod
    async def update_order_message(cls, order: Order, new_status: str):
        """
        Обновление сообщения с заказом после изменения статуса
        
        Args:
            order: Заказ
            new_status: Новый статус
        """
        if not cls._bot or not order.notification_message_id or not order.support_chat_id:
            return
        
        try:
            # Форматируем данные клиента
            customer_data = cls._format_customer_data(order.input_data)
            
            status_emoji = {
                "pending": "⏳",
                "processing": "🔄",
                "completed": "✅",
                "cancelled": "❌"
            }
            
            text = f"""{status_emoji.get(new_status, '❓')} <b>ORDER #{order.id}</b> - {new_status.upper()}

🔧 <b>Service:</b> {order.service_name}
📂 <b>Category:</b> {order.category.upper()}

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}
"""
            
            if order.taken_at:
                text += f"🔄 <b>Taken:</b> {order.taken_at.strftime('%Y-%m-%d %H:%M')}\n"
            
            if order.completed_at:
                text += f"✅ <b>Completed:</b> {order.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
            
            await cls._bot.edit_message_text(
                chat_id=order.support_chat_id,
                message_id=order.notification_message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=None  # Убираем кнопки после завершения
            )
        
        except Exception as e:
            logger.error(f"Failed to update order message: {e}")

