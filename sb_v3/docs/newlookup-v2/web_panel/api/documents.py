from __future__ import annotations

"""
Admin API for seller-uploaded Document and Fullz items.
Routes:
  GET  /api/documents/items            – paginated list (both types)
  GET  /api/documents/stats            – summary counts
  POST /api/documents/items/{id}/approve  – approve a document item
  POST /api/documents/items/{id}/reject   – reject a document item
  POST /api/documents/items/{id}/toggle-stock
  DELETE /api/documents/items/{id}

  GET  /api/documents/fullz            – paginated list of fullz items
  POST /api/documents/fullz/{id}/approve
  POST /api/documents/fullz/{id}/reject
  POST /api/documents/fullz/{id}/toggle-stock
  DELETE /api/documents/fullz/{id}
"""

import logging
from datetime import datetim, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Seller, SellerDocumentItem, SellerFullzItem
from shared.database.session import async_session_maker
from web_panel.auth import get_current_user, has_any_role

router = APIRouter(prefix="/api/documents", tags=["documents"])
logger = logging.getLogger(__name__)

_DOC_SUBTYPE_LABELS = {
    "dl_front_back": "DL (Front+Back)",
    "dl_selfie":     "DL + Selfie",
    "passport":      "Passport",
    "business_docs": "Business Docs",
}


