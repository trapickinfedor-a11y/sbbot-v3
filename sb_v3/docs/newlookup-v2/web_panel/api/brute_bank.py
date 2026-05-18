from __future__ import annotations

"""
API for Brute Bank groups, variants and item moderation.
"""

import logging
import os
from datetime import datetim, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.brute_bank_group_key import make_brute_group_key
from shared.database.models import BruteBankGroup, BruteBankItem, Seller
from shared.services.moderation_pricing_service import apply_brute_markup
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter()
logger = logging.getLogger(__name__)

SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]


class BruteGroupCreate(BaseModel):
    bank_code: str
    bank_name: str
    category: str = "general"
    attributes: Optional[str] = None
    position: int = 0
    is_active: bool = True


class BruteGroupUpdate(BaseModel):
    bank_name: Optional[str] = None
    category: Optional[str] = None
    attributes: Optional[str] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


class BruteItemUpdate(BaseModel):
    group_id: Optional[int] = None
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    category: Optional[str] = None
    balance_info: Optional[str] = None
    balance_range: Optional[str] = None
    account_type: Optional[str] = None
    account_details: Optional[str] = None
    price: Optional[float] = None
    is_active: Optional[bool] = None


class ModerationAction(BaseModel):
    comment: Optional[str] = None


async def _find_matching_group(db: AsyncSession, bank_code: str, category: Optional[str] = None) -> Optional[BruteBankGroup]:
    gkey = make_brute_group_key(bank_code, None)
    result = await db.execute(
        select(BruteBankGroup).where(
            BruteBankGroup.group_key == gkey,
        )
    )
    return result.scalar_one_or_none()


@router.get("/api/brute-bank/stats")
async def brute_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_read_access("brute_bank")),
):
    pending_q = await db.execute(select(func.count()).where(BruteBankItem.moderation_status == "pending"))
    available_q = await db.execute(select(func.count()).where(
        BruteBankItem.moderation_status == "approved",
        BruteBankItem.status == "available",
        BruteBankItem.is_active == True,
    ))
    sold_q = await db.execute(select(func.count()).where(BruteBankItem.status == "sold"))
    total_q = await db.execute(select(func.count()).select_from(BruteBankItem))
    groups_q = await db.execute(select(func.count()).select_from(BruteBankGroup).where(BruteBankGroup.is_active == True))
    return {
        "pending_moderation": pending_q.scalar() or 0,
        "available": available_q.scalar() or 0,
        "sold": sold_q.scalar() or 0,
        "total": total_q.scalar() or 0,
        "active_groups": groups_q.scalar() or 0,
    }


@router.get("/api/brute-bank/groups")
async def list_brute_groups(
    category: Optional[str] = None,
    active_only: bool = False,
    include_empty: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_read_access("brute_bank")),
):
    stmt = select(BruteBankGroup).order_by(BruteBankGroup.position, BruteBankGroup.bank_name)
    if category:
        stmt = stmt.where(BruteBankGroup.category == category)
    if active_only:
        stmt = stmt.where(BruteBankGroup.is_active == True)
    result = await db.execute(stmt)
    groups = result.scalars().all()

    items = []
    for group in groups:
        available_q = await db.execute(select(func.count()).where(
            BruteBankItem.group_id == group.id,
            BruteBankItem.moderation_status == "approved",
            BruteBankItem.status == "available",
            BruteBankItem.is_active == True,
        ))
        variants_q = await db.execute(select(func.count()).select_from(
            select(
                BruteBankItem.balance_range,
                BruteBankItem.account_type,
                BruteBankItem.price,
            ).where(
                BruteBankItem.group_id == group.id,
                BruteBankItem.moderation_status == "approved",
                BruteBankItem.status == "available",
                BruteBankItem.is_active == True,
            ).group_by(
                BruteBankItem.balance_range,
                BruteBankItem.account_type,
                BruteBankItem.price,
            ).subquery()
        ))
        available_count = int(available_q.scalar() or 0)
        if not include_empty and available_count <= 0:
            continue
        items.append({
            "id": group.id,
            "bank_code": group.bank_code,
            "bank_name": group.bank_name,
            "category": group.category,
            "attributes": group.attributes,
            "position": group.position,
            "is_active": group.is_active,
            "available_count": available_count,
            "variants_count": int(variants_q.scalar() or 0),
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        })
    return items


