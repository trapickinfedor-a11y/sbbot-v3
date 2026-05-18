"""
Unified Withdrawals API — единый роутер для всех типов выводов.
Агрегирует: SellerWithdrawal, WorkerWithdrawal, MarketerWithdrawal, BotOwnerWithdrawal.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, desc, union_all, literal_column, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import require_finance_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action
from shared.database.models import (
    SellerWithdrawal,
    WorkerWithdrawal,
    MarketerWithdrawal,
    BotOwnerWithdrawal,
    Seller,
    Worker,
    Marketer,
)

router = APIRouter(prefix="/api/withdrawals", tags=["withdrawals"])
logger = logging.getLogger(__name__)


class WithdrawalItem(BaseModel):
    id: int
    source: str  # seller | worker | marketer | bot_owner
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    amount: float
    requisites: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    funds_reserved: bool = False
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    processed_by: Optional[int] = None


class WithdrawalListResponse(BaseModel):
    items: List[WithdrawalItem]
    total: int
    limit: int
    offset: int


class WithdrawalActionRequest(BaseModel):
    reason: Optional[str] = None


@router.get("", response_model=WithdrawalListResponse)
async def list_withdrawals(
    source: Optional[str] = Query(None, description="seller|worker|marketer|bot_owner"),
    status: Optional[str] = Query(None, description="pending|approved|rejected"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Единый список всех выводов с фильтрами."""
    items: List[WithdrawalItem] = []
    total = 0

    sources = [source] if source else ["seller", "worker", "marketer", "bot_owner"]

    # Собираем все выводы из нужных таблиц
    all_rows: list[tuple] = []

    for src in sources:
        model, entity_id_col, entity_name_func = _get_withdrawal_config(src)
        if not model:
            continue

        q = select(model)
        if status:
            q = q.where(model.status == status)

        count = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
        total += count

        rows = (await db.execute(
            q.order_by(desc(model.created_at)).limit(limit).offset(offset)
        )).scalars().all()

        entity_ids = [entity_id_col(r) for r in rows if entity_id_col(r)]
        names_map = await entity_name_func(db, entity_ids) if entity_ids else {}

        for r in rows:
            eid = entity_id_col(r)
            all_rows.append((
                r.created_at or datetime.min,
                WithdrawalItem(
                    id=r.id,
                    source=src,
                    entity_id=eid,
                    entity_name=names_map.get(eid),
                    amount=float(r.amount) if r.amount else 0,
                    requisites=r.requisites,
                    status=r.status,
                    reject_reason=r.reject_reason,
                    funds_reserved=bool(getattr(r, "funds_reserved", False)),
                    created_at=r.created_at,
                    processed_at=r.processed_at,
                    processed_by=r.processed_by,
                ),
            ))

    all_rows.sort(key=lambda x: x[0], reverse=True)
    page = all_rows[offset:offset + limit] if source is None else [(dt, item) for dt, item in all_rows]
    items = [item for _, item in (all_rows[:limit] if not source else page)]

    return WithdrawalListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats")
async def withdrawal_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Агрегированная статистика по всем выводам."""
    result = {}
    for src, model in [
        ("seller", SellerWithdrawal),
        ("worker", WorkerWithdrawal),
        ("marketer", MarketerWithdrawal),
        ("bot_owner", BotOwnerWithdrawal),
    ]:
        pending = await db.scalar(
            select(func.count(model.id)).where(model.status == "pending")
        ) or 0
        pending_amount = float(await db.scalar(
            select(func.coalesce(func.sum(model.amount), 0)).where(model.status == "pending")
        ) or 0)
        approved = await db.scalar(
            select(func.count(model.id)).where(model.status == "approved")
        ) or 0
        approved_amount = float(await db.scalar(
            select(func.coalesce(func.sum(model.amount), 0)).where(model.status == "approved")
        ) or 0)
        result[src] = {
            "pending_count": pending,
            "pending_amount": pending_amount,
            "approved_count": approved,
            "approved_amount": approved_amount,
        }

    result["total_pending"] = sum(v["pending_count"] for v in result.values() if isinstance(v, dict))
    result["total_pending_amount"] = sum(v["pending_amount"] for v in result.values() if isinstance(v, dict))
    return result


@router.post("/{source}/{withdrawal_id}/approve")
async def approve_withdrawal(
    source: str,
    withdrawal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Одобрить вывод."""
    model, _, _ = _get_withdrawal_config(source)
    if not model:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    w = await db.scalar(select(model).where(model.id == withdrawal_id))
    if not w:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail=f"Withdrawal status is '{w.status}', expected 'pending'")

    w.status = "approved"
    w.processed_at = datetime.now(timezone.utc)
    w.processed_by = current_user.get("admin_id")
    await db.commit()

    ip = request.client.host if request.client else None
    await log_action(db, current_user.get("admin_id"), "withdrawal_approve",
                     f"{source}_withdrawal", withdrawal_id,
                     {"amount": float(w.amount)}, ip)
    await db.commit()
    return {"ok": True, "status": "approved"}


@router.post("/{source}/{withdrawal_id}/reject")
async def reject_withdrawal(
    source: str,
    withdrawal_id: int,
    data: WithdrawalActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Отклонить вывод."""
    model, _, _ = _get_withdrawal_config(source)
    if not model:
        raise HTTPException(status_code=400, detail=f"Unknown source: {source}")

    w = await db.scalar(select(model).where(model.id == withdrawal_id))
    if not w:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail=f"Withdrawal status is '{w.status}', expected 'pending'")

    w.status = "rejected"
    w.reject_reason = data.reason
    w.processed_at = datetime.now(timezone.utc)
    w.processed_by = current_user.get("admin_id")
    await db.commit()

    ip = request.client.host if request.client else None
    await log_action(db, current_user.get("admin_id"), "withdrawal_reject",
                     f"{source}_withdrawal", withdrawal_id,
                     {"amount": float(w.amount), "reason": data.reason}, ip)
    await db.commit()
    return {"ok": True, "status": "rejected"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_withdrawal_config(source: str):
    """Возвращает (Model, entity_id_getter, names_loader) для источника."""
    configs = {
        "seller": (SellerWithdrawal, lambda r: r.seller_id, _load_seller_names),
        "worker": (WorkerWithdrawal, lambda r: r.worker_id, _load_worker_names),
        "marketer": (MarketerWithdrawal, lambda r: r.marketer_id, _load_marketer_names),
        "bot_owner": (BotOwnerWithdrawal, lambda r: r.owner_user_id, _load_bot_owner_names),
    }
    return configs.get(source, (None, None, None))


async def _load_seller_names(db: AsyncSession, ids: list) -> dict:
    rows = (await db.execute(select(Seller.id, Seller.display_name, Seller.username).where(Seller.id.in_(ids)))).all()
    return {r[0]: r[1] or r[2] or f"Seller #{r[0]}" for r in rows}


async def _load_worker_names(db: AsyncSession, ids: list) -> dict:
    rows = (await db.execute(select(Worker.id, Worker.username, Worker.telegram_id).where(Worker.id.in_(ids)))).all()
    return {r[0]: r[1] or f"Worker #{r[2]}" for r in rows}


async def _load_marketer_names(db: AsyncSession, ids: list) -> dict:
    rows = (await db.execute(select(Marketer.id, Marketer.display_name, Marketer.username).where(Marketer.id.in_(ids)))).all()
    return {r[0]: r[1] or r[2] or f"Marketer #{r[0]}" for r in rows}


async def _load_bot_owner_names(db: AsyncSession, ids: list) -> dict:
    return {uid: f"Owner #{uid}" for uid in ids}
