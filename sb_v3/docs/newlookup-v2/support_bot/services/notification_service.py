"""
Сервис уведомлений клиентам Mirror Bot
"""

import logging
import os
from typing import Optional
from aiogram import Bot
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Order
from shared.security.internal_api import build_internal_api_headers
from support_bot.config import support_bot_config
from support_bot.services.order_delivery_service import OrderDeliveryService

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений клиентам"""
    
    _bot: Optional[Bot] = None
    
    @classmethod
    def init(cls, bot: Bot):
        """Инициализация сервиса с ботом"""
        cls._bot = bot
    
    @classmethod
    async def _get_user_balance(cls, order: Order) -> float:
        """Получить баланс пользователя безопасно"""
        try:
            from mirror_bot.services.user_service import UserService
            from shared.database.session import get_session
            
            async with get_session() as session:
                user = await UserService.get_user(session, order.user_id, order.mirror_bot_id)
                return user.balance if user else 0.00
        except Exception as e:
            logger.error(f"Failed to get user balance: {e}")
            return 0.00
    
    @classmethod
    async def notify_order_completed(
        cls, 
        order: Order, 
        result_status: str,
        session: Optional[AsyncSession] = None,
        result_text: Optional[str] = None,
        result_file_url: Optional[str] = None,
        result_file_name: Optional[str] = None
    ):
        """
        Уведомление о завершении single заказа через mirror bot пользователя
        
        Args:
            order: Заказ
            result_status: "done" или "nf"
            session: Сессия БД (опционально)
            result_text: Текст результата
            result_file_url: URL файла результата
            result_file_name: Имя файла результата
        """
        from shared.services.notification_log_service import fire_log
        try:
            if session:
                # Используем новый сервис доставки через mirror bot
                success = await OrderDeliveryService.deliver_order_result(
                    session=session,
                    order=order,
                    result_text=result_text,
                    result_file_url=result_file_url,
                    result_file_name=result_file_name,
                    result_status=result_status
                )
                
                if success:
                    logger.info(f"Order result delivered to user {order.user_id} via mirror bot")
                    fire_log(
                        event_type=f"order_{result_status}_to_user",
                        channel="mirror_bot",
                        status="sent",
                        recipient_id=order.user_id,
                        related_id=order.id,
                        related_type="order",
                    )
                    return
                else:
                    logger.warning(f"Failed to deliver via mirror bot, falling back to support bot")
                    fire_log(
                        event_type=f"order_{result_status}_to_user",
                        channel="mirror_bot",
                        status="failed",
                        recipient_id=order.user_id,
                        related_id=order.id,
                        related_type="order",
                        error_message="Mirror bot delivery failed, using fallback",
                    )
            
            # Fallback: отправляем через support bot (старый способ)
            if not cls._bot:
                logger.warning("Bot not initialized in NotificationService")
                fire_log(
                    event_type=f"order_{result_status}_to_user",
                    channel="support_bot",
                    status="failed",
                    recipient_id=order.user_id,
                    related_id=order.id,
                    related_type="order",
                    error_message="Bot not initialized",
                )
                return
            
            if result_status == "done":
                user_balance = await cls._get_user_balance(order)
                text = f"""✅ <b>Your order completed!</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ✅ DONE

Your result is ready! Check your order details.

Your balance: <b>${user_balance:.2f}</b>
"""
                if result_text:
                    text += f"\n<b>Result:</b>\n{result_text}"
                    
            else:  # nf
                user_balance = await cls._get_user_balance(order)
                text = f"""❌ <b>Your order - Not Found</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ❌ NF (Not Found)

Unfortunately, the requested information was not found.
Your balance has been <b>refunded</b>.

Your balance: <b>${user_balance:.2f}</b>
"""
            
            await cls._bot.send_message(
                chat_id=order.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            fire_log(
                event_type=f"order_{result_status}_to_user",
                channel="support_bot",
                status="sent",
                recipient_id=order.user_id,
                related_id=order.id,
                related_type="order",
            )
            logger.info(f"Fallback notification sent to user {order.user_id} for order {order.id}")
        
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            fire_log(
                event_type=f"order_{result_status}_to_user",
                channel="support_bot",
                status="failed",
                recipient_id=order.user_id,
                related_id=order.id,
                related_type="order",
                error_message=str(e),
            )
    
    @classmethod
    async def notify_bulk_order_completed(cls, order: Order, summary: dict):
        """
        Уведомление о завершении bulk заказа
        
        Args:
            order: Заказ
            summary: Сводка {"done": X, "nf": Y, "total": Z}
        """
        if not cls._bot:
            logger.warning("Bot not initialized in NotificationService")
            return
        
        try:
            user_balance = await cls._get_user_balance(order)
            
            text = f"""🎯 <b>Your bulk order completed!</b>

<b>Service:</b> {order.service_name}
<b>Total Items:</b> {summary['total']}

<b>📊 Final Results:</b>
   ✅ <b>Found & Delivered:</b> {summary['done']} items
   ❌ <b>Not Found (Refunded):</b> {summary['nf']} items

