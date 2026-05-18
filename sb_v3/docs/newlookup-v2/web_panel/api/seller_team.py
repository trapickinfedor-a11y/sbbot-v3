"""Seller Team Management API - Helpers & Audit"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Seller, SellerHelper, SellerHelperAuditLog
from shared.services.seller_actor_service import SellerActorContext, resolve_seller_actor
from web_panel.database import get_db
from web_panel.api.seller_mini_app import get_current_seller_from_webapp

router = APIRouter(prefix="/api/seller-mini-app/team", tags=["seller-team"])

VALID_ROLES = ["support_helper", "upload_helper", "finance_helper", "manager_helper"]


class HelperResponse(BaseModel):
    id: int
    telegram_id: int
    display_name: str
    username: Optional[str]
    role: str
    is_active: bool
    invited_at: str
    joined_at: Optional[str]


class AddHelperRequest(BaseModel):
    identifier: str  # username or user_id
    role: str = "support_helper"


class UpdateHelperRolesRequest(BaseModel):
    role: str


class AuditEntryResponse(BaseModel):
    id: int
    action: str
    object_type: Optional[str]
    object_id: Optional[int]
    created_at: str


@router.get("/helpers")
async def get_seller_helpers(
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Get list of seller helpers"""
    seller = seller_actor.seller

    result = await db.execute(
        select(SellerHelper)
        .where(SellerHelper.seller_id == seller.id)
        .order_by(SellerHelper.created_at.desc())
    )
    helpers = result.scalars().all()

    return [
        HelperResponse(
            id=h.id,
            telegram_id=h.telegram_id,
            display_name=h.display_name or f"Helper {h.id}",
            username=h.username,
            role=h.role,
            is_active=(h.status == "active"),
            invited_at=h.created_at.isoformat(),
            joined_at=h.joined_at.isoformat() if h.joined_at else None,
        )
        for h in helpers
    ]


@router.post("/helpers", status_code=201)
async def add_seller_helper(
    body: AddHelperRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Invite a new helper"""
    seller = seller_actor.seller

    # Only manager or seller owner can add helpers
    if seller_actor.is_helper and seller_actor.role != "manager_helper":
        raise HTTPException(status_code=403, detail="Only managers can add helpers")

    # Validate role
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")

    # Find user by identifier (telegram_id)
    try:
        telegram_id = int(body.identifier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Please provide Telegram user ID")

    # Check if helper already exists for this seller
    existing_result = await db.execute(
        select(SellerHelper).where(
            SellerHelper.seller_id == seller.id,
            SellerHelper.telegram_id == telegram_id,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Helper already exists")

    # Create helper
    helper = SellerHelper(
        seller_id=seller.id,
        telegram_id=telegram_id,
        display_name=body.identifier,
        role=body.role,
        status="pending",
        invited_by=seller.id,
        created_at=datetime.now(timezone.utc),
    )

    db.add(helper)
    await db.flush()

    # Audit log
    audit = SellerHelperAuditLog(
        seller_id=seller.id,
        helper_id=helper.id,
        action="helper_invited",
        object_type="seller_helper",
        object_id=helper.id,
        payload_json={"telegram_id": telegram_id, "role": body.role},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(helper)

    return {"id": helper.id, "telegram_id": helper.telegram_id}


@router.post("/add", status_code=201)
async def add_helper_alias(
    body: AddHelperRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Alias for /helpers POST - for frontend compatibility"""
    return await add_seller_helper(body, db, seller_actor)


@router.patch("/helpers/{helper_id}/roles")
async def update_helper_roles(
    helper_id: int,
    body: UpdateHelperRolesRequest,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Update helper role"""
    seller = seller_actor.seller

    helper = await db.get(SellerHelper, helper_id)
    if not helper or helper.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Helper not found")

    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")

    helper.role = body.role
    db.add(helper)

    # Audit
    audit = SellerHelperAuditLog(
        seller_id=seller.id,
        helper_id=helper_id,
        action="helper_role_updated",
        object_type="seller_helper",
        object_id=helper_id,
        payload_json={"new_role": body.role},
    )
    db.add(audit)
    await db.commit()

    return {"ok": True}


@router.delete("/helpers/{helper_id}")
async def remove_helper(
    helper_id: int,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Remove a helper"""
    seller = seller_actor.seller

    helper = await db.get(SellerHelper, helper_id)
    if not helper or helper.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Helper not found")

    await db.delete(helper)

    # Audit
    audit = SellerHelperAuditLog(
        seller_id=seller.id,
        helper_id=None,
        action="helper_removed",
        object_type="seller_helper",
        object_id=helper_id,
    )
    db.add(audit)
    await db.commit()

    return {"ok": True}


@router.get("/helpers/{helper_id}/audit")
async def get_helper_audit(
    helper_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    seller_actor: SellerActorContext = Depends(get_current_seller_from_webapp),
):
    """Get audit log for a helper"""
    seller = seller_actor.seller

    # Verify helper belongs to seller
    helper = await db.get(SellerHelper, helper_id)
    if not helper or helper.seller_id != seller.id:
        raise HTTPException(status_code=404, detail="Helper not found")

    result = await db.execute(
        select(SellerHelperAuditLog)
        .where(
            SellerHelperAuditLog.seller_id == seller.id,
            SellerHelperAuditLog.helper_id == helper_id,
        )
        .order_by(SellerHelperAuditLog.created_at.desc())
        .limit(limit)
    )

    events = result.scalars().all()

    return [
        AuditEntryResponse(
            id=e.id,
            action=e.action,
            object_type=e.object_type,
            object_id=e.object_id,
            created_at=e.created_at.isoformat(),
        )
        for e in events
    ]
