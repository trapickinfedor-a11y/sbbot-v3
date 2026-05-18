"""
API endpoints для управления товарами
"""

import os
import uuid
import aiofiles
from datetime import datetim, timezone
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from pydantic import BaseModel

from web_panel.auth import require_catalog_read_access, require_catalog_write_access
from web_panel.database import get_db
from shared.database.models import Product, ProductPurchase, ProductCatalogService, ProductModerationLog
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.product_audit_service import log_product_action
from shared.services.product_catalog_service import ProductCatalogManager
from web_panel.services.audit_service import log_action

router = APIRouter()

# Директории для хранения файлов товаров
PRODUCTS_DIR = "uploads/products"
os.makedirs(PRODUCTS_DIR, exist_ok=True)

# Поддерживаемые типы файлов
ALLOWED_FILE_TYPES = {
    'text/plain': 'txt',
    'application/zip': 'zip', 
    'application/x-zip-compressed': 'zip',
    'application/pdf': 'pdf',
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg', 
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp'
}


async def _log_product_moderation_history(
    db: AsyncSession,
    *,
    product: Product,
    moderator_id: Optional[int],
    action: str,
    previous_status: Optional[str],
    new_status: Optional[str],
    comment: Optional[str] = None,
) -> None:
    db.add(
        ProductModerationLog(
            product_id=product.id,
            moderator_id=moderator_id,
            action=action,
            comment=comment,
            previous_status=previous_status,
            new_status=new_status,
        )
    )
    await db.flush()

# Pydantic модели
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str  # docs, pros_fullz
    service: str   # dl_front_back, work_travel, etc
    state: str     # US state code
    price: float

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_available: Optional[bool] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    service: str
    state: str
    price: float
    file_name: str
    file_type: str
    is_available: bool
    created_at: str
    updated_at: str

class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ProductModerationUpdate(BaseModel):
    status: str
    comment: Optional[str] = None


class ProductModerationResponse(BaseModel):
    id: int
    moderation_status: str
    moderation_comment: Optional[str] = None
    moderated_at: Optional[str] = None
    moderated_by: Optional[int] = None


class CatalogServiceCreate(BaseModel):
    category_key: str
    category_name: Optional[str] = None
    menu_group: str
    code: str
    name: str
    description: Optional[str] = None
    order: int = 0
    is_active: bool = True


class CatalogServiceUpdate(BaseModel):
    category_key: Optional[str] = None
    category_name: Optional[str] = None
    menu_group: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class CatalogServiceResponse(BaseModel):
    id: int
    category_key: str
    category_name: Optional[str] = None
    menu_group: str
    code: str
    name: str
    description: Optional[str]
    order: int
    is_active: bool
    created_at: str
    updated_at: str


async def _ensure_valid_catalog_service(db: AsyncSession, category: str, service: str) -> ProductCatalogService:
    catalog_service = await ProductCatalogManager.get_service(db, service)
    if not catalog_service or catalog_service.category_key != category:
        raise HTTPException(status_code=400, detail="Unknown product service for selected category")
    if not catalog_service.is_active:
        raise HTTPException(status_code=400, detail="Selected product service is disabled")
    return catalog_service


def _serialize_product_moderation(product: Product) -> ProductModerationResponse:
    return ProductModerationResponse(
        id=product.id,
        moderation_status=product.moderation_status,
        moderation_comment=product.moderation_comment,
        moderated_at=product.moderated_at.isoformat() if product.moderated_at else None,
        moderated_by=product.moderated_by,
    )


@router.get("/categories")
async def get_product_categories(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("products")),
):
    """Получить список категорий товаров"""
    await ProductCatalogManager.ensure_defaults(db)
    return await ProductCatalogManager.get_categories_payload(db, active_only=True)


