"""
API для Worker CRM: выводы, отчёты о расходах, HR-метрики
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from decimal import Decimal

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel

from web_panel.database import get_db
from web_panel.auth import get_current_user
from web_panel.config import web_panel_config
from web_panel.services.audit_service import log_action
from shared.services.nocodb_service import NocoDBService

logger = logging.getLogger(__name__)
from shared.database.models import Worker, WorkerWithdrawal, WorkerExpenseReport, Order
from shared.services.ledger_service import LedgerService

router = APIRouter(prefix="/api/worker-crm", tags=["worker-crm"])


# ========== Withdrawals ==========

@router.get("/withdrawal-tasks")
async def get_withdrawal_tasks(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Заявки на вывод воркеров"""
    query = select(WorkerWithdrawal).order_by(WorkerWithdrawal.created_at.desc())
    if status:
        query = query.where(WorkerWithdrawal.status == status)
    result = await db.execute(query)
    tasks = result.scalars().all()
    items = []
    for t in tasks:
        worker_res = await db.execute(select(Worker).where(Worker.id == t.worker_id))
        worker = worker_res.scalar_one_or_none()
        items.append({
            "id": t.id,
            "worker_id": t.worker_id,
            "worker_name": (worker.username or f"#{worker.telegram_id}") if worker else "?",
            "amount": float(t.amount),
            "requisites": t.requisites,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "processed_at": t.processed_at.isoformat() if t.processed_at else None,
        })
    return {"withdrawals": items}


