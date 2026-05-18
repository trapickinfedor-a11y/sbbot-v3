"""
API endpoints для управления услугами/товарами
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
from decimal import Decimal

from web_panel.database import get_db
from web_panel.auth import get_current_user
from shared.database.models import ServicePrice

# Legacy aliases for old model names (Service, Category, StockItem were replaced by ServicePrice)
Service = ServicePrice
Category = None  # Not used in current schema
StockItem = None  # Not used in current schema

router = APIRouter(prefix="/api/services", tags=["services"])


# ========== Pydantic Models ==========

class ServiceCreate(BaseModel):
    category_id: int
    code: str
    name: str
    description: str
    price: Decimal
    old_price: Optional[Decimal] = None
    processing_time: str
    auto_delivery: bool = False
    input_template: Optional[str] = None
    output_format: Optional[str] = None
    validation_required: bool = True
    require_dob: bool = False
    require_ssn: bool = False
    require_address: bool = False
    require_phone: bool = False
    require_name: bool = False
    validation_config: Optional[dict] = None
    icon: Optional[str] = None
    order: int = 0
    is_active: bool = True
    is_featured: bool = False
    metadata: Optional[dict] = None


class ServiceUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    old_price: Optional[Decimal] = None
    processing_time: Optional[str] = None
    auto_delivery: Optional[bool] = None
    input_template: Optional[str] = None
    output_format: Optional[str] = None
    validation_required: Optional[bool] = None
    require_dob: Optional[bool] = None
    require_ssn: Optional[bool] = None
    require_address: Optional[bool] = None
    require_phone: Optional[bool] = None
    require_name: Optional[bool] = None
    validation_config: Optional[dict] = None
    icon: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    metadata: Optional[dict] = None


class ServiceResponse(BaseModel):
    id: int
    category_id: int
    category_name: str
    category_code: str
    code: str
    name: str
    description: str
    price: Decimal
    old_price: Optional[Decimal]
    processing_time: str
    auto_delivery: bool
    input_template: Optional[str]
    output_format: Optional[str]
    validation_required: bool
    require_dob: bool
    require_ssn: bool
    require_address: bool
    require_phone: bool
    require_name: bool
    validation_config: Optional[dict]
    icon: Optional[str]
    order: int
    is_active: bool
    is_featured: bool
    stock_count: int = 0
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Endpoints ==========

@router.get("", response_model=List[ServiceResponse])
async def get_services(
    category_id: Optional[int] = None,
    active_only: bool = False,
    auto_delivery_only: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить список услуг"""
    
    query = select(Service, Category).join(Category).order_by(Category.order, Service.order)
    
    if category_id:
        query = query.where(Service.category_id == category_id)
    
    if active_only:
        query = query.where(Service.is_active == True)
    
    if auto_delivery_only is not None:
        query = query.where(Service.auto_delivery == auto_delivery_only)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            Service.name.ilike(search_term) |
            Service.description.ilike(search_term) |
            Service.code.ilike(search_term)
        )
    
    result = await db.execute(query)
    rows = result.all()
    
    services = []
    for service, category in rows:
        # Подсчитать stock
        stock_result = await db.execute(
            select(func.count(StockItem.id)).where(
                StockItem.service_id == service.id,
                StockItem.is_available == True
            )
        )
        stock_count = stock_result.scalar() or 0
        
        service_dict = {
            "id": service.id,
            "category_id": service.category_id,
            "category_name": category.name,
            "category_code": category.code,
            "code": service.code,
            "name": service.name,
            "description": service.description,
            "price": service.price,
            "old_price": service.old_price,
            "processing_time": service.processing_time,
            "auto_delivery": service.auto_delivery,
            "input_template": service.input_template,
            "output_format": service.output_format,
            "validation_required": service.validation_required,
            "require_dob": service.require_dob,
            "require_ssn": service.require_ssn,
            "require_address": service.require_address,
            "require_phone": service.require_phone,
            "require_name": service.require_name,
            "validation_config": service.validation_config,
            "icon": service.icon,
            "order": service.order,
            "is_active": service.is_active,
            "is_featured": service.is_featured,
            "stock_count": stock_count,
            "metadata": service.service_metadata,
            "created_at": service.created_at,
            "updated_at": service.updated_at
        }
        services.append(ServiceResponse(**service_dict))
    
    return services


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Получить услугу по ID"""
    
    result = await db.execute(
        select(Service, Category).join(Category).where(Service.id == service_id)
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service, category = row
    
    # Подсчитать stock
    stock_result = await db.execute(
        select(func.count(StockItem.id)).where(
            StockItem.service_id == service.id,
            StockItem.is_available == True
        )
    )
    stock_count = stock_result.scalar() or 0
    
    service_dict = {
        "id": service.id,
        "category_id": service.category_id,
        "category_name": category.name,
        "category_code": category.code,
        "code": service.code,
        "name": service.name,
        "description": service.description,
        "price": service.price,
        "old_price": service.old_price,
        "processing_time": service.processing_time,
        "auto_delivery": service.auto_delivery,
        "input_template": service.input_template,
        "output_format": service.output_format,
        "validation_required": service.validation_required,
        "require_dob": service.require_dob,
        "require_ssn": service.require_ssn,
        "require_address": service.require_address,
        "require_phone": service.require_phone,
        "require_name": service.require_name,
        "validation_config": service.validation_config,
        "icon": service.icon,
        "order": service.order,
        "is_active": service.is_active,
        "is_featured": service.is_featured,
        "stock_count": stock_count,
        "metadata": service.service_metadata,
        "created_at": service.created_at,
        "updated_at": service.updated_at
    }
    
    return ServiceResponse(**service_dict)


@router.post("", response_model=ServiceResponse)
async def create_service(
    data: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Создать новую услугу"""
    
    # Проверить что категория существует
    category_result = await db.execute(select(Category).where(Category.id == data.category_id))
    category = category_result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Проверить что код уникален
    existing = await db.execute(select(Service).where(Service.code == data.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Service with this code already exists")
    
    service = Service(
        category_id=data.category_id,
        code=data.code,
        name=data.name,
        description=data.description,
        price=data.price,
        old_price=data.old_price,
        processing_time=data.processing_time,
        auto_delivery=data.auto_delivery,
        input_template=data.input_template,
        output_format=data.output_format,
        validation_required=data.validation_required,
        require_dob=data.require_dob,
        require_ssn=data.require_ssn,
        require_address=data.require_address,
        require_phone=data.require_phone,
        require_name=data.require_name,
        validation_config=data.validation_config,
        icon=data.icon,
        order=data.order,
        is_active=data.is_active,
        is_featured=data.is_featured,
        service_metadata=data.metadata
    )
    
    db.add(service)
    await db.commit()
    await db.refresh(service)
    
    return ServiceResponse(
        **service.__dict__,
        category_name=category.name,
        category_code=category.code,
        stock_count=0
    )


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Обновить услугу"""
    
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Обновить поля
    if data.category_id is not None:
        # Проверить что категория существует
        cat_result = await db.execute(select(Category).where(Category.id == data.category_id))
        if not cat_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Category not found")
        service.category_id = data.category_id
    
    if data.name is not None:
        service.name = data.name
    if data.description is not None:
        service.description = data.description
    if data.price is not None:
        service.price = data.price
    if data.old_price is not None:
        service.old_price = data.old_price
    if data.processing_time is not None:
        service.processing_time = data.processing_time
    if data.auto_delivery is not None:
        service.auto_delivery = data.auto_delivery
    if data.input_template is not None:
        service.input_template = data.input_template
    if data.output_format is not None:
        service.output_format = data.output_format
    if data.validation_required is not None:
        service.validation_required = data.validation_required
    if data.require_dob is not None:
        service.require_dob = data.require_dob
    if data.require_ssn is not None:
        service.require_ssn = data.require_ssn
    if data.require_address is not None:
        service.require_address = data.require_address
    if data.require_phone is not None:
        service.require_phone = data.require_phone
    if data.require_name is not None:
        service.require_name = data.require_name
    if data.validation_config is not None:
        service.validation_config = data.validation_config
    if data.icon is not None:
        service.icon = data.icon
    if data.order is not None:
        service.order = data.order
    if data.is_active is not None:
        service.is_active = data.is_active
    if data.is_featured is not None:
        service.is_featured = data.is_featured
    if data.metadata is not None:
        service.service_metadata = data.metadata
    
    service.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(service)
    
    # Получить категорию для ответа
    cat_result = await db.execute(select(Category).where(Category.id == service.category_id))
    category = cat_result.scalar_one()
    
    # Подсчитать stock
    stock_result = await db.execute(
        select(func.count(StockItem.id)).where(
            StockItem.service_id == service.id,
            StockItem.is_available == True
        )
    )
    stock_count = stock_result.scalar() or 0
    
    return ServiceResponse(
        **service.__dict__,
        category_name=category.name,
        category_code=category.code,
        stock_count=stock_count
    )


@router.delete("/{service_id}")
async def delete_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Удалить услугу"""
    
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    await db.delete(service)
    await db.commit()
    
    return {"status": "success", "message": "Service deleted"}


@router.post("/{service_id}/toggle")
async def toggle_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Включить/выключить услугу"""
    
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service.is_active = not service.is_active
    service.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "status": "success",
        "is_active": service.is_active,
        "message": f"Service {'activated' if service.is_active else 'deactivated'}"
    }

