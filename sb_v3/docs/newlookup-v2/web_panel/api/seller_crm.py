from __future__ import annotations

"""
API для Seller CRM (Kanban заказов продавцов)
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelt, timezone
from typing import Optional, List
from pydantic import BaseModel
from aiogram import Bot
from aiogram.enums import ParseMode

from web_panel.database import get_db
from web_panel.auth import require_finance_access, require_seller_moderation_access, require_seller_read_access
from shared.database.models import SellerOrder, SellerCCOrder, Seller, SellerBank, SellerCCItem, SellerWithdrawal, SellerOrderDispute
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.ledger_service import LedgerService
from shared.services.seller_dispute_service import SellerDisputeService
from shared.services.seller_order_delivery_service import get_seller_order_v24_windows, release_seller_order_reservation
from shared.services.nocodb_service import NocoDBService
from web_panel.services.audit_service import log_action
from shared.services.admin_notification_service import AdminNotificationService
from shared.utils.seller_product_meta import bank_item_badge, cc_item_badge
from support_bot.services.balance_service import BalanceService

router = APIRouter(prefix="/api/seller-crm", tags=["seller-crm"])
logger = logging.getLogger(__name__)
SELLER_BOT_TOKEN = os.getenv("SELLER_BOT_TOKEN", "")

# Kanban column mapping: API status -> display
COLUMN_STATUS_MAP = {
    "new": "pending_admin",           # Новые
    "awaiting": "approved",           # Ожидают подтверждения
    "in_progress": "in_progress",     # В работе
    "completed": "completed",         # Завершены
}
STATUS_TO_COLUMN = {v: k for k, v in COLUMN_STATUS_MAP.items()}


async def _notify_seller_withdrawal_status(telegram_id: int, text: str) -> None:
    if not telegram_id or not SELLER_BOT_TOKEN:
        return
    bot = Bot(token=SELLER_BOT_TOKEN)
    try:
        await bot.send_message(telegram_id, text, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.warning("Failed to notify seller %s about withdrawal update: %s", telegram_id, exc)
    finally:
        await bot.session.close()


class SellerCRMOrder(BaseModel):
    id: int
    order_type: str  # "bank" | "cc"
    seller_id: int
    seller_name: str
    item_name: str
    buyer_label: str
    status: str
    price_for_buyer: float
    price_for_seller: float
    quantity: int
    created_at: datetime
    admin_approved_at: Optional[datetime]
    taken_at: Optional[datetime]
    completed_at: Optional[datetime]
    auto_complete_at: Optional[datetime] = None
    dispute_deadline_at: Optional[datetime] = None
    escrow_released: Optional[bool] = None
    marketer_commission_paid: Optional[bool] = None
    worker_paid: Optional[bool] = None

    class Config:
        from_attributes = True


class UpdateOrderStatus(BaseModel):
    status: str  # pending_admin, approved, in_progress, completed
    order_type: str  # bank | cc


class SellerCRMDispute(BaseModel):
    id: int
    order_id: int
    seller_id: int
    seller_name: str
    bank_name: str
    buyer_user_id: int
    reason: str
    description: Optional[str]
    status: str
    seller_response_due_at: Optional[datetime] = None
    seller_responded_at: Optional[datetime] = None
    assigned_admin_id: Optional[int] = None
    appeal_status: Optional[str] = None
    appeal_reason: Optional[str] = None
    appeal_requested_at: Optional[datetime] = None
    buyer_evidence: Optional[dict] = None
    seller_evidence: Optional[dict] = None
    resolution_note: Optional[str]
    resolved_by: Optional[int]
    created_at: datetime
    resolved_at: Optional[datetime]
    order_status: str
    dispute_deadline_at: Optional[datetime]
    auto_complete_at: Optional[datetime]


class ResolveSellerDispute(BaseModel):
    outcome: str  # resolved_buyer | resolved_seller | cancelled
    resolution_note: Optional[str] = None


class AppealSellerDispute(BaseModel):
    reason: str


class ReviewAppealSellerDispute(BaseModel):
    status: str  # approved | rejected
    note: Optional[str] = None


@router.get("/orders")
async def get_kanban_orders(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_read_access())
):
    """Получить заказы для Kanban, сгруппированные по статусам"""
    # Bank orders (SellerOrder)
    bank_result = await db.execute(
        select(SellerOrder).order_by(SellerOrder.created_at.desc()).limit(200)
    )
    bank_orders = bank_result.scalars().all()

    # CC orders (SellerCCOrder)
    cc_result = await db.execute(
        select(SellerCCOrder).order_by(SellerCCOrder.created_at.desc()).limit(200)
    )
    cc_orders = cc_result.scalars().all()

    # Build response by column
    columns = {
        "new": [],
        "awaiting": [],
        "in_progress": [],
        "completed": [],
    }

    for order in bank_orders:
        if order.status == "disputed":
            continue
        col = STATUS_TO_COLUMN.get(order.status, "new")
        seller_res = await db.execute(select(Seller).where(Seller.id == order.seller_id))
        seller = seller_res.scalar_one_or_none()
        bank_res = await db.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        bank = bank_res.scalar_one_or_none()
        columns[col].append(SellerCRMOrder(
            id=order.id,
            order_type="bank",
            seller_id=order.seller_id,
            seller_name=(seller.display_name or seller.username or "?") if seller else "?",
            item_name=f"{bank.bank_name} [{bank_item_badge(getattr(order, 'product_type', getattr(bank, 'product_type', 'bank') if bank else 'bank'), getattr(order, 'product_subtype', getattr(bank, 'product_subtype', 'log') if bank else 'log'))}]" if bank else "?",
            buyer_label="Buyer",
            status=order.status,
            price_for_buyer=float(order.price_for_buyer),
            price_for_seller=float(order.price_for_seller),
            quantity=order.quantity,
            created_at=order.created_at,
            admin_approved_at=order.admin_approved_at,
            taken_at=order.taken_at,
            completed_at=order.completed_at,
            auto_complete_at=getattr(order, "auto_complete_at", None),
            dispute_deadline_at=getattr(order, "dispute_deadline_at", None),
            escrow_released=getattr(order, "escrow_released", None),
            marketer_commission_paid=getattr(order, "marketer_commission_paid", None),
            worker_paid=getattr(order, "worker_paid", None),
        ))

    for order in cc_orders:
        col = STATUS_TO_COLUMN.get(order.status, "new")
        seller_res = await db.execute(select(Seller).where(Seller.id == order.seller_id))
        seller = seller_res.scalar_one_or_none()
        item_res = await db.execute(select(SellerCCItem).where(SellerCCItem.id == order.seller_cc_item_id))
        item = item_res.scalar_one_or_none()
        columns[col].append(SellerCRMOrder(
            id=order.id,
            order_type="cc",
            seller_id=order.seller_id,
            seller_name=(seller.display_name or seller.username or "?") if seller else "?",
            item_name=f"{item.item_name} [{cc_item_badge(getattr(order, 'product_subtype', getattr(item, 'product_subtype', 'with_fullz') if item else 'with_fullz'))}]" if item else "?",
            buyer_label="Buyer",
            status=order.status,
            price_for_buyer=float(order.price_for_buyer),
            price_for_seller=float(order.price_for_seller),
            quantity=order.quantity,
            created_at=order.created_at,
            admin_approved_at=order.admin_approved_at,
            taken_at=None,
            completed_at=order.completed_at,
            auto_complete_at=None,
            dispute_deadline_at=None,
            escrow_released=None,
            marketer_commission_paid=None,
            worker_paid=None,
        ))

    return {
        "columns": {
            "new": [o.model_dump(mode="json") for o in columns["new"]],
            "awaiting": [o.model_dump(mode="json") for o in columns["awaiting"]],
            "in_progress": [o.model_dump(mode="json") for o in columns["in_progress"]],
            "completed": [o.model_dump(mode="json") for o in columns["completed"]],
        }
    }


@router.get("/disputes")
async def get_seller_order_disputes(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_read_access())
):
    query = select(SellerOrderDispute).order_by(SellerOrderDispute.created_at.desc())
    if status:
        query = query.where(SellerOrderDispute.status == status)
    disputes = (await db.execute(query)).scalars().all()
    items: list[dict] = []
    for dispute in disputes:
        order = await db.scalar(select(SellerOrder).where(SellerOrder.id == dispute.order_id))
        if not order:
            continue
        seller = await db.scalar(select(Seller).where(Seller.id == order.seller_id))
        bank = await db.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        items.append(SellerCRMDispute(
            id=dispute.id,
            order_id=order.id,
            seller_id=order.seller_id,
            seller_name=(seller.display_name or seller.username or "?") if seller else "?",
            bank_name=bank.bank_name if bank else "?",
            buyer_user_id=order.buyer_user_id,
            reason=dispute.reason,
            description=dispute.description,
            status=dispute.status,
            seller_response_due_at=getattr(dispute, "seller_response_due_at", None),
            seller_responded_at=getattr(dispute, "seller_responded_at", None),
            assigned_admin_id=getattr(dispute, "assigned_admin_id", None),
            appeal_status=getattr(dispute, "appeal_status", None),
            appeal_reason=getattr(dispute, "appeal_reason", None),
            appeal_requested_at=getattr(dispute, "appeal_requested_at", None),
            buyer_evidence=getattr(dispute, "buyer_evidence", None),
            seller_evidence=getattr(dispute, "seller_evidence", None),
            resolution_note=dispute.resolution_note,
            resolved_by=dispute.resolved_by,
            created_at=dispute.created_at,
            resolved_at=dispute.resolved_at,
            order_status=order.status,
            dispute_deadline_at=getattr(order, "dispute_deadline_at", None),
            auto_complete_at=getattr(order, "auto_complete_at", None),
        ).model_dump(mode="json"))
    return {"disputes": items}


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_seller_order_dispute(
    dispute_id: int,
    body: ResolveSellerDispute,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    valid_outcomes = {"resolved_buyer", "resolved_seller", "cancelled"}
    if body.outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Invalid outcome. Use: {sorted(valid_outcomes)}")

    dispute = await db.scalar(select(SellerOrderDispute).where(SellerOrderDispute.id == dispute_id))
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    order = await db.scalar(select(SellerOrder).where(SellerOrder.id == dispute.order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Seller order not found")

    now = datetime.now(timezone.utc)
    old_status = dispute.status
    dispute.assigned_admin_id = current_user.get("admin_id")
    bank = await db.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    seller = await db.scalar(select(Seller).where(Seller.id == order.seller_id))
    bank_name = bank.bank_name if bank else "Bank"
    resolution_note = body.resolution_note or ""

    if body.outcome == "resolved_buyer":
        try:
            await SellerDisputeService.resolve_for_buyer(
                db,
                dispute=dispute,
                order=order,
                actor_admin_id=current_user.get("admin_id"),
                resolution_note=resolution_note,
            )
        except RuntimeError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Refund failed")
    elif body.outcome == "resolved_seller":
        await SellerDisputeService.resolve_for_seller(
            db,
            dispute=dispute,
            order=order,
            actor_admin_id=current_user.get("admin_id"),
            resolution_note=resolution_note,
        )
    else:
        order.admin_notes = resolution_note or order.admin_notes

    if body.outcome == "cancelled":
        dispute_window_hours, _ = await get_seller_order_v24_windows(db)
        order.status = "completed"
        order.check_window_minutes = dispute_window_hours * 60
        order.check_expires_at = now + timedelta(hours=dispute_window_hours)
        order.auto_complete_at = now + timedelta(hours=dispute_window_hours)
        order.dispute_deadline_at = None
        dispute.status = body.outcome
        dispute.resolution_note = resolution_note or None
        dispute.resolved_by = current_user.get("admin_id")
        dispute.resolved_at = now

    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_order_dispute_resolve",
        "seller_order_dispute",
        dispute.id,
        {
            "old_status": old_status,
            "new_status": dispute.status,
            "order_id": order.id,
            "outcome": body.outcome,
            "resolution_note": resolution_note,
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "status": dispute.status, "order_status": order.status}


@router.post("/disputes/{dispute_id}/appeal")
async def request_seller_order_dispute_appeal(
    dispute_id: int,
    body: AppealSellerDispute,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    try:
        dispute = await SellerDisputeService.request_appeal(
            db,
            dispute_id=dispute_id,
            reason=body.reason,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    await db.commit()
    return {
        "ok": True,
        "appeal_status": dispute.appeal_status,
        "appeal_requested_at": dispute.appeal_requested_at,
    }


@router.post("/disputes/{dispute_id}/appeal/review")
async def review_seller_order_dispute_appeal(
    dispute_id: int,
    body: ReviewAppealSellerDispute,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    if body.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid appeal status")
    try:
        dispute = await SellerDisputeService.review_appeal(
            db,
            dispute_id=dispute_id,
            status=body.status,
            actor_admin_id=current_user.get("admin_id"),
            note=body.note,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    await db.commit()
    return {"ok": True, "appeal_status": dispute.appeal_status}


@router.patch("/orders/{order_type}/{order_id}")
async def update_order_status(
    order_type: str,
    order_id: int,
    body: UpdateOrderStatus,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    """Обновить статус заказа (для drag-and-drop в Kanban)"""
    if order_type == "bank":
        result = await db.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        order = result.scalar_one_or_none()
    elif order_type == "cc":
        result = await db.execute(select(SellerCCOrder).where(SellerCCOrder.id == order_id))
        order = result.scalar_one_or_none()
    else:
        raise HTTPException(status_code=400, detail="Invalid order_type")

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order_type == "bank":
        open_dispute = await db.scalar(
            select(SellerOrderDispute).where(
                SellerOrderDispute.order_id == order_id,
                SellerOrderDispute.status == "open",
            )
        )
        if open_dispute or order.status == "disputed":
            raise HTTPException(status_code=400, detail="Resolve the dispute before moving this order")

    valid_statuses = ["pending_admin", "approved", "in_progress", "completed"]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {valid_statuses}")

    old_status = order.status
    order.status = body.status
    now = datetime.now(timezone.utc)
    if body.status == "approved":
        order.admin_approved_at = order.admin_approved_at or now
    elif body.status == "in_progress" and hasattr(order, "taken_at"):
        order.taken_at = order.taken_at or now
    elif body.status == "completed":
        order.completed_at = now

    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_order_status_update",
        "seller_order",
        order_id,
        {
            "order_type": order_type,
            "old_status": old_status,
            "new_status": body.status,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "status": body.status}


# ========== Seller Withdrawals ==========

class CreateWithdrawal(BaseModel):
    seller_id: int
    amount: float
    requisites: Optional[str] = None


@router.get("/withdrawals")
async def get_withdrawals(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Список заявок на вывод средств продавцов"""
    query = select(SellerWithdrawal).order_by(SellerWithdrawal.created_at.desc())
    if status:
        query = query.where(SellerWithdrawal.status == status)
    result = await db.execute(query)
    withdrawals = result.scalars().all()
    items = []
    for w in withdrawals:
        seller_res = await db.execute(select(Seller).where(Seller.id == w.seller_id))
        seller = seller_res.scalar_one_or_none()
        projection = await LedgerProjectionService.get_seller_projection(db, w.seller_id) if seller else None
        items.append({
            "id": w.id,
            "seller_id": w.seller_id,
            "seller_name": (seller.display_name or seller.username or "?") if seller else "?",
            "amount": float(w.amount),
            "withdrawable_balance": float(projection["withdrawable_balance"]) if projection else 0.0,
            "requisites": w.requisites,
            "status": w.status,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "processed_at": w.processed_at.isoformat() if w.processed_at else None,
        })
    return {"withdrawals": items}


