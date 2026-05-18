"""
Интеграция веб-панели с ботами
"""

from aiogram import Bot
from typing import Optional, Dict, Any
import logging
import os
from web_panel.config import web_panel_config
from shared.security.internal_api import build_internal_api_headers

logger = logging.getLogger(__name__)


class BotIntegration:
    """Класс для интеграции веб-панели с ботами"""
    
    def __init__(self):
        self.support_bot: Optional[Bot] = None
        self.main_bot: Optional[Bot] = None
        
        # Инициализируем ботов если токены есть
        if web_panel_config.support_bot_token:
            self.support_bot = Bot(token=web_panel_config.support_bot_token)
            
        if web_panel_config.main_bot_token:
            self.main_bot = Bot(token=web_panel_config.main_bot_token)
    
    async def notify_support_order_update(
        self, 
        order_id: int, 
        status: str, 
        worker_id: Optional[int] = None,
        result_data: Optional[Dict] = None
    ):
        """Уведомить support bot об обновлении заказа"""
        if not self.support_bot:
            logger.warning("Support bot not configured")
            return
        
        try:
            # Отправляем уведомление в канал заказов
            if web_panel_config.orders_channel_id:
                message = f"📋 Order #{order_id} updated\n"
                message += f"Status: {status}\n"
                
                if worker_id:
                    message += f"Worker ID: {worker_id}\n"
                
                if result_data:
                    message += f"Result: {str(result_data)[:200]}...\n"
                
                await self.support_bot.send_message(
                    chat_id=web_panel_config.orders_channel_id,
                    text=message
                )
                
        except Exception as e:
            logger.error(f"Failed to notify support bot: {e}")
    
    async def notify_user_balance_update(
        self, 
        user_id: int, 
        amount: float, 
        reason: str,
        mirror_bot_id: int
    ):
        """Уведомить пользователя об изменении баланса через его mirror bot"""
        try:
            # Отправляем через API для поддержки мультиязычности
            import aiohttp
            
            # Получаем язык пользователя
            from shared.database.session import async_session_maker
            from shared.database.models import User
            from sqlalchemy import select
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(
                        User.user_id == user_id,
                        User.mirror_bot_id == mirror_bot_id
                    )
                )
                user = result.scalar_one_or_none()
                user_language = user.language if user else "en"
            
            api_url = os.getenv("MAIN_BOT_API_URL", "http://main_bot:8080") + "/api/notify-balance-update"
            
            payload = {
                "user_id": user_id,
                "mirror_bot_id": mirror_bot_id,
                "amount": amount,
                "reason": reason,
                "user_language": user_language
            }
            
            async with aiohttp.ClientSession() as client_session:
                async with client_session.post(
                    api_url,
                    json=payload,
                    headers=build_internal_api_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Balance update notification sent to user {user_id} via API")
                    else:
                        response_text = await response.text()
                        logger.warning(f"Failed to send balance update: HTTP {response.status}, Response: {response_text}")
            
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} about balance update: {e}")
    
    async def notify_user_ban(
        self, 
        user_id: int, 
        is_banned: bool, 
        reason: Optional[str] = None,
        mirror_bot_id: Optional[int] = None
    ):
        """Уведомить пользователя о бане/разбане через его mirror bot"""
        try:
            # Если mirror_bot_id не передан, получаем его из пользователя
            if not mirror_bot_id:
                from shared.database.session import async_session_maker
                from shared.database.models import User
                from sqlalchemy import select
                
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(User).where(User.user_id == user_id)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        mirror_bot_id = user.mirror_bot_id
                    else:
                        logger.error(f"User {user_id} not found")
                        return
            
            # Получаем токен mirror bot из базы данных
            from shared.database.session import async_session_maker
            from shared.database.models import MirrorBot
            from sqlalchemy import select
            
            async with async_session_maker() as session:
                result = await session.execute(
                    select(MirrorBot).where(MirrorBot.id == mirror_bot_id)
                )
                mirror_bot = result.scalar_one_or_none()
                
                if not mirror_bot:
                    logger.error(f"Mirror bot {mirror_bot_id} not found")
                    return
                
                # Создаем экземпляр бота с токеном mirror bot
                from aiogram import Bot
                bot = Bot(token=mirror_bot.bot_token)
                
                try:
                    if is_banned:
                        message = f"🚫 Account Suspended\n\n"
                        if reason:
                            message += f"Reason: {reason}\n"
                        message += f"Contact support for more information."
                    else:
                        message = f"✅ Account Restored\n\n"
                        message += f"Your account has been restored. You can use the bot again."
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=message
                    )
                    
                    logger.info(f"Ban status notification sent to user {user_id} via mirror bot {mirror_bot_id}")
                    
                finally:
                    await bot.session.close()
            
        except Exception as e:
            logger.error(f"Failed to notify user {user_id} about ban status via mirror bot: {e}")
    
    async def broadcast_message(
        self, 
        user_ids: list, 
        message: str,
        mirror_bot_id: Optional[int] = None
    ):
        """Отправить сообщение списку пользователей"""
        if not self.main_bot:
            logger.warning("Main bot not configured")
            return
        
        success_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                await self.main_bot.send_message(
                    chat_id=user_id,
                    text=message
                )
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                failed_count += 1
        
        logger.info(f"Broadcast completed: {success_count} success, {failed_count} failed")
        return {"success": success_count, "failed": failed_count}


# Глобальный экземпляр для использования в API
bot_integration = BotIntegration()
