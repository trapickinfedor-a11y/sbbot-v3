"""Admin API — referral management: links, rewards moderation, withdrawals, settings, stats."""
from __future__ import annotations

import json
from datetime import datetim, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import (
    Referral,
    ReferralReward,
    ReferralSettings,
    ReferralWithdrawal,
    User,
)
from web_panel.auth import require_page_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter(prefix="/api/admin-referrals", tags=["admin-referrals"])


# ─── helpers ─────────────────────────────────────────────────────────────────


def _dt(d: Optional[datetime]) -> Optional[str]:
    return d.isoformat() if d else None


async def _get_or_create_settings(db: AsyncSession) -> ReferralSettings:
    row = await db.scalar(select(ReferralSettings).where(ReferralSettings.id == 1))
    if not row:
        row = ReferralSettings(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


# ═══════════════════════════════════════════════════════════════════════════════
# Referral Links Table
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/links")
async def list_referral_links(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("referrals")),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    referrer_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """List referral relationships with filters."""
    q = select(Referral)
    if referrer_id:
        q = q.where(Referral.referrer_id == referrer_id)
    if date_from:
        try:
            q = q.where(Referral.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.where(Referral.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    total_q = select(func.count()).select_from(q.subquery())
    total = await db.scalar(total_q) or 0

    q = q.order_by(Referral.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    # Collect all user telegram_ids to fetch usernames in bulk
    tg_ids = set()
    for r in rows:
        tg_ids.add(r.referrer_id)
        tg_ids.add(r.referred_id)

    username_map: dict = {}
    if tg_ids:
        users = (await db.execute(
            select(User.telegram_id, User.username).where(User.telegram_id.in_(list(tg_ids)))
        )).all()
        username_map = {u.telegram_id: u.username for u in users}

    items = []
    for r in rows:
        items.append(
            {
                "id": r.id,
                "referrer_id": r.referrer_id,
                "referrer_username": username_map.get(r.referrer_id),
                "referred_id": r.referred_id,
                "referred_username": username_map.get(r.referred_id),
                "earned_total": 0.0,
                "created_at": _dt(r.created_at),
            }
        )
    return {"total": total, "items": items}


# ═══════════════════════════════════════════════════════════════════════════════
# Rewards Moderation
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/rewards")
async def list_rewards(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("referrals")),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    referrer_id: Optional[int] = Query(None),
):
    """List referral rewards with optional status filter."""
    q = select(ReferralReward)
    if status:
        q = q.where(ReferralReward.status == status)
    if referrer_id:
        q = q.where(ReferralReward.referrer_id == referrer_id)

    total = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    q = q.order_by(ReferralReward.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    items = [
        {
            "id": r.id,
            "referrer_id": r.referrer_id,
            "referred_user_id": r.referred_user_id,
            "amount_display": float(r.amount_display),
            "amount_real": float(r.amount_real),
            "level": r.level,
            "source": r.source,
            "status": r.status,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": _dt(r.reviewed_at),
            "reject_reason": r.reject_reason,
            "created_at": _dt(r.created_at),
        }
        for r in rows
    ]
    return {"total": total, "items": items}


class ReviewRewardPayload(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: Optional[str] = None


@router.post("/rewards/{reward_id}/review")
async def review_reward(
    reward_id: int,
    payload: ReviewRewardPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("referrals")),
):
    """Approve or reject a referral reward."""
    reward = await db.scalar(select(ReferralReward).where(ReferralReward.id == reward_id))
    if not reward:
        raise HTTPException(404, "Reward not found")
    if reward.status not in ("pending_moderation",):
        raise HTTPException(400, f"Reward is already {reward.status}")

    reward.status = "approved" if payload.action == "approve" else "rejected"
    reward.reviewed_by = current_user.get("admin_id")
    reward.reviewed_at = datetime.now(timezone.utc)
    if payload.action == "reject":
        reward.reject_reason = payload.comment
    await db.commit()

    await log_action(
        db,
        current_user.get("admin_id"),
        f"referral_reward_{payload.action}",
        "referral_rewards",
        reward_id,
        {"comment": payload.comment},
        request.client.host if request.client else None,
    )
    return {"ok": True, "status": reward.status}


# ═══════════════════════════════════════════════════════════════════════════════
# Withdrawal Moderation
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/withdrawals")
async def list_withdrawals(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("referrals")),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
):
    q = select(ReferralWithdrawal)
    if status:
        q = q.where(ReferralWithdrawal.status == status)

    total = await db.scalar(select(func.count()).select_from(q.subquery())) or 0
    q = q.order_by(ReferralWithdrawal.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    items = [
        {
            "id": r.id,
            "referrer_id": r.referrer_id,
            "amount": float(r.amount),
            "requisites": r.requisites,
            "status": r.status,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": _dt(r.reviewed_at),
            "reject_reason": r.reject_reason,
            "created_at": _dt(r.created_at),
        }
        for r in rows
    ]
    return {"total": total, "items": items}


class ReviewWithdrawalPayload(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: Optional[str] = None


@router.post("/withdrawals/{withdrawal_id}/review")
async def review_withdrawal(
    withdrawal_id: int,
    payload: ReviewWithdrawalPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("referrals")),
):
    """Approve or reject a referral withdrawal."""
    row = await db.scalar(select(ReferralWithdrawal).where(ReferralWithdrawal.id == withdrawal_id))
    if not row:
        raise HTTPException(404, "Withdrawal not found")
    if row.status != "pending_moderation":
        raise HTTPException(400, f"Withdrawal is already {row.status}")

    row.status = "approved" if payload.action == "approve" else "rejected"
    row.reviewed_by = current_user.get("admin_id")
    row.reviewed_at = datetime.now(timezone.utc)
    if payload.action == "reject":
        row.reject_reason = payload.comment
    await db.commit()

    await log_action(
        db,
        current_user.get("admin_id"),
        f"referral_withdrawal_{payload.action}",
        "referral_withdrawals",
        withdrawal_id,
        {"amount": float(row.amount), "comment": payload.comment},
        request.client.host if request.client else None,
    )
    return {"ok": True, "status": row.status}


# ═══════════════════════════════════════════════════════════════════════════════
# Settings (levels, anti-fraud, withdrawal limits)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/settings")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("referrals")),
):
    s = await _get_or_create_settings(db)
    return {
        "level1_display_pct": s.level1_display_pct,
        "level1_real_pct": s.level1_real_pct,
        "level2_display_pct": s.level2_display_pct,
        "level2_real_pct": s.level2_real_pct,
        "level3_display_pct": s.level3_display_pct,
        "level3_real_pct": s.level3_real_pct,
        "level4_display_pct": s.level4_display_pct,
        "level4_real_pct": s.level4_real_pct,
        "max_daily_referrals": s.max_daily_referrals,
        "cooldown_hours": s.cooldown_hours,
        "min_purchase_usd": s.min_purchase_usd,
        "min_withdrawal_usd": s.min_withdrawal_usd,
        "is_active": s.is_active,
        "updated_at": _dt(s.updated_at),
    }


class ReferralSettingsPayload(BaseModel):
    level1_display_pct: float = Field(ge=0, le=100)
    level1_real_pct: float = Field(ge=0, le=100)
    level2_display_pct: float = Field(ge=0, le=100)
    level2_real_pct: float = Field(ge=0, le=100)
    level3_display_pct: float = Field(ge=0, le=100)
    level3_real_pct: float = Field(ge=0, le=100)
    level4_display_pct: float = Field(ge=0, le=100)
    level4_real_pct: float = Field(ge=0, le=100)
    max_daily_referrals: int = Field(ge=0, le=10000)
    cooldown_hours: int = Field(ge=0, le=8760)
    min_purchase_usd: float = Field(ge=0)
    min_withdrawal_usd: float = Field(ge=0)
    is_active: bool


@router.put("/settings")
async def update_settings(
    payload: ReferralSettingsPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("referrals")),
):
    s = await _get_or_create_settings(db)
    for field, value in payload.dict().items():
        setattr(s, field, value)
    await db.commit()

    await log_action(
        db,
        current_user.get("admin_id"),
        "referral_settings_update",
        "referral_settings",
        1,
        payload.dict(),
        request.client.host if request.client else None,
    )
    return {"ok": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Statistics
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_page_access("referrals")),
):
    """Top referrers, conversion stats, totals."""
    total_links = await db.scalar(select(func.count(Referral.id))) or 0
    total_rewards = await db.scalar(select(func.count(ReferralReward.id))) or 0
    total_approved = (
        await db.scalar(
            select(func.count(ReferralReward.id)).where(ReferralReward.status == "approved")
        )
        or 0
    )
    total_pending = (
        await db.scalar(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.status == "pending_moderation"
            )
        )
        or 0
    )
    total_paid_amount = (
        await db.scalar(
            select(func.sum(ReferralReward.amount_real)).where(
                ReferralReward.status.in_(["approved", "paid"])
            )
        )
        or Decimal("0")
    )

    # Top 10 referrers by number of referrals
    top_referrers_q = (
        select(Referral.referrer_id, func.count(Referral.id).label("cnt"))
        .group_by(Referral.referrer_id)
        .order_by(func.count(Referral.id).desc())
        .limit(10)
    )
    top_rows = (await db.execute(top_referrers_q)).all()

    top_referrers = []
    for referrer_id, cnt in top_rows:
        user = await db.scalar(select(User).where(User.user_id == referrer_id))
        earned = (
            await db.scalar(
                select(func.sum(ReferralReward.amount_real)).where(
                    ReferralReward.referrer_id == referrer_id,
                    ReferralReward.status.in_(["approved", "paid"]),
                )
            )
            or Decimal("0")
        )
        top_referrers.append(
            {
                "referrer_id": referrer_id,
                "username": user.username if user else str(referrer_id),
                "referrals_count": cnt,
                "earned": float(earned),
            }
        )

    conversion_rate = round(total_approved / total_rewards * 100, 1) if total_rewards > 0 else 0.0

    return {
        "total_links": total_links,
        "total_rewards": total_rewards,
        "total_approved": total_approved,
        "total_pending": total_pending,
        "total_paid_amount": float(total_paid_amount),
        "conversion_rate": conversion_rate,
        "top_referrers": top_referrers,
    }
