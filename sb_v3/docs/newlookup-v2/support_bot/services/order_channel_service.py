"""
Сервис для отправки заказов в канал
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.enums import ParseMode

from shared.database.models import Order

logger = logging.getLogger(__name__)


class OrderChannelService:
    """Сервис для отправки всех заказов в отдельный канал"""
    
    _bot: Optional[Bot] = None
    _channel_id: Optional[int] = None
    
    @classmethod
    def init(cls, bot: Bot, channel_id: int):
        """Инициализация сервиса"""
        cls._bot = bot
        cls._channel_id = channel_id
        logger.info(f"OrderChannelService initialized with channel {channel_id}")
    
    @classmethod
    async def send_order_to_channel(cls, order: Order):
        """
        Отправить заказ в канал
        
        Args:
            order: Заказ для отправки
        """
        if not cls._bot or not cls._channel_id:
            logger.warning("OrderChannelService not initialized")
            return
        
        try:
            # Форматируем данные
            customer_data = "\n".join([
                f"   • <b>{key.replace('_', ' ').title()}:</b> <code>{value}</code>"
                for key, value in order.input_data.items()
            ])
            
            order_type = f"BULK x{order.bulk_count}" if order.is_bulk else "Single"
            
            text = f"""📦 <b>NEW ORDER #{order.id}</b>

🔧 <b>Service:</b> {order.service_name}
📂 <b>Category:</b> {order.category.upper()}
📊 <b>Type:</b> {order_type}
👤 <b>Buyer:</b> <code>hidden</code>

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M UTC')}
"""
            
            await cls._bot.send_message(
                chat_id=cls._channel_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Order #{order.id} sent to channel {cls._channel_id}")
        
        except Exception as e:
            logger.error(f"Failed to send order to channel: {e}")

