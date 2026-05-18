"""
Сервис для работы с жалобами в Support Bot
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.database.models import Complaint, Worker, User
from typing import Optional


class ComplaintService:
    """Сервис для создания жалоб от работников"""
    
    @staticmethod
    async def create_complaint(
        session: AsyncSession,
        worker_id: int,
        user_id: int,
        order_id: Optional[int],
        reason: str,
        description: str
    ) -> Complaint:
        """Создать новую жалобу"""
        
        complaint = Complaint(
            worker_id=worker_id,
            user_id=user_id,
            order_id=order_id,
            reason=reason,
            description=description,
            status="pending"
        )
        
        session.add(complaint)
        await session.commit()
        await session.refresh(complaint)
        
        return complaint
    
    @staticmethod
    async def get_worker_complaints(
        session: AsyncSession,
        worker_id: int,
        limit: int = 20
    ):
        """Получить жалобы работника"""
        
        result = await session.execute(
            select(Complaint)
            .where(Complaint.worker_id == worker_id)
            .order_by(Complaint.created_at.desc())
            .limit(limit)
        )
        
        return list(result.scalars().all())