<b>💰 Summary:</b>
• Items found: {summary['done']} × ${order.price / order.bulk_count:.2f} = ${summary['done'] * (order.price / order.bulk_count):.2f}
• Items refunded: {summary['nf']} × ${order.price / order.bulk_count:.2f} = ${summary['nf'] * (order.price / order.bulk_count):.2f}

All individual results have been sent above. Check your chat history for each item's details and files.

Your current balance: <b>${user_balance:.2f}</b>

Thank you for your order! 🙏
"""
            
            await cls._bot.send_message(
                chat_id=order.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Bulk order notification sent to user {order.user_id} for order {order.id}")
        
        except Exception as e:
            logger.error(f"Failed to send bulk notification: {e}")
    
    @classmethod
    async def notify_addinfo_completed(cls, order: Order, wait_hours: int, session: Optional[AsyncSession] = None):
        """
        Уведомление о выполнении Add Info заказа через mirror bot пользователя
        
        Args:
            order: Заказ
            wait_hours: Время ожидания в часах
            session: Сессия БД (опционально)
        """
        try:
            if session:
                # Используем новый сервис доставки через mirror bot (мультиязычный)
                success = await OrderDeliveryService.notify_addinfo_completed(order, wait_hours)
                
                if success:
                    logger.info(f"Add Info notification delivered to user {order.user_id} via mirror bot")
                    return
                else:
                    logger.warning(f"Failed to deliver Add Info via mirror bot, falling back to support bot")
            
            # Fallback: отправляем через support bot (старый способ)
            if not cls._bot:
                logger.warning("Bot not initialized in NotificationService")
                return
            
            user_balance = await cls._get_user_balance(order)
            
            text = f"""✅ <b>Your Add Info order #{order.id} completed!</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ✅ Information will be added

⏱ <b>Wait time:</b> approximately {wait_hours} hours

The information will be added to your credit reports.
You will receive a notification when it's ready.

Your balance: <b>${user_balance:.2f}</b>
"""
            
            await cls._bot.send_message(
                chat_id=order.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Fallback Add Info notification sent to user {order.user_id} for order {order.id}")
        
        except Exception as e:
            logger.error(f"Failed to send Add Info notification: {e}")
    
    @classmethod
    async def notify_order_with_files(cls, order: Order):
        """
        Уведомление о завершении заказа с файлами
        
        Args:
            order: Заказ с файлами
        """
        if not cls._bot:
            logger.warning("Bot not initialized in NotificationService")
            return
        
        try:
            user_balance = await cls._get_user_balance(order)
            
            text = f"""✅ <b>Your order #{order.id} completed!</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ✅ DONE

Your result is ready! Check the files below.

Your balance: <b>${user_balance:.2f}</b>
"""
            
            await cls._bot.send_message(
                chat_id=order.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем файлы
            if order.files:
                for file_info in order.files:
                    try:
                        if file_info.get("type") == "document":
                            await cls._bot.send_document(
                                chat_id=order.user_id,
                                document=file_info["file_id"],
                                caption=f"Order #{order.id} - {file_info.get('file_name', 'Result')}"
                            )
                        elif file_info.get("type") == "photo":
                            await cls._bot.send_photo(
                                chat_id=order.user_id,
                                photo=file_info["file_id"],
                                caption=f"Order #{order.id} - Result"
                            )
                    except Exception as e:
                        logger.error(f"Failed to send file: {e}")
            
            logger.info(f"Order with files notification sent to user {order.user_id} for order {order.id}")
        
        except Exception as e:
            logger.error(f"Failed to send files notification: {e}")
    
    @classmethod
    async def notify_bulk_item_with_files(cls, order: Order, bulk_item):
        """
        Уведомление о завершении элемента bulk заказа с файлами
        
        Args:
            order: Заказ
            bulk_item: Элемент bulk заказа
        """
        if not cls._bot:
            logger.warning("Bot not initialized in NotificationService")
            return
        
        try:
            user_balance = await cls._get_user_balance(order)
            
            # Получаем данные клиента для этого элемента
            customer_data = ""
            if bulk_item.input_data:
                data_lines = []
                for key, value in bulk_item.input_data.items():
                    if key not in ['item_number'] and value:
                        formatted_key = key.replace('_', ' ').title()
                        data_lines.append(f"<b>{formatted_key}:</b> {value}")
                if data_lines:
                    customer_data = f"\n\n<b>Your data:</b>\n" + "\n".join(data_lines)
            
            text = f"""✅ <b>Your order #{order.id} item #{bulk_item.item_number} completed!</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ✅ DONE{customer_data}

Your result for item #{bulk_item.item_number} is ready! Check the files below.

