"""
Сервис для получения информации о пользователях и ботах из Telegram API
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

logger = logging.getLogger(__name__)


class TelegramInfoService:
    """Сервис для получения информации из Telegram API"""
    
    @staticmethod
    async def get_bot_info(bot_token: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о боте по токену
        
        Args:
            bot_token: Токен бота
            
        Returns:
            Словарь с информацией о боте или None при ошибке
        """
        try:
            bot = Bot(token=bot_token)
            bot_info = await bot.get_me()
            await bot.session.close()
            
            return {
                'id': bot_info.id,
                'username': bot_info.username,
                'first_name': bot_info.first_name,
                'is_bot': bot_info.is_bot
            }
        except (TelegramBadRequest, TelegramAPIError) as e:
            logger.warning(f"Не удалось получить информацию о боте: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении информации о боте: {e}")
            return None
    
    @staticmethod
    async def get_user_info(bot_token: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе через бота
        
        Args:
            bot_token: Токен бота
            user_id: ID пользователя
            
        Returns:
            Словарь с информацией о пользователе или None при ошибке
        """
        try:
            bot = Bot(token=bot_token)
            
            # Пытаемся получить информацию о пользователе через getChat
            try:
                chat = await bot.get_chat(user_id)
                await bot.session.close()
                
                return {
                    'id': chat.id,
                    'username': chat.username,
                    'first_name': chat.first_name,
                    'last_name': chat.last_name,
                    'type': chat.type
                }
            except TelegramBadRequest:
                # Если getChat не работает, пользователь не начинал диалог с ботом
                logger.info(f"Пользователь {user_id} не начинал диалог с ботом")
                await bot.session.close()
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе {user_id}: {e}")
            return None
    
    @staticmethod
    async def update_bot_usernames(db_session, bot_tokens: Dict[int, str]) -> int:
        """
        Обновляет username всех ботов в базе данных
        
        Args:
            db_session: Сессия базы данных
            bot_tokens: Словарь {bot_id: bot_token}
            
        Returns:
            Количество обновленных ботов
        """
        from shared.database.models import MirrorBot
        from sqlalchemy import update
        
        updated_count = 0
        
        for bot_id, bot_token in bot_tokens.items():
            bot_info = await TelegramInfoService.get_bot_info(bot_token)
            if bot_info and bot_info.get('username'):
                # Обновляем username в базе данных
                stmt = update(MirrorBot).where(
                    MirrorBot.id == bot_id
                ).values(bot_username=bot_info['username'])
                
                await db_session.execute(stmt)
                updated_count += 1
                logger.info(f"Обновлен username бота {bot_id}: @{bot_info['username']}")
        
        await db_session.commit()
        return updated_count
    
    @staticmethod
    async def update_user_usernames(db_session, user_data: list) -> int:
        """
        Обновляет username пользователей в базе данных
        
        Args:
            db_session: Сессия базы данных  
            user_data: Список кортежей (user_id, telegram_user_id, bot_token)
            
        Returns:
            Количество обновленных пользователей
        """
        from shared.database.models import User
        from sqlalchemy import update
        
        updated_count = 0
        
        for user_id, telegram_user_id, bot_token in user_data:
            user_info = await TelegramInfoService.get_user_info(bot_token, telegram_user_id)
            if user_info and user_info.get('username'):
                # Обновляем username в базе данных
                stmt = update(User).where(
                    User.id == user_id
                ).values(username=user_info['username'])
                
                await db_session.execute(stmt)
                updated_count += 1
                logger.info(f"Обновлен username пользователя {user_id}: @{user_info['username']}")
            
            # Добавляем небольшую задержку, чтобы не превысить лимиты API
            await asyncio.sleep(0.1)
        
        await db_session.commit()
        return updated_count
