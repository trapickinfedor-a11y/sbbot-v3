"""
API endpoints для управления селлерами
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetim, timezone
from decimal import Decimal

from web_panel.database import get_db
from web_panel.auth import (
    can_view_finances,
    require_admin_management_access,
    require_seller_moderation_access,
    require_seller_read_access,
)
from shared.database.models import Seller, SellerBank, SellerOrder
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.seller_deposit_service import SellerDepositService
from web_panel.services.audit_service import log_action

router = APIRouter(prefix="/api/sellers", tags=["sellers"])


# ========== Pydantic Models ==========

class SellerResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    display_name: Optional[str]
    seller_type: str
    access_status: str
    is_approved: bool
    is_active: bool
    markup_percent: float
    total_orders: int
    total_earned: Optional[Decimal] = None
    security_deposit_balance: Optional[Decimal] = None
    security_deposit_status: str = "unpaid"
    security_deposit_categories: List[str] = []
    ban_reason: Optional[str] = None
    is_banned_for_leak: bool = False
    deposit_balance: Optional[Decimal] = None
    pending_balance: Optional[Decimal] = None
    withdrawable_balance: Optional[Decimal] = None
    banks_count: int = 0
    in_stock_count: int = 0
    active_orders: int = 0
    created_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True


class SellerUpdate(BaseModel):
    seller_type: Optional[str] = None
    is_approved: Optional[bool] = None
    is_active: Optional[bool] = None
    markup_percent: Optional[float] = None
    display_name: Optional[str] = None
    deposit_balance: Optional[float] = None
    audit_reason: Optional[str] = None


class SellerBanRequest(BaseModel):
    reason: str
    audit_reason: Optional[str] = None


class SellerBankResponse(BaseModel):
    id: int
    seller_id: int
    seller_name: str
    bank_name: str
    bank_code: str
    category: str
    product_type: str
    product_subtype: str
    seller_price: Optional[Decimal] = None
    buyer_price: Optional[Decimal] = None
    is_in_stock: bool
    stock_count: int
    description: Optional[str]
    instruction: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SellerOrderResponse(BaseModel):
    id: int
    seller_id: int
    seller_name: str
    bank_name: str
    buyer_label: str
    status: str
    price_for_buyer: Optional[Decimal] = None
    price_for_seller: Optional[Decimal] = None
    quantity: int
    admin_notes: Optional[str]
    created_at: datetime
    admin_approved_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ========== Endpoints ==========

@router.get("", response_model=List[SellerResponse])
async def get_sellers(
    approved_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_read_access())
):
    finance_visible = can_view_finances(current_user)
    query = select(Seller).order_by(Seller.created_at.desc())
    if approved_only:
        query = query.where(Seller.is_approved == True)

    result = await db.execute(query)
    sellers = result.scalars().all()

    if not sellers:
        return []

    seller_ids = [s.id for s in sellers]

    # Пакетная загрузка banks_count и in_stock_count (1 запрос вместо 2*N)
    banks_counts_result = await db.execute(
        select(SellerBank.seller_id, func.count(SellerBank.id).label("cnt"))
        .where(and_(SellerBank.seller_id.in_(seller_ids), SellerBank.is_active == True))
        .group_by(SellerBank.seller_id)
    )
    banks_counts: dict[int, int] = {row.seller_id: row.cnt for row in banks_counts_result.all()}

    in_stock_counts_result = await db.execute(
        select(SellerBank.seller_id, func.count(SellerBank.id).label("cnt"))
        .where(and_(
            SellerBank.seller_id.in_(seller_ids),
            SellerBank.is_active == True,
            SellerBank.is_in_stock == True,
        ))
        .group_by(SellerBank.seller_id)
    )
    in_stock_counts: dict[int, int] = {row.seller_id: row.cnt for row in in_stock_counts_result.all()}

    # Пакетная загрузка active orders (1 запрос вместо N)
    active_orders_result = await db.execute(
        select(SellerOrder.seller_id, func.count(SellerOrder.id).label("cnt"))
        .where(and_(
            SellerOrder.seller_id.in_(seller_ids),
            SellerOrder.status.in_(["pending_admin", "approved", "in_progress"]),
        ))
        .group_by(SellerOrder.seller_id)
    )
    active_orders_counts: dict[int, int] = {row.seller_id: row.cnt for row in active_orders_result.all()}

    response = []
    for seller in sellers:
        projection = await LedgerProjectionService.get_seller_projection(db, seller.id) if finance_visible else None
        banks_count = banks_counts.get(seller.id, 0)
        in_stock_count = in_stock_counts.get(seller.id, 0)
        active_orders = active_orders_counts.get(seller.id, 0)

        response.append(SellerResponse(
            id=seller.id,
            telegram_id=seller.telegram_id,
            username=seller.username,
            display_name=seller.display_name,
            seller_type=seller.seller_type,
            access_status=getattr(seller, "access_status", "pending_deposit"),
            is_approved=seller.is_approved,
            is_active=seller.is_active,
            markup_percent=seller.markup_percent,
            total_orders=seller.total_orders,
            total_earned=seller.total_earned if finance_visible else None,
            security_deposit_balance=(getattr(seller, "security_deposit_balance", 0) or 0) if finance_visible else None,
            security_deposit_status=getattr(seller, "security_deposit_status", "unpaid"),
            security_deposit_categories=list(getattr(seller, "security_deposit_categories", None) or []),
            ban_reason=getattr(seller, "ban_reason", None),
            is_banned_for_leak=bool(getattr(seller, "is_banned_for_leak", False)),
            deposit_balance=(getattr(seller, "deposit_balance", 0) or 0) if finance_visible else None,
            pending_balance=(projection["pending_balance"] if projection else None),
            withdrawable_balance=(projection["withdrawable_balance"] if projection else None),
            banks_count=banks_count,
            in_stock_count=in_stock_count,
            active_orders=active_orders,
            created_at=seller.created_at,
            approved_at=seller.approved_at
        ))
    
    return response


@router.get("/{seller_id}", response_model=SellerResponse)
async def get_seller(
    seller_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_read_access())
):
    finance_visible = can_view_finances(current_user)
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    projection = await LedgerProjectionService.get_seller_projection(db, seller.id) if finance_visible else None
    
    return SellerResponse(
        id=seller.id,
        telegram_id=seller.telegram_id,
        username=seller.username,
        display_name=seller.display_name,
        seller_type=seller.seller_type,
        access_status=getattr(seller, "access_status", "pending_deposit"),
        is_approved=seller.is_approved,
        is_active=seller.is_active,
        markup_percent=seller.markup_percent,
        total_orders=seller.total_orders,
        total_earned=seller.total_earned if finance_visible else None,
        security_deposit_balance=(getattr(seller, "security_deposit_balance", 0) or 0) if finance_visible else None,
        security_deposit_status=getattr(seller, "security_deposit_status", "unpaid"),
        security_deposit_categories=list(getattr(seller, "security_deposit_categories", None) or []),
        ban_reason=getattr(seller, "ban_reason", None),
        is_banned_for_leak=bool(getattr(seller, "is_banned_for_leak", False)),
        deposit_balance=(getattr(seller, "deposit_balance", 0) or 0) if finance_visible else None,
        pending_balance=(projection["pending_balance"] if projection else None),
        withdrawable_balance=(projection["withdrawable_balance"] if projection else None),
        created_at=seller.created_at,
        approved_at=seller.approved_at
    )


@router.put("/{seller_id}", response_model=SellerResponse)
async def update_seller(
    seller_id: int,
    data: SellerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin_management_access())
):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    old_values = {
        "seller_type": seller.seller_type,
        "access_status": getattr(seller, "access_status", "pending_deposit"),
        "is_approved": seller.is_approved,
        "is_active": seller.is_active,
        "markup_percent": float(seller.markup_percent),
        "display_name": seller.display_name,
        "deposit_balance": float(getattr(seller, "deposit_balance", 0) or 0),
        "pending_balance": float((await LedgerProjectionService.get_seller_projection(db, seller.id))["pending_balance"]),
        "withdrawable_balance": float((await LedgerProjectionService.get_seller_projection(db, seller.id))["withdrawable_balance"]),
    }

    if data.seller_type is not None:
        seller.seller_type = data.seller_type
    if data.is_approved is not None:
        seller.is_approved = data.is_approved
        if data.is_approved and not seller.approved_at:
            seller.approved_at = datetime.now(timezone.utc)
    if data.is_active is not None:
        seller.is_active = data.is_active
    if data.markup_percent is not None:
        seller.markup_percent = data.markup_percent
    if data.display_name is not None:
        seller.display_name = data.display_name
    if data.deposit_balance is not None:
        manual_balance = Decimal(str(data.deposit_balance))
        seller.deposit_balance = manual_balance
    
    admin_id = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(
        db,
        admin_id,
        "seller_update",
        "seller",
        seller.id,
        {
            "old": old_values,
            "new": {
                "seller_type": seller.seller_type,
                "access_status": getattr(seller, "access_status", "pending_deposit"),
                "is_approved": seller.is_approved,
                "is_active": seller.is_active,
                "markup_percent": float(seller.markup_percent),
                "display_name": seller.display_name,
                "deposit_balance": float(getattr(seller, "deposit_balance", 0) or 0),
            },
            "actor_role": current_user.get("role"),
        },
        ip_address,
    )
    if seller.is_active != old_values["is_active"]:
        await log_action(
            db,
            admin_id,
            "seller_unban" if seller.is_active else "seller_ban",
            "seller",
            seller.id,
            {
                "reason": data.audit_reason,
                "old_is_active": old_values["is_active"],
                "new_is_active": seller.is_active,
                "actor_role": current_user.get("role"),
            },
            ip_address,
        )
    old_deposit = Decimal(str(old_values["deposit_balance"]))
    new_deposit = Decimal(str(float(getattr(seller, "deposit_balance", 0) or 0)))
    if new_deposit != old_deposit:
        await log_action(
            db,
            admin_id,
            "seller_deposit_withhold" if new_deposit < old_deposit else "seller_deposit_adjust",
            "seller",
            seller.id,
            {
                "reason": data.audit_reason,
                "old_deposit_balance": float(old_deposit),
                "new_deposit_balance": float(new_deposit),
                "delta": float(new_deposit - old_deposit),
                "actor_role": current_user.get("role"),
            },
            ip_address,
        )
    await db.commit()
    await db.refresh(seller)
    updated_projection = await LedgerProjectionService.get_seller_projection(db, seller.id)
    
    return SellerResponse(
        id=seller.id,
        telegram_id=seller.telegram_id,
        username=seller.username,
        display_name=seller.display_name,
        seller_type=seller.seller_type,
        access_status=getattr(seller, "access_status", "pending_deposit"),
        is_approved=seller.is_approved,
        is_active=seller.is_active,
        markup_percent=seller.markup_percent,
        total_orders=seller.total_orders,
        total_earned=seller.total_earned,
        security_deposit_balance=getattr(seller, "security_deposit_balance", 0) or 0,
        security_deposit_status=getattr(seller, "security_deposit_status", "unpaid"),
        security_deposit_categories=list(getattr(seller, "security_deposit_categories", None) or []),
        ban_reason=getattr(seller, "ban_reason", None),
        is_banned_for_leak=bool(getattr(seller, "is_banned_for_leak", False)),
        deposit_balance=getattr(seller, "deposit_balance", 0) or 0,
        pending_balance=updated_projection["pending_balance"],
        withdrawable_balance=updated_projection["withdrawable_balance"],
        created_at=seller.created_at,
        approved_at=seller.approved_at
    )


@router.post("/{seller_id}/approve")
async def approve_seller(
    seller_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin_management_access())
):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    allowed_categories = SellerDepositService.activate_seller_access(
        seller,
        approved_at=datetime.now(timezone.utc),
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_approve",
        "seller",
        seller.id,
        {
            "seller_name": seller.display_name or seller.username,
            "access_status": seller.access_status,
            "allowed_categories": sorted(allowed_categories),
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    
    return {"status": "success", "message": "Seller approved"}


@router.post("/{seller_id}/toggle")
async def toggle_seller(
    seller_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin_management_access())
):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    seller.is_active = not seller.is_active
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_unban" if seller.is_active else "seller_ban",
        "seller",
        seller.id,
        {
            "is_active": seller.is_active,
            "seller_name": seller.display_name or seller.username,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    
    return {"status": "success", "is_active": seller.is_active}


@router.post("/{seller_id}/ban")
async def ban_seller(
    seller_id: int,
    data: SellerBanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    if not data.reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required")

    affected = await SellerDepositService.ban_seller(
        db,
        seller,
        actor_id=current_user.get("admin_id"),
        reason=data.reason.strip(),
        source="web_panel",
        ban_for_leak=False,
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_ban",
        "seller",
        seller.id,
        {
            "reason": data.reason.strip(),
            "affected": affected,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return {"status": "success", "affected": affected}


@router.post("/{seller_id}/ban-for-leak")
async def ban_seller_for_leak(
    seller_id: int,
    data: SellerBanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    if not data.reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required")

    affected = await SellerDepositService.ban_seller(
        db,
        seller,
        actor_id=current_user.get("admin_id"),
        reason=data.reason.strip(),
        source="web_panel_leak_ban",
        ban_for_leak=True,
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_leak_ban",
        "seller",
        seller.id,
        {
            "reason": data.reason.strip(),
            "affected": affected,
            "actor_role": current_user.get("role"),
            "deposit_withheld": True,
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return {"status": "success", "affected": affected}


@router.get("/{seller_id}/banks", response_model=List[SellerBankResponse])
async def get_seller_banks(
    seller_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_read_access())
):
    finance_visible = can_view_finances(current_user)
    result = await db.execute(
        select(SellerBank).where(SellerBank.seller_id == seller_id).order_by(SellerBank.category)
    )
    banks = result.scalars().all()
    
    seller_result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = seller_result.scalar_one_or_none()
    seller_name = seller.display_name if seller else "Unknown"
    
    return [
        SellerBankResponse(
            id=b.id,
            seller_id=b.seller_id,
            seller_name=seller_name,
            bank_name=b.bank_name,
            bank_code=b.bank_code,
            category=b.category,
            product_type=getattr(b, "product_type", "bank"),
            product_subtype=getattr(b, "product_subtype", "log"),
            seller_price=b.seller_price if finance_visible else None,
            buyer_price=b.buyer_price if finance_visible else None,
            is_in_stock=b.is_in_stock,
            stock_count=b.stock_count,
            description=b.description,
            instruction=getattr(b, "instruction", None),
            is_active=b.is_active,
            created_at=b.created_at,
            updated_at=b.updated_at
        ) for b in banks
    ]


@router.get("/orders/all", response_model=List[SellerOrderResponse])
async def get_all_seller_orders(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_read_access())
):
    finance_visible = can_view_finances(current_user)
    query = select(SellerOrder).order_by(SellerOrder.created_at.desc()).limit(limit)
    if status:
        query = query.where(SellerOrder.status == status)
    
    result = await db.execute(query)
    orders = result.scalars().all()
    
    response = []
    for order in orders:
        seller_result = await db.execute(select(Seller).where(Seller.id == order.seller_id))
        seller = seller_result.scalar_one_or_none()
        
        bank_result = await db.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        bank = bank_result.scalar_one_or_none()
        
        response.append(SellerOrderResponse(
            id=order.id,
            seller_id=order.seller_id,
            seller_name=seller.display_name if seller else "Unknown",
            bank_name=bank.bank_name if bank else "Unknown",
            buyer_label="Buyer",
            status=order.status,
            price_for_buyer=order.price_for_buyer if finance_visible else None,
            price_for_seller=order.price_for_seller if finance_visible else None,
            quantity=order.quantity,
            admin_notes=order.admin_notes,
            created_at=order.created_at,
            admin_approved_at=order.admin_approved_at,
            completed_at=order.completed_at
        ))
    
    return response
