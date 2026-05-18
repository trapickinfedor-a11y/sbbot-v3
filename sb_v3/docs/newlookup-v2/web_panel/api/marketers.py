"""API для маркетологов"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date, timedelt, timezone
from typing import Optional, List
from pydantic import BaseModel

from web_panel.database import get_db
from web_panel.auth import require_finance_access
from shared.database.models import Marketer, MarketerWithdrawal, MarketerStats, MarketerActivityLog, User, MirrorBot, Transaction
from shared.services.ledger_service import LedgerService
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.marketer_activity_log import log_marketer_activity
from shared.services.marketer_monitoring_service import (
    build_marketer_withdrawal_block_reason,
    evaluate_marketer_withdrawal_risk,
    notify_marketer_withdrawal_blocked,
)
from shared.services.nocodb_service import NocoDBService
from web_panel.services.audit_service import log_action

router = APIRouter(prefix="/api/marketers", tags=["marketers"])
logger = logging.getLogger(__name__)


class MarketerResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    display_name: Optional[str]
    promo_code: str
    reward_percent: float
    user_bonus_percent: float
    balance: float
    total_earned: float
    total_withdrawn: float
    is_active: bool
    referrals_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MarketerWithdrawalResponse(BaseModel):
    id: int
    marketer_id: int
    marketer_name: str
    amount: float
    requisites: Optional[str]
    status: str
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


def _safe_percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _group_marketer_series(stats: list[MarketerStats], group_by: str) -> dict:
    buckets: dict[str, dict] = {}
    for stat in stats:
        if group_by == "week":
            bucket_start = stat.date - timedelta(days=stat.date.weekday())
            key = bucket_start.isoformat()
            label = f"Week of {bucket_start.isoformat()}"
        elif group_by == "month":
            key = stat.date.strftime("%Y-%m")
            label = stat.date.strftime("%Y-%m")
        else:
            key = stat.date.isoformat()
            label = key

        bucket = buckets.setdefault(
            key,
            {
                "label": label,
                "registrations": 0,
                "first_topups": 0,
                "topup_amount": 0.0,
                "earned": 0.0,
            },
        )
        bucket["registrations"] += stat.registrations or 0
        bucket["first_topups"] += stat.first_topups or 0
        bucket["topup_amount"] += float(stat.topup_amount or 0)
        bucket["earned"] += float(stat.earned or 0)

    ordered = [buckets[key] for key in sorted(buckets.keys())]
    return {
        "labels": [item["label"] for item in ordered],
        "registrations": [item["registrations"] for item in ordered],
        "first_topups": [item["first_topups"] for item in ordered],
        "topup_amount": [round(item["topup_amount"], 2) for item in ordered],
        "earned": [round(item["earned"], 2) for item in ordered],
    }


async def _compute_marketer_churn(db: AsyncSession, marketer_id: int) -> dict:
    user_ids = list(
        await db.scalars(select(User.user_id).where(User.marketer_id == marketer_id))
    )
    if not user_ids:
        return {"paying_users": 0, "churned_users": 0, "churn_rate": 0.0}

    last_active_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    topup_rows = (
        await db.execute(
            select(
                Transaction.user_id,
                func.max(Transaction.created_at).label("last_topup_at"),
            )
            .where(
                Transaction.user_id.in_(user_ids),
                Transaction.type == "topup",
            )
            .group_by(Transaction.user_id)
        )
    ).all()

    paying_users = len(topup_rows)
    churned_users = sum(1 for row in topup_rows if row.last_topup_at and row.last_topup_at < last_active_cutoff)
    return {
        "paying_users": paying_users,
        "churned_users": churned_users,
        "churn_rate": _safe_percent(churned_users, paying_users),
    }


@router.get("", response_model=List[dict])
async def get_marketers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Список маркетологов"""
    result = await db.execute(select(Marketer).order_by(Marketer.created_at.desc()))
    marketers = result.scalars().all()
    items = []
    for m in marketers:
        refs = await db.execute(select(func.count(User.id)).where(User.marketer_id == m.id))
        items.append({
            "id": m.id,
            "telegram_id": m.telegram_id,
            "username": m.username,
            "display_name": m.display_name,
            "promo_code": m.promo_code,
            "reward_percent": float(m.reward_percent),
            "user_bonus_percent": float(m.user_bonus_percent),
            "balance": float(m.balance),
            "total_earned": float(m.total_earned),
            "total_withdrawn": float(m.total_withdrawn),
            "is_active": m.is_active,
            "referrals_count": refs.scalar() or 0,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return items


@router.get("/withdrawals")
async def get_withdrawals(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Заявки на вывод маркетологов"""
    query = select(MarketerWithdrawal).order_by(MarketerWithdrawal.created_at.desc())
    if status:
        query = query.where(MarketerWithdrawal.status == status)
    result = await db.execute(query)
    withdrawals = result.scalars().all()
    items = []
    for w in withdrawals:
        m_res = await db.execute(select(Marketer).where(Marketer.id == w.marketer_id))
        m = m_res.scalar_one_or_none()
        items.append({
            "id": w.id,
            "marketer_id": w.marketer_id,
            "marketer_name": (m.display_name or m.username or "?") if m else "?",
            "amount": float(w.amount),
            "requisites": w.requisites,
            "status": w.status,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "processed_at": w.processed_at.isoformat() if w.processed_at else None,
        })
    return {"withdrawals": items}


@router.post("/withdrawals/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Одобрить вывод"""
    result = await db.execute(select(MarketerWithdrawal).where(MarketerWithdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    m_res = await db.execute(select(Marketer).where(Marketer.id == w.marketer_id))
    m = m_res.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Marketer not found")
    projected_balance = float((await LedgerProjectionService.get_marketer_projection(db, m.id))["balance"])
    if not getattr(w, "funds_reserved", False) and projected_balance < float(w.amount):
        raise HTTPException(status_code=400, detail="Insufficient balance")
    suspicious_bots = await evaluate_marketer_withdrawal_risk(db, m.id)
    if suspicious_bots:
        reason = build_marketer_withdrawal_block_reason(suspicious_bots)
        w.status = "blocked"
        w.processed_at = datetime.now(timezone.utc)
        w.reject_reason = reason
        await log_marketer_activity(
            db,
            m.id,
            "withdrawal_blocked",
            amount=w.amount,
            details=reason,
            withdrawal_id=w.id,
        )
        await log_action(
            db,
            current_user.get("admin_id"),
            "marketer_withdrawal_block",
            "marketer_withdrawal",
            w.id,
            {
                "marketer_id": w.marketer_id,
                "amount": float(w.amount),
                "reason": reason,
                "actor_role": current_user.get("role"),
                "auto_blocked": True,
                "bots": suspicious_bots,
            },
            request.client.host if request.client else None,
        )
        if getattr(w, "funds_reserved", False):
            await LedgerService.release_marketer_withdrawal_reservation(
                db,
                marketer=m,
                amount=w.amount,
                withdrawal_id=w.id,
            )
        await db.commit()
        NocoDBService.log_event(
            event_type="payout_status_changed",
            actor_type="admin",
            actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
            target_type="marketer_withdrawal",
            target_id=w.id,
            status="blocked",
            payload={"marketer_id": w.marketer_id, "amount": float(w.amount), "reason": reason},
            timestamp=w.processed_at,
        )
        try:
            await notify_marketer_withdrawal_blocked(m, w, suspicious_bots)
        except Exception as exc:
            logger.warning("Failed to send marketer withdrawal block alert: %s", exc)
        raise HTTPException(status_code=400, detail=reason)
    if not getattr(w, "funds_reserved", False):
        if not await LedgerService.reserve_marketer_withdrawal(
            db,
            marketer=m,
            amount=w.amount,
            withdrawal_id=w.id,
        ):
            raise HTTPException(status_code=400, detail="Insufficient balance")
        w.funds_reserved = True
    await LedgerService.finalize_marketer_withdrawal(
        db,
        marketer=m,
        amount=w.amount,
        withdrawal_id=w.id,
    )
    w.status = "approved"
    w.processed_at = datetime.now(timezone.utc)
    processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    w.processed_by = processed_by
    await log_marketer_activity(
        db, m.id, "withdrawal_approved",
        amount=w.amount,
        details=f"Вывод одобрен админом",
        withdrawal_id=w.id,
        processed_by=processed_by
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "marketer_withdrawal_approve",
        "marketer_withdrawal",
        w.id,
        {
            "marketer_id": w.marketer_id,
            "amount": float(w.amount),
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="payout_status_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="marketer_withdrawal",
        target_id=w.id,
        status="approved",
        payload={"marketer_id": w.marketer_id, "amount": float(w.amount)},
        timestamp=w.processed_at,
    )
    return {"ok": True}


class RejectBody(BaseModel):
    reason: Optional[str] = None


@router.get("/{marketer_id}/analytics")
async def get_marketer_analytics(
    marketer_id: int,
    days: int = 30,
    group_by: str = "day",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Аналитика маркетолога: KPI и графики earnings."""
    if group_by not in {"day", "week", "month"}:
        raise HTTPException(status_code=400, detail="group_by must be one of: day, week, month")
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(MarketerStats)
        .where(and_(MarketerStats.marketer_id == marketer_id, MarketerStats.date >= since))
        .order_by(MarketerStats.date)
    )
    stats = result.scalars().all()
    grouped_series = _group_marketer_series(stats, group_by)
    registrations_total = sum(s.registrations or 0 for s in stats)
    first_topups_total = sum(s.first_topups or 0 for s in stats)
    topup_amount_total = round(sum(float(s.topup_amount or 0) for s in stats), 2)
    earned_total = round(sum(float(s.earned or 0) for s in stats), 2)
    churn = await _compute_marketer_churn(db, marketer_id)

    return {
        **grouped_series,
        "summary": {
            "period_days": days,
            "group_by": group_by,
            "registrations": registrations_total,
            "first_topups": first_topups_total,
            "topup_amount": topup_amount_total,
            "earned": earned_total,
            "conversion_rate": _safe_percent(first_topups_total, registrations_total),
            "arpu": round(topup_amount_total / registrations_total, 2) if registrations_total else 0.0,
            "churn_rate": churn["churn_rate"],
            "paying_users": churn["paying_users"],
            "churned_users": churn["churned_users"],
        },
    }


@router.get("/{marketer_id}/stats-by-bot")
async def get_marketer_stats_by_bot(
    marketer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Статистика маркетолога по каждому боту (рефералы и заработок)"""
    result = await db.execute(
        select(User.mirror_bot_id, func.count(User.id).label("refs"), func.sum(User.balance).label("total_balance"))
        .where(User.marketer_id == marketer_id)
        .group_by(User.mirror_bot_id)
    )
    rows = result.all()
    items = []
    for row in rows:
        bot_res = await db.execute(select(MirrorBot).where(MirrorBot.id == row.mirror_bot_id))
        bot = bot_res.scalar_one_or_none()
        items.append({
            "mirror_bot_id": row.mirror_bot_id,
            "bot_username": bot.bot_username if bot else None,
            "referrals_count": row.refs,
            "users_total_balance": float(row.total_balance or 0),
        })
    return {"bots": items}


@router.get("/{marketer_id}/activity-log")
async def get_marketer_activity_log(
    marketer_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Лог действий маркетолога"""
    result = await db.execute(
        select(MarketerActivityLog)
        .where(MarketerActivityLog.marketer_id == marketer_id)
        .order_by(MarketerActivityLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()
    return {
        "items": [
            {
                "id": l.id,
                "action": l.action,
                "amount": float(l.amount) if l.amount else None,
                "details": l.details,
                "withdrawal_id": l.withdrawal_id,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    }


@router.get("/withdrawals/full")
async def get_all_withdrawals_full(
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Полная история выводов с деталями для логов"""
    query = select(MarketerWithdrawal).order_by(MarketerWithdrawal.created_at.desc()).limit(limit)
    if status:
        query = query.where(MarketerWithdrawal.status == status)
    result = await db.execute(query)
    withdrawals = result.scalars().all()
    items = []
    for w in withdrawals:
        m_res = await db.execute(select(Marketer).where(Marketer.id == w.marketer_id))
        m = m_res.scalar_one_or_none()
        items.append({
            "id": w.id,
            "marketer_id": w.marketer_id,
            "marketer_name": (m.display_name or m.username or "?") if m else "?",
            "promo_code": m.promo_code if m else "?",
            "amount": float(w.amount),
            "requisites": w.requisites,
            "status": w.status,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "processed_at": w.processed_at.isoformat() if w.processed_at else None,
            "processed_by": w.processed_by,
            "reject_reason": w.reject_reason,
        })
    return {"withdrawals": items}


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: int,
    request: Request,
    body: RejectBody = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Отклонить вывод"""
    result = await db.execute(select(MarketerWithdrawal).where(MarketerWithdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    w.status = "rejected"
    w.processed_at = datetime.now(timezone.utc)
    processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    w.processed_by = processed_by
    w.reject_reason = body.reason if body else None
    m_res = await db.execute(select(Marketer).where(Marketer.id == w.marketer_id))
    m = m_res.scalar_one_or_none()
    if m:
        if getattr(w, "funds_reserved", False):
            await LedgerService.release_marketer_withdrawal_reservation(
                db,
                marketer=m,
                amount=w.amount,
                withdrawal_id=w.id,
            )
        await log_marketer_activity(
            db, m.id, "withdrawal_rejected",
            amount=w.amount,
            details=w.reject_reason or "Отклонено",
            withdrawal_id=w.id,
            processed_by=processed_by
        )
    await log_action(
        db,
        current_user.get("admin_id"),
        "marketer_withdrawal_reject",
        "marketer_withdrawal",
        w.id,
        {
            "marketer_id": w.marketer_id,
            "amount": float(w.amount),
            "reason": body.reason if body else None,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="payout_status_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="marketer_withdrawal",
        target_id=w.id,
        status="rejected",
        payload={"marketer_id": w.marketer_id, "amount": float(w.amount), "reason": w.reject_reason},
        timestamp=w.processed_at,
    )
    return {"ok": True}