@router.post("/withdrawal-tasks/{task_id}/approve")
async def approve_withdrawal_task(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Одобрить вывод воркеру"""
    result = await db.execute(select(WorkerWithdrawal).where(WorkerWithdrawal.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    worker_res = await db.execute(select(Worker).where(Worker.id == task.worker_id))
    worker = worker_res.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    if not getattr(task, "funds_reserved", False):
        if not await LedgerService.reserve_worker_withdrawal(
            db,
            worker=worker,
            amount=task.amount,
            withdrawal_id=task.id,
        ):
            raise HTTPException(status_code=400, detail="Insufficient worker balance")
        task.funds_reserved = True
    await LedgerService.finalize_worker_withdrawal(
        db,
        worker=worker,
        amount=task.amount,
        withdrawal_id=task.id,
    )
    task.status = "approved"
    task.processed_at = datetime.now(timezone.utc)
    task.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "worker_withdrawal_approve",
        "worker_withdrawal",
        task.id,
        {
            "worker_id": task.worker_id,
            "amount": float(task.amount),
            "requisites": task.requisites,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="payout_status_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="worker_withdrawal",
        target_id=task.id,
        status="approved",
        payload={"worker_id": task.worker_id, "amount": float(task.amount)},
        timestamp=task.processed_at,
    )

    if web_panel_config.support_bot_token:
        try:
            bot = Bot(token=web_panel_config.support_bot_token)
            await bot.send_message(
                worker.telegram_id,
                f"✅ Withdrawal approved!\n\nAmount: ${float(task.amount):.2f}\n"
                f"Requisites: {task.requisites or '-'}",
                parse_mode=None,
            )
            await bot.session.close()
        except Exception as e:
            logger.warning("Failed to notify worker about withdrawal approval: %s", e)
    return {"ok": True}


class RejectBody(BaseModel):
    reason: Optional[str] = None


@router.post("/withdrawal-tasks/{task_id}/reject")
async def reject_withdrawal_task(
    task_id: int,
    request: Request,
    body: RejectBody = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Отклонить вывод"""
    result = await db.execute(select(WorkerWithdrawal).where(WorkerWithdrawal.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    worker = await db.scalar(select(Worker).where(Worker.id == task.worker_id))
    if worker and getattr(task, "funds_reserved", False):
        await LedgerService.release_worker_withdrawal_reservation(
            db,
            worker=worker,
            amount=task.amount,
            withdrawal_id=task.id,
        )
    task.status = "rejected"
    task.processed_at = datetime.now(timezone.utc)
    task.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    task.reject_reason = body.reason if body else None
    await log_action(
        db,
        current_user.get("admin_id"),
        "worker_withdrawal_reject",
        "worker_withdrawal",
        task.id,
        {
            "worker_id": task.worker_id,
            "amount": float(task.amount),
            "requisites": task.requisites,
            "reason": task.reject_reason,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request and request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="payout_status_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="worker_withdrawal",
        target_id=task.id,
        status="rejected",
        payload={"worker_id": task.worker_id, "amount": float(task.amount), "reason": task.reject_reason},
        timestamp=task.processed_at,
    )

    if worker and web_panel_config.support_bot_token:
        try:
            bot = Bot(token=web_panel_config.support_bot_token)
            text = f"❌ Withdrawal rejected\n\nAmount: ${float(task.amount):.2f}"
            if task.reject_reason:
                text += f"\nReason: {task.reject_reason}"
            await bot.send_message(worker.telegram_id, text, parse_mode=None)
            await bot.session.close()
        except Exception as e:
            logger.warning("Failed to notify worker about withdrawal rejection: %s", e)
    return {"ok": True}


# ========== Withdrawal Aliases (templates use /withdrawals, not /withdrawal-tasks) ==========

@router.get("/withdrawals")
async def get_withdrawals_alias(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Alias for /withdrawal-tasks — used by withdrawals.html and finance.html"""
    return await get_withdrawal_tasks(status=status, db=db, current_user=current_user)


@router.post("/withdrawals/{task_id}/approve")
async def approve_withdrawal_alias(
    task_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Alias for /withdrawal-tasks/{id}/approve"""
    return await approve_withdrawal_task(task_id=task_id, request=request, db=db, current_user=current_user)


@router.post("/withdrawals/{task_id}/reject")
async def reject_withdrawal_alias(
    task_id: int,
    request: Request,
    body: RejectBody = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Alias for /withdrawal-tasks/{id}/reject"""
    return await reject_withdrawal_task(task_id=task_id, request=request, body=body, db=db, current_user=current_user)


# ========== Expense Reports ==========

class CreateExpenseReport(BaseModel):
    worker_id: int
    amount: float
    category: str  # subscription, tools, other
    description: Optional[str] = None


@router.get("/expense-reports")
async def get_expense_reports(
    status: Optional[str] = None,
    worker_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Отчёты воркеров о расходах"""
    query = select(WorkerExpenseReport).order_by(WorkerExpenseReport.created_at.desc())
    if status:
        query = query.where(WorkerExpenseReport.status == status)
    if worker_id:
        query = query.where(WorkerExpenseReport.worker_id == worker_id)
    result = await db.execute(query)
    reports = result.scalars().all()
    items = []
    for r in reports:
        worker_res = await db.execute(select(Worker).where(Worker.id == r.worker_id))
        worker = worker_res.scalar_one_or_none()
        items.append({
            "id": r.id,
            "worker_id": r.worker_id,
            "worker_name": (worker.username or f"#{worker.telegram_id}") if worker else "?",
            "amount": float(r.amount),
            "category": r.category,
            "description": r.description,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            "admin_comment": r.admin_comment,
        })
    return {"reports": items}


@router.post("/expense-reports")
async def create_expense_report(
    body: CreateExpenseReport,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Создать отчёт о расходах (админ от имени воркера)"""
    worker_res = await db.execute(select(Worker).where(Worker.id == body.worker_id))
    worker = worker_res.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    r = WorkerExpenseReport(
        worker_id=body.worker_id,
        amount=Decimal(str(body.amount)),
        category=body.category,
        description=body.description,
        status="pending",
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": r.id, "status": "pending"}


@router.post("/expense-reports/{report_id}/approve")
async def approve_expense_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Одобрить отчёт о расходах"""
    result = await db.execute(select(WorkerExpenseReport).where(WorkerExpenseReport.id == report_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    if r.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    r.status = "approved"
    r.processed_at = datetime.now(timezone.utc)
    r.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    await db.commit()

    worker_res = await db.execute(select(Worker).where(Worker.id == r.worker_id))
    worker = worker_res.scalar_one_or_none()
    if worker and web_panel_config.support_bot_token:
        try:
            bot = Bot(token=web_panel_config.support_bot_token)
            await bot.send_message(
                worker.telegram_id,
                f"✅ Expense report approved!\n\nAmount: ${float(r.amount):.2f}\nCategory: {r.category}",
                parse_mode=None,
            )
            await bot.session.close()
        except Exception as e:
            logger.warning("Failed to notify worker about expense approval: %s", e)
    return {"ok": True}


@router.post("/expense-reports/{report_id}/reject")
async def reject_expense_report(
    report_id: int,
    body: RejectBody = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Отклонить отчёт о расходах"""
    result = await db.execute(select(WorkerExpenseReport).where(WorkerExpenseReport.id == report_id))
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    if r.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    r.status = "rejected"
    r.processed_at = datetime.now(timezone.utc)
    r.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    r.admin_comment = body.reason if body else None
    await db.commit()

    worker_res = await db.execute(select(Worker).where(Worker.id == r.worker_id))
    worker = worker_res.scalar_one_or_none()
    if worker and web_panel_config.support_bot_token:
        try:
            bot = Bot(token=web_panel_config.support_bot_token)
            text = f"❌ Expense report rejected\n\nAmount: ${float(r.amount):.2f}\nCategory: {r.category}"
            if r.admin_comment:
                text += f"\nReason: {r.admin_comment}"
            await bot.send_message(worker.telegram_id, text, parse_mode=None)
            await bot.session.close()
        except Exception as e:
            logger.warning("Failed to notify worker about expense rejection: %s", e)
    return {"ok": True}


# ========== HR Metrics ==========

@router.get("/hr-metrics")
async def get_hr_metrics(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    HR-метрики для отслеживания воркеров:
    - Время выполнения заказов (taken_at → completed_at)
    - Время до первого ответа
    - Заказов на воркера
    - Средний чек и т.д.
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Заказы с taken_at и completed_at
    orders_result = await db.execute(
        select(
            Order.worker_id,
            Order.id,
            Order.taken_at,
            Order.completed_at,
            Order.price,
            Order.status,
        )
        .where(
            Order.worker_id.isnot(None),
            Order.taken_at.isnot(None),
            Order.completed_at.isnot(None),
            Order.status == "completed",
            Order.completed_at >= start_date,
        )
    )
    orders = orders_result.all()

    # Расчёт времени выполнения (в минутах)
    completion_times = []
    worker_metrics = {}

    for row in orders:
        worker_id, order_id, taken_at, completed_at, price, status = row
        if taken_at and completed_at:
            delta = (completed_at - taken_at).total_seconds() / 60
            completion_times.append(delta)
            if worker_id not in worker_metrics:
                worker_metrics[worker_id] = {
                    "worker_id": worker_id,
                    "orders_count": 0,
                    "completion_times": [],
                    "total_revenue": 0.0,
                }
            worker_metrics[worker_id]["orders_count"] += 1
            worker_metrics[worker_id]["completion_times"].append(delta)
            worker_metrics[worker_id]["total_revenue"] += float(price or 0)

    # Агрегация по воркерам
    workers_result = await db.execute(select(Worker).where(Worker.id.in_(worker_metrics.keys())))
    workers_map = {w.id: w for w in workers_result.scalars().all()}

    by_worker = []
    for wid, m in worker_metrics.items():
        times = m["completion_times"]
        avg_min = sum(times) / len(times) if times else 0
        worker = workers_map.get(wid)
        by_worker.append({
            "worker_id": wid,
            "worker_name": (worker.username or f"#{worker.telegram_id}") if worker else "?",
            "orders_count": m["orders_count"],
            "avg_completion_minutes": round(avg_min, 1),
            "min_completion_minutes": round(min(times), 1) if times else 0,
            "max_completion_minutes": round(max(times), 1) if times else 0,
            "total_revenue": round(m["total_revenue"], 2),
        })

    by_worker.sort(key=lambda x: x["orders_count"], reverse=True)

    # Общие метрики
    all_times = [t for m in worker_metrics.values() for t in m["completion_times"]]
    total_orders = len(orders)
    total_revenue = sum(m["total_revenue"] for m in worker_metrics.values())

    return {
        "period_days": period_days,
        "summary": {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "avg_completion_minutes": round(sum(all_times) / len(all_times), 1) if all_times else 0,
            "min_completion_minutes": round(min(all_times), 1) if all_times else 0,
            "max_completion_minutes": round(max(all_times), 1) if all_times else 0,
            "workers_count": len(worker_metrics),
        },
        "by_worker": by_worker,
    }
