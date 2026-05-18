from __future__ import annotations

"""
API for moderating SellerBank and SellerCCItem
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetim, timezone
from decimal import Decimal

from web_panel.database import get_db
from web_panel.auth import require_seller_moderation_access
from shared.database.models import (
    Seller,
    SellerBank,
    SellerCCItem,
    SellerCheckItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
    SellerEnrollItem,
    BruteBankItem,
    SellerLogsItem,
    SellerBankItem,
)
from shared.services.moderation_pricing_service import (
    MARKUP_RULES,
    apply_bank_markup,
    apply_cc_markup,
    apply_check_markup,
    apply_nfc_markup,
    apply_otp_markup,
    apply_selfreg_cc_markup,
)
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from web_panel.services.audit_service import log_action
router = APIRouter(prefix="/api/seller-moderation", tags=["seller-moderation"])


class PendingBankResponse(BaseModel):
    id: int
    upload_batch_id: Optional[int] = None
    bank_name: str
    bank_code: str
    category: str
    product_type: str
    product_subtype: str
    seller_price: Decimal
    base_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    buyer_price: Decimal
    markup_percent: Optional[float] = None
    markup_fixed: Optional[Decimal] = None
    markup_code: Optional[str] = None
    markup_kind: Optional[str] = None
    markup_value: Optional[Decimal] = None
    seller_name: str
    created_at: datetime
    moderation_status: str

    class Config:
        from_attributes = True


class PendingCCResponse(BaseModel):
    id: int
    upload_batch_id: Optional[int] = None
    item_name: str
    cc_code: str
    category_code: str
    product_type: str
    product_subtype: str
    seller_price: Decimal
    base_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    buyer_price: Decimal
    markup_percent: Optional[float] = None
    markup_fixed: Optional[Decimal] = None
    markup_code: Optional[str] = None
    markup_kind: Optional[str] = None
    markup_value: Optional[Decimal] = None
    seller_name: str
    created_at: datetime
    moderation_status: str

    class Config:
        from_attributes = True


class ModerationAction(BaseModel):
    action: str  # approve, reject


class ChangesRequestedBody(BaseModel):
    comment: str


class ApprovalBody(BaseModel):
    rule_code: Optional[str] = None
    base_price: Optional[Decimal] = None


def _seller_name(seller: Seller) -> str:
    return seller.display_name or seller.username or str(seller.telegram_id)


def _serialize_special_item(item, seller: Seller, *, summary: str) -> dict:
    return {
        "id": item.id,
        "upload_batch_id": getattr(item, "upload_batch_id", None),
        "item_name": getattr(item, "item_name", None) or getattr(item, "bank_name", None),
        "product_type": getattr(item, "product_type", ""),
        "product_subtype": getattr(item, "product_subtype", ""),
        "seller_price": float(getattr(item, "seller_price", 0) or 0),
        "base_price": float(getattr(item, "base_price", 0) or 0),
        "final_price": float(getattr(item, "final_price", getattr(item, "buyer_price", 0)) or 0),
        "buyer_price": float(getattr(item, "buyer_price", 0) or 0),
        "markup_percent": getattr(item, "markup_percent", None),
        "markup_fixed": float(getattr(item, "markup_fixed", 0) or 0) if getattr(item, "markup_fixed", None) is not None else None,
        "markup_code": getattr(item, "markup_code", None),
        "moderation_status": getattr(item, "moderation_status", ""),
        "seller_name": _seller_name(seller),
        "summary": summary,
        "created_at": item.created_at.isoformat() if getattr(item, "created_at", None) else None,
    }


@router.get("/banks", response_model=List[PendingBankResponse])
async def list_pending_banks(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    """List banks pending moderation"""
    result = await db.execute(
        select(SellerBank, Seller).join(Seller, SellerBank.seller_id == Seller.id).where(
            SellerBank.moderation_status == status,
            SellerBank.is_active == True
        ).order_by(SellerBank.created_at.desc()).limit(50)
    )
    rows = result.all()
    return [
        PendingBankResponse(
            id=b.id,
            upload_batch_id=getattr(b, "upload_batch_id", None),
            bank_name=b.bank_name,
            bank_code=b.bank_code,
            category=b.category,
            product_type=getattr(b, "product_type", "bank"),
            product_subtype=getattr(b, "product_subtype", "log"),
            seller_price=b.seller_price,
            base_price=getattr(b, "base_price", None),
            final_price=getattr(b, "final_price", None),
            buyer_price=b.buyer_price,
            markup_percent=getattr(b, "markup_percent", None),
            markup_fixed=getattr(b, "markup_fixed", None),
            markup_code=getattr(b, "markup_code", None),
            markup_kind=getattr(b, "markup_kind", None),
            markup_value=getattr(b, "markup_value", None),
            seller_name=s.display_name or s.username or str(s.telegram_id),
            created_at=b.created_at,
            moderation_status=getattr(b, "moderation_status", "pending_moderation")
        )
        for b, s in rows
    ]


@router.get("/cc-items", response_model=List[PendingCCResponse])
async def list_pending_cc(
    status: Optional[str] = "pending_moderation",
    q: Optional[str] = None,
    card_type: Optional[str] = None,
    card_brand: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    """List CC items with optional filters by status, text search, card_type, card_brand."""
    conds = [SellerCCItem.is_active == True]
    if status:
        conds.append(SellerCCItem.moderation_status == status)

    if q:
        q_clean = q.strip()
        if q_clean.isdigit() and len(q_clean) >= 4:
            conds.append(SellerCCItem.card_bin.startswith(q_clean[:6]))
        else:
            like_q = f"%{q_clean}%"
            conds.append(or_(
                SellerCCItem.bank_name.ilike(like_q),
                SellerCCItem.card_brand.ilike(like_q),
                SellerCCItem.item_name.ilike(like_q),
                SellerCCItem.card_type.ilike(like_q),
            ))

    if card_type:
        conds.append(SellerCCItem.card_type.ilike(card_type.strip()))
    if card_brand:
        conds.append(SellerCCItem.card_brand.ilike(card_brand.strip()))

    stmt = (
        select(SellerCCItem, Seller)
        .join(Seller, SellerCCItem.seller_id == Seller.id)
        .where(and_(*conds))
        .order_by(SellerCCItem.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        PendingCCResponse(
            id=i.id,
            upload_batch_id=getattr(i, "upload_batch_id", None),
            item_name=i.item_name,
            cc_code=i.cc_code,
            category_code=i.category_code,
            product_type=getattr(i, "product_type", "cc"),
            product_subtype=getattr(i, "product_subtype", "with_fullz"),
            seller_price=i.seller_price,
            base_price=getattr(i, "base_price", None),
            final_price=getattr(i, "final_price", None),
            buyer_price=i.buyer_price,
            markup_percent=getattr(i, "markup_percent", None),
            markup_fixed=getattr(i, "markup_fixed", None),
            markup_code=getattr(i, "markup_code", None),
            markup_kind=getattr(i, "markup_kind", None),
            markup_value=getattr(i, "markup_value", None),
            seller_name=s.display_name or s.username or str(s.telegram_id),
            created_at=i.created_at,
            moderation_status=getattr(i, "moderation_status", "pending_moderation")
        )
        for i, s in rows
    ]


@router.get("/markup-rules")
async def get_markup_rules(
    _: dict = Depends(require_seller_moderation_access())
):
    return [
        {
            "code": rule.code,
            "label": rule.label,
            "kind": rule.kind,
            "value": float(rule.value),
        }
        for rule in MARKUP_RULES.values()
    ]


@router.post("/banks/{bank_id}/approve")
async def approve_bank(
    bank_id: int,
    request: Request,
    body: Optional[ApprovalBody] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    body = body or ApprovalBody()
    """Approve a seller bank"""
    result = await db.execute(select(SellerBank).where(SellerBank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        raise HTTPException(404, "Bank not found")
    rule = apply_bank_markup(bank, base_price=body.base_price, rule_code=body.rule_code)
    bank.moderation_status = "approved"
    bank.moderated_at = datetime.now(timezone.utc)
    bank.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_bank_moderation_approve",
        "seller_bank",
        bank.id,
        {
            "seller_id": bank.seller_id,
            "bank_name": bank.bank_name,
            "bank_code": bank.bank_code,
            "upload_batch_id": getattr(bank, "upload_batch_id", None),
            "base_price": float(bank.base_price or 0),
            "final_price": float(getattr(bank, "final_price", bank.buyer_price) or 0),
            "buyer_price": float(bank.buyer_price or 0),
            "markup_code": rule.code if rule else None,
            "moderation_status": bank.moderation_status,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="seller_item_moderation_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="seller_bank",
        target_id=bank.id,
        status="approved",
        payload={"seller_id": bank.seller_id, "bank_code": bank.bank_code, "buyer_price": float(bank.buyer_price or 0)},
        timestamp=bank.moderated_at,
    )
    await SellerUploadBatchService.recalc_batch_status(db, bank.upload_batch_id, "bank")
    return {
        "ok": True,
        "status": "approved",
        "final_price": float(getattr(bank, "final_price", bank.buyer_price) or 0),
        "buyer_price": float(bank.buyer_price or 0),
        "markup_code": rule.code if rule else None,
    }


@router.post("/banks/{bank_id}/reject")
async def reject_bank(
    bank_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    """Reject a seller bank"""
    result = await db.execute(select(SellerBank).where(SellerBank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        raise HTTPException(404, "Bank not found")
    bank.moderation_status = "rejected"
    bank.moderated_at = datetime.now(timezone.utc)
    bank.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_bank_moderation_reject",
        "seller_bank",
        bank.id,
        {
            "seller_id": bank.seller_id,
            "bank_name": bank.bank_name,
            "bank_code": bank.bank_code,
            "upload_batch_id": getattr(bank, "upload_batch_id", None),
            "moderation_status": bank.moderation_status,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="seller_item_moderation_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="seller_bank",
        target_id=bank.id,
        status="rejected",
        payload={"seller_id": bank.seller_id, "bank_code": bank.bank_code},
        timestamp=bank.moderated_at,
    )
    await SellerUploadBatchService.recalc_batch_status(db, bank.upload_batch_id, "bank")
    return {"ok": True, "status": "rejected"}


@router.post("/banks/{bank_id}/request-changes")
async def request_changes_bank(
    bank_id: int,
    body: ChangesRequestedBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    """Request changes for a seller bank"""
    result = await db.execute(select(SellerBank).where(SellerBank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        raise HTTPException(404, "Bank not found")
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    bank.moderation_status = "changes_requested"
    bank.moderation_comment = comment
    bank.moderated_at = datetime.now(timezone.utc)
    bank.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_bank_moderation_changes_requested",
        "seller_bank",
        bank.id,
        {
            "seller_id": bank.seller_id,
            "bank_name": bank.bank_name,
            "bank_code": bank.bank_code,
            "upload_batch_id": getattr(bank, "upload_batch_id", None),
            "moderation_status": bank.moderation_status,
            "comment": bank.moderation_comment,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, bank.upload_batch_id, "bank")
    return {"ok": True, "status": "changes_requested"}


@router.post("/cc-items/{item_id}/approve")
async def approve_cc_item(
    item_id: int,
    request: Request,
    body: Optional[ApprovalBody] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    body = body or ApprovalBody()
    """Approve a seller CC item"""
    result = await db.execute(select(SellerCCItem).where(SellerCCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "CC item not found")
    rule = apply_cc_markup(item, base_price=body.base_price, rule_code=body.rule_code)
    item.moderation_status = "approved"
    item.is_approved = True
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_cc_moderation_approve",
        "seller_cc_item",
        item.id,
        {
            "seller_id": item.seller_id,
            "item_name": item.item_name,
            "cc_code": item.cc_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "base_price": float(item.base_price or 0),
            "final_price": float(getattr(item, "final_price", item.buyer_price) or 0),
            "buyer_price": float(item.buyer_price or 0),
            "markup_code": rule.code if rule else None,
            "moderation_status": item.moderation_status,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="seller_item_moderation_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="seller_cc_item",
        target_id=item.id,
        status="approved",
        payload={"seller_id": item.seller_id, "cc_code": item.cc_code, "buyer_price": float(item.buyer_price or 0)},
        timestamp=item.moderated_at,
    )
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, "cc")
    return {
        "ok": True,
        "status": "approved",
        "final_price": float(getattr(item, "final_price", item.buyer_price) or 0),
        "buyer_price": float(item.buyer_price or 0),
        "markup_code": rule.code if rule else None,
    }


@router.post("/cc-items/{item_id}/reject")
async def reject_cc_item(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    """Reject a seller CC item"""
    result = await db.execute(select(SellerCCItem).where(SellerCCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "CC item not found")
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_cc_moderation_reject",
        "seller_cc_item",
        item.id,
        {
            "seller_id": item.seller_id,
            "item_name": item.item_name,
            "cc_code": item.cc_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "moderation_status": item.moderation_status,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    NocoDBService.log_event(
        event_type="seller_item_moderation_changed",
        actor_type="admin",
        actor_id=current_user.get("telegram_id") or current_user.get("user_id"),
        target_type="seller_cc_item",
        target_id=item.id,
        status="rejected",
        payload={"seller_id": item.seller_id, "cc_code": item.cc_code},
        timestamp=item.moderated_at,
    )
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, "cc")
    return {"ok": True, "status": "rejected"}


@router.post("/cc-items/{item_id}/request-changes")
async def request_changes_cc_item(
    item_id: int,
    body: ChangesRequestedBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_seller_moderation_access())
):
    """Request changes for a seller CC item"""
    result = await db.execute(select(SellerCCItem).where(SellerCCItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "CC item not found")
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    item.moderation_status = "changes_requested"
    item.moderation_comment = comment
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    item.is_approved = False
    await log_action(
        db,
        current_user.get("admin_id"),
        "seller_cc_moderation_changes_requested",
        "seller_cc_item",
        item.id,
        {
            "seller_id": item.seller_id,
            "item_name": item.item_name,
            "cc_code": item.cc_code,
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "moderation_status": item.moderation_status,
            "comment": item.moderation_comment,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, "cc")
    return {"ok": True, "status": "changes_requested"}


@router.get("/nfc-items")
async def list_pending_nfc_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerNFCItem, Seller)
            .join(Seller, SellerNFCItem.seller_id == Seller.id)
            .where(SellerNFCItem.moderation_status == status, SellerNFCItem.is_active == True)
            .order_by(SellerNFCItem.created_at.desc())
        )
    ).all()
    return [
        _serialize_special_item(item, seller, summary=f"{item.nfc_type.upper()} | {item.bank_name} | {item.country} {item.state or ''} {item.zip or ''}".strip())
        for item, seller in rows
    ]


@router.get("/otp-items")
async def list_pending_otp_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerOTPItem, Seller)
            .join(Seller, SellerOTPItem.seller_id == Seller.id)
            .where(SellerOTPItem.moderation_status == status, SellerOTPItem.is_active == True)
            .order_by(SellerOTPItem.created_at.desc())
        )
    ).all()
    return [
        _serialize_special_item(item, seller, summary=f"{item.bank_name} | balance ${float(item.balance):.2f} | fullz {'yes' if item.has_fullz else 'no'} | {item.sms_access_type}")
        for item, seller in rows
    ]


@router.get("/selfreg-cc-items")
async def list_pending_selfreg_cc_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerSelfregCCItem, Seller)
            .join(Seller, SellerSelfregCCItem.seller_id == Seller.id)
            .where(SellerSelfregCCItem.moderation_status == status, SellerSelfregCCItem.is_active == True)
            .order_by(SellerSelfregCCItem.created_at.desc())
        )
    ).all()
    return [
        _serialize_special_item(
            item,
            seller,
            summary=f"{item.bank_name} | credit ${float(item.credit_limit or 0):.2f} | vcc ${float(item.vcc_limit or 0):.2f} | {item.state or '-'} {item.zip or ''}".strip(),
        )
        for item, seller in rows
    ]


@router.get("/check-items")
async def list_pending_check_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerCheckItem, Seller)
            .join(Seller, SellerCheckItem.seller_id == Seller.id)
            .where(SellerCheckItem.moderation_status == status, SellerCheckItem.is_active == True)
            .order_by(SellerCheckItem.created_at.desc())
        )
    ).all()
    return [
        _serialize_special_item(item, seller, summary=f"{item.check_type} | {item.bank_name} | amount ${float(item.amount):.2f} | {item.state or '-'} {item.zip or ''}".strip())
        for item, seller in rows
    ]


async def _approve_special_item(item, body: Optional[ApprovalBody], request: Request, db: AsyncSession, current_user: dict, *, item_type: str, apply_markup, entity_type: str):
    body = body or ApprovalBody()
    rule = apply_markup(item, base_price=body.base_price, rule_code=body.rule_code)
    item.moderation_status = "approved"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    item.moderation_comment = None
    await log_action(
        db,
        current_user.get("admin_id"),
        f"{entity_type}_moderation_approve",
        entity_type,
        item.id,
        {
            "seller_id": item.seller_id,
            "item_name": getattr(item, "item_name", getattr(item, "bank_name", str(item.id))),
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "base_price": float(getattr(item, "base_price", 0) or 0),
            "final_price": float(getattr(item, "final_price", getattr(item, "buyer_price", 0)) or 0),
            "buyer_price": float(getattr(item, "buyer_price", 0) or 0),
            "markup_code": rule.code,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, item_type)
    return {
        "ok": True,
        "status": "approved",
        "final_price": float(getattr(item, "final_price", getattr(item, "buyer_price", 0)) or 0),
        "buyer_price": float(getattr(item, "buyer_price", 0) or 0),
        "markup_code": rule.code,
    }


async def _reject_special_item(item, request: Request, db: AsyncSession, current_user: dict, *, item_type: str, entity_type: str):
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        f"{entity_type}_moderation_reject",
        entity_type,
        item.id,
        {
            "seller_id": item.seller_id,
            "item_name": getattr(item, "item_name", getattr(item, "bank_name", str(item.id))),
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, item_type)
    return {"ok": True, "status": "rejected"}


async def _changes_special_item(item, body: ChangesRequestedBody, request: Request, db: AsyncSession, current_user: dict, *, item_type: str, entity_type: str):
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    item.moderation_status = "changes_requested"
    item.moderation_comment = comment
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await log_action(
        db,
        current_user.get("admin_id"),
        f"{entity_type}_moderation_changes_requested",
        entity_type,
        item.id,
        {
            "seller_id": item.seller_id,
            "item_name": getattr(item, "item_name", getattr(item, "bank_name", str(item.id))),
            "upload_batch_id": getattr(item, "upload_batch_id", None),
            "comment": comment,
            "source": "web_panel",
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    await SellerUploadBatchService.recalc_batch_status(db, item.upload_batch_id, item_type)
    return {"ok": True, "status": "changes_requested"}


@router.post("/nfc-items/{item_id}/approve")
async def approve_nfc_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerNFCItem).where(SellerNFCItem.id == item_id))
    if not item:
        raise HTTPException(404, "NFC item not found")
    return await _approve_special_item(item, body, request, db, current_user, item_type="nfc", apply_markup=apply_nfc_markup, entity_type="seller_nfc_item")


@router.post("/nfc-items/{item_id}/reject")
async def reject_nfc_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerNFCItem).where(SellerNFCItem.id == item_id))
    if not item:
        raise HTTPException(404, "NFC item not found")
    return await _reject_special_item(item, request, db, current_user, item_type="nfc", entity_type="seller_nfc_item")


@router.post("/nfc-items/{item_id}/request-changes")
async def changes_nfc_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerNFCItem).where(SellerNFCItem.id == item_id))
    if not item:
        raise HTTPException(404, "NFC item not found")
    return await _changes_special_item(item, body, request, db, current_user, item_type="nfc", entity_type="seller_nfc_item")


@router.post("/otp-items/{item_id}/approve")
async def approve_otp_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerOTPItem).where(SellerOTPItem.id == item_id))
    if not item:
        raise HTTPException(404, "OTP item not found")
    return await _approve_special_item(item, body, request, db, current_user, item_type="otp", apply_markup=apply_otp_markup, entity_type="seller_otp_item")


@router.post("/otp-items/{item_id}/reject")
async def reject_otp_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerOTPItem).where(SellerOTPItem.id == item_id))
    if not item:
        raise HTTPException(404, "OTP item not found")
    return await _reject_special_item(item, request, db, current_user, item_type="otp", entity_type="seller_otp_item")


@router.post("/otp-items/{item_id}/request-changes")
async def changes_otp_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerOTPItem).where(SellerOTPItem.id == item_id))
    if not item:
        raise HTTPException(404, "OTP item not found")
    return await _changes_special_item(item, body, request, db, current_user, item_type="otp", entity_type="seller_otp_item")


@router.post("/selfreg-cc-items/{item_id}/approve")
async def approve_selfreg_cc_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerSelfregCCItem).where(SellerSelfregCCItem.id == item_id))
    if not item:
        raise HTTPException(404, "Selfreg CC item not found")
    return await _approve_special_item(item, body, request, db, current_user, item_type="selfreg_cc", apply_markup=apply_selfreg_cc_markup, entity_type="seller_selfreg_cc_item")


@router.post("/selfreg-cc-items/{item_id}/reject")
async def reject_selfreg_cc_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerSelfregCCItem).where(SellerSelfregCCItem.id == item_id))
    if not item:
        raise HTTPException(404, "Selfreg CC item not found")
    return await _reject_special_item(item, request, db, current_user, item_type="selfreg_cc", entity_type="seller_selfreg_cc_item")


@router.post("/selfreg-cc-items/{item_id}/request-changes")
async def changes_selfreg_cc_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerSelfregCCItem).where(SellerSelfregCCItem.id == item_id))
    if not item:
        raise HTTPException(404, "Selfreg CC item not found")
    return await _changes_special_item(item, body, request, db, current_user, item_type="selfreg_cc", entity_type="seller_selfreg_cc_item")


@router.post("/check-items/{item_id}/approve")
async def approve_check_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerCheckItem).where(SellerCheckItem.id == item_id))
    if not item:
        raise HTTPException(404, "Check item not found")
    return await _approve_special_item(item, body, request, db, current_user, item_type="check", apply_markup=apply_check_markup, entity_type="seller_check_item")


@router.post("/check-items/{item_id}/reject")
async def reject_check_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerCheckItem).where(SellerCheckItem.id == item_id))
    if not item:
        raise HTTPException(404, "Check item not found")
    return await _reject_special_item(item, request, db, current_user, item_type="check", entity_type="seller_check_item")


@router.post("/check-items/{item_id}/request-changes")
async def changes_check_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerCheckItem).where(SellerCheckItem.id == item_id))
    if not item:
        raise HTTPException(404, "Check item not found")
    return await _changes_special_item(item, body, request, db, current_user, item_type="check", entity_type="seller_check_item")


# ==================== ENROLLMENT ITEMS ====================

@router.get("/enroll-items")
async def list_pending_enroll_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerEnrollItem, Seller)
            .join(Seller, SellerEnrollItem.seller_id == Seller.id)
            .where(SellerEnrollItem.moderation_status == status, SellerEnrollItem.is_active == True)
            .order_by(SellerEnrollItem.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        _serialize_special_item(
            item, 
            seller, 
            summary=f"{item.portal} | {item.bank_name or 'N/A'} | ${float(item.balance):.2f} | SSN:{'✓' if item.has_ssn else '✗'} DOB:{'✓' if item.has_dob else '✗'}"
        )
        for item, seller in rows
    ]


@router.post("/enroll-items/{item_id}/approve")
async def approve_enroll_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerEnrollItem).where(SellerEnrollItem.id == item_id))
    if not item:
        raise HTTPException(404, "Enrollment item not found")
    # Generic markup - just use seller_price as buyer_price if not set
    body = body or ApprovalBody()
    if not item.buyer_price:
        item.buyer_price = item.seller_price
    item.moderation_status = "approved"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "approved", "buyer_price": float(item.buyer_price)}


@router.post("/enroll-items/{item_id}/reject")
async def reject_enroll_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerEnrollItem).where(SellerEnrollItem.id == item_id))
    if not item:
        raise HTTPException(404, "Enrollment item not found")
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "rejected"}


@router.post("/enroll-items/{item_id}/request-changes")
async def changes_enroll_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerEnrollItem).where(SellerEnrollItem.id == item_id))
    if not item:
        raise HTTPException(404, "Enrollment item not found")
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    item.moderation_status = "changes_requested"
    item.moderation_comment = comment
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "changes_requested"}


# ==================== BRUTE BANK ITEMS ====================

@router.get("/brute-items")
async def list_pending_brute_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(BruteBankItem, Seller)
            .join(Seller, BruteBankItem.seller_id == Seller.id)
            .where(BruteBankItem.moderation_status == status, BruteBankItem.is_active == True)
            .order_by(BruteBankItem.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        _serialize_special_item(
            item, 
            seller, 
            summary=f"{item.bank_name} ({item.bank_code}) | {item.category} | {item.balance_range or 'N/A'}"
        )
        for item, seller in rows
    ]


@router.post("/brute-items/{item_id}/approve")
async def approve_brute_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(BruteBankItem).where(BruteBankItem.id == item_id))
    if not item:
        raise HTTPException(404, "Brute item not found")
    body = body or ApprovalBody()
    if not item.buyer_price:
        item.buyer_price = item.seller_price
    item.moderation_status = "approved"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "approved", "buyer_price": float(item.buyer_price)}


@router.post("/brute-items/{item_id}/reject")
async def reject_brute_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(BruteBankItem).where(BruteBankItem.id == item_id))
    if not item:
        raise HTTPException(404, "Brute item not found")
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "rejected"}


@router.post("/brute-items/{item_id}/request-changes")
async def changes_brute_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(BruteBankItem).where(BruteBankItem.id == item_id))
    if not item:
        raise HTTPException(404, "Brute item not found")
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    item.moderation_status = "changes_requested"
    item.moderation_comment = comment
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "changes_requested"}


# ==================== LOGS ITEMS ====================

@router.get("/logs-items")
async def list_pending_logs_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerLogsItem, Seller)
            .join(Seller, SellerLogsItem.seller_id == Seller.id)
            .where(SellerLogsItem.moderation_status == status, SellerLogsItem.is_active == True)
            .order_by(SellerLogsItem.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        _serialize_special_item(
            item, 
            seller, 
            summary=f"{item.bank} | ${float(item.total_balance):.2f} | CVV:{'✓' if item.has_cvv else '✗'} BT:{'✓' if item.bt_available else '✗'} Zelle:{'✓' if item.zelle_enroll else '✗'}"
        )
        for item, seller in rows
    ]


@router.post("/logs-items/{item_id}/approve")
async def approve_logs_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerLogsItem).where(SellerLogsItem.id == item_id))
    if not item:
        raise HTTPException(404, "Logs item not found")
    body = body or ApprovalBody()
    if not item.buyer_price:
        item.buyer_price = item.seller_price
    item.moderation_status = "approved"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "approved", "buyer_price": float(item.buyer_price)}


@router.post("/logs-items/{item_id}/reject")
async def reject_logs_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerLogsItem).where(SellerLogsItem.id == item_id))
    if not item:
        raise HTTPException(404, "Logs item not found")
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "rejected"}


@router.post("/logs-items/{item_id}/request-changes")
async def changes_logs_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerLogsItem).where(SellerLogsItem.id == item_id))
    if not item:
        raise HTTPException(404, "Logs item not found")
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    item.moderation_status = "changes_requested"
    item.moderation_comment = comment
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "changes_requested"}


# ==================== SELLER BANK ITEMS (Selfreg BA) ====================

@router.get("/seller-bank-items")
async def list_pending_seller_bank_items(
    status: str = "pending_moderation",
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_seller_moderation_access())
):
    rows = (
        await db.execute(
            select(SellerBankItem, Seller)
            .join(Seller, SellerBankItem.seller_id == Seller.id)
            .where(SellerBankItem.moderation_status == status, SellerBankItem.is_active == True)
            .order_by(SellerBankItem.created_at.desc())
            .limit(100)
        )
    ).all()
    return [
        _serialize_special_item(
            item, 
            seller, 
            summary=f"{item.bank} | ${float(item.balance):.2f} | {item.state or 'N/A'} {item.zip or ''} | Phone:{'✓' if item.has_phone else '✗'} Email:{'✓' if item.email_access else '✗'}"
        )
        for item, seller in rows
    ]


@router.post("/seller-bank-items/{item_id}/approve")
async def approve_seller_bank_item(item_id: int, body: Optional[ApprovalBody] = None, request: Request = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerBankItem).where(SellerBankItem.id == item_id))
    if not item:
        raise HTTPException(404, "Seller bank item not found")
    body = body or ApprovalBody()
    if not item.buyer_price:
        item.buyer_price = item.seller_price
    item.moderation_status = "approved"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "approved", "buyer_price": float(item.buyer_price)}


@router.post("/seller-bank-items/{item_id}/reject")
async def reject_seller_bank_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerBankItem).where(SellerBankItem.id == item_id))
    if not item:
        raise HTTPException(404, "Seller bank item not found")
    item.moderation_status = "rejected"
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "rejected"}


@router.post("/seller-bank-items/{item_id}/request-changes")
async def changes_seller_bank_item(item_id: int, body: ChangesRequestedBody, request: Request, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_seller_moderation_access())):
    item = await db.scalar(select(SellerBankItem).where(SellerBankItem.id == item_id))
    if not item:
        raise HTTPException(404, "Seller bank item not found")
    comment = (body.comment or "").strip()
    if not comment:
        raise HTTPException(400, "Comment is required")
    item.moderation_status = "changes_requested"
    item.moderation_comment = comment
    item.moderated_at = datetime.now(timezone.utc)
    item.moderated_by = current_user.get("admin_id")
    await db.commit()
    return {"ok": True, "status": "changes_requested"}