@router.get("/catalog-services", response_model=List[CatalogServiceResponse])
async def list_catalog_services(
    category_key: Optional[str] = None,
    menu_group: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("products")),
):
    await ProductCatalogManager.ensure_defaults(db)
    rows = await ProductCatalogManager.list_services(
        db,
        category_key=category_key,
        menu_group=menu_group,
        active_only=False,
    )
    return [
        CatalogServiceResponse(
            id=row.id,
            category_key=row.category_key,
            category_name=getattr(row, "category_name", None),
            menu_group=row.menu_group,
            code=row.code,
            name=row.name,
            description=row.description,
            order=row.order,
            is_active=row.is_active,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
        for row in rows
    ]


@router.post("/catalog-services", response_model=CatalogServiceResponse)
async def create_catalog_service(
    data: CatalogServiceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products")),
):
    await ProductCatalogManager.ensure_defaults(db)
    existing = await ProductCatalogManager.get_service(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Catalog service code already exists")
    service = ProductCatalogService(**data.model_dump())
    db.add(service)
    await log_action(
        db,
        current_user.get("admin_id"),
        "product_catalog_service_create",
        "product_catalog_service",
        None,
        data.model_dump(),
        request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(service)
    return CatalogServiceResponse(
        id=service.id,
        category_key=service.category_key,
        category_name=getattr(service, "category_name", None),
        menu_group=service.menu_group,
        code=service.code,
        name=service.name,
        description=service.description,
        order=service.order,
        is_active=service.is_active,
        created_at=service.created_at.isoformat(),
        updated_at=service.updated_at.isoformat(),
    )


@router.put("/catalog-services/{service_id}", response_model=CatalogServiceResponse)
async def update_catalog_service(
    service_id: int,
    data: CatalogServiceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products")),
):
    result = await db.execute(select(ProductCatalogService).where(ProductCatalogService.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Catalog service not found")
    old_values = {
        "category_key": service.category_key,
        "category_name": getattr(service, "category_name", None),
        "menu_group": service.menu_group,
        "name": service.name,
        "description": service.description,
        "order": service.order,
        "is_active": service.is_active,
    }
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(service, key, value)
    await log_action(
        db,
        current_user.get("admin_id"),
        "product_catalog_service_update",
        "product_catalog_service",
        service.id,
        {"old": old_values, "new": data.model_dump(exclude_none=True)},
        request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(service)
    return CatalogServiceResponse(
        id=service.id,
        category_key=service.category_key,
        category_name=getattr(service, "category_name", None),
        menu_group=service.menu_group,
        code=service.code,
        name=service.name,
        description=service.description,
        order=service.order,
        is_active=service.is_active,
        created_at=service.created_at.isoformat(),
        updated_at=service.updated_at.isoformat(),
    )


@router.delete("/catalog-services/{service_id}")
async def delete_catalog_service(
    service_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products")),
):
    result = await db.execute(select(ProductCatalogService).where(ProductCatalogService.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Catalog service not found")
    await log_action(
        db,
        current_user.get("admin_id"),
        "product_catalog_service_delete",
        "product_catalog_service",
        service.id,
        {
            "code": service.code,
            "name": service.name,
            "category_key": service.category_key,
            "menu_group": service.menu_group,
        },
        request.client.host if request.client else None,
    )
    await db.delete(service)
    await db.commit()
    return {"ok": True}


@router.get("/states")
async def get_states(current_user: dict = Depends(require_catalog_read_access("products"))):
    """Получить список штатов США"""
    states = [
        {"code": "AL", "name": "Alabama"}, {"code": "AK", "name": "Alaska"},
        {"code": "AZ", "name": "Arizona"}, {"code": "AR", "name": "Arkansas"},
        {"code": "CA", "name": "California"}, {"code": "CO", "name": "Colorado"},
        {"code": "CT", "name": "Connecticut"}, {"code": "DE", "name": "Delaware"},
        {"code": "FL", "name": "Florida"}, {"code": "GA", "name": "Georgia"},
        {"code": "HI", "name": "Hawaii"}, {"code": "ID", "name": "Idaho"},
        {"code": "IL", "name": "Illinois"}, {"code": "IN", "name": "Indiana"},
        {"code": "IA", "name": "Iowa"}, {"code": "KS", "name": "Kansas"},
        {"code": "KY", "name": "Kentucky"}, {"code": "LA", "name": "Louisiana"},
        {"code": "ME", "name": "Maine"}, {"code": "MD", "name": "Maryland"},
        {"code": "MA", "name": "Massachusetts"}, {"code": "MI", "name": "Michigan"},
        {"code": "MN", "name": "Minnesota"}, {"code": "MS", "name": "Mississippi"},
        {"code": "MO", "name": "Missouri"}, {"code": "MT", "name": "Montana"},
        {"code": "NE", "name": "Nebraska"}, {"code": "NV", "name": "Nevada"},
        {"code": "NH", "name": "New Hampshire"}, {"code": "NJ", "name": "New Jersey"},
        {"code": "NM", "name": "New Mexico"}, {"code": "NY", "name": "New York"},
        {"code": "NC", "name": "North Carolina"}, {"code": "ND", "name": "North Dakota"},
        {"code": "OH", "name": "Ohio"}, {"code": "OK", "name": "Oklahoma"},
        {"code": "OR", "name": "Oregon"}, {"code": "PA", "name": "Pennsylvania"},
        {"code": "RI", "name": "Rhode Island"}, {"code": "SC", "name": "South Carolina"},
        {"code": "SD", "name": "South Dakota"}, {"code": "TN", "name": "Tennessee"},
        {"code": "TX", "name": "Texas"}, {"code": "UT", "name": "Utah"},
        {"code": "VT", "name": "Vermont"}, {"code": "VA", "name": "Virginia"},
        {"code": "WA", "name": "Washington"}, {"code": "WV", "name": "West Virginia"},
        {"code": "WI", "name": "Wisconsin"}, {"code": "WY", "name": "Wyoming"}
    ]
    return {"states": states}


@router.get("/", response_model=ProductListResponse)
async def get_products(
    page: int = 1,
    per_page: int = 10,
    category: Optional[str] = None,
    service: Optional[str] = None,
    state: Optional[str] = None,
    available_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("products"))
):
    """Получить список товаров с фильтрацией и пагинацией"""
    
    # Базовый запрос
    query = select(Product)
    
    # Применяем фильтры
    filters = []
    if category:
        filters.append(Product.category == category)
    if service:
        filters.append(Product.service == service)
    if state:
        filters.append(Product.state == state)
    if available_only:
        filters.append(Product.is_available == True)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Подсчет общего количества
    count_query = select(func.count(Product.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Пагинация
    offset = (page - 1) * per_page
    query = query.order_by(desc(Product.created_at)).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Формируем ответ
    product_responses = []
    for product in products:
        product_responses.append(ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            category=product.category,
            service=product.service,
            state=product.state,
            price=float(product.price),
            file_name=product.file_name,
            file_type=product.file_type,
            is_available=product.is_available,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat()
        ))
    
    total_pages = (total + per_page - 1) // per_page
    
    return ProductListResponse(
        products=product_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/moderation/pending", response_model=List[ProductResponse])
async def get_pending_moderation_products(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("products"))
):
    result = await db.execute(
        select(Product)
        .where(Product.moderation_status == "pending_moderation")
        .order_by(desc(Product.created_at))
    )
    products = result.scalars().all()
    return [
        ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            category=product.category,
            service=product.service,
            state=product.state,
            price=float(product.price),
            file_name=product.file_name,
            file_type=product.file_type,
            is_available=product.is_available,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat()
        )
        for product in products
    ]


@router.post("/moderation/{product_id}", response_model=ProductModerationResponse)
async def moderate_product(
    product_id: int,
    data: ProductModerationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products"))
):
    valid_statuses = {"approved", "rejected", "changes_requested", "pending_moderation"}
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid moderation status")

    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old_status = product.moderation_status
    old_comment = product.moderation_comment
    product.moderation_status = data.status
    product.moderation_comment = data.comment
    product.moderated_at = datetime.now(timezone.utc)
    product.moderated_by = current_user.get("admin_id")

    await _log_product_moderation_history(
        db,
        product=product,
        moderator_id=current_user.get("admin_id"),
        action="moderate",
        previous_status=old_status,
        new_status=product.moderation_status,
        comment=data.comment or old_comment,
    )
    await db.commit()
    await db.refresh(product)
    try:
        await log_action(
            db,
            current_user.get("admin_id"),
            "product_moderation_update",
            "product",
            product.id,
            {
                "old_status": old_status,
                "new_status": product.moderation_status,
                "comment": data.comment,
            },
            request.client.host if request.client else None,
        )
        await log_product_action(
            db,
            action="moderate",
            actor_type="admin",
            actor_id=current_user.get("admin_id"),
            product=product,
            details={
                "old_status": old_status,
                "new_status": product.moderation_status,
                "comment": data.comment,
            },
        )
    except Exception:
        pass
    return _serialize_product_moderation(product)


@router.post("/", response_model=ProductResponse)
async def create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form(...),
    service: str = Form(...),
    state: str = Form(...),
    price: float = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products"))
):
    """Создать новый товар с файлом"""
    await ProductCatalogManager.ensure_defaults(db)
    await _ensure_valid_catalog_service(db, category, service)
    
    # Проверяем тип файла
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_FILE_TYPES.values())}"
        )
    
    # Генерируем уникальное имя файла
    file_extension = ALLOWED_FILE_TYPES[file.content_type]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(PRODUCTS_DIR, unique_filename)
    
    try:
        # Сохраняем файл
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Создаем запись в БД
        product = Product(
            name=name,
            description=description if description else None,
            category=category,
            service=service,
            state=state.upper(),
            price=Decimal(str(price)),
            file_path=file_path,
            file_name=file.filename or unique_filename,
            file_type=file_extension
        )
        db.add(product)
        await db.flush()
        await _log_product_moderation_history(
            db,
            product=product,
            moderator_id=current_user.get("admin_id"),
            action="create",
            previous_status=None,
            new_status=product.moderation_status,
            comment=product.moderation_comment,
        )
        await db.commit()
        await db.refresh(product)
        try:
            await log_action(
                db,
                current_user.get("admin_id"),
                "product_create",
                "product",
                product.id,
                {
                    "category": product.category,
                    "service": product.service,
                    "state": product.state,
                    "file_name": product.file_name,
                },
                request.client.host if request.client else None,
            )
            await log_product_action(
                db,
                action="create",
                actor_type="admin",
                actor_id=current_user.get("admin_id"),
                product=product,
                details={
                    "category": product.category,
                    "service": product.service,
                    "state": product.state,
                    "file_name": product.file_name,
                },
            )
        except Exception:
            pass
        try:
            await AdminNotificationService.notify_admin_action(
                "NEW PRODUCT PENDING MODERATION",
                [
                    f"📦 <b>Product:</b> {product.name}",
                    f"📂 <b>Category:</b> {product.category}",
                    f"🔧 <b>Service:</b> {product.service}",
                    f"💵 <b>Price:</b> ${float(product.price):.2f}",
                    f"🛡 <b>Status:</b> {product.moderation_status}",
                ],
                event_type="product_pending_moderation",
                urgent=True,
            )
        except Exception:
            pass
            
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            category=product.category,
            service=product.service,
            state=product.state,
            price=float(product.price),
            file_name=product.file_name,
            file_type=product.file_type,
            is_available=product.is_available,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat()
        )
        
    except Exception as e:
        # Удаляем файл если что-то пошло не так
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("products"))
):
    """Получить товар по ID"""
    
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        category=product.category,
        service=product.service,
        state=product.state,
        price=float(product.price),
        file_name=product.file_name,
        file_type=product.file_type,
        is_available=product.is_available,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat()
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products"))
):
    """Обновить товар"""
    
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    old_values = {
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "is_available": product.is_available,
    }
    old_status = product.moderation_status
    old_comment = product.moderation_comment
    description_changed = data.description is not None and data.description != product.description
    # Обновляем поля
    if data.name is not None:
        product.name = data.name
    if data.description is not None:
        product.description = data.description
    if data.price is not None:
        product.price = Decimal(str(data.price))
    if data.is_available is not None:
        product.is_available = data.is_available
    if description_changed:
        product.moderation_status = "pending_moderation"
        product.moderation_comment = None
        product.moderated_at = None
        product.moderated_by = None
    
    await _log_product_moderation_history(
        db,
        product=product,
        moderator_id=current_user.get("admin_id"),
        action="update",
        previous_status=old_status,
        new_status=product.moderation_status,
        comment=product.moderation_comment or old_comment,
    )
    await db.commit()
    await db.refresh(product)
    try:
        await log_action(
            db,
            current_user.get("admin_id"),
            "product_update",
            "product",
            product.id,
            {"old": old_values, "new": data.model_dump(exclude_none=True)},
            request.client.host if request.client else None,
        )
        await log_product_action(
            db,
            action="update",
            actor_type="admin",
            actor_id=current_user.get("admin_id"),
            product=product,
            details={"old": old_values, "new": data.model_dump(exclude_none=True)},
        )
    except Exception:
        pass
    
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        category=product.category,
        service=product.service,
        state=product.state,
        price=float(product.price),
        file_name=product.file_name,
        file_type=product.file_type,
        is_available=product.is_available,
        created_at=product.created_at.isoformat(),
        updated_at=product.updated_at.isoformat()
    )


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_write_access("products"))
):
    """Удалить товар"""
    
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_snapshot = {
        "name": product.name,
        "category": product.category,
        "service": product.service,
        "state": product.state,
        "file_name": product.file_name,
    }
    await _log_product_moderation_history(
        db,
        product=product,
        moderator_id=current_user.get("admin_id"),
        action="delete",
        previous_status=product.moderation_status,
        new_status=None,
        comment=product.moderation_comment,
    )
    try:
        await log_action(
            db,
            current_user.get("admin_id"),
            "product_delete",
            "product",
            product.id,
            product_snapshot,
            request.client.host if request.client else None,
        )
        await log_product_action(
            db,
            action="delete",
            actor_type="admin",
            actor_id=current_user.get("admin_id"),
            product=product,
            details=product_snapshot,
        )
    except Exception:
        pass

    # Удаляем файл
    if os.path.exists(product.file_path):
        os.remove(product.file_path)
    
    # Удаляем из БД
    await db.delete(product)
    await db.commit()
    
    return {"message": "Product deleted successfully"}


