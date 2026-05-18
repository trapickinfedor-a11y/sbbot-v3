"""
API endpoints для управления товарами на складе (автовыдача)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

from web_panel.database import get_db
from web_panel.auth import get_current_user
from shared.database.models import Order

# StockItem and Service models were removed in current schema
StockItem = None
Service = None

router = APIRouter(prefix="/api/stock", tags=["stock"])


# ========== Pydantic Models ==========

class StockItemCreate(BaseModel):
    service_id: int
    content: str
    file_id: Optional[str] = None
    additional_data: Optional[dict] = None
    notes: Optional[str] = None


class StockItemBulkCreate(BaseModel):
    service_id: int
    items: List[str]  # Список content (каждая строка - отдельный товар)
    file_id: Optional[str] = None
    additional_data: Optional[dict] = None
    notes: Optional[str] = None


class StockItemUpdate(BaseModel):
    content: Optional[str] = None
    file_id: Optional[str] = None
    additional_data: Optional[dict] = None
    status: Optional[str] = None
    is_available: Optional[bool] = None
    notes: Optional[str] = None


class StockItemResponse(BaseModel):
    id: int
    service_id: int
    service_name: str
    service_code: str
    content: str
    file_id: Optional[str]
    additional_data: Optional[dict]
    status: str
    is_available: bool
    order_id: Optional[int]
    sold_at: Optional[datetime]
    uploaded_by: int
    uploaded_at: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True


class StockStats(BaseModel):
    service_id: int
    service_name: str
    service_code: str
    total_items: int
    available_items: int
    sold_items: int
    reserved_items: int
    invalid_items: int


# ========== Endpoints ==========

@router.get("", response_model=List[StockItemResponse])
async def get_stock_items(
    service_id: Optional[int] = None,
    status: Optional[str] = None,
    available_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить список товаров на складе"""
    
    query = select(StockItem, Service).join(Service).order_by(StockItem.uploaded_at.desc())
    
    if service_id:
        query = query.where(StockItem.service_id == service_id)
    
    if status:
        query = query.where(StockItem.status == status)
    
    if available_only:
        query = query.where(StockItem.is_available == True)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for stock_item, service in rows:
        item_dict = {
            "id": stock_item.id,
            "service_id": stock_item.service_id,
            "service_name": service.name,
            "service_code": service.code,
            "content": stock_item.content,
            "file_id": stock_item.file_id,
            "additional_data": stock_item.additional_data,
            "status": stock_item.status,
            "is_available": stock_item.is_available,
            "order_id": stock_item.order_id,
            "sold_at": stock_item.sold_at,
            "uploaded_by": stock_item.uploaded_by,
            "uploaded_at": stock_item.uploaded_at,
            "notes": stock_item.notes
        }
        items.append(StockItemResponse(**item_dict))
    
    return items


@router.get("/stats", response_model=List[StockStats])
async def get_stock_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить статистику по товарам на складе"""
    
    # Получить все услуги с автовыдачей
    services_result = await db.execute(
        select(Service).where(Service.auto_delivery == True)
    )
    services = services_result.scalars().all()
    
    stats = []
    for service in services:
        # Подсчитать товары по статусам
        total_result = await db.execute(
            select(func.count(StockItem.id)).where(StockItem.service_id == service.id)
        )
        total = total_result.scalar() or 0
        
        available_result = await db.execute(
            select(func.count(StockItem.id)).where(
                and_(
                    StockItem.service_id == service.id,
                    StockItem.status == "available",
                    StockItem.is_available == True
                )
            )
        )
        available = available_result.scalar() or 0
        
        sold_result = await db.execute(
            select(func.count(StockItem.id)).where(
                and_(
                    StockItem.service_id == service.id,
                    StockItem.status == "sold"
                )
            )
        )
        sold = sold_result.scalar() or 0
        
        reserved_result = await db.execute(
            select(func.count(StockItem.id)).where(
                and_(
                    StockItem.service_id == service.id,
                    StockItem.status == "reserved"
                )
            )
        )
        reserved = reserved_result.scalar() or 0
        
        invalid_result = await db.execute(
            select(func.count(StockItem.id)).where(
                and_(
                    StockItem.service_id == service.id,
                    StockItem.status == "invalid"
                )
            )
        )
        invalid = invalid_result.scalar() or 0
        
        stats.append(StockStats(
            service_id=service.id,
            service_name=service.name,
            service_code=service.code,
            total_items=total,
            available_items=available,
            sold_items=sold,
            reserved_items=reserved,
            invalid_items=invalid
        ))
    
    return stats


@router.post("", response_model=StockItemResponse)
async def create_stock_item(
    data: StockItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Добавить товар на склад"""
    
    # Проверить что услуга существует и имеет auto_delivery
    service_result = await db.execute(select(Service).where(Service.id == data.service_id))
    service = service_result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if not service.auto_delivery:
        raise HTTPException(status_code=400, detail="Service does not support auto delivery")
    
    stock_item = StockItem(
        service_id=data.service_id,
        content=data.content,
        file_id=data.file_id,
        additional_data=data.additional_data,
        notes=data.notes,
        status="available",
        is_available=True,
        uploaded_by=current_user["user_id"]
    )
    
    db.add(stock_item)
    await db.commit()
    await db.refresh(stock_item)
    
    return StockItemResponse(
        **stock_item.__dict__,
        service_name=service.name,
        service_code=service.code
    )


