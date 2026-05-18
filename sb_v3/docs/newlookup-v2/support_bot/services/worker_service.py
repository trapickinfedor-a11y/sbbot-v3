"""
Сервис для работы с воркерами (саппортами)
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from shared.database.models import Worker, WorkerStats


class WorkerService:
    """Сервис для управления воркерами"""
    
    @staticmethod
    async def get_worker(session: AsyncSession, telegram_id: int) -> Optional[Worker]:
        """Получить воркера по Telegram ID"""
        result = await session.execute(
            select(Worker).where(Worker.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_active_workers(session: AsyncSession) -> List[Worker]:
        """Получить всех активных воркеров"""
        result = await session.execute(
            select(Worker).where(
                Worker.is_active == True,
                Worker.is_suspended == False,
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def is_worker_active(session: AsyncSession, telegram_id: int) -> bool:
        """Проверить, является ли пользователь активным воркером"""
        worker = await WorkerService.get_worker(session, telegram_id)
        return worker is not None and worker.is_active and not getattr(worker, "is_suspended", False)
    
    @staticmethod
    async def create_worker(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str],
        categories: List[str]
    ) -> Worker:
        """Создать нового воркера"""
        worker = Worker(
            telegram_id=telegram_id,
            username=username,
            categories=categories,
            is_active=True
        )
        session.add(worker)
        await session.commit()
        await session.refresh(worker)
        return worker
    
    @staticmethod
    async def update_categories(
        session: AsyncSession,
        worker: Worker,
        categories: List[str]
    ) -> Worker:
        """Обновить категории воркера"""
        worker.categories = categories
        await session.commit()
        await session.refresh(worker)
        return worker
    
    @staticmethod
    async def update_services(
        session: AsyncSession,
        worker: Worker,
        services: List[str]
    ) -> Worker:
        """Обновить сервисы воркера"""
        worker.services = services
        await session.commit()
        await session.refresh(worker)
        return worker
    
    @staticmethod
    async def get_worker_stats_today(
        session: AsyncSession,
        worker_id: int
    ) -> List[WorkerStats]:
        """Получить статистику воркера за сегодня"""
        today = date.today()
        result = await session.execute(
            select(WorkerStats).where(
                WorkerStats.worker_id == worker_id,
                WorkerStats.date == today
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_worker_stats_period(
        session: AsyncSession,
        worker_id: int,
        start_date: date,
        end_date: date
    ) -> List[WorkerStats]:
        """Получить статистику воркера за период"""
        result = await session.execute(
            select(WorkerStats).where(
                WorkerStats.worker_id == worker_id,
                WorkerStats.date >= start_date,
                WorkerStats.date <= end_date
            )
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_or_create_stats(
        session: AsyncSession,
        worker_id: int,
        category: str
    ) -> WorkerStats:
        """Получить или создать статистику за сегодня"""
        today = date.today()
        
        result = await session.execute(
            select(WorkerStats).where(
                WorkerStats.worker_id == worker_id,
                WorkerStats.date == today,
                WorkerStats.category == category
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            stats = WorkerStats(
                worker_id=worker_id,
                date=today,
                category=category
            )
            session.add(stats)
            await session.commit()
            await session.refresh(stats)
        
        return stats
    
    @staticmethod
    async def increment_stat(
        session: AsyncSession,
        worker_id: int,
        category: str,
        stat_type: str  # "done", "nf", "cancelled"
    ):
        """Увеличить счетчик статистики"""
        stats = await WorkerService.get_or_create_stats(session, worker_id, category)
        
        if stat_type == "done":
            stats.orders_done += 1
        elif stat_type == "nf":
            stats.orders_nf += 1
        elif stat_type == "cancelled":
            stats.orders_cancelled += 1
        
        stats.orders_total += 1
        await session.commit()

