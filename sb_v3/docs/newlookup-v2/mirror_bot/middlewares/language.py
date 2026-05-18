"""
Language middleware for Mirror Bot
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import User as UserModel
from mirror_bot.constants.language_loader import LanguageLoader
from shared.services.ui_translation_service import UiTranslator

logger = logging.getLogger(__name__)


class LanguageMiddleware(BaseMiddleware):
    """
    Middleware для автоматического определения языка пользователя
    и добавления его в контекст обработчика
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события и добавление языка пользователя в контекст
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие Telegram
            data: Данные контекста
            
        Returns:
            Результат выполнения обработчика
        """
        
        # Получаем пользователя из события
        user: User = data.get('event_from_user')
        if not user:
            # Если пользователь не найден, используем язык по умолчанию
            data['user_language'] = LanguageLoader.DEFAULT_LANGUAGE
            data['texts'] = LanguageLoader.get_texts()
            data['buttons'] = LanguageLoader.get_buttons()
            return await handler(event, data)
        
        # Получаем сессию базы данных
        session: AsyncSession = data.get('session')
        mirror_bot_id: int = data.get('mirror_bot_id')
        
        user_language = LanguageLoader.DEFAULT_LANGUAGE
        
        if session and mirror_bot_id:
            try:
                # Ищем пользователя в базе данных
                stmt = select(UserModel).where(
                    UserModel.user_id == user.id,
                    UserModel.mirror_bot_id == mirror_bot_id
                )
                result = await session.execute(stmt)
                db_user = result.scalar_one_or_none()
                
                if db_user and db_user.language:
                    user_language = db_user.language
                    
            except Exception as e:
                logger.error("Error getting user language: %s", e)
        
        # Добавляем язык и тексты в контекст
        data['user_language'] = user_language
        data['texts'] = LanguageLoader.get_texts(user_language)
        data['buttons'] = LanguageLoader.get_buttons(user_language)
        data['ui_texts'] = UiTranslator(session=session, language=user_language, namespace="mirror_bot")
        
        # Вызываем следующий обработчик
        return await handler(event, data)


class LanguageHelper:
    """
    Вспомогательный класс для работы с языками в обработчиках
    """
    
    @staticmethod
    def get_texts_from_data(data: Dict[str, Any]):
        """Получить тексты из данных контекста"""
        return data.get('texts', LanguageLoader.get_texts())
    
    @staticmethod
    def get_buttons_from_data(data: Dict[str, Any]):
        """Получить кнопки из данных контекста"""
        return data.get('buttons', LanguageLoader.get_buttons())
    
    @staticmethod
    def get_language_from_data(data: Dict[str, Any]) -> str:
        """Получить язык из данных контекста"""
        return data.get('user_language', LanguageLoader.DEFAULT_LANGUAGE)
    
    @staticmethod
    async def update_user_language(
        session: AsyncSession, 
        user_id: int, 
        mirror_bot_id: int, 
        new_language: str
    ) -> bool:
        """
        Обновить язык пользователя в базе данных
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            mirror_bot_id: ID mirror bot
            new_language: Новый язык
            
        Returns:
            True если обновление прошло успешно
        """
        try:
            # Проверяем что язык поддерживается
            if new_language not in LanguageLoader.SUPPORTED_LANGUAGES:
                return False
            
            # Ищем пользователя
            stmt = select(UserModel).where(
                UserModel.user_id == user_id,
                UserModel.mirror_bot_id == mirror_bot_id
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # Обновляем язык
                user.language = new_language
                await session.commit()
                return True
                
        except Exception as e:
            logger.error("Error updating user language: %s", e)
            await session.rollback()
            
        return False
