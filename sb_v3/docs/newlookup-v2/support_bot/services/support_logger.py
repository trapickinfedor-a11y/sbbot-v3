"""
Сервис логирования действий саппортов
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.enums import ParseMode
from datetime import datetime

from shared.services.log_channel_service import LogChannelService
from support_bot.config import support_bot_config
from support_bot.constants.service_names import get_full_service_name

logger = logging.getLogger(__name__)


class SupportLogger:
    """Сервис для логирования всех действий саппортов в админский чат"""
    
    _bot: Optional[Bot] = None
    
    @classmethod
    def init(cls, bot: Bot):
        """Инициализация сервиса с ботом"""
        cls._bot = bot
    
    @classmethod
    async def _send_to_channels(
        cls,
        text: str,
        event_type: str = "support_event",
        urgent: bool = False,
        broadcast_to_log_channels: bool = True,
    ):
        """Публичные каналы отключены, оставляем только локальный лог."""
        logger.info("SupportLogger skipped channel broadcast for %s", event_type)
    
    @classmethod
    async def log_order_taken(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int):
        """Логирование взятия заказа в работу"""
        if not cls._bot:
            return
        
        try:
            text = f"""🔥 <b>ORDER TAKEN</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}

🎯 Worker has taken the order and started processing."""
            
            await cls._send_to_channels(
                text,
                event_type="support_order_taken",
                urgent=True,
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log order taken: {e}")
    
    @classmethod
    async def log_order_completed(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int, result_status: str, result_text: Optional[str] = None):
        """Логирование завершения заказа"""
        if not cls._bot:
            return
        
        try:
            if result_status == "bulk_completed":
                status_emoji = "🎯"
                status_text = "BULK ORDER COMPLETED"
            else:
                status_emoji = "✅" if result_status == "done" else "❌"
                status_text = "DONE" if result_status == "done" else "NOT FOUND"
            
            text = f"""{status_emoji} <b>{status_text}</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
📊 <b>Result:</b> {status_text}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""

            if result_text:
                text += f"\n\n📝 <b>Result Details:</b>\n<code>{result_text[:200]}{'...' if len(result_text) > 200 else ''}</code>"
            
            text += f"\n\n✉️ Client has been notified about the result."
            
            await cls._send_to_channels(
                text,
                event_type="support_order_completed",
                urgent=result_status != "done",
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log order completed: {e}")
    
    @classmethod
    async def log_bulk_item_completed(cls, worker_username: str, worker_id: int, order_id: int, item_number: int, service_name: str, user_id: int, result_status: str, refund_amount: Optional[float] = None):
        """Логирование завершения элемента bulk заказа"""
        if not cls._bot:
            return
        
        try:
            from support_bot.constants.service_names import get_full_service_name
            
            status_emoji = "✅" if result_status == "done" else "❌"
            status_text = "DONE" if result_status == "done" else "NOT FOUND"
            
            text = f"""{status_emoji} <b>BULK ITEM COMPLETED</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id} - Item #{item_number}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
📊 <b>Result:</b> {status_text}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""

            if refund_amount:
                text += f"\n💰 <b>Refund:</b> ${refund_amount:.2f}"
            
            text += f"\n\n✉️ Client has been notified about the result."
            
            await cls._send_to_channels(
                text,
                event_type="bulk_item_completed",
                urgent=result_status != "done",
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log bulk item completed: {e}")
    
    @classmethod
    async def log_order_with_files(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int, files_count: int):
        """Логирование завершения заказа с файлами"""
        if not cls._bot:
            return
        
        try:
            text = f"""📎 <b>ORDER COMPLETED WITH FILES</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
📁 <b>Files sent:</b> {files_count}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}

✉️ Client has been notified and received the files."""
            
            await cls._send_to_channels(
                text,
                event_type="support_order_with_files",
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log order with files: {e}")
    
    @classmethod
    async def log_addinfo_completed(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int, wait_hours: int):
        """Логирование завершения Add Info заказа"""
        if not cls._bot:
            return
        
        try:
            text = f"""📝 <b>ADD INFO COMPLETED</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