def _require_view(user: dict) -> None:
    if not has_any_role(user, "admin", "owner", "super_admin", "moderator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _require_action(user: dict) -> None:
    if not has_any_role(user, "admin", "owner", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _doc_to_dict(item: SellerDocumentItem, seller_name: str = "") -> dict:
    return {
        "id": item.id,
        "seller_id": item.seller_id,
        "seller_name": seller_name,
        "item_name": item.item_name,
        "product_subtype": item.product_subtype,
        "subtype_label": _DOC_SUBTYPE_LABELS.get(item.product_subtype, item.product_subtype),
        "state": item.state,
        "quality": item.quality,
        "has_hologram": item.has_hologram,
        "has_selfie": item.has_selfie,
        "seller_description": item.seller_description,
        "seller_price": float(item.seller_price),
        "buyer_price": float(item.buyer_price),
        "moderation_status": item.moderation_status,
        "moderation_comment": item.moderation_comment,
        "is_in_stock": item.is_in_stock,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _fullz_to_dict(item: SellerFullzItem, seller_name: str = "") -> dict:
    return {
        "id": item.id,
        "seller_id": item.seller_id,
        "seller_name": seller_name,
        "item_name": item.item_name,
        "fullz_type": item.fullz_type,
        "state": item.state,
        "credit_score": item.credit_score,
        "age_range": item.age_range,
        "gender": item.gender,
        "company_type": item.company_type,
        "loan_size": item.loan_size,
        "report_group": item.report_group,
        "quantity": item.quantity,
        "seller_description": item.seller_description,
        "seller_price": float(item.seller_price),
        "buyer_price": float(item.buyer_price),
        "moderation_status": item.moderation_status,
        "moderation_comment": item.moderation_comment,
        "is_in_stock": item.is_in_stock,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_documents_stats(current_user=Depends(get_current_user)):
    _require_view(current_user)
    async with async_session_maker() as session:
        doc_total_q = await session.execute(
            select(func.count()).where(SellerDocumentItem.is_active == True)
        )
        doc_pending_q = await session.execute(
            select(func.count()).where(
                SellerDocumentItem.is_active == True,
                SellerDocumentItem.moderation_status == "pending_moderation",
            )
        )
        doc_approved_q = await session.execute(
            select(func.count()).where(
                SellerDocumentItem.is_active == True,
                SellerDocumentItem.moderation_status == "approved",
            )
        )
        fullz_total_q = await session.execute(
            select(func.count()).where(SellerFullzItem.is_active == True)
        )
        fullz_pending_q = await session.execute(
            select(func.count()).where(
                SellerFullzItem.is_active == True,
                SellerFullzItem.moderation_status == "pending_moderation",
            )
        )
        fullz_approved_q = await session.execute(
            select(func.count()).where(
                SellerFullzItem.is_active == True,
                SellerFullzItem.moderation_status == "approved",
            )
        )

        # By subtype breakdown for docs
        subtype_q = await session.execute(
            select(SellerDocumentItem.product_subtype, func.count())
            .where(SellerDocumentItem.is_active == True, SellerDocumentItem.moderation_status == "approved")
            .group_by(SellerDocumentItem.product_subtype)
        )
        doc_by_subtype = {row[0]: row[1] for row in subtype_q.fetchall()}

        # By type for fullz
        ftype_q = await session.execute(
            select(SellerFullzItem.fullz_type, func.count())
            .where(SellerFullzItem.is_active == True, SellerFullzItem.moderation_status == "approved")
            .group_by(SellerFullzItem.fullz_type)
        )
        fullz_by_type = {row[0]: row[1] for row in ftype_q.fetchall()}

    return {
        "documents": {
            "total": doc_total_q.scalar() or 0,
            "pending": doc_pending_q.scalar() or 0,
            "approved": doc_approved_q.scalar() or 0,
            "by_subtype": doc_by_subtype,
        },
        "fullz": {
            "total": fullz_total_q.scalar() or 0,
            "pending": fullz_pending_q.scalar() or 0,
            "approved": fullz_approved_q.scalar() or 0,
            "by_type": fullz_by_type,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Document items CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/items")
async def list_document_items(
    status: Optional[str] = Query(None, description="pending_moderation | approved | rejected"),
    subtype: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
):
    _require_view(current_user)
    async with async_session_maker() as session:
        filters = [SellerDocumentItem.is_active == True]
        if status:
            filters.append(SellerDocumentItem.moderation_status == status)
        if subtype:
            filters.append(SellerDocumentItem.product_subtype == subtype)
        if seller_id:
            filters.append(SellerDocumentItem.seller_id == seller_id)

        q = await session.execute(
            select(SellerDocumentItem, Seller.display_name)
            .join(Seller, Seller.id == SellerDocumentItem.seller_id)
            .where(*filters)
            .order_by(desc(SellerDocumentItem.created_at))
            .limit(limit)
            .offset(offset)
        )
        rows = q.fetchall()
        total_q = await session.execute(
            select(func.count())
            .select_from(SellerDocumentItem)
            .where(*filters)
        )
        total = total_q.scalar() or 0

    return {
        "total": total,
        "items": [_doc_to_dict(item, seller_name or "") for item, seller_name in rows],
    }


class ModerationBody(BaseModel):
    comment: Optional[str] = None


@router.post("/items/{item_id}/approve")
async def approve_document_item(
    item_id: int,
    body: ModerationBody = ModerationBody(),
    current_user=Depends(get_current_user),
):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item.moderation_status = "approved"
        item.moderation_comment = body.comment
        item.moderated_at = datetime.now(timezone.utc)
        item.moderated_by = current_user.get("id")
        await session.commit()
    return {"success": True, "id": item_id, "status": "approved"}


@router.post("/items/{item_id}/reject")
async def reject_document_item(
    item_id: int,
    body: ModerationBody = ModerationBody(),
    current_user=Depends(get_current_user),
):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item.moderation_status = "rejected"
        item.moderation_comment = body.comment
        item.is_in_stock = False
        item.moderated_at = datetime.now(timezone.utc)
        item.moderated_by = current_user.get("id")
        await session.commit()
    return {"success": True, "id": item_id, "status": "rejected"}


@router.post("/items/{item_id}/toggle-stock")
async def toggle_document_stock(item_id: int, current_user=Depends(get_current_user)):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item.is_in_stock = not item.is_in_stock
        await session.commit()
    return {"success": True, "id": item_id, "is_in_stock": item.is_in_stock}


@router.delete("/items/{item_id}")
async def delete_document_item(item_id: int, current_user=Depends(get_current_user)):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerDocumentItem).where(SellerDocumentItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item.is_active = False
        item.is_in_stock = False
        await session.commit()
    return {"success": True, "id": item_id}


# ─────────────────────────────────────────────────────────────────────────────
# Fullz items CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/fullz")
async def list_fullz_items(
    status: Optional[str] = Query(None),
    fullz_type: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
):
    _require_view(current_user)
    async with async_session_maker() as session:
        filters = [SellerFullzItem.is_active == True]
        if status:
            filters.append(SellerFullzItem.moderation_status == status)
        if fullz_type:
            filters.append(SellerFullzItem.fullz_type == fullz_type)
        if seller_id:
            filters.append(SellerFullzItem.seller_id == seller_id)

        q = await session.execute(
            select(SellerFullzItem, Seller.display_name)
            .join(Seller, Seller.id == SellerFullzItem.seller_id)
            .where(*filters)
            .order_by(desc(SellerFullzItem.created_at))
            .limit(limit)
            .offset(offset)
        )
        rows = q.fetchall()
        total_q = await session.execute(
            select(func.count())
            .select_from(SellerFullzItem)
            .where(*filters)
        )
        total = total_q.scalar() or 0

    return {
        "total": total,
        "items": [_fullz_to_dict(item, seller_name or "") for item, seller_name in rows],
    }


@router.post("/fullz/{item_id}/approve")
async def approve_fullz_item(
    item_id: int,
    body: ModerationBody = ModerationBody(),
    current_user=Depends(get_current_user),
):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerFullzItem).where(SellerFullzItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Fullz item not found")
        item.moderation_status = "approved"
        item.moderation_comment = body.comment
        item.moderated_at = datetime.now(timezone.utc)
        item.moderated_by = current_user.get("id")
        await session.commit()
    return {"success": True, "id": item_id, "status": "approved"}


@router.post("/fullz/{item_id}/reject")
async def reject_fullz_item(
    item_id: int,
    body: ModerationBody = ModerationBody(),
    current_user=Depends(get_current_user),
):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerFullzItem).where(SellerFullzItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Fullz item not found")
        item.moderation_status = "rejected"
        item.moderation_comment = body.comment
        item.is_in_stock = False
        item.moderated_at = datetime.now(timezone.utc)
        item.moderated_by = current_user.get("id")
        await session.commit()
    return {"success": True, "id": item_id, "status": "rejected"}


@router.post("/fullz/{item_id}/toggle-stock")
async def toggle_fullz_stock(item_id: int, current_user=Depends(get_current_user)):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerFullzItem).where(SellerFullzItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Fullz item not found")
        item.is_in_stock = not item.is_in_stock
        await session.commit()
    return {"success": True, "id": item_id, "is_in_stock": item.is_in_stock}


@router.delete("/fullz/{item_id}")
async def delete_fullz_item(item_id: int, current_user=Depends(get_current_user)):
    _require_action(current_user)
    async with async_session_maker() as session:
        q = await session.execute(select(SellerFullzItem).where(SellerFullzItem.id == item_id))
        item = q.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Fullz item not found")
        item.is_active = False
        item.is_in_stock = False
        await session.commit()
    return {"success": True, "id": item_id}