@router.post("/api/brute-bank/groups")
async def create_brute_group(
    data: BruteGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    payload = data.model_dump()
    payload["group_key"] = make_brute_group_key(payload["bank_code"], payload.get("attributes"))
    existing = await db.execute(select(BruteBankGroup).where(BruteBankGroup.group_key == payload["group_key"]))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Group with this bank code and attributes already exists")
    group = BruteBankGroup(**payload)
    db.add(group)
    await db.flush()
    items_q = await db.execute(select(BruteBankItem).where(
        BruteBankItem.group_id == None,
        BruteBankItem.bank_code == data.bank_code,
    ))
    for item in items_q.scalars().all():
        item.group_id = group.id
        item.bank_name = data.bank_name
        item.category = data.category
    await db.commit()
    await db.refresh(group)
    return {"id": group.id, "bank_code": group.bank_code}


@router.put("/api/brute-bank/groups/{group_id}")
async def update_brute_group(
    group_id: int,
    data: BruteGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    result = await db.execute(select(BruteBankGroup).where(BruteBankGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    previous_name = group.bank_name
    previous_category = group.category
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(group, key, value)
    if (data.bank_name is not None and data.bank_name != previous_name) or (data.category is not None and data.category != previous_category):
        linked = await db.execute(select(BruteBankItem).where(BruteBankItem.group_id == group.id))
        for item in linked.scalars().all():
            if data.bank_name is not None:
                item.bank_name = data.bank_name
            if data.category is not None:
                item.category = data.category
    await db.commit()
    return {"ok": True}


@router.delete("/api/brute-bank/groups/{group_id}")
async def delete_brute_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    result = await db.execute(select(BruteBankGroup).where(BruteBankGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    linked = await db.execute(select(BruteBankItem).where(BruteBankItem.group_id == group.id))
    for item in linked.scalars().all():
        item.group_id = None
    await db.delete(group)
    await db.commit()
    return {"ok": True}


@router.get("/api/brute-bank/groups/{group_id}/variants")
async def get_group_variants(
    group_id: int,
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_read_access("brute_bank")),
):
    result = await db.execute(select(BruteBankGroup).where(BruteBankGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    stmt = select(
        BruteBankItem.balance_range,
        BruteBankItem.account_type,
        BruteBankItem.price,
        func.count(BruteBankItem.id).label("quantity"),
        func.max(BruteBankItem.balance_info).label("balance_info"),
    ).where(BruteBankItem.group_id == group_id)
    if available_only:
        stmt = stmt.where(
            BruteBankItem.moderation_status == "approved",
            BruteBankItem.status == "available",
            BruteBankItem.is_active == True,
        )
    stmt = stmt.group_by(
        BruteBankItem.balance_range,
        BruteBankItem.account_type,
        BruteBankItem.price,
    ).order_by(BruteBankItem.price, BruteBankItem.balance_range, BruteBankItem.account_type)

    variant_rows = (await db.execute(stmt)).all()
    return {
        "group": {
            "id": group.id,
            "bank_code": group.bank_code,
            "bank_name": group.bank_name,
            "category": group.category,
            "attributes": group.attributes,
        },
        "variants": [
            {
                "balance_range": row.balance_range,
                "account_type": row.account_type,
                "price": float(row.price),
                "quantity": int(row.quantity or 0),
                "balance_info": row.balance_info,
            }
            for row in variant_rows
            if int(row.quantity or 0) > 0
        ],
    }


@router.get("/api/brute-bank/items")
async def list_brute_items(
    moderation_status: Optional[str] = Query(None, description="pending | approved | rejected"),
    status: Optional[str] = Query(None, description="available | sold | removed"),
    category: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_read_access("brute_bank")),
):
    filters = []
    if moderation_status:
        filters.append(BruteBankItem.moderation_status == moderation_status)
    if status:
        filters.append(BruteBankItem.status == status)
    if category:
        filters.append(BruteBankItem.category == category)
    if seller_id is not None:
        filters.append(BruteBankItem.seller_id == seller_id)
    if group_id is not None:
        filters.append(BruteBankItem.group_id == group_id)

    q = select(BruteBankItem, BruteBankGroup).outerjoin(BruteBankGroup, BruteBankItem.group_id == BruteBankGroup.id)
    if filters:
        q = q.where(*filters)
    q = q.order_by(desc(BruteBankItem.created_at)).limit(limit).offset(offset)
    rows = (await db.execute(q)).all()

    total_q = select(func.count()).select_from(BruteBankItem)
    if filters:
        total_q = total_q.where(*filters)
    total = (await db.execute(total_q)).scalar() or 0

    return {
        "total": total,
        "items": [
            {
                "id": item.id,
                "group_id": item.group_id,
                "group_name": group.bank_name if group else None,
                "group_attributes": group.attributes if group else None,
                "seller_id": item.seller_id,
                "upload_batch_id": item.upload_batch_id,
                "bank_name": item.bank_name,
                "bank_code": item.bank_code,
                "category": item.category,
                "balance_info": item.balance_info,
                "balance_range": item.balance_range,
                "account_type": item.account_type,
                "account_details": item.account_details,
                "price": float(item.price),
                "moderation_status": item.moderation_status,
                "moderation_comment": item.moderation_comment,
                "status": item.status,
                "buyer_user_id": item.buyer_user_id,
                "is_active": item.is_active,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "approved_at": item.approved_at.isoformat() if item.approved_at else None,
                "sold_at": item.sold_at.isoformat() if item.sold_at else None,
            }
            for item, group in rows
        ],
    }


@router.get("/api/brute-bank/items/{item_id}")
async def get_brute_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_read_access("brute_bank")),
):
    result = await db.execute(
        select(BruteBankItem, BruteBankGroup)
        .outerjoin(BruteBankGroup, BruteBankItem.group_id == BruteBankGroup.id)
        .where(BruteBankItem.id == item_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    item, group = row
    return {
        "id": item.id,
        "group_id": item.group_id,
        "group_name": group.bank_name if group else None,
        "group_attributes": group.attributes if group else None,
        "seller_id": item.seller_id,
        "upload_batch_id": item.upload_batch_id,
        "bank_name": item.bank_name,
        "bank_code": item.bank_code,
        "category": item.category,
        "credentials": item.credentials,
        "balance_info": item.balance_info,
        "balance_range": item.balance_range,
        "account_type": item.account_type,
        "account_details": item.account_details,
        "price": float(item.price),
        "moderation_status": item.moderation_status,
        "moderation_comment": item.moderation_comment,
        "moderated_by": item.moderated_by,
        "status": item.status,
        "buyer_user_id": item.buyer_user_id,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "sold_at": item.sold_at.isoformat() if item.sold_at else None,
    }


@router.put("/api/brute-bank/items/{item_id}")
async def update_brute_item(
    item_id: int,
    data: BruteItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    result = await db.execute(select(BruteBankItem).where(BruteBankItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    payload = data.model_dump(exclude_none=True)
    if "price" in payload:
        payload["price"] = Decimal(str(payload["price"]))
    for key, value in payload.items():
        setattr(item, key, value)

    if item.group_id is None:
        group = await _find_matching_group(db, item.bank_code)
        if group:
            item.group_id = group.id
            item.bank_name = group.bank_name
            item.category = group.category

    await db.commit()
    return {"ok": True}


@router.delete("/api/brute-bank/items/{item_id}")
async def delete_brute_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    result = await db.execute(select(BruteBankItem).where(BruteBankItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    item.is_active = False
    item.status = "removed"
    await db.commit()
    return {"ok": True}


@router.post("/api/brute-bank/items/{item_id}/approve")
async def approve_brute_item(
    item_id: int,
    request: Request,
    data: ModerationAction = ModerationAction(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    result = await db.execute(select(BruteBankItem).where(BruteBankItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    if item.group_id is None:
        group = await _find_matching_group(db, item.bank_code)
        if group:
            item.group_id = group.id
            item.bank_name = group.bank_name
            item.category = group.category

    rule = apply_brute_markup(item)
    item.moderation_status = "approved"
    item.status = "available"
    item.is_active = True
    item.moderation_comment = data.comment
    item.moderated_by = current_user.get("telegram_id") or current_user.get("admin_id")
    item.approved_at = datetime.now(timezone.utc)
    await log_action(
        db,
        current_user.get("admin_id"),
        "brute_bank_moderation_approve",
        "brute_bank_item",
        item.id,
        {
            "seller_id": item.seller_id,
            "bank_name": item.bank_name,
            "bank_code": item.bank_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "base_price": float(item.base_price or item.price or 0),
            "buyer_price": float(item.buyer_price or item.price or 0),
            "markup_code": rule.code,
            "moderation_status": item.moderation_status,
            "comment": data.comment,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request and request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, "brute")
    await _notify_seller(item, approved=True)
    return {"ok": True, "status": "approved", "buyer_price": float(item.buyer_price or item.price or 0), "markup_code": rule.code}


@router.post("/api/brute-bank/items/{item_id}/reject")
async def reject_brute_item(
    item_id: int,
    request: Request,
    data: ModerationAction = ModerationAction(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_catalog_write_access("brute_bank")),
):
    result = await db.execute(select(BruteBankItem).where(BruteBankItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    item.moderation_status = "rejected"
    item.status = "removed"
    item.is_active = False
    item.moderation_comment = data.comment
    item.moderated_by = current_user.get("telegram_id") or current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "brute_bank_moderation_reject",
        "brute_bank_item",
        item.id,
        {
            "seller_id": item.seller_id,
            "bank_name": item.bank_name,
            "bank_code": item.bank_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "moderation_status": item.moderation_status,
            "comment": data.comment,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request and request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, "brute")
    await _notify_seller(item, approved=False, comment=data.comment)
    return {"ok": True, "status": "rejected"}


async def _notify_seller(item: BruteBankItem, approved: bool, comment: str = None):
    """Notify seller via seller bot about moderation result."""
    try:
        from seller_bot.config import seller_bot_config
        if not seller_bot_config.bot_token:
            return

        from shared.database.session import async_session_maker
        async with async_session_maker() as session:
            result = await session.execute(select(Seller).where(Seller.id == item.seller_id))
            seller = result.scalar_one_or_none()
            if not seller:
                return

        from aiogram import Bot
        from aiogram.enums import ParseMode
        bot = Bot(token=seller_bot_config.bot_token)
        try:
            if approved:
                text = (
                    f"✅ *Your Brute Bank item was approved!*\n\n"
                    f"🏦 *Bank:* {item.bank_name}\n"
                    f"💰 *Price:* ${item.price:.2f}\n\n"
                    f"It is now visible to buyers."
                )
            else:
                text = (
                    f"❌ *Your Brute Bank item was rejected.*\n\n"
                    f"🏦 *Bank:* {item.bank_name}\n"
                    + (f"📝 *Reason:* {comment}\n" if comment else "")
                    + "\nPlease review and re-submit."
                )
            await bot.send_message(seller.telegram_id, text, parse_mode=ParseMode.MARKDOWN)
        finally:
            await bot.session.close()
    except Exception as exc:
        logger.error("Failed to notify seller about brute item moderation: %s", exc)