⏱ <b>Wait time:</b> {wait_hours} hours
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}

✉️ Client has been notified about the processing time."""
            
            await cls._send_to_channels(
                text,
                event_type="support_addinfo_completed",
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log addinfo completed: {e}")
    
    @classmethod
    async def log_order_cancelled(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int, reason: Optional[str] = None):
        """Логирование отмены заказа"""
        if not cls._bot:
            return
        
        try:
            text = f"""❌ <b>ORDER CANCELLED</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""

            if reason:
                text += f"\n\n📝 <b>Reason:</b> {reason}"
            
            text += f"\n\n💰 Client's balance has been refunded."
            
            await cls._send_to_channels(
                text,
                event_type="support_order_cancelled",
                urgent=True,
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log order cancelled: {e}")
    
    @classmethod
    async def log_addinfo_processing(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int, hours: int, estimated_ready: str):
        """Логирование установки времени для Add Info"""
        if not cls._bot:
            return
        
        try:
            text = f"""⏰ <b>ADD INFO TIME SET</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
⏱ <b>Wait time:</b> {hours} hours
📅 <b>Estimated ready:</b> {estimated_ready}
⏰ <b>Set at:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}

✅ Customer has been notified."""
            
            await cls._send_to_channels(text, event_type="support_addinfo_processing")
            
        except Exception as e:
            logger.error(f"Failed to log addinfo processing: {e}")
    
    @classmethod
    async def log_bulk_item_reset(cls, worker_username: str, worker_id: int, order_id: int, item_number: int, old_status: str):
        """Логирование сброса статуса элемента bulk заказа"""
        if not cls._bot:
            return
        
        try:
            text = f"""🔄 <b>BULK ITEM STATUS RESET</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id} - Item {item_number}
📊 <b>Status:</b> {old_status.upper()} → PENDING
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""
            
            await cls._send_to_channels(text, event_type="support_bulk_item_reset")
            
        except Exception as e:
            logger.error(f"Failed to log bulk item reset: {e}")

    @classmethod
    async def log_complaint_filed(cls, worker_username: str, worker_id: int, order_id: int, user_id: int, complaint_text: str):
        """Логирование жалобы на клиента"""
        if not cls._bot:
            return
        
        try:
            text = f"""⚠️ <b>CLIENT COMPLAINT FILED</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
👥 <b>Client:</b> {user_id}
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}

📝 <b>Complaint:</b>
<code>{complaint_text}</code>

⚠️ <b>Action required:</b> Review client behavior and take appropriate measures."""
            
            await cls._send_to_channels(text, event_type="support_complaint_filed", urgent=True)
            
        except Exception as e:
            logger.error(f"Failed to log complaint: {e}")
    
    @classmethod
    async def log_bulk_order_completed(cls, worker_username: str, worker_id: int, order_id: int, service_name: str, user_id: int, summary: dict):
        """Логирование завершения bulk заказа"""
        if not cls._bot:
            return
        
        try:
            text = f"""📦 <b>BULK ORDER COMPLETED</b>
            
👤 <b>Worker:</b> @{worker_username} (ID: {worker_id})
📦 <b>Order:</b> #{order_id}
🔧 <b>Service:</b> {get_full_service_name(service_name)}
👥 <b>Client:</b> {user_id}
📊 <b>Results:</b> ✅ {summary.get('done', 0)} DONE, ❌ {summary.get('nf', 0)} NF (Total: {summary.get('total', 0)})
⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}

✉️ Client has been notified with detailed results."""
            
            await cls._send_to_channels(
                text,
                event_type="support_bulk_order_completed",
                broadcast_to_log_channels=False,
            )
            
        except Exception as e:
            logger.error(f"Failed to log bulk order completed: {e}")
