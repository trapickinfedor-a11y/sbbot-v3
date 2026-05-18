"""
Сервис уведомлений для Support Tickets
Отправляет уведомления пользователям о новых ответах от админов
"""

import logging
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from shared.database.models import MirrorBot, SupportTicket, SupportMessage, User
from mirror_bot.constants.language_loader import get_texts

logger = logging.getLogger(__name__)


class SupportNotificationService:
    """Сервис отправки уведомлений пользователям о новых ответах в тикетах"""
    
    @staticmethod
    async def get_user_language(session: AsyncSession, user_id: int, mirror_bot_id: int) -> str:
        """Получить язык пользователя из базы данных"""
        try:
            stmt = select(User).where(
                User.user_id == user_id,
                User.mirror_bot_id == mirror_bot_id
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user and user.language:
                return user.language
            return "en"  # По умолчанию английский
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return "en"
    
    @staticmethod
    async def notify_user_about_reply(
        session: AsyncSession,
        ticket_id: int,
        message_text: str,
        files: Optional[list] = None
    ) -> bool:
        """
        Отправить уведомление пользователю о новом ответе в тикете
        
        Args:
            session: Сессия БД
            ticket_id: ID тикета
            message_text: Текст сообщения от админа
            files: Список файлов (опционально)
            
        Returns:
            True если уведомление отправлено, False otherwise
        """
        try:
            # Получаем тикет
            ticket_result = await session.execute(
                select(SupportTicket).where(SupportTicket.id == ticket_id)
            )
            ticket = ticket_result.scalar_one_or_none()
            
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found")
                return False
            
            # Получаем bot token
            bot_result = await session.execute(
                select(MirrorBot).where(MirrorBot.id == ticket.mirror_bot_id)
            )
            mirror_bot = bot_result.scalar_one_or_none()
            
            if not mirror_bot:
                logger.error(f"Mirror bot {ticket.mirror_bot_id} not found")
                return False
            
            # Создаем Bot экземпляр
            bot = Bot(token=mirror_bot.bot_token)
            
            try:
                # Получаем язык пользователя
                user_language = await SupportNotificationService.get_user_language(session, ticket.user_id, ticket.mirror_bot_id)
                texts = get_texts(user_language)
                
                # Формируем сообщение
                notification_text = (
                    texts.SUPPORT_NEW_REPLY_TITLE.format(ticket_id=ticket.id) +
                    texts.SUPPORT_REPLY_CATEGORY_LABEL.format(category=ticket.category) +
                    texts.SUPPORT_REPLY_SUBJECT_LABEL.format(subject=ticket.subject) +
                    texts.SUPPORT_REPLY_FROM_SUPPORT_LABEL +
                    f"{message_text}"
                )
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=ticket.user_id,
                    text=notification_text,
                    parse_mode="Markdown"
                )
                
                # Если есть файлы, отправляем их
                if files:
                    from mirror_bot.services.file_service import FileService
                    
                    file_service = FileService(bot)
                    
                    for file_info in files:
                        # Отправляем файл пользователю
                        success = await file_service.send_file_to_user(
                            chat_id=ticket.user_id,
                            file_data=file_info
                        )
                        
                        if not success:
                            logger.error(f"Failed to send file {file_info.get('file_id')} to user {ticket.user_id}")
                            # Отправляем сообщение об ошибке
                            await bot.send_message(
                                chat_id=ticket.user_id,
                                text=f"❌ Не удалось отправить файл: {file_info.get('file_name', 'Неизвестный файл')}"
                            )
                
                logger.info(f"Notification sent to user {ticket.user_id} for ticket {ticket_id}")
                return True
                
            finally:
                await bot.session.close()
                
        except Exception as e:
            logger.error(f"Error sending notification for ticket {ticket_id}: {e}")
            return False
    
    @staticmethod
    async def notify_user_about_status_change(
        session: AsyncSession,
        ticket_id: int,
        new_status: str
    ) -> bool:
        """
        Отправить уведомление пользователю об изменении статуса тикета
        
        Args:
            session: Сессия БД
            ticket_id: ID тикета
            new_status: Новый статус
            
        Returns:
            True если уведомление отправлено, False otherwise
        """
        try:
            # Получаем тикет
            ticket_result = await session.execute(
                select(SupportTicket).where(SupportTicket.id == ticket_id)
            )
            ticket = ticket_result.scalar_one_or_none()
            
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found")
                return False
            
            # Получаем bot token
            bot_result = await session.execute(
                select(MirrorBot).where(MirrorBot.id == ticket.mirror_bot_id)
            )
            mirror_bot = bot_result.scalar_one_or_none()
            
            if not mirror_bot:
                logger.error(f"Mirror bot {ticket.mirror_bot_id} not found")
                return False
            
            # Создаем Bot экземпляр
            bot = Bot(token=mirror_bot.bot_token)
            
            try:
                # Получаем язык пользователя
                user_language = await SupportNotificationService.get_user_language(session, ticket.user_id, ticket.mirror_bot_id)
                texts = get_texts(user_language)
                
                # Маппинг статусов на многоязычные названия
                status_text = {
                    "open": texts.STATUS_OPEN,
                    "in_progress": texts.STATUS_IN_PROGRESS,
                    "waiting_user": texts.STATUS_WAITING_USER,
                    "closed": texts.STATUS_CLOSED
                }.get(new_status, new_status)
                
                # Формируем сообщение
                notification_text = (
                    texts.SUPPORT_STATUS_CHANGE_TITLE.format(ticket_id=ticket.id) +
                    texts.SUPPORT_STATUS_SUBJECT_LABEL.format(subject=ticket.subject) +
                    texts.SUPPORT_STATUS_NEW_STATUS_LABEL.format(status=status_text)
                )
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=ticket.user_id,
                    text=notification_text,
                    parse_mode="Markdown"
                )
                
                logger.info(f"Status change notification sent to user {ticket.user_id} for ticket {ticket_id}")
                return True
                
            finally:
                await bot.session.close()
                
        except Exception as e:
            logger.error(f"Error sending status notification for ticket {ticket_id}: {e}")
            return False