Your balance: <b>${user_balance:.2f}</b>
"""
            
            await cls._bot.send_message(
                chat_id=order.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем файлы
            if bulk_item.result_data and bulk_item.result_data.get("files"):
                for file_info in bulk_item.result_data["files"]:
                    try:
                        if file_info.get("type") == "document":
                            await cls._bot.send_document(
                                chat_id=order.user_id,
                                document=file_info["file_id"],
                                caption=f"📄 <b>Order #{order.id} - Item #{bulk_item.item_number}</b>\n\n<b>File:</b> {file_info.get('file_name', 'Result')}\n<b>Service:</b> {order.service_name}",
                                parse_mode=ParseMode.HTML
                            )
                        elif file_info.get("type") == "photo":
                            await cls._bot.send_photo(
                                chat_id=order.user_id,
                                photo=file_info["file_id"],
                                caption=f"📸 <b>Order #{order.id} - Item #{bulk_item.item_number}</b>\n\n<b>Result Image</b>\n<b>Service:</b> {order.service_name}",
                                parse_mode=ParseMode.HTML
                            )
                    except Exception as e:
                        logger.error(f"Failed to send file: {e}")
            
            logger.info(f"Bulk item notification with files sent for order {order.id} item {bulk_item.item_number}")
        
        except Exception as e:
            logger.error(f"Failed to send bulk item notification with files: {e}")
    
    @classmethod
    async def notify_bulk_item_nf(cls, order: Order, bulk_item, refund_amount: float):
        """
        Уведомление о том, что элемент bulk заказа не найден (NF)
        
        Args:
            order: Заказ
            bulk_item: Элемент bulk заказа
            refund_amount: Сумма возврата
        """
        if not cls._bot:
            logger.warning("Bot not initialized in NotificationService")
            return
        
        try:
            user_balance = await cls._get_user_balance(order)
            
            # Получаем данные клиента для этого элемента
            customer_data = ""
            if bulk_item.input_data:
                data_lines = []
                for key, value in bulk_item.input_data.items():
                    if key not in ['item_number'] and value:
                        formatted_key = key.replace('_', ' ').title()
                        data_lines.append(f"<b>{formatted_key}:</b> {value}")
                if data_lines:
                    customer_data = f"\n\n<b>Your data:</b>\n" + "\n".join(data_lines)
            
            text = f"""❌ <b>Your order #{order.id} item #{bulk_item.item_number} - NOT FOUND</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ❌ NOT FOUND{customer_data}

Unfortunately, we couldn't find information for item #{bulk_item.item_number}.
<b>Refund:</b> ${refund_amount:.2f} has been returned to your balance.

Your balance: <b>${user_balance:.2f}</b>
"""
            
            await cls._bot.send_message(
                chat_id=order.user_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Bulk item NF notification sent for order {order.id} item {bulk_item.item_number}")
        
        except Exception as e:
            logger.error(f"Failed to send bulk item NF notification: {e}")
    
    @classmethod
    async def notify_order_cancelled(cls, order: Order, reason: str = "cancelled"):
        """
        Уведомление об отмене заказа через API с мультиязычной поддержкой
        
        Args:
            order: Заказ
            reason: Причина отмены ("cancelled", "invalid_data", "no_stock")
        """
        try:
            # Получаем язык пользователя из БД
            from shared.database import get_session
            from shared.database.models import User
            from sqlalchemy import select
            
            user_language = "en"
            async for session in get_session():
                result = await session.execute(
                    select(User).where(User.user_id == order.user_id, User.mirror_bot_id == order.mirror_bot_id)
                )
                user = result.scalar_one_or_none()
                user_language = user.language if user and user.language else "en"
                break  # Выходим после первой сессии
            
            # Отправляем через API
            import aiohttp
            
            api_url = os.getenv("MAIN_BOT_API_URL", "http://main_bot:8080") + "/api/notify-order-cancelled"
            
            payload = {
                "user_id": order.user_id,
                "mirror_bot_id": order.mirror_bot_id,
                "order_id": order.id,
                "service_name": order.service_name,
                "refund_amount": float(order.price),
                "reason": reason,
                "user_language": user_language
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http_session:
                async with http_session.post(
                    api_url,
                    json=payload,
                    headers=build_internal_api_headers(),
                ) as response:
                    if response.status == 200:
                        logger.info(f"Order cancellation notification sent via API for order {order.id}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send cancellation notification via API: {response.status} - {error_text}")
                        
                        # Fallback на старый метод если API не работает
                        if cls._bot:
                            user_balance = await cls._get_user_balance(order)
                            text = f"""⚠️ <b>Your order #{order.id} was cancelled</b>

<b>Service:</b> {order.service_name}
<b>Status:</b> ❌ CANCELLED

The order has been cancelled and your balance has been <b>refunded</b>.

If you have any questions, please contact support.

Your balance: <b>${user_balance:.2f}</b>
"""
                            await cls._bot.send_message(
                                chat_id=order.user_id,
                                text=text,
                                parse_mode=ParseMode.HTML
                            )
        
        except Exception as e:
            logger.error(f"Failed to send cancellation notification: {e}")
            from shared.services.notification_log_service import fire_log
            fire_log(
                event_type="order_cancelled_to_user",
                channel="api",
                status="failed",
                recipient_id=order.user_id,
                related_id=order.id,
                related_type="order",
                error_message=str(e),
            )

