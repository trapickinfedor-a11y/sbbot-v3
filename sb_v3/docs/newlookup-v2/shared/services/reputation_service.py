"""Reputation Service — расчёт Seller Score и Buyer Score (Trust Score)"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import Seller, User


# ── Seller Score ──────────────────────────────────────────────────────────

async def recalculate_seller_score(session: AsyncSession, seller_id: int) -> float:
    """
    Seller Score = avg_feedback * 0.6 + dispute_success * 0.2 + verification_bonus * 0.1 + tenure_bonus * 0.1
    Range: 1.0 – 5.0
    """
    seller_r = await session.execute(select(Seller).where(Seller.id == seller_id))
    seller = seller_r.scalar_one_or_none()
    if not seller:
        return 5.0

    # Feedback score from likes/dislikes
    total_feedback = seller.likes_count + seller.dislikes_count
    if total_feedback > 0:
        avg_feedback = seller.likes_count / total_feedback  # 0..1
    else:
        avg_feedback = 0.8  # neutral for new sellers

    # Dispute success rate — disputes resolved in seller's favour vs total
    try:
        from shared.database.models import SellerOrderDispute
        total_disp_r = await session.execute(
            select(func.count(SellerOrderDispute.id)).where(
                SellerOrderDispute.seller_id == seller_id
            )
        )
        seller_won_r = await session.execute(
            select(func.count(SellerOrderDispute.id)).where(
                and_(
                    SellerOrderDispute.seller_id == seller_id,
                    SellerOrderDispute.resolution.in_(["resolved_seller", "cancelled"])
                )
            )
        )
        total_disp = total_disp_r.scalar() or 0
        seller_won = seller_won_r.scalar() or 0
        dispute_success = (seller_won / total_disp) if total_disp > 0 else 0.9
    except Exception:
        dispute_success = 0.9

    # Tenure bonus: 0.5 if >180 days on platform
    days_on = (datetime.now(timezone.utc) - seller.created_at).days if seller.created_at else 0
    tenure_bonus = min(0.5, days_on / 180 * 0.5)

    # Verification bonus: placeholder (0 or 0.5)
    verification_bonus = 0.0  # could be based on a 'is_verified' field

    # Raw score calculation
    raw = avg_feedback * 0.6 + dispute_success * 0.2 + verification_bonus * 0.1 + min(tenure_bonus, 0.5) * 0.1
    score = round(1.0 + raw * 4.0, 2)
    score = max(1.0, min(5.0, score))

    seller.seller_score = score
    seller.score_updated_at = datetime.now(timezone.utc)
    await session.commit()

    # Apply dynamic platform fee based on score
    _apply_platform_fee(seller, score)
    await session.commit()

    return score


def _apply_platform_fee(seller: Seller, score: float):
    """
    Top Seller (≥4.8): markup_percent = 12
    Low Rating (<3.5): markup_percent = 18
    Standard: markup_percent = 15
    """
    if score >= 4.8:
        seller.markup_percent = 12.0
    elif score < 3.5:
        seller.markup_percent = 18.0
    else:
        seller.markup_percent = 15.0


def get_seller_badge(score: float) -> str:
    """Returns emoji badge for seller based on score"""
    if score >= 4.8:
        return "🏆 Top Seller"
    elif score < 3.5:
        return "⚠️ Low Rating"
    return ""


# ── Buyer Score (Trust Score) ──────────────────────────────────────────────

async def recalculate_buyer_trust_score(session: AsyncSession, user_id: int) -> int:
    """
    Buyer trust_score: starts at 100, modified by behavior.
    - More purchases: +
    - Reviews left: +
    - Disputes opened % too high: -
    - Disputes lost: --
    """
    user_r = await session.execute(select(User).where(User.id == user_id))
    user = user_r.scalar_one_or_none()
    if not user:
        return 100

    # Base score
    score = 100

    # Bonus for purchases
    try:
        from shared.database.models import SellerOrder
        purchases_r = await session.execute(
            select(func.count(SellerOrder.id)).where(
                and_(SellerOrder.buyer_user_id == user.user_id, SellerOrder.status == "completed")
            )
        )
        purchases = purchases_r.scalar() or 0
        score += min(20, purchases // 5)  # up to +20 for 100 purchases
    except Exception:
        pass

    # Penalty for high dispute rate
    try:
        from shared.database.models import SellerOrderDispute
        disputes_r = await session.execute(
            select(func.count(SellerOrderDispute.id)).where(
                SellerOrderDispute.buyer_user_id == user.user_id
            )
        )
        total_disputes = disputes_r.scalar() or 0
        if purchases > 0 and total_disputes > 0:
            dispute_rate = total_disputes / purchases
            if dispute_rate > 0.2:  # >20% dispute rate
                score -= int(dispute_rate * 50)
    except Exception:
        pass

    score = max(0, min(200, score))
    user.trust_score = score
    await session.commit()
    return score


async def recalculate_all_seller_scores(session: AsyncSession) -> int:
    """Пересчитывает Seller Score для всех активных продавцов"""
    sellers_r = await session.execute(
        select(Seller.id).where(Seller.is_active == True)
    )
    seller_ids = [row[0] for row in sellers_r.fetchall()]
    count = 0
    for sid in seller_ids:
        try:
            await recalculate_seller_score(session, sid)
            count += 1
        except Exception:
            pass
    return count