@router.post("/withdrawals")
async def create_withdrawal(
    body: CreateWithdrawal,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Создать заявку на вывод (админ от имени продавца или из бота)"""
    seller_res = await db.execute(select(Seller).where(Seller.id == body.seller_id))
    seller = seller_res.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    projection = await LedgerProjectionService.get_seller_projection(db, seller.id)
    if float(projection["withdrawable_balance"]) < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    w = SellerWithdrawal(seller_id=body.seller_id, amount=body.amount, requisites=body.requisites)
    db.add(w)
    await db.flush()
    if not await LedgerService.reserve_seller_withdrawal(
        db,
        seller=seller,
        amount=body.amount,
        withdrawal_id=w.id,
    ):
        raise HTTPException(status_code=400, detail="Insufficient balance")
    w.funds_reserved = True
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_withdrawal_create",
        "seller_withdrawal",
        None,
        {
            "seller_id": body.seller_id,
            "amount": body.amount,
            "requisites": body.requisites,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(w)
    return {"id": w.id, "status": "pending"}


@router.post("/withdrawals/{withdrawal_id}/approve")
async def approve_withdrawal(
    withdrawal_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Одобрить вывод средств"""
    result = await db.execute(select(SellerWithdrawal).where(SellerWithdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    seller_res = await db.execute(select(Seller).where(Seller.id == w.seller_id))
    seller = seller_res.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    if not getattr(w, "funds_reserved", False):
        if not await LedgerService.reserve_seller_withdrawal(
            db,
            seller=seller,
            amount=w.amount,
            withdrawal_id=w.id,
        ):
            raise HTTPException(status_code=400, detail="Insufficient seller balance")
        w.funds_reserved = True
    await LedgerService.finalize_seller_withdrawal(
        db,
        seller=seller,
        amount=w.amount,
        withdrawal_id=w.id,
    )
    w.status = "approved"
    w.processed_at = datetime.now(timezone.utc)
    w.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_withdrawal_approve",
        "seller_withdrawal",
        w.id,
        {
            "seller_id": w.seller_id,
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
        target_type="seller_withdrawal",
        target_id=w.id,
        status="approved",
        payload={"seller_id": w.seller_id, "amount": float(w.amount)},
        timestamp=w.processed_at,
    )
    await AdminNotificationService.notify_admin_action(
        "SELLER WITHDRAWAL APPROVED",
        [
            f"💸 <b>Withdrawal:</b> #{w.id}",
            f"🏪 <b>Seller:</b> #{w.seller_id}",
            f"💵 <b>Amount:</b> ${float(w.amount):.2f}",
            f"🔑 <b>By:</b> {current_user.get('username', 'web_panel')}",
        ],
        event_type="seller_withdrawal_approved",
        urgent=True,
    )
    await _notify_seller_withdrawal_status(
        seller.telegram_id,
        f"✅ <b>Withdrawal approved</b>\n\nAmount: <b>${float(w.amount):.2f}</b>\nStatus: approved"
    )
    return {"ok": True}


class RejectWithdrawalBody(BaseModel):
    reason: Optional[str] = None


@router.post("/withdrawals/{withdrawal_id}/reject")
async def reject_withdrawal(
    withdrawal_id: int,
    request: Request,
    body: RejectWithdrawalBody = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Отклонить вывод средств"""
    result = await db.execute(select(SellerWithdrawal).where(SellerWithdrawal.id == withdrawal_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if w.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    w.status = "rejected"
    w.processed_at = datetime.now(timezone.utc)
    w.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    w.reject_reason = body.reason if body else None
    seller = await db.scalar(select(Seller).where(Seller.id == w.seller_id))
    if seller and getattr(w, "funds_reserved", False):
        await LedgerService.release_seller_withdrawal_reservation(
            db,
            seller=seller,
            amount=w.amount,
            withdrawal_id=w.id,
        )
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_withdrawal_reject",
        "seller_withdrawal",
        w.id,
        {
            "seller_id": w.seller_id,
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
        target_type="seller_withdrawal",
        target_id=w.id,
        status="rejected",
        payload={"seller_id": w.seller_id, "amount": float(w.amount), "reason": w.reject_reason},
        timestamp=w.processed_at,
    )
    seller_res = await db.execute(select(Seller).where(Seller.id == w.seller_id))
    seller = seller_res.scalar_one_or_none()
    if seller:
        reason_text = f"\nReason: {w.reject_reason}" if w.reject_reason else ""
        await _notify_seller_withdrawal_status(
            seller.telegram_id,
            f"❌ <b>Withdrawal rejected</b>\n\nAmount: <b>${float(w.amount):.2f}</b>{reason_text}"
        )
    return {"ok": True}


# ========== Совместимость со старыми withdrawal-tasks маршрутами ==========

@router.get("/withdrawal-tasks")
async def get_withdrawal_tasks(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Совместимый список seller withdrawals на базе основной БД"""
    query = select(SellerWithdrawal).order_by(SellerWithdrawal.created_at.desc())
    if status:
        query = query.where(SellerWithdrawal.status == status)
    result = await db.execute(query)
    tasks = result.scalars().all()
    items = []
    for t in tasks:
        seller_res = await db.execute(select(Seller).where(Seller.id == t.seller_id))
        seller = seller_res.scalar_one_or_none()
        projection = await LedgerProjectionService.get_seller_projection(db, t.seller_id) if seller else None
        items.append({
            "id": t.id,
            "seller_id": t.seller_id,
            "seller_name": (seller.display_name or seller.username or "?") if seller else "?",
            "amount": float(t.amount),
            "withdrawable_balance": float(projection["withdrawable_balance"]) if projection else 0.0,
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
    current_user: dict = Depends(require_finance_access())
):
    """Одобрить seller withdrawal через совместимый legacy маршрут"""
    result = await db.execute(select(SellerWithdrawal).where(SellerWithdrawal.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    seller_res = await db.execute(select(Seller).where(Seller.id == task.seller_id))
    seller = seller_res.scalar_one_or_none()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    if not getattr(task, "funds_reserved", False):
        if not await LedgerService.reserve_seller_withdrawal(
            db,
            seller=seller,
            amount=task.amount,
            withdrawal_id=task.id,
        ):
            raise HTTPException(status_code=400, detail="Insufficient seller balance")
        task.funds_reserved = True
    await LedgerService.finalize_seller_withdrawal(
        db,
        seller=seller,
        amount=task.amount,
        withdrawal_id=task.id,
    )
    task.status = "approved"
    task.processed_at = datetime.now(timezone.utc)
    task.processed_by = current_user.get("telegram_id") or current_user.get("user_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_withdrawal_approve",
        "seller_withdrawal",
        task.id,
        {
            "seller_id": task.seller_id,
            "amount": float(task.amount),
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await _notify_seller_withdrawal_status(
        seller.telegram_id,
        f"✅ <b>Withdrawal approved</b>\n\nAmount: <b>${float(task.amount):.2f}</b>\nStatus: approved"
    )
    return {"ok": True}


@router.post("/withdrawal-tasks/{task_id}/reject")
async def reject_withdrawal_task(
    task_id: int,
    request: Request,
    body: RejectWithdrawalBody = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Отклонить seller withdrawal через совместимый legacy маршрут"""
    result = await db.execute(select(SellerWithdrawal).where(SellerWithdrawal.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Already processed")
    seller = await db.scalar(select(Seller).where(Seller.id == task.seller_id))
    if seller and getattr(task, "funds_reserved", False):
        await LedgerService.release_seller_withdrawal_reservation(
            db,
            seller=seller,
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
        "seller_withdrawal_reject",
        "seller_withdrawal",
        task.id,
        {
            "seller_id": task.seller_id,
            "amount": float(task.amount),
            "reason": body.reason if body else None,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    reason_text = f"\nReason: {task.reject_reason}" if task.reject_reason else ""
    await _notify_seller_withdrawal_status(
        seller.telegram_id if seller else None,
        f"❌ <b>Withdrawal rejected</b>\n\nAmount: <b>${float(task.amount):.2f}</b>{reason_text}"
    )
    return {"ok": True}


# ========== NocoDB Sync ==========

@router.get("/nocodb/status")
async def nocodb_status(current_user: dict = Depends(require_finance_access())):
    """Статус интеграции NocoDB (настроена ли)"""
    from web_panel.config import web_panel_config
    configured = bool(
        web_panel_config.nocodb_base_url
        and web_panel_config.nocodb_api_token
        and web_panel_config.nocodb_table_id
    )
    return {
        "configured": configured,
        "base_url": web_panel_config.nocodb_base_url if configured else None,
    }


@router.post("/nocodb/sync")
async def nocodb_sync(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_finance_access())
):
    """Запустить синхронизацию заказов Seller CRM в NocoDB"""
    from web_panel.config import web_panel_config
    from web_panel.services.nocodb_sync import NocoDBSyncService

    if not all([
        web_panel_config.nocodb_base_url,
        web_panel_config.nocodb_api_token,
        web_panel_config.nocodb_table_id,
    ]):
        raise HTTPException(
            status_code=400,
            detail="NocoDB не настроен. Установите NOCODB_BASE_URL, NOCODB_API_TOKEN, NOCODB_TABLE_ID в .env"
        )

    service = NocoDBSyncService(
        base_url=web_panel_config.nocodb_base_url,
        api_token=web_panel_config.nocodb_api_token,
        table_id=web_panel_config.nocodb_table_id,
    )
    try:
        stats = await service.sync_orders(db)
        return {
            "ok": True,
            "message": f"Синхронизировано: создано {stats['created']}, обновлено {stats['updated']}, ошибок {stats['errors']}",
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")


@router.post("/nocodb/test")
async def nocodb_test(current_user: dict = Depends(require_finance_access())):
    """Проверить подключение к NocoDB"""
    from web_panel.config import web_panel_config
    from web_panel.services.nocodb_sync import NocoDBSyncService

    if not all([
        web_panel_config.nocodb_base_url,
        web_panel_config.nocodb_api_token,
    ]):
        raise HTTPException(
            status_code=400,
            detail="NocoDB не настроен. Установите NOCODB_BASE_URL и NOCODB_API_TOKEN"
        )

    service = NocoDBSyncService(
        base_url=web_panel_config.nocodb_base_url,
        api_token=web_panel_config.nocodb_api_token,
        table_id=web_panel_config.nocodb_table_id or "dummy",
    )
    ok = await service.test_connection()
    return {"ok": ok, "message": "Подключение успешно" if ok else "Не удалось подключиться"}
