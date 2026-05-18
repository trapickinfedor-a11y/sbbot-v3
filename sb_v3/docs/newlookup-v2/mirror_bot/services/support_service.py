from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from shared.database.models import SupportTicket, SupportMessage
from shared.services.nocodb_service import NocoDBService
from typing import Optional, List
from datetime import datetim, timezone
import logging

logger = logging.getLogger(__name__)


class SupportService:
    """Сервис для работы с support tickets"""
    
    @staticmethod
    async def create_ticket(
        session: AsyncSession,
        user_id: int,
        mirror_bot_id: int,
        category: str,
        subject: str,
        initial_message: str
    ) -> SupportTicket:
        """Создать новый тикет"""
        ticket = SupportTicket(
            user_id=user_id,
            mirror_bot_id=mirror_bot_id,
            category=category,
            subject=subject,
            status="open"
        )
        
        session.add(ticket)
        await session.flush()
        
        # Добавляем первое сообщение
        message = SupportMessage(
            ticket_id=ticket.id,
            sender_type="user",
            sender_id=user_id,
            message_text=initial_message,
            is_read=True  # Свое сообщение сразу прочитано
        )
        
        session.add(message)
        await session.commit()
        await session.refresh(ticket)
        NocoDBService.log_support_ticket(
            ticket_id=ticket.id,
            user_id=user_id,
            message=initial_message,
            extra={
                "mirror_bot_id": mirror_bot_id,
                "category": category,
                "subject": subject,
                "sender_type": "user",
            },
        )
        
        # Уведомляем админов о новом тикете
        try:
            from shared.services.admin_notification_service import AdminNotificationService
            await AdminNotificationService.notify_new_support_ticket(
                ticket_id=ticket.id,
                user_id=user_id,
                category=category,
                subject=subject
            )
        except Exception as e:
            logger.warning(f"Failed to send admin notification about new ticket: {e}")
        
        return ticket
    
    @staticmethod
    async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> Optional[SupportTicket]:
        """Получить тикет по ID"""
        result = await session.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_ticket_with_messages(session: AsyncSession, ticket_id: int) -> Optional[SupportTicket]:
        """Получить тикет с сообщениями"""
        result = await session.execute(
            select(SupportTicket)
            .where(SupportTicket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        
        if ticket:
            # Подгружаем messages через relationship
            await session.refresh(ticket, ["messages"])
        
        return ticket
    
    @staticmethod
    async def get_user_tickets(
        session: AsyncSession,
        user_id: int,
        mirror_bot_id: int,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[SupportTicket]:
        """Получить тикеты пользователя"""
        query = select(SupportTicket).where(
            and_(
                SupportTicket.user_id == user_id,
                SupportTicket.mirror_bot_id == mirror_bot_id
            )
        )
        
        if status == "open":
            query = query.where(SupportTicket.status.in_(["open", "in_progress", "waiting_user"]))
        elif status == "closed":
            query = query.where(SupportTicket.status == "closed")
        elif status:
            query = query.where(SupportTicket.status == status)
        
        query = query.order_by(SupportTicket.updated_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def add_message_to_ticket(
        session: AsyncSession,
        ticket_id: int,
        sender_type: str,
        sender_id: int,
        message_text: str,
        files: Optional[list] = None
    ) -> SupportMessage:
        """Добавить сообщение к тикету"""
        message = SupportMessage(
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message_text=message_text,
            files=files,
            is_read=False  # Новое сообщение не прочитано
        )
        
        session.add(message)
        
        # Обновляем updated_at тикета
        ticket = await SupportService.get_ticket_by_id(session, ticket_id)
        if ticket:
            ticket.updated_at = datetime.now(timezone.utc)
        
        await session.commit()
        await session.refresh(message)
        ticket = await SupportService.get_ticket_by_id(session, ticket_id)
        NocoDBService.log_support_ticket(
            ticket_id=ticket_id,
            user_id=ticket.user_id if ticket else sender_id,
            message=message_text if sender_type != "admin" else None,
            support_reply=message_text if sender_type == "admin" else None,
            files=files,
            timestamp=message.created_at,
            extra={"sender_type": sender_type, "sender_id": sender_id},
        )
        
        return message
    
    @staticmethod
    async def update_ticket_status(
        session: AsyncSession,
        ticket_id: int,
        status: str
    ) -> bool:
        """Обновить статус тикета"""
        ticket = await SupportService.get_ticket_by_id(session, ticket_id)
        
        if not ticket:
            return False
        
        ticket.status = status
        ticket.updated_at = datetime.now(timezone.utc)
        
        if status == "closed":
            ticket.closed_at = datetime.now(timezone.utc)
        
        await session.commit()
        return True
    
    @staticmethod
    async def mark_messages_as_read(
        session: AsyncSession,
        ticket_id: int,
        user_id: int
    ):
        """Отметить сообщения как прочитанные"""
        # Получаем непрочитанные сообщения, которые НЕ от этого пользователя
        result = await session.execute(
            select(SupportMessage).where(
                and_(
                    SupportMessage.ticket_id == ticket_id,
                    SupportMessage.is_read == False,
                    SupportMessage.sender_id != user_id
                )
            )
        )
        
        messages = result.scalars().all()
        
        for message in messages:
            message.is_read = True
        
        await session.commit()
    
    @staticmethod
    async def get_unread_messages_count(
        session: AsyncSession,
        ticket_id: int,
        user_id: int
    ) -> int:
        """Получить количество непрочитанных сообщений для пользователя"""
        result = await session.execute(
            select(func.count(SupportMessage.id)).where(
                and_(
                    SupportMessage.ticket_id == ticket_id,
                    SupportMessage.is_read == False,
                    SupportMessage.sender_id != user_id  # Не считаем свои сообщения
                )
            )
        )
        
        return result.scalar_one()
    
    @staticmethod
    async def get_all_tickets(
        session: AsyncSession,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[SupportTicket]:
        """Получить все тикеты (для админ-панели)"""
        query = select(SupportTicket)
        
        if category:
            query = query.where(SupportTicket.category == category)
        
        if status:
            if status == "open":
                query = query.where(SupportTicket.status.in_(["open", "in_progress", "waiting_user"]))
            elif status == "closed":
                query = query.where(SupportTicket.status == "closed")
            else:
                query = query.where(SupportTicket.status == status)
        
        query = query.order_by(SupportTicket.updated_at.desc())
        
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_tickets_count(
        session: AsyncSession,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Получить количество тикетов"""
        query = select(func.count(SupportTicket.id))
        
        if category:
            query = query.where(SupportTicket.category == category)
        
        if status:
            if status == "open":
                query = query.where(SupportTicket.status.in_(["open", "in_progress", "waiting_user"]))
            elif status == "closed":
                query = query.where(SupportTicket.status == "closed")
            else:
                query = query.where(SupportTicket.status == status)
        
        result = await session.execute(query)
        return result.scalar_one()

