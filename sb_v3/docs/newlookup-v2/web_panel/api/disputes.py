"""
Unified Disputes API — единый роутер для управления спорами.
Агрегирует данные из SellerOrderDispute + SellerOrder.
"""

import logging
from datetime import datetim, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from web_panel.auth import require_finance_access, get_current_user
from web_panel.database import get_db
from web_panel.services.audit_service import log_action
from shared.database.models import (
    SellerOrderDispute,
    SellerOrder,
    Seller,
    SellerBank,
    SellerCCItem,
    User,
)
from shared.services.seller_dispute_service import SellerDisputeService

router = APIRouter(prefix="/api/disputes", tags=["disputes"])
logger = logging.getLogger(__name__)


class DisputeResponse(BaseModel):
    id: int
    order_id: int
    status: str
    reason: Optional[str] = None
    description: Optional[str] = None
    opened_by: Optional[int] = None
    buyer_username: Optional[str] = None
    seller_id: Optional[int] = None
    seller_name: Optional[str] = None
    seller_total_disputes: Optional[int] = None
    seller_open_disputes: Optional[int] = None
    order_status: Optional[str] = None
    order_amount: Optional[float] = None
    assigned_admin_id: Optional[int] = None
    appeal_status: Optional[str] = None
    appeal_reason: Optional[str] = None
    resolution_note: Optional[str] = None
    resolved_by: Optional[int] = None
    seller_response_due_at: Optional[datetime] = None
    seller_responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class DisputeListResponse(BaseModel):
    items: List[DisputeResponse]
    total: int
    limit: int
    offset: int


class ResolveRequest(BaseModel):
    resolution: str  # "buyer" | "seller"
    note: Optional[str] = None


class AssignRequest(BaseModel):
    admin_id: int


@router.get("", response_model=DisputeListResponse)
async def list_disputes(
    status: Optional[str] = Query(None, description="open|resolved_buyer|resolved_seller|cancelled"),
    seller_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Список всех споров с фильтрами и пагинацией."""
    base = select(SellerOrderDispute)
    if status:
        base = base.where(SellerOrderDispute.status == status)
    if seller_id:
        order_ids_q = select(SellerOrder.id).where(SellerOrder.seller_id == seller_id)
        base = base.where(SellerOrderDispute.order_id.in_(order_ids_q))

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    rows = (await db.execute(
        base.order_by(desc(SellerOrderDispute.created_at)).limit(limit).offset(offset)
    )).scalars().all()

    order_ids = [d.order_id for d in rows]
    orders_map: dict = {}
    sellers_map: dict = {}
    buyers_map: dict = {}

    if order_ids:
        orders_result = await db.execute(
            select(SellerOrder).where(SellerOrder.id.in_(order_ids))
        )
        for o in orders_result.scalars().all():
            orders_map[o.id] = o

        seller_ids = list({o.seller_id for o in orders_map.values() if o.seller_id})
        if seller_ids:
            sellers_result = await db.execute(select(Seller).where(Seller.id.in_(seller_ids)))
            for s in sellers_result.scalars().all():
                sellers_map[s.id] = s
            
            # Calculate dispute statistics per seller
            seller_dispute_stats = {}
            for seller_id in seller_ids:
                # Total disputes for this seller
                total_disputes_q = select(func.count(SellerOrderDispute.id)).select_from(
                    SellerOrderDispute
                ).join(
                    SellerOrder, SellerOrderDispute.order_id == SellerOrder.id
                ).where(
                    SellerOrder.seller_id == seller_id
                )
                total_disputes = await db.scalar(total_disputes_q) or 0
                
                # Open disputes for this seller
                open_disputes_q = select(func.count(SellerOrderDispute.id)).select_from(
                    SellerOrderDispute
                ).join(
                    SellerOrder, SellerOrderDispute.order_id == SellerOrder.id
                ).where(
                    SellerOrder.seller_id == seller_id,
                    SellerOrderDispute.status.in_(['open', 'in_moderation', 'waiting_for_seller_response', 'waiting_for_buyer_response', 'appealed'])
                )
                open_disputes = await db.scalar(open_disputes_q) or 0
                
                seller_dispute_stats[seller_id] = {
                    'total': total_disputes,
                    'open': open_disputes
                }
        else:
            seller_dispute_stats = {}

        buyer_ids = list({o.buyer_user_id for o in orders_map.values() if getattr(o, "buyer_user_id", None)})
        if buyer_ids:
            buyers_result = await db.execute(select(User).where(User.user_id.in_(buyer_ids)))
            for u in buyers_result.scalars().all():
                buyers_map[u.user_id] = u

    items = []
    for d in rows:
        order = orders_map.get(d.order_id)
        seller = sellers_map.get(order.seller_id) if order else None
        buyer = buyers_map.get(getattr(order, "buyer_user_id", None)) if order else None
        
        # Get seller dispute stats
        seller_stats = seller_dispute_stats.get(order.seller_id) if order and order.seller_id else None
        
        items.append(DisputeResponse(
            id=d.id,
            order_id=d.order_id,
            status=d.status,
            reason=d.reason,
            description=d.description,
            opened_by=d.opened_by,
            buyer_username=buyer.username if buyer else None,
            seller_id=order.seller_id if order else None,
            seller_name=(seller.display_name or seller.username) if seller else None,
            seller_total_disputes=seller_stats['total'] if seller_stats else None,
            seller_open_disputes=seller_stats['open'] if seller_stats else None,
            order_status=order.status if order else None,
            order_amount=float(order.price_for_buyer) if order and order.price_for_buyer else None,
            assigned_admin_id=d.assigned_admin_id,
            appeal_status=d.appeal_status,
            appeal_reason=d.appeal_reason,
            resolution_note=d.resolution_note,
            resolved_by=d.resolved_by,
            seller_response_due_at=d.seller_response_due_at,
            seller_responded_at=d.seller_responded_at,
            created_at=d.created_at,
            resolved_at=d.resolved_at,
        ))

    return DisputeListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats")
async def dispute_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Агрегированная статистика по спорам."""
    open_count = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status == "open")
    ) or 0
    overdue_count = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(and_(
            SellerOrderDispute.status == "open",
            SellerOrderDispute.seller_response_due_at < datetime.now(timezone.utc),
            SellerOrderDispute.seller_responded_at.is_(None),
        ))
    ) or 0
    appeals_count = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(
            SellerOrderDispute.appeal_status == "requested"
        )
    ) or 0
    resolved_buyer = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status == "resolved_buyer")
    ) or 0
    resolved_seller = await db.scalar(
        select(func.count(SellerOrderDispute.id)).where(SellerOrderDispute.status == "resolved_seller")
    ) or 0

    return {
        "open": open_count,
        "overdue": overdue_count,
        "appeals_pending": appeals_count,
        "resolved_buyer": resolved_buyer,
        "resolved_seller": resolved_seller,
        "total": open_count + resolved_buyer + resolved_seller,
    }


