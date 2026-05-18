from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.pricing_config_service import PricingConfigService
from web_panel.auth import require_page_access
from web_panel.database import get_db
from web_panel.services.audit_service import log_action

router = APIRouter()


class PricingConfigUpdate(BaseModel):
    value_type: str
    value: Any
    description: Optional[str] = None
    is_active: bool = True


class PricingConfigCreate(BaseModel):
    key: str
    value_type: str
    value: Any
    description: Optional[str] = None
    is_active: bool = True


@router.get("/")
async def get_pricing_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    await PricingConfigService.ensure_defaults(db)
    rows = await PricingConfigService.list_all(db)
    return [
        {
            "id": row.id,
            "key": row.key,
            "value_type": row.value_type,
            "value": PricingConfigService.deserialize(row),
            "description": row.description,
            "is_active": row.is_active,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


@router.post("/")
async def create_pricing_config(
    payload: PricingConfigCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    if payload.value_type not in {"number", "text", "json", "bool", "string"}:
        raise HTTPException(status_code=400, detail="Unsupported value_type")

    row = await PricingConfigService.upsert(
        db,
        key=payload.key,
        value_type=payload.value_type,
        value=payload.value,
        description=payload.description,
        is_active=payload.is_active,
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "pricing_config_create",
        "pricing_config",
        row.id,
        {"key": row.key, "actor_role": current_user.get("role")},
        request.client.host if request.client else None,
    )
    await db.commit()
    return {
        "id": row.id,
        "key": row.key,
        "value_type": row.value_type,
        "value": PricingConfigService.deserialize(row),
        "description": row.description,
        "is_active": row.is_active,
    }


@router.delete("/{key}")
async def delete_pricing_config(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    from sqlalchemy import select, delete
    from shared.database.models import SystemSetting
    row = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.execute(delete(SystemSetting).where(SystemSetting.key == key))
    await log_action(
        db,
        current_user.get("admin_id"),
        "pricing_config_delete",
        "pricing_config",
        row.id,
        {"key": key, "actor_role": current_user.get("role")},
        request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "deleted": key}


@router.put("/{key}")
async def update_pricing_config(
    key: str,
    payload: PricingConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_page_access("pricing-config")),
):
    if payload.value_type not in {"number", "text", "json", "bool"}:
        raise HTTPException(status_code=400, detail="Unsupported value_type")

    row = await PricingConfigService.upsert(
        db,
        key=key,
        value_type=payload.value_type,
        value=payload.value,
        description=payload.description,
        is_active=payload.is_active,
    )
    await log_action(
        db,
        current_user.get("admin_id"),
        "pricing_config_update",
        "pricing_config",
        row.id,
        {
            "key": row.key,
            "value_type": row.value_type,
            "value": PricingConfigService.deserialize(row),
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    return {
        "id": row.id,
        "key": row.key,
        "value_type": row.value_type,
        "value": PricingConfigService.deserialize(row),
        "description": row.description,
        "is_active": row.is_active,
    }
