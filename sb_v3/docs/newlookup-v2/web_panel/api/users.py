"""
API для управления пользователями
"""

import html
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select, and_, func, case, cast, or_, String
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from decimal import Decimal
import os
import uuid
import aiofiles
from aiogram.types import FSInputFile

from web_panel.auth import (
    can_ban_users,
    can_edit_crm,
    can_view_crm,
    can_view_finances,
    get_current_user,
    require_page_access,
)
from web_panel.services.audit_service import log_action
from web_panel.database import get_db
from shared.database.models import (
    User,
    Order,
    Transaction,
    MirrorBot,
    ProductPurchase,
    Product,
    Seller,
    SellerOrder,
    SellerBank,
    SellerCCOrder,
    SellerCCItem,
    BruteBankOrder,
    BruteBankItem,
    SupportTicket,
)
from shared.services.ledger_service import LedgerService
from aiogram import Bot
from web_panel.config import web_panel_config

# Локальные константы для админских сообщений
# WEB_ADMIN_MESSAGE_PREFIX = "📢 **Message from Admin:**\n\n"  # Заменено на мультиязычную функцию
from web_panel.services.bot_integration import bot_integration
from web_panel.utils.multilang import get_user_admin_message_prefix

router = APIRouter()
logger = logging.getLogger(__name__)

DEBIT_TRANSACTION_TYPES = {"purchase"}


