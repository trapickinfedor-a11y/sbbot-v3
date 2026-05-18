"""
API для управления позициями банков
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from web_panel.database import get_db
from shared.database.models import BankPosition
from web_panel.services.audit_service import log_action

# Импортируем BankData для получения списка банков
from mirror_bot.constants.bank_data import BankData

router = APIRouter()


class BankPositionItem(BaseModel):
    bank_id: str
    name: str
    category: str
    position: int


class BankCategoryResponse(BaseModel):
    category: str
    category_name: str
    items: List[BankPositionItem]


class UpdatePositionsRequest(BaseModel):
    category: str
    bank_ids: List[str]  # Порядок банков (bank_id в нужном порядке)


@router.get("/categories", response_model=List[BankCategoryResponse])
async def get_bank_categories(
    current_user: dict = Depends(require_catalog_read_access("banks")),
    db: AsyncSession = Depends(get_db)
):
    """Получить все категории банков с текущими позициями"""
    
    # Получаем позиции из БД
    result = await db.execute(select(BankPosition).order_by(BankPosition.category, BankPosition.position))
    positions_db = {f"{p.category}:{p.bank_id}": p.position for p in result.scalars().all()}
    
    categories_response = []
    for cat_key, cat_data in BankData.CATEGORIES.items():
        items = cat_data.get("items", [])
        
        # Сортируем по позиции из БД (если есть), иначе по умолчанию
        def get_position(bank):
            key = f"{cat_key}:{bank['id']}"
            return positions_db.get(key, 999)
        
        sorted_items = sorted(items, key=get_position)
        
        # Обновляем позиции в БД для консистентности (если нет записи - добавляем)
        bank_positions = []
        for idx, bank in enumerate(sorted_items):
            pos = positions_db.get(f"{cat_key}:{bank['id']}", idx)
            bank_positions.append(BankPositionItem(
                bank_id=bank["id"],
                name=bank.get("name", bank["id"]),
                category=cat_key,
                position=pos
            ))
        
        categories_response.append(BankCategoryResponse(
            category=cat_key,
            category_name=cat_data.get("name", cat_key),
            items=bank_positions
        ))
    
    return categories_response


@router.put("/positions")
async def update_bank_positions(
    data: UpdatePositionsRequest,
    request: Request,
    current_user: dict = Depends(require_catalog_write_access("banks")),
    db: AsyncSession = Depends(get_db)
):
    """Обновить порядок банков в категории"""
    
    # Проверяем что категория существует
    if data.category not in BankData.CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неизвестная категория: {data.category}"
        )
    
    valid_bank_ids = {b["id"] for b in BankData.CATEGORIES[data.category]["items"]}
    for bank_id in data.bank_ids:
        if bank_id not in valid_bank_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неизвестный банк: {bank_id}"
            )
    
    # Удаляем старые позиции для этой категории
    from sqlalchemy import delete
    await db.execute(delete(BankPosition).where(BankPosition.category == data.category))
    
    # Добавляем новые позиции
    for position, bank_id in enumerate(data.bank_ids):
        bp = BankPosition(bank_id=bank_id, category=data.category, position=position)
        db.add(bp)
    
    await log_action(
        db,
        current_user.get("admin_id"),
        "bank_positions_update",
        "bank_category",
        None,
        {
            "category": data.category,
            "bank_ids": data.bank_ids,
            "actor_role": current_user.get("role"),
        },
        request.client.host if request.client else None,
    )
    await db.commit()
    
    return {"message": "Позиции обновлены", "category": data.category}
