from __future__ import annotations

"""
API for Another Services section — manage buttons/links shown in bot
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetim, timezone

from web_panel.database import get_db
from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from shared.database.models import AnotherServiceButton

router = APIRouter(prefix="/api/another-services", tags=["another-services"])


class ButtonCreate(BaseModel):
    text_en: str
    text_ru: Optional[str] = None
    text_zh: Optional[str] = None
    text_es: Optional[str] = None
    url: Optional[str] = None
    callback_data: Optional[str] = None
    button_type: str = "url"  # url | callback | info
    position: int = 0
    is_active: bool = True


class ButtonUpdate(BaseModel):
    text_en: Optional[str] = None
    text_ru: Optional[str] = None
    text_zh: Optional[str] = None
    text_es: Optional[str] = None
    url: Optional[str] = None
    callback_data: Optional[str] = None
    button_type: Optional[str] = None
    position: Optional[int] = None
    is_active: Optional[bool] = None


def _btn_dict(b: AnotherServiceButton) -> dict:
    return {
        "id": b.id,
        "text_en": b.text_en,
        "text_ru": b.text_ru,
        "text_zh": b.text_zh,
        "text_es": b.text_es,
        "url": b.url,
        "callback_data": b.callback_data,
        "button_type": b.button_type,
        "position": b.position,
        "is_active": b.is_active,
        "created_at": b.created_at.isoformat(),
    }


@router.get("/buttons")
async def list_buttons(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("another-services"))
):
    result = await db.execute(
        select(AnotherServiceButton).order_by(AnotherServiceButton.position, AnotherServiceButton.id)
    )
    return [_btn_dict(b) for b in result.scalars().all()]


@router.post("/buttons")
async def create_button(
    data: ButtonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("another-services"))
):
    btn = AnotherServiceButton(**data.model_dump())
    db.add(btn)
    await db.commit()
    await db.refresh(btn)
    return _btn_dict(btn)


# NOTE: /buttons/reorder must be declared before /buttons/{btn_id} to avoid routing conflict
@router.post("/buttons/reorder")
async def reorder_buttons(
    order: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("another-services"))
):
    """Update positions from ordered list of IDs."""
    for pos, btn_id in enumerate(order):
        result = await db.execute(select(AnotherServiceButton).where(AnotherServiceButton.id == btn_id))
        btn = result.scalar_one_or_none()
        if btn:
            btn.position = pos
    await db.commit()
    return {"ok": True}


@router.put("/buttons/{btn_id}")
async def update_button(
    btn_id: int, data: ButtonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("another-services"))
):
    result = await db.execute(select(AnotherServiceButton).where(AnotherServiceButton.id == btn_id))
    btn = result.scalar_one_or_none()
    if not btn:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(btn, k, v)
    btn.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.post("/buttons/{btn_id}/toggle")
async def toggle_button(
    btn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("another-services"))
):
    result = await db.execute(select(AnotherServiceButton).where(AnotherServiceButton.id == btn_id))
    btn = result.scalar_one_or_none()
    if not btn:
        raise HTTPException(status_code=404, detail="Not found")
    btn.is_active = not btn.is_active
    await db.commit()
    return {"ok": True, "is_active": btn.is_active}


@router.delete("/buttons/{btn_id}")
async def delete_button(
    btn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("another-services"))
):
    result = await db.execute(select(AnotherServiceButton).where(AnotherServiceButton.id == btn_id))
    btn = result.scalar_one_or_none()
    if not btn:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(btn)
    await db.commit()
    return {"ok": True}