def _ensure_crm_view(current_user: dict) -> None:
    if not can_view_crm(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _ensure_crm_edit(current_user: dict) -> None:
    if not can_edit_crm(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _ensure_ban_access(current_user: dict) -> None:
    if not can_ban_users(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _ensure_finance_access(current_user: dict) -> None:
    if not can_view_finances(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _decimal_to_float(value: Optional[Decimal]) -> float:
    return float(value or 0)


def _signed_transaction_amount(transaction: Transaction) -> Decimal:
    amount = Decimal(str(transaction.amount or 0))
    if amount < 0:
        return amount
    if transaction.type in DEBIT_TRANSACTION_TYPES:
        return -amount
    return amount


def _build_balance_history(
    transactions: List[Transaction],
    current_balance: Decimal,
) -> List[dict]:
    running_balance = Decimal(str(current_balance or 0))
    history: List[dict] = []

    for transaction in transactions:
        signed_amount = _signed_transaction_amount(transaction)
        balance_after = running_balance
        balance_before = balance_after - signed_amount

        history.append(
            {
                "id": transaction.id,
                "type": transaction.type,
                "amount": _decimal_to_float(transaction.amount),
                "signed_amount": _decimal_to_float(signed_amount),
                "description": transaction.description,
                "created_at": transaction.created_at,
                "balance_before": _decimal_to_float(balance_before),
                "balance_after": _decimal_to_float(balance_after),
            }
        )

        running_balance = balance_before

    return history


async def get_user_language(db: AsyncSession, user_id: int, mirror_bot_id: int) -> str:
    """Получить язык пользователя из базы данных"""
    try:
        stmt = select(User).where(
            User.user_id == user_id,
            User.mirror_bot_id == mirror_bot_id
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user and user.language:
            return user.language
        return "en"  # По умолчанию английский
    except Exception:
        return "en"


class UserResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str]
    mirror_bot_id: int
    language: str
    trust_score: int
    last_active_at: Optional[datetime]
    balance: Optional[float] = None
    referrer_id: Optional[int]
    referral_link: str
    is_banned: bool
    ban_reason: Optional[str]
    created_at: datetime
    order_count: int = 0
    
    class Config:
        from_attributes = True


class UserDetailSummary(BaseModel):
    transactions_total: int
    orders_total: int
    orders_completed: int
    orders_pending: int
    orders_processing: int
    order_spent_total: float
    product_purchases_total: int
    product_spent_total: float
    marketplace_purchases_total: int
    marketplace_spent_total: float
    seller_sales_total: int = 0
    support_tickets_total: int = 0


class UserUpdateBalance(BaseModel):
    amount: float
    reason: str


class UserBanRequest(BaseModel):
    is_banned: bool
    reason: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str


class UserUpdate(BaseModel):
    balance: Optional[float] = None
    is_banned: Optional[bool] = None
    ban_reason: Optional[str] = None


@router.get("/")
async def get_users(
    mirror_bot_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Получить список пользователей с пагинацией"""
    _ensure_crm_view(current_user)
    finance_visible = can_view_finances(current_user)

    try:
        # Подсчет общего количества
        count_stmt = select(func.count(User.id))

        if mirror_bot_id:
            count_stmt = count_stmt.where(User.mirror_bot_id == mirror_bot_id)
        if search:
            normalized_search = search.strip()
            if normalized_search:
                count_stmt = count_stmt.where(
                    or_(
                        User.username.ilike(f"%{normalized_search}%"),
                        cast(User.user_id, String).ilike(f"%{normalized_search}%"),
                    )
                )

        total_count_result = await db.execute(count_stmt)
        total = total_count_result.scalar() or 0

        # Получение пользователей с пагинацией
        stmt = select(User)

        if mirror_bot_id:
            stmt = stmt.where(User.mirror_bot_id == mirror_bot_id)
        if search:
            normalized_search = search.strip()
            if normalized_search:
                stmt = stmt.where(
                    or_(
                        User.username.ilike(f"%{normalized_search}%"),
                        cast(User.user_id, String).ilike(f"%{normalized_search}%"),
                    )
                )

        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(stmt)
        users = result.scalars().all()
        user_ids = [user.user_id for user in users]
        order_counts: dict[int, int] = {}
        if user_ids:
            counts_result = await db.execute(
                select(Order.user_id, func.count(Order.id))
                .where(Order.user_id.in_(user_ids))
                .group_by(Order.user_id)
            )
            order_counts = {uid: int(total or 0) for uid, total in counts_result.all()}

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                UserResponse.model_validate(
                    {
                        **UserResponse.model_validate(user).model_dump(),
                        "balance": float(user.balance) if finance_visible else None,
                        "order_count": order_counts.get(user.user_id, 0),
                    }
                )
                for user in users
            ]
        }

    except Exception as e:
        logger.exception("[USERS API] get_users error")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Получить информацию о пользователе"""
    _ensure_crm_view(current_user)
    
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    payload = UserResponse.model_validate(user).model_dump()
    if not can_view_finances(current_user):
        payload["balance"] = None
    return payload


@router.get("/{user_id}/details")
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Получить расширенную карточку пользователя с историей операций и покупок"""
    _ensure_crm_view(current_user)

    user_result = await db.execute(
        select(User, MirrorBot.bot_username, MirrorBot.owner_user_id)
        .outerjoin(MirrorBot, User.mirror_bot_id == MirrorBot.id)
        .where(User.user_id == user_id)
    )
    user_row = user_result.first()

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    user, bot_username, bot_owner_user_id = user_row

    transactions_total = int(await db.scalar(select(func.count(Transaction.id)).where(Transaction.user_id == user_id)) or 0)
    transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .limit(100)
    )
    transactions = list(transactions_result.scalars().all())

    order_stats_result = await db.execute(
        select(
            func.count(Order.id).label("total"),
            func.sum(case((Order.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Order.status == "pending", 1), else_=0)).label("pending"),
            func.sum(case((Order.status == "processing", 1), else_=0)).label("processing"),
            func.coalesce(func.sum(Order.price), 0).label("spent_total"),
        ).where(Order.user_id == user_id)
    )
    order_stats = order_stats_result.first()

    product_stats_result = await db.execute(
        select(
            func.count(ProductPurchase.id).label("total"),
            func.coalesce(func.sum(Product.price), 0).label("spent_total"),
        )
        .select_from(ProductPurchase)
        .outerjoin(Product, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.user_id == user_id)
    )
    product_stats = product_stats_result.first()

    seller_order_stats_result = await db.execute(
        select(
            func.count(SellerOrder.id).label("total"),
            func.coalesce(func.sum(SellerOrder.price_for_buyer), 0).label("spent_total"),
        ).where(SellerOrder.buyer_user_id == user_id)
    )
    seller_order_stats = seller_order_stats_result.first()

    seller_cc_stats_result = await db.execute(
        select(
            func.count(SellerCCOrder.id).label("total"),
            func.coalesce(func.sum(SellerCCOrder.price_for_buyer), 0).label("spent_total"),
        ).where(SellerCCOrder.buyer_user_id == user_id)
    )
    seller_cc_stats = seller_cc_stats_result.first()

    brute_order_stats_result = await db.execute(
        select(
            func.count(BruteBankOrder.id).label("total"),
            func.coalesce(func.sum(BruteBankOrder.price_for_buyer), 0).label("spent_total"),
        ).where(BruteBankOrder.buyer_user_id == user_id)
    )
    brute_order_stats = brute_order_stats_result.first()
    finance_visible = can_view_finances(current_user)

    orders_result = await db.execute(
        select(Order)
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(50)
    )
    orders = list(orders_result.scalars().all())

    product_purchases_result = await db.execute(
        select(ProductPurchase, Product)
        .outerjoin(Product, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.user_id == user_id)
        .order_by(ProductPurchase.purchased_at.desc(), ProductPurchase.id.desc())
        .limit(50)
    )
    product_purchase_rows = product_purchases_result.all()

    seller_orders_result = await db.execute(
        select(SellerOrder, SellerBank)
        .outerjoin(SellerBank, SellerOrder.seller_bank_id == SellerBank.id)
        .where(SellerOrder.buyer_user_id == user_id)
        .order_by(SellerOrder.created_at.desc(), SellerOrder.id.desc())
        .limit(50)
    )
    seller_order_rows = seller_orders_result.all()

    seller_cc_orders_result = await db.execute(
        select(SellerCCOrder, SellerCCItem)
        .outerjoin(SellerCCItem, SellerCCOrder.seller_cc_item_id == SellerCCItem.id)
        .where(SellerCCOrder.buyer_user_id == user_id)
        .order_by(SellerCCOrder.created_at.desc(), SellerCCOrder.id.desc())
        .limit(50)
    )
    seller_cc_order_rows = seller_cc_orders_result.all()

    brute_orders_result = await db.execute(
        select(BruteBankOrder, BruteBankItem)
        .outerjoin(BruteBankItem, BruteBankOrder.brute_bank_item_id == BruteBankItem.id)
        .where(BruteBankOrder.buyer_user_id == user_id)
        .order_by(BruteBankOrder.created_at.desc(), BruteBankOrder.id.desc())
        .limit(50)
    )
    brute_order_rows = brute_orders_result.all()

    support_tickets_total = int(await db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.user_id == user_id)) or 0)
    support_tickets_result = await db.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == user_id)
        .order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())
        .limit(50)
    )
    support_tickets = list(support_tickets_result.scalars().all())

    seller_profile = await db.scalar(select(Seller).where(Seller.telegram_id == user.user_id))
    seller_sales: List[dict] = []
    seller_sales_total = 0
    if seller_profile:
        seller_sales_total = int(
            (await db.scalar(select(func.count(SellerOrder.id)).where(SellerOrder.seller_id == seller_profile.id)) or 0)
            + (await db.scalar(select(func.count(SellerCCOrder.id)).where(SellerCCOrder.seller_id == seller_profile.id)) or 0)
            + (await db.scalar(select(func.count(BruteBankOrder.id)).where(BruteBankOrder.seller_id == seller_profile.id)) or 0)
        )
        seller_bank_sales_result = await db.execute(
            select(SellerOrder, SellerBank)
            .outerjoin(SellerBank, SellerOrder.seller_bank_id == SellerBank.id)
            .where(SellerOrder.seller_id == seller_profile.id)
            .order_by(SellerOrder.created_at.desc(), SellerOrder.id.desc())
            .limit(50)
        )
        for sale, bank in seller_bank_sales_result.all():
            seller_sales.append(
                {
                    "source": "seller_bank",
                    "sale_id": sale.id,
                    "title": bank.bank_name if bank else f"Seller bank #{sale.seller_bank_id}",
                    "subtitle": bank.bank_code if bank else None,
                    "status": sale.status,
                    "buyer_user_id": sale.buyer_user_id,
                "amount": _decimal_to_float(sale.price_for_buyer) if finance_visible else None,
                    "created_at": sale.created_at,
                    "completed_at": sale.completed_at,
                }
            )
        seller_cc_sales_result = await db.execute(
            select(SellerCCOrder, SellerCCItem)
            .outerjoin(SellerCCItem, SellerCCOrder.seller_cc_item_id == SellerCCItem.id)
            .where(SellerCCOrder.seller_id == seller_profile.id)
            .order_by(SellerCCOrder.created_at.desc(), SellerCCOrder.id.desc())
            .limit(50)
        )
        for sale, item in seller_cc_sales_result.all():
            seller_sales.append(
                {
                    "source": "seller_cc",
                    "sale_id": sale.id,
                    "title": item.item_name if item else f"Seller CC #{sale.seller_cc_item_id}",
                    "subtitle": item.cc_code if item else None,
                    "status": sale.status,
                    "buyer_user_id": sale.buyer_user_id,
                    "amount": _decimal_to_float(sale.price_for_buyer) if finance_visible else None,
                    "created_at": sale.created_at,
                    "completed_at": sale.completed_at,
                }
            )
        brute_sales_result = await db.execute(
            select(BruteBankOrder, BruteBankItem)
            .outerjoin(BruteBankItem, BruteBankOrder.brute_bank_item_id == BruteBankItem.id)
            .where(BruteBankOrder.seller_id == seller_profile.id)
            .order_by(BruteBankOrder.created_at.desc(), BruteBankOrder.id.desc())
            .limit(50)
        )
        for sale, item in brute_sales_result.all():
            seller_sales.append(
                {
                    "source": "brute_bank",
                    "sale_id": sale.id,
                    "title": item.bank_name if item else f"Brute bank #{sale.brute_bank_item_id}",
                    "subtitle": item.bank_code if item else None,
                    "status": sale.status,
                    "buyer_user_id": sale.buyer_user_id,
                    "amount": _decimal_to_float(sale.price_for_buyer) if finance_visible else None,
                    "created_at": sale.created_at,
                    "completed_at": sale.delivered_at,
                }
            )
        seller_sales.sort(
            key=lambda item: (item["created_at"] or datetime.min, item["sale_id"]),
            reverse=True,
        )

    marketplace_purchases: List[dict] = []

    for seller_order, seller_bank in seller_order_rows:
        marketplace_purchases.append(
            {
                "source": "seller_bank",
                "purchase_id": seller_order.id,
                "title": seller_bank.bank_name if seller_bank else f"Seller bank #{seller_order.seller_bank_id}",
                "subtitle": seller_bank.bank_code if seller_bank else None,
                "status": seller_order.status,
                "price_for_buyer": _decimal_to_float(seller_order.price_for_buyer) if finance_visible else None,
                "price_for_seller": _decimal_to_float(seller_order.price_for_seller) if finance_visible else None,
                "quantity": seller_order.quantity,
                "seller_id": seller_order.seller_id,
                "mirror_bot_id": seller_order.mirror_bot_id,
                "created_at": seller_order.created_at,
                "completed_at": seller_order.completed_at,
            }
        )

    for seller_cc_order, seller_cc_item in seller_cc_order_rows:
        marketplace_purchases.append(
            {
                "source": "seller_cc",
                "purchase_id": seller_cc_order.id,
                "title": seller_cc_item.item_name if seller_cc_item else f"Seller CC #{seller_cc_order.seller_cc_item_id}",
                "subtitle": seller_cc_item.cc_code if seller_cc_item else None,
                "status": seller_cc_order.status,
                "price_for_buyer": _decimal_to_float(seller_cc_order.price_for_buyer) if finance_visible else None,
                "price_for_seller": _decimal_to_float(seller_cc_order.price_for_seller) if finance_visible else None,
                "quantity": seller_cc_order.quantity,
                "seller_id": seller_cc_order.seller_id,
                "mirror_bot_id": seller_cc_order.mirror_bot_id,
                "created_at": seller_cc_order.created_at,
                "completed_at": seller_cc_order.completed_at,
            }
        )

    for brute_order, brute_item in brute_order_rows:
        marketplace_purchases.append(
            {
                "source": "brute_bank",
                "purchase_id": brute_order.id,
                "title": brute_item.bank_name if brute_item else f"Brute bank #{brute_order.brute_bank_item_id}",
                "subtitle": brute_item.bank_code if brute_item else None,
                "status": brute_order.status,
                "price_for_buyer": _decimal_to_float(brute_order.price_for_buyer) if finance_visible else None,
                "price_for_seller": _decimal_to_float(brute_order.price_for_seller) if finance_visible else None,
                "quantity": 1,
                "seller_id": brute_order.seller_id,
                "mirror_bot_id": brute_order.mirror_bot_id,
                "created_at": brute_order.created_at,
                "completed_at": brute_order.delivered_at,
            }
        )

    marketplace_purchases.sort(
        key=lambda item: (item["created_at"] or datetime.min, item["purchase_id"]),
        reverse=True,
    )

    marketplace_total = (
        int(seller_order_stats.total or 0)
        + int(seller_cc_stats.total or 0)
        + int(brute_order_stats.total or 0)
    )
    marketplace_spent_total = (
        Decimal(str(seller_order_stats.spent_total or 0))
        + Decimal(str(seller_cc_stats.spent_total or 0))
        + Decimal(str(brute_order_stats.spent_total or 0))
    )

    return {
        "user": {
            "id": user.id,
            "user_id": user.user_id,
            "username": user.username,
            "mirror_bot_id": user.mirror_bot_id,
            "bot_username": bot_username,
            "bot_owner_user_id": bot_owner_user_id,
            "language": user.language,
            "trust_score": user.trust_score,
            "last_active_at": user.last_active_at,
            "balance": _decimal_to_float(user.balance) if finance_visible else None,
            "referrer_id": user.referrer_id,
            "referral_link": user.referral_link,
            "is_banned": user.is_banned,
            "ban_reason": user.ban_reason,
            "rules_accepted": user.rules_accepted,
            "created_at": user.created_at,
        },
        "summary": UserDetailSummary(
            transactions_total=transactions_total if finance_visible else 0,
            orders_total=int(order_stats.total or 0),
            orders_completed=int(order_stats.completed or 0),
            orders_pending=int(order_stats.pending or 0),
            orders_processing=int(order_stats.processing or 0),
            order_spent_total=_decimal_to_float(order_stats.spent_total) if finance_visible else 0.0,
            product_purchases_total=int(product_stats.total or 0),
            product_spent_total=_decimal_to_float(product_stats.spent_total) if finance_visible else 0.0,
            marketplace_purchases_total=marketplace_total,
            marketplace_spent_total=_decimal_to_float(marketplace_spent_total) if finance_visible else 0.0,
            seller_sales_total=seller_sales_total,
            support_tickets_total=support_tickets_total,
        ).model_dump(),
        "balance_history": _build_balance_history(transactions, user.balance) if finance_visible else [],
        "orders": [
            {
                "id": order.id,
                "category": order.category,
                "service_name": order.service_name,
                "price": _decimal_to_float(order.price) if finance_visible else None,
                "status": order.status,
                "is_bulk": order.is_bulk,
                "bulk_count": order.bulk_count,
                "worker_id": order.worker_id,
                "created_at": order.created_at,
                "completed_at": order.completed_at,
            }
            for order in orders
        ],
        "product_purchases": [
            {
                "purchase_id": purchase.id,
                "product_id": purchase.product_id,
                "name": product.name if product else f"Product #{purchase.product_id}",
                "category": product.category if product else None,
                "service": product.service if product else None,
                "state": product.state if product else None,
                "file_type": product.file_type if product else None,
                "price": _decimal_to_float(product.price if product else 0) if finance_visible else None,
                "purchased_at": purchase.purchased_at,
                "delivered_at": purchase.delivered_at,
                "file_deleted_at": purchase.file_deleted_at,
            }
            for purchase, product in product_purchase_rows
        ],
        "marketplace_purchases": marketplace_purchases,
        "seller_sales": seller_sales,
        "support_tickets": [
            {
                "id": ticket.id,
                "category": ticket.category,
                "subject": ticket.subject,
                "status": ticket.status,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "closed_at": ticket.closed_at,
            }
            for ticket in support_tickets
        ],
        "access": {
            "can_view_finances": finance_visible,
            "can_edit": can_edit_crm(current_user),
            "can_ban": can_ban_users(current_user),
        },
    }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Обновить пользователя"""
    _ensure_crm_edit(current_user)
    
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    ban_changed = False
    old_banned = user.is_banned
    
    # Обновляем поля
    if data.balance is not None:
        raise HTTPException(
            status_code=400,
            detail="Direct balance overwrite is disabled. Use /balance endpoint with a reason."
        )
    
    if data.is_banned is not None:
        if data.is_banned != user.is_banned:
            ban_changed = True
        user.is_banned = data.is_banned
        if not data.is_banned:
            user.ban_reason = None
        
    if data.ban_reason is not None:
        user.ban_reason = data.ban_reason
    
    admin_id = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    if ban_changed:
        await log_action(
            db,
            admin_id,
            "user_ban" if user.is_banned else "user_unban",
            "user",
            user_id,
            {
                "reason": user.ban_reason,
                "old_is_banned": old_banned,
                "new_is_banned": user.is_banned,
                "actor_role": current_user.get("role"),
            },
            ip_address,
        )
    
    await db.commit()
    await db.refresh(user)
    
    # Уведомляем пользователя и админов при смене статуса бана
    if ban_changed:
        try:
            await bot_integration.notify_user_ban(
                user_id=user_id,
                is_banned=user.is_banned,
                reason=user.ban_reason,
                mirror_bot_id=user.mirror_bot_id
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to notify user about ban: {e}")
        
        try:
            from shared.services.admin_notification_service import AdminNotificationService
            await AdminNotificationService.notify_user_banned(
                user_id=user_id,
                is_banned=user.is_banned,
                reason=user.ban_reason or "",
                admin_username=current_user.get("username", "web_panel")
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to send admin notification: {e}")
    
    return {
        "message": "User updated successfully",
        "user_id": user_id,
        "balance": float(user.balance),
        "is_banned": user.is_banned
    }


@router.post("/{user_id}/balance")
async def update_user_balance(
    user_id: int,
    data: UserUpdateBalance,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Изменить баланс пользователя"""
    _ensure_finance_access(current_user)
    
    reason = (data.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Reason is required")
    if data.amount == 0:
        raise HTTPException(status_code=400, detail="Amount must not be zero")

    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_balance = user.balance
    amount_decimal = Decimal(str(data.amount))
    transaction = await LedgerService.credit_user_balance(
        db,
        user_id=user_id,
        amount=amount_decimal,
        tx_type="admin_adjustment",
        description=f"Admin adjustment: {reason}",
        related_entity_type="admin_adjustment",
        related_entity_id=user_id,
    )
    admin_id = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(
        db,
        admin_id,
        "user_balance_update",
        "user",
        user_id,
        {
            "amount": data.amount,
            "reason": reason,
            "old_balance": float(old_balance),
            "new_balance": float(user.balance),
            "actor_role": current_user.get("role"),
        },
        ip_address,
    )
    await db.commit()
    await db.refresh(user)
    
    # Уведомляем пользователя через бота
    try:
        await bot_integration.notify_user_balance_update(
            user_id=user_id,
            amount=data.amount,
            reason=reason,
            mirror_bot_id=user.mirror_bot_id
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to notify user about balance update: {e}")
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_balance_update(
            user_id=user_id,
            amount=data.amount,
            reason=reason,
            admin_username=current_user.get("username", "web_panel")
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to send admin notification: {e}")
    
    return {
        "message": "Balance updated successfully",
        "old_balance": float(old_balance),
        "new_balance": float(user.balance),
        "change": data.amount
    }


@router.post("/{user_id}/ban")
async def ban_user(
    user_id: int,
    data: UserBanRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Забанить/разбанить пользователя"""
    _ensure_ban_access(current_user)
    
    reason = (data.reason or "").strip() if data.reason else None
    if data.is_banned and not reason:
        raise HTTPException(status_code=400, detail="Reason is required when banning a user")

    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_banned = data.is_banned
    user.ban_reason = reason if data.is_banned else None
    
    admin_id = current_user.get("admin_id")
    ip_address = request.client.host if request.client else None
    await log_action(
        db,
        admin_id,
        "user_ban" if data.is_banned else "user_unban",
        "user",
        user_id,
        {
            "reason": reason,
            "new_is_banned": data.is_banned,
            "actor_role": current_user.get("role"),
        },
        ip_address,
    )
    await db.commit()
    
    # Уведомляем пользователя через бота
    try:
        await bot_integration.notify_user_ban(
            user_id=user_id,
            is_banned=data.is_banned,
            reason=reason,
            mirror_bot_id=user.mirror_bot_id
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to notify user about ban status: {e}")
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_user_banned(
            user_id=user_id,
            is_banned=data.is_banned,
            reason=reason or "",
            admin_username=current_user.get("username", "web_panel")
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to send admin notification: {e}")
    
    return {
        "message": f"User {'banned' if data.is_banned else 'unbanned'} successfully",
        "reason": reason,
        "user_id": user_id,
        "is_banned": user.is_banned
    }


@router.post("/{user_id}/send-message")
async def send_message_to_user(
    user_id: int,
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Отправить сообщение пользователю через его бота с поддержкой файлов"""
    _ensure_crm_edit(current_user)
    
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем mirror bot пользователя
    bot_result = await db.execute(
        select(MirrorBot).where(MirrorBot.id == user.mirror_bot_id)
    )
    mirror_bot = bot_result.scalar_one_or_none()
    
    if not mirror_bot:
        raise HTTPException(status_code=404, detail="Mirror bot not found")
    
    temp_file_path = None
    
    try:
        # Получаем мультиязычный префикс для пользователя
        admin_prefix = await get_user_admin_message_prefix(db, user_id, user.mirror_bot_id)

        # Экранируем пользовательский текст чтобы предотвратить HTML-инъекцию
        safe_message = html.escape(message)

        # Отправляем через Mirror Bot пользователя
        bot = Bot(token=mirror_bot.bot_token)

        # Если есть файл, сохраняем его временно
        if file and file.size > 0:
            # Создаем временную директорию если её нет
            temp_dir = "/tmp/admin_messages"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Генерируем уникальное имя файла
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
            temp_filename = f"{uuid.uuid4()}{file_extension}"
            temp_file_path = os.path.join(temp_dir, temp_filename)
            
            # Сохраняем файл
            async with aiofiles.open(temp_file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Определяем тип файла
            content_type = file.content_type or ""
            
            # Отправляем сообщение с файлом
            if content_type.startswith('image/'):
                await bot.send_photo(
                    chat_id=user_id,
                    photo=FSInputFile(temp_file_path),
                    caption=f"{admin_prefix}{safe_message}",
                    parse_mode="HTML"
                )
            elif content_type.startswith('video/'):
                await bot.send_video(
                    chat_id=user_id,
                    video=FSInputFile(temp_file_path),
                    caption=f"{admin_prefix}{safe_message}",
                    parse_mode="HTML"
                )
            else:
                await bot.send_document(
                    chat_id=user_id,
                    document=FSInputFile(temp_file_path),
                    caption=f"{admin_prefix}{safe_message}",
                    parse_mode="HTML"
                )
        else:
            await bot.send_message(
                chat_id=user_id,
                text=f"{admin_prefix}{safe_message}",
                parse_mode="HTML"
            )
        
        await bot.session.close()
        
        return {
            "message": "Message sent successfully",
            "user_id": user_id,
            "via_bot": mirror_bot.id,
            "bot_username": mirror_bot.bot_username,
            "has_file": file is not None and file.size > 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
    
    finally:
        # Удаляем временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error("Failed to delete temp file %s: %s", temp_file_path, e)


class CrossBotMessageRequest(BaseModel):
    message: str
    preferred_bot_id: Optional[int] = None


@router.post("/{user_id}/send-message-any-bot")
async def send_message_via_any_bot(
    user_id: int,
    data: CrossBotMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Отправить сообщение пользователю через любой доступный бот"""
    _ensure_crm_edit(current_user)
    
    # Получаем всех активных ботов
    stmt = select(MirrorBot).where(MirrorBot.is_active == True).order_by(MirrorBot.id)
    result = await db.execute(stmt)
    available_bots = result.scalars().all()
    
    if not available_bots:
        raise HTTPException(status_code=404, detail="No active bots available")
    
    # Если указан предпочтительный бот, пробуем его первым
    bots_to_try = []
    if data.preferred_bot_id:
        preferred_bot = next((bot for bot in available_bots if bot.id == data.preferred_bot_id), None)
        if preferred_bot:
            bots_to_try.append(preferred_bot)
            bots_to_try.extend([bot for bot in available_bots if bot.id != data.preferred_bot_id])
        else:
            bots_to_try = available_bots
    else:
        bots_to_try = available_bots
    
    last_error = None
    
    # Пробуем отправить через каждый бот
    for mirror_bot in bots_to_try:
        try:
            bot = Bot(token=mirror_bot.bot_token)
            
            await bot.send_message(
                chat_id=user_id,
                text=f"📢 <b>Message from Admin:</b>\n\n{data.message}",
                parse_mode="HTML"
            )
            
            await bot.session.close()
            
            return {
                "message": "Message sent successfully",
                "user_id": user_id,
                "via_bot": mirror_bot.id,
                "bot_username": mirror_bot.bot_username,
                "attempts": bots_to_try.index(mirror_bot) + 1
            }
        
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Failed to send message via bot {mirror_bot.id}: {e}")
            try:
                await bot.session.close()
            except Exception as close_error:
                logger.debug(f"Error closing bot session: {close_error}")
            continue
    
    # Если не удалось отправить ни через один бот
    raise HTTPException(
        status_code=500, 
        detail=f"Failed to send message via any bot. Last error: {last_error}"
    )


@router.get("/{user_id}/orders")
async def get_user_orders(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Получить заказы пользователя"""
    _ensure_crm_view(current_user)
    
    stmt = select(Order).where(Order.user_id == user_id)
    
    if status:
        stmt = stmt.where(Order.status == status)
    
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    return [
        {
            "id": order.id,
            "category": order.category,
            "service_name": order.service_name,
            "price": float(order.price),
            "status": order.status,
            "created_at": order.created_at,
            "completed_at": order.completed_at
        }
        for order in orders
    ]


@router.get("/{user_id}/stats")
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Получить статистику пользователя"""
    _ensure_crm_view(current_user)
    
    stmt = select(User).where(User.user_id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Подсчитываем заказы
    stmt = select(
        func.count(Order.id).label("total_orders"),
        func.sum(func.case((Order.status == "completed", 1), else_=0)).label("completed"),
        func.sum(func.case((Order.status == "pending", 1), else_=0)).label("pending"),
        func.sum(func.case((Order.status == "processing", 1), else_=0)).label("processing"),
        func.sum(Order.price).label("total_spent")
    ).where(Order.user_id == user_id)
    
    result = await db.execute(stmt)
    stats = result.first()
    
    return {
        "user_id": user_id,
        "balance": float(user.balance) if can_view_finances(current_user) else None,
        "total_orders": stats.total_orders or 0,
        "completed_orders": stats.completed or 0,
        "pending_orders": stats.pending or 0,
        "processing_orders": stats.processing or 0,
        "total_spent": float(stats.total_spent or 0) if can_view_finances(current_user) else None,
        "created_at": user.created_at
    }


@router.get("/search/{user_id}")
async def search_user_across_bots(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("users"))
):
    """Найти пользователя во всех ботах системы"""
    _ensure_crm_view(current_user)
    
    # Ищем пользователя во всех ботах
    stmt = select(User, MirrorBot).join(
        MirrorBot, User.mirror_bot_id == MirrorBot.id
    ).where(User.user_id == user_id)
    
    result = await db.execute(stmt)
    user_bot_pairs = result.all()
    
    if not user_bot_pairs:
        raise HTTPException(status_code=404, detail="User not found in any bot")
    
    # Получаем статистику заказов
    stmt = select(
        func.count(Order.id).label("total_orders"),
        func.sum(func.case((Order.status == "completed", 1), else_=0)).label("completed"),
        func.sum(Order.price).label("total_spent")
    ).where(Order.user_id == user_id)
    
    result = await db.execute(stmt)
    stats = result.first()
    
    # Получаем всех активных ботов для отправки сообщений
    stmt = select(MirrorBot).where(MirrorBot.is_active == True)
    result = await db.execute(stmt)
    available_bots = result.scalars().all()
    
    finance_visible = can_view_finances(current_user)
    user_data = []
    for user_record, mirror_bot in user_bot_pairs:
        user_data.append({
            "user_id": user_record.user_id,
            "username": user_record.username,
            "mirror_bot_id": mirror_bot.id,
            "bot_username": mirror_bot.bot_username,
            "bot_owner": mirror_bot.owner_user_id,
            "balance": float(user_record.balance) if finance_visible else None,
            "is_banned": user_record.is_banned,
            "ban_reason": user_record.ban_reason,
            "language": user_record.language,
            "trust_score": user_record.trust_score,
            "last_active_at": user_record.last_active_at,
            "created_at": user_record.created_at
        })
    
    return {
        "user_id": user_id,
        "found_in_bots": user_data,
        "total_orders": stats.total_orders or 0,
        "completed_orders": stats.completed or 0,
        "total_spent": float(stats.total_spent or 0) if finance_visible else None,
        "available_bots_for_contact": [
            {
                "id": bot.id,
                "username": bot.bot_username,
                "owner": bot.owner_user_id,
                "is_active": bot.is_active
            }
            for bot in available_bots
        ]
    }

