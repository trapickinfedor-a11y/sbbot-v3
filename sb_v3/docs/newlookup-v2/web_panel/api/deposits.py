"""Ledger explorer and reconciliation diagnostics."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Transaction, User, Worker, WorkerOrder
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.ledger_reconciliation_service import LedgerReconciliationService
from web_panel.auth import require_finance_access
from web_panel.database import get_db

router = APIRouter()


@router.get("/stats")
async def get_deposit_stats(
    period_days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
    total = await db.scalar(select(func.count(Transaction.id))) or 0
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    completed_amount = float(
        await db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.status == "completed")
        )
        or 0
    )
    pending_count = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.status == "pending"))
        or 0
    )
    on_hold_count = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.status == "on_hold"))
        or 0
    )
    failed_count = int(
        await db.scalar(select(func.count(Transaction.id)).where(Transaction.status == "failed"))
        or 0
    )
    topup_row = (
        await db.execute(
            select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.type == "topup"
            )
        )
    ).first()
    period_row = (
        await db.execute(
            select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.created_at >= start_date
            )
        )
    ).first()
    today_row = (
        await db.execute(
            select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.created_at >= today_start
            )
        )
    ).first()

    return {
        "total_transactions": total,
        "topup_count": int(topup_row[0] or 0),
        "topup_total": float(topup_row[1] or 0),
        "period_count": int(period_row[0] or 0),
        "period_total": float(period_row[1] or 0),
        "period_days": period_days,
        "today_count": int(today_row[0] or 0),
        "today_total": float(today_row[1] or 0),
        "completed_total_amount": completed_amount,
        "pending_count": pending_count,
        "on_hold_count": on_hold_count,
        "failed_count": failed_count,
        "total_workers": int(await db.scalar(select(func.count(Worker.id))) or 0),
        "active_workers": int(
            await db.scalar(select(func.count(Worker.id)).where(Worker.is_active == True, Worker.is_suspended == False))
            or 0
        ),
        "worker_orders_completed": int(
            await db.scalar(select(func.count(WorkerOrder.id)).where(WorkerOrder.status == "completed"))
            or 0
        ),
    }


@router.get("/")
async def get_deposits(
    type: Optional[str] = None,
    status: Optional[str] = None,
    account_type: Optional[str] = None,
    account_id: Optional[int] = None,
    user_id: Optional[int] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    count_stmt = select(func.count(Transaction.id))
    data_stmt = select(Transaction)

    if type:
        count_stmt = count_stmt.where(Transaction.type == type)
        data_stmt = data_stmt.where(Transaction.type == type)
    if status:
        count_stmt = count_stmt.where(Transaction.status == status)
        data_stmt = data_stmt.where(Transaction.status == status)
    if account_type:
        count_stmt = count_stmt.where(Transaction.account_type == account_type)
        data_stmt = data_stmt.where(Transaction.account_type == account_type)
    if account_id is not None:
        count_stmt = count_stmt.where(Transaction.account_id == account_id)
        data_stmt = data_stmt.where(Transaction.account_id == account_id)

    if user_id:
        count_stmt = count_stmt.where(Transaction.user_id == user_id)
        data_stmt = data_stmt.where(Transaction.user_id == user_id)
    if related_entity_type:
        count_stmt = count_stmt.where(Transaction.related_entity_type == related_entity_type)
        data_stmt = data_stmt.where(Transaction.related_entity_type == related_entity_type)
    if related_entity_id is not None:
        count_stmt = count_stmt.where(Transaction.related_entity_id == related_entity_id)
        data_stmt = data_stmt.where(Transaction.related_entity_id == related_entity_id)
    if idempotency_key:
        count_stmt = count_stmt.where(Transaction.idempotency_key == idempotency_key)
        data_stmt = data_stmt.where(Transaction.idempotency_key == idempotency_key)
    if search:
        pattern = f"%{search.strip()}%"
        count_stmt = count_stmt.where(
            or_(
                Transaction.description.ilike(pattern),
                Transaction.idempotency_key.ilike(pattern),
                Transaction.related_entity_type.ilike(pattern),
            )
        )
        data_stmt = data_stmt.where(
            or_(
                Transaction.description.ilike(pattern),
                Transaction.idempotency_key.ilike(pattern),
                Transaction.related_entity_type.ilike(pattern),
            )
        )

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    data_stmt = data_stmt.order_by(desc(Transaction.created_at)).limit(limit).offset(offset)
    result = await db.execute(data_stmt)
    transactions = result.scalars().all()

    user_ids = list(set(t.user_id for t in transactions))
    users_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.user_id.in_(user_ids))
        )
        for u in users_result.scalars().all():
            users_map[u.user_id] = u

    items = []
    for t in transactions:
        user = users_map.get(t.user_id)
        items.append({
            "id": t.id,
            "user_id": t.user_id,
            "username": user.username if user else None,
            "account_type": t.account_type,
            "account_id": t.account_id,
            "type": t.type,
            "amount": float(t.amount),
            "currency": t.currency,
            "status": t.status,
            "related_entity_type": t.related_entity_type,
            "related_entity_id": t.related_entity_id,
            "effective_at": t.effective_at.isoformat() if t.effective_at else None,
            "idempotency_key": t.idempotency_key,
            "description": t.description,
            "created_at": t.created_at.isoformat(),
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items
    }


@router.get("/projection")
async def get_projection(
    account_type: str,
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    if account_type == "user":
        return {"account_type": account_type, "account_id": account_id, "projection": {"balance": float(await LedgerProjectionService.get_user_balance(db, account_id))}}
    if account_type == "seller":
        projection = await LedgerProjectionService.get_seller_projection(db, account_id)
        return {"account_type": account_type, "account_id": account_id, "projection": {k: float(v) for k, v in projection.items()}}
    if account_type == "worker":
        projection = await LedgerProjectionService.get_worker_projection(db, account_id)
        return {"account_type": account_type, "account_id": account_id, "projection": {k: float(v) for k, v in projection.items()}}
    if account_type == "marketer":
        projection = await LedgerProjectionService.get_marketer_projection(db, account_id)
        return {"account_type": account_type, "account_id": account_id, "projection": {k: float(v) for k, v in projection.items()}}
    if account_type == "owner":
        projection = await LedgerProjectionService.get_owner_projection(db, account_id)
        return {"account_type": account_type, "account_id": account_id, "projection": {k: float(v) for k, v in projection.items()}}
    raise HTTPException(status_code=400, detail="Unsupported account_type")


@router.post("/reconciliation/run")
async def run_reconciliation(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    result = await LedgerReconciliationService.run_full_reconciliation(db, emit_alerts=False)
    return {
        "ok": result["ok"],
        "issue_count": result["issue_count"],
        "issues": result["issues"][:200],
    }