@router.post("/bulk", response_model=dict)
async def create_stock_items_bulk(
    data: StockItemBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Массовое добавление товаров на склад"""
    
    # Проверить что услуга существует и имеет auto_delivery
    service_result = await db.execute(select(Service).where(Service.id == data.service_id))
    service = service_result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if not service.auto_delivery:
        raise HTTPException(status_code=400, detail="Service does not support auto delivery")
    
    # Добавить все товары
    added_count = 0
    for content in data.items:
        if not content.strip():
            continue
        
        stock_item = StockItem(
            service_id=data.service_id,
            content=content.strip(),
            file_id=data.file_id,
            additional_data=data.additional_data,
            notes=data.notes,
            status="available",
            is_available=True,
            uploaded_by=current_user["user_id"]
        )
        
        db.add(stock_item)
        added_count += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "added_count": added_count,
        "message": f"Added {added_count} items to stock"
    }


@router.put("/{item_id}", response_model=StockItemResponse)
async def update_stock_item(
    item_id: int,
    data: StockItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновить товар на складе"""
    
    result = await db.execute(select(StockItem).where(StockItem.id == item_id))
    stock_item = result.scalar_one_or_none()
    
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    # Обновить поля
    if data.content is not None:
        stock_item.content = data.content
    if data.file_id is not None:
        stock_item.file_id = data.file_id
    if data.additional_data is not None:
        stock_item.additional_data = data.additional_data
    if data.status is not None:
        stock_item.status = data.status
    if data.is_available is not None:
        stock_item.is_available = data.is_available
    if data.notes is not None:
        stock_item.notes = data.notes
    
    await db.commit()
    await db.refresh(stock_item)
    
    # Получить услугу для ответа
    service_result = await db.execute(select(Service).where(Service.id == stock_item.service_id))
    service = service_result.scalar_one()
    
    return StockItemResponse(
        **stock_item.__dict__,
        service_name=service.name,
        service_code=service.code
    )


@router.delete("/{item_id}")
async def delete_stock_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удалить товар со склада"""
    
    result = await db.execute(select(StockItem).where(StockItem.id == item_id))
    stock_item = result.scalar_one_or_none()
    
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    if stock_item.status == "sold":
        raise HTTPException(status_code=400, detail="Cannot delete sold item")
    
    await db.delete(stock_item)
    await db.commit()
    
    return {"status": "success", "message": "Stock item deleted"}


@router.post("/{item_id}/mark-invalid")
async def mark_item_invalid(
    item_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Пометить товар как невалидный"""
    
    result = await db.execute(select(StockItem).where(StockItem.id == item_id))
    stock_item = result.scalar_one_or_none()
    
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    stock_item.status = "invalid"
    stock_item.is_available = False
    stock_item.notes = f"Invalid: {reason}" + (f"\n\nPrevious notes: {stock_item.notes}" if stock_item.notes else "")
    
    await db.commit()
    
    return {
        "status": "success",
        "message": "Item marked as invalid"
    }