@router.get("/{dispute_id}")
async def get_dispute(
    dispute_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Детальная информация о споре."""
    dispute = await db.scalar(select(SellerOrderDispute).where(SellerOrderDispute.id == dispute_id))
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    order = await db.scalar(select(SellerOrder).where(SellerOrder.id == dispute.order_id))
    seller = await db.scalar(select(Seller).where(Seller.id == order.seller_id)) if order else None

    return {
        "dispute": {
            "id": dispute.id,
            "order_id": dispute.order_id,
            "status": dispute.status,
            "reason": dispute.reason,
            "description": dispute.description,
            "opened_by": dispute.opened_by,
            "buyer_evidence": dispute.buyer_evidence,
            "seller_evidence": dispute.seller_evidence,
            "assigned_admin_id": dispute.assigned_admin_id,
            "appeal_status": dispute.appeal_status,
            "appeal_reason": dispute.appeal_reason,
            "resolution_note": dispute.resolution_note,
            "resolved_by": dispute.resolved_by,
            "seller_response_due_at": dispute.seller_response_due_at,
            "seller_responded_at": dispute.seller_responded_at,
            "created_at": dispute.created_at,
            "resolved_at": dispute.resolved_at,
        },
        "order": {
            "id": order.id,
            "seller_id": order.seller_id,
            "status": order.status,
            "price_for_buyer": float(order.price_for_buyer) if order.price_for_buyer else 0,
            "price_for_seller": float(order.price_for_seller) if order.price_for_seller else 0,
            "quantity": order.quantity,
            "created_at": order.created_at,
        } if order else None,
        "seller": {
            "id": seller.id,
            "username": seller.username,
            "display_name": seller.display_name,
            "seller_score": seller.seller_score,
        } if seller else None,
    }


@router.post("/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: int,
    data: ResolveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Разрешить спор в пользу покупателя или продавца."""
    dispute = await db.scalar(select(SellerOrderDispute).where(SellerOrderDispute.id == dispute_id))
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.status != "open":
        raise HTTPException(status_code=400, detail="Dispute is not open")

    order = await db.scalar(select(SellerOrder).where(SellerOrder.id == dispute.order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    admin_id = current_user.get("admin_id")

    if data.resolution == "buyer":
        await SellerDisputeService.resolve_for_buyer(db, dispute, order, admin_id, data.note)
    elif data.resolution == "seller":
        await SellerDisputeService.resolve_for_seller(db, dispute, order, admin_id, data.note)
    else:
        raise HTTPException(status_code=400, detail="resolution must be 'buyer' or 'seller'")

    await db.commit()
    ip = request.client.host if request.client else None
    await log_action(db, admin_id, f"dispute_resolve_{data.resolution}", "dispute", dispute_id,
                     {"order_id": dispute.order_id, "note": data.note}, ip)
    await db.commit()

    return {"ok": True, "status": dispute.status}


@router.post("/{dispute_id}/assign")
async def assign_dispute(
    dispute_id: int,
    data: AssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Назначить спор на администратора."""
    dispute = await db.scalar(select(SellerOrderDispute).where(SellerOrderDispute.id == dispute_id))
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    dispute.assigned_admin_id = data.admin_id
    await db.commit()

    ip = request.client.host if request.client else None
    await log_action(db, current_user.get("admin_id"), "dispute_assign", "dispute", dispute_id,
                     {"assigned_to": data.admin_id}, ip)
    await db.commit()
    return {"ok": True}


@router.post("/{dispute_id}/appeal/review")
async def review_appeal(
    dispute_id: int,
    status: str = Query(..., description="accepted|rejected"),
    note: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access()),
):
    """Рассмотреть апелляцию."""
    admin_id = current_user.get("admin_id")
    await SellerDisputeService.review_appeal(db, dispute_id, status, admin_id, note)
    await db.commit()

    ip = request.client.host if request and request.client else None
    await log_action(db, admin_id, f"dispute_appeal_{status}", "dispute", dispute_id,
                     {"note": note}, ip)
    await db.commit()
    return {"ok": True}
