"""Worker Score Service — расчёт рейтинга воркера"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import Worker, WorkerOrder, WorkerStats


async def recalculate_worker_score(session: AsyncSession, worker_id: int) -> float:
    """
    Seller Score = (avg_buyer_rating * 0.6) + (success_rate * 0.2) + (speed_bonus * 0.2)
    Worker Score = success_rate * 0.6 + speed_factor * 0.2 + tenure_bonus * 0.2
    """
    worker_r = await session.execute(select(Worker).where(Worker.id == worker_id))
    worker = worker_r.scalar_one_or_none()
    if not worker:
        return 5.0

    # Success rate: completed / total
    total_r = await session.execute(
        select(func.count(WorkerOrder.id)).where(WorkerOrder.worker_id == worker_id)
    )
    total = total_r.scalar() or 0

    completed_r = await session.execute(
        select(func.count(WorkerOrder.id)).where(
            and_(WorkerOrder.worker_id == worker_id, WorkerOrder.status == "completed")
        )
    )
    completed = completed_r.scalar() or 0
    success_rate = (completed / total) if total > 0 else 1.0

    # Avg completion time (minutes)
    avg_time_r = await session.execute(
        select(
            func.avg(
                func.julianday(WorkerOrder.completed_at) * 1440
                - func.julianday(WorkerOrder.taken_at) * 1440
            )
        ).where(
            and_(
                WorkerOrder.worker_id == worker_id,
                WorkerOrder.status == "completed",
                WorkerOrder.taken_at.isnot(None),
                WorkerOrder.completed_at.isnot(None),
            )
        )
    )
    avg_minutes = avg_time_r.scalar()
    if avg_minutes is None:
        avg_minutes = 30.0

    # Speed factor: faster = higher (target < 15 min = full score)
    speed_factor = min(1.0, 15.0 / max(avg_minutes, 1.0))

    # Tenure bonus: days on platform / 180 * 0.5 (max 0.5)
    days_on = (datetime.now(timezone.utc) - worker.created_at).days
    tenure_bonus = min(0.5, days_on / 180 * 0.5)

    raw_score = success_rate * 0.6 + speed_factor * 0.2 + tenure_bonus * 0.2
    score = round(1.0 + raw_score * 4.0, 2)  # scale 1.0..5.0
    score = max(1.0, min(5.0, score))

    worker.worker_score = score
    worker.success_rate = success_rate
    worker.avg_completion_minutes = avg_minutes
    worker.score_updated_at = datetime.now(timezone.utc)
    await session.commit()
    return score


async def get_worker_dashboard(session: AsyncSession, worker_id: int) -> dict:
    """KPI-дашборд воркера"""
    worker_r = await session.execute(select(Worker).where(Worker.id == worker_id))
    worker = worker_r.scalar_one_or_none()
    if not worker:
        return {}

    # Today stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_r = await session.execute(
        select(
            func.count(WorkerOrder.id).label("total"),
            func.sum(
                func.cast(WorkerOrder.status == "completed", type_=None)
            ).label("completed"),
        ).where(
            and_(WorkerOrder.worker_id == worker_id, WorkerOrder.created_at >= today_start)
        )
    )
    today_row = today_r.one_or_none()
    today_total = today_row.total if today_row else 0
    today_done = today_row.completed if today_row else 0

    # Active orders
    active_r = await session.execute(
        select(func.count(WorkerOrder.id)).where(
            and_(WorkerOrder.worker_id == worker_id, WorkerOrder.status == "in_progress")
        )
    )
    active_count = active_r.scalar() or 0

    # Month earnings from stats
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_earnings_r = await session.execute(
        select(func.coalesce(func.sum(WorkerStats.earnings), 0)).where(
            and_(
                WorkerStats.worker_id == worker_id,
                WorkerStats.date >= month_start,
            )
        )
    )
    month_earnings = float(month_earnings_r.scalar() or 0)

    # Recalculate score if stale
    if not worker.score_updated_at or (datetime.now(timezone.utc) - worker.score_updated_at).seconds > 3600:
        await recalculate_worker_score(session, worker_id)
        await session.refresh(worker)

    return {
        "worker_score": worker.worker_score,
        "avg_minutes": worker.avg_completion_minutes or 0,
        "success_rate": worker.success_rate,
        "total_completed": worker.orders_completed,
        "active_orders": active_count,
        "today_total": today_total,
        "today_done": today_done,
        "month_earnings": month_earnings,
        "balance": float(worker.balance or 0),
    }