@router.get("/{product_id}/download")
async def download_product_file(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_catalog_read_access("products"))
):
    """Скачать файл товара (для админа)"""
    
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not os.path.exists(product.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        await log_action(
            db,
            current_user.get("admin_id"),
            "product_download",
            "product",
            product.id,
            {"file_name": product.file_name},
            request.client.host if request.client else None,
        )
        await log_product_action(
            db,
            action="download",
            actor_type="admin",
            actor_id=current_user.get("admin_id"),
            product=product,
            details={"file_name": product.file_name},
            notify_if_stale=True,
        )
    except Exception:
        pass
    
    return FileResponse(
        path=product.file_path,
        filename=product.file_name,
        media_type='application/octet-stream'
    )


# API для бота
@router.get("/bot/{category}/{service}/{state}")
async def get_products_for_bot(
    category: str,
    service: str,
    state: str,
    page: int = 1,
    per_page: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Получить товары для бота с пагинацией"""
    
    # Фильтруем только доступные товары
    query = select(Product).where(
        and_(
            Product.category == category,
            Product.service == service,
            Product.state == state.upper(),
            Product.is_available == True,
            Product.is_active == True,
            Product.moderation_status == "approved",
        )
    )
    
    # Подсчет общего количества
    count_query = select(func.count(Product.id)).where(
        and_(
            Product.category == category,
            Product.service == service,
            Product.state == state.upper(),
            Product.is_available == True,
            Product.is_active == True,
            Product.moderation_status == "approved",
        )
    )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Пагинация
    offset = (page - 1) * per_page
    query = query.order_by(desc(Product.created_at)).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    # Формируем ответ для бота
    product_list = []
    for product in products:
        product_list.append({
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "file_type": product.file_type
        })
    
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "products": product_list,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }