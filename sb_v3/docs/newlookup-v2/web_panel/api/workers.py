"""
API для управления воркерами
"""

from typing import List, Optional
from datetime import datetim, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from web_panel.auth import get_current_user, require_page_access
from web_panel.database import get_db
from web_panel.constants.categories import ALL_CATEGORIES, CATEGORIES_DATA
from shared.database.models import User, Order, Worker, BulkOrderItem, WorkerViolation, WorkerOrder

router = APIRouter()


def validate_worker_rate_fields(fixed_price: Optional[float], commission_percent: Optional[float]) -> None:
    fixed = fixed_price if fixed_price is not None else 0
    commission = commission_percent if commission_percent is not None else 0
    if fixed and commission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose either fixed_price or commission_percent, not both",
        )
    if fixed is not None and fixed < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fixed_price cannot be negative")
    if commission_percent is not None and not (0 <= commission_percent <= 100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="commission_percent must be between 0 and 100",
        )


async def calculate_worker_earnings(db: AsyncSession, worker_id: int, from_date: datetime = None) -> float:
    """
    Рассчитать общий заработок воркера с учетом NF элементов в bulk заказах

    Args:
        db: Database session
        worker_id: ID воркера
        from_date: Начальная дата для фильтрации заказов (опционально)

    Returns:
        float: Общий заработок
    """
    from web_panel.api.orders import calculate_order_income

    # Получаем все выполненные заказы воркера
    query = select(Order).where(
        Order.worker_id == worker_id,
        Order.status == "completed"
    )

    if from_date:
        query = query.where(Order.created_at >= from_date)

    result = await db.execute(query)
    completed_orders = result.scalars().all()

    # Рассчитываем общий заработок
    total_earned = 0.0
    for order in completed_orders:
        if order.is_bulk:
            # Для bulk заказов загружаем элементы
            bulk_items_query = select(BulkOrderItem).where(BulkOrderItem.order_id == order.id)
            bulk_items_result = await db.execute(bulk_items_query)
            bulk_items = bulk_items_result.scalars().all()
            total_earned += calculate_order_income(order, bulk_items)
        else:
            # Для single заказов берем полную цену
            total_earned += float(order.price)

    return total_earned


class WorkerCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    categories: List[str]
    services: Optional[List[str]] = []
    can_load_products: Optional[bool] = False
    fixed_price: Optional[float] = None
    commission_percent: Optional[float] = None


class WorkerUpdate(BaseModel):
    username: Optional[str] = None
    categories: Optional[List[str]] = None
    services: Optional[List[str]] = None
    is_active: Optional[bool] = None
    can_load_products: Optional[bool] = None
    fixed_price: Optional[float] = None
    commission_percent: Optional[float] = None
    balance: Optional[float] = None


class WorkerResponse(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    categories: List[str]
    services: Optional[List[str]] = []
    is_active: bool
    can_load_products: bool = False
    balance: float
    orders_count: int
    total_earned: float
    created_at: Optional[str] = None
    fixed_price: Optional[float] = None
    commission_percent: Optional[float] = None
    violation_count: int = 0
    is_suspended: bool = False
    suspended_at: Optional[str] = None
    suspended_reason: Optional[str] = None


class WorkerViolationResponse(BaseModel):
    id: int
    worker_id: int
    order_id: Optional[int] = None
    violation_type: str
    original_text: str
    filtered_text: str
    created_at: str


@router.get("/", response_model=List[WorkerResponse])
async def get_workers(
    status_filter: Optional[str] = None,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список воркеров
    """
    
    query = select(Worker)
    
    if status_filter == "active":
        query = query.where(Worker.is_active == True)
    elif status_filter == "inactive":
        query = query.where(Worker.is_active == False)
    
    result = await db.execute(query)
    workers = result.scalars().all()
    
    # Преобразуем в формат ответа
    worker_responses = []
    for worker in workers:
        # Получаем статистику заказов для воркера
        orders_query = select(func.count(Order.id)).where(Order.worker_id == worker.id)
        orders_result = await db.execute(orders_query)
        orders_count = orders_result.scalar() or 0
        
        # total_earned из БД (начисляется при завершении заказа) или расчёт для старых данных
        total_earned = float(worker.total_earned or 0) if getattr(worker, 'total_earned', None) else await calculate_worker_earnings(db, worker.id)
        
        worker_responses.append(WorkerResponse(
            id=worker.id,
            telegram_id=worker.telegram_id,
            username=worker.username,
            categories=worker.categories or [],
            services=worker.services or [],
            is_active=worker.is_active,
            can_load_products=getattr(worker, 'can_load_products', False),
            balance=float(worker.balance),
            orders_count=orders_count,
            total_earned=total_earned,
            created_at=worker.created_at.isoformat() if worker.created_at else None,
            fixed_price=float(worker.fixed_price) if getattr(worker, 'fixed_price', None) else None,
            commission_percent=float(worker.commission_percent) if getattr(worker, 'commission_percent', None) else None,
            violation_count=int(getattr(worker, "violation_count", 0) or 0),
            is_suspended=bool(getattr(worker, "is_suspended", False)),
            suspended_at=worker.suspended_at.isoformat() if getattr(worker, "suspended_at", None) else None,
            suspended_reason=getattr(worker, "suspended_reason", None),
        ))
    
    return worker_responses


@router.post("/", response_model=WorkerResponse)
async def create_worker(
    worker: WorkerCreate,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать нового воркера
    """
    
    # Проверяем, что воркер с таким telegram_id не существует
    existing_worker_query = select(Worker).where(Worker.telegram_id == worker.telegram_id)
    existing_worker_result = await db.execute(existing_worker_query)
    existing_worker = existing_worker_result.scalar_one_or_none()
    
    if existing_worker:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker with Telegram ID {worker.telegram_id} already exists"
        )
    
    validate_worker_rate_fields(worker.fixed_price, worker.commission_percent)

    from decimal import Decimal
    new_worker = Worker(
        telegram_id=worker.telegram_id,
        username=worker.username,
        categories=worker.categories,
        services=worker.services or [],
        balance=0.00,
        orders_completed=0,
        is_active=True,
        can_load_products=worker.can_load_products or False,
        fixed_price=Decimal(str(worker.fixed_price)) if worker.fixed_price is not None else None,
        commission_percent=worker.commission_percent,
    )
    
    db.add(new_worker)
    await db.commit()
    await db.refresh(new_worker)
    
    # Возвращаем созданного воркера
    return WorkerResponse(
        id=new_worker.id,
        telegram_id=new_worker.telegram_id,
        username=new_worker.username,
        categories=new_worker.categories or [],
        services=new_worker.services or [],
        is_active=new_worker.is_active,
        can_load_products=new_worker.can_load_products,
        balance=float(new_worker.balance),
        orders_count=0,
        total_earned=0.0,
        created_at=new_worker.created_at.isoformat() if new_worker.created_at else None,
        fixed_price=float(new_worker.fixed_price) if getattr(new_worker, 'fixed_price', None) else None,
        commission_percent=float(new_worker.commission_percent) if getattr(new_worker, 'commission_percent', None) else None,
        violation_count=int(getattr(new_worker, "violation_count", 0) or 0),
        is_suspended=bool(getattr(new_worker, "is_suspended", False)),
        suspended_at=new_worker.suspended_at.isoformat() if getattr(new_worker, "suspended_at", None) else None,
        suspended_reason=getattr(new_worker, "suspended_reason", None),
    )


@router.get("/categories")
async def get_worker_categories(
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список доступных категорий для воркеров с сервисами.
    Hardcoded categories + dynamic AccountCategory from DB.
    """
    from shared.database.models import AccountCategory, AccountItem

    categories = []
    for category_key, category_data in CATEGORIES_DATA.items():
        all_services = []
        for subcategory_name, services in category_data["services"].items():
            for service in services:
                if isinstance(service, dict):
                    all_services.append({
                        "code": service["code"],
                        "name": service["name"],
                        "display_name": service["name"],
                        "subcategory": subcategory_name
                    })
                else:
                    all_services.append({
                        "code": service,
                        "name": service,
                        "display_name": service,
                        "subcategory": subcategory_name
                    })

        if category_key == "🧾 Subscriptions / Accounts":
            db_cats = await db.execute(
                select(AccountCategory)
                .where(AccountCategory.is_active == True)
                .order_by(AccountCategory.position)
            )
            for cat in db_cats.scalars().all():
                db_items = await db.execute(
                    select(AccountItem)
                    .where(AccountItem.category_code == cat.code, AccountItem.is_active == True)
                    .order_by(AccountItem.position)
                )
                for item in db_items.scalars().all():
                    code = f"acc_db_{item.id}"
                    if not any(s["code"] == code for s in all_services):
                        all_services.append({
                            "code": code,
                            "name": item.name,
                            "display_name": f"{item.name} ({cat.name})",
                            "subcategory": cat.name,
                        })

        categories.append({
            "id": category_key,
            "name": category_key,
            "code": category_key,
            "display_name": category_data["name"],
            "emoji": category_data["emoji"],
            "services": all_services,
            "services_count": len(all_services)
        })

    return categories


@router.get("/stats")
async def get_worker_stats(
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику воркеров
    """
    total_workers = int(await db.scalar(select(func.count(Worker.id))) or 0)
    active_workers = int(
        await db.scalar(select(func.count(Worker.id)).where(Worker.is_active == True, Worker.is_suspended == False))
        or 0
    )
    total_orders_processed = int(
        await db.scalar(select(func.count(WorkerOrder.id)).where(WorkerOrder.status == "completed"))
        or 0
    )
    total_earnings = float(await db.scalar(select(func.coalesce(func.sum(Worker.total_earned), 0))) or 0)
    average_completion = float(
        await db.scalar(select(func.coalesce(func.avg(Worker.orders_completed), 0)))
        or 0
    )
    return {
        "total_workers": total_workers,
        "active_workers": active_workers,
        "total_orders_processed": total_orders_processed,
        "total_earnings": total_earnings,
        "average_rating": round(average_completion, 2),
    }


@router.get("/violations/recent", response_model=List[WorkerViolationResponse])
async def get_recent_violations(
    limit: int = 50,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkerViolation)
        .order_by(WorkerViolation.created_at.desc())
        .limit(max(1, min(limit, 200)))
    )
    return [
        WorkerViolationResponse(
            id=row.id,
            worker_id=row.worker_id,
            order_id=row.order_id,
            violation_type=row.violation_type,
            original_text=row.original_text,
            filtered_text=row.filtered_text,
            created_at=row.created_at.isoformat(),
        )
        for row in result.scalars().all()
    ]


@router.get("/{worker_id}/violations", response_model=List[WorkerViolationResponse])
async def get_worker_violations(
    worker_id: int,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    worker = await db.scalar(select(Worker).where(Worker.id == worker_id))
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    result = await db.execute(
        select(WorkerViolation)
        .where(WorkerViolation.worker_id == worker_id)
        .order_by(WorkerViolation.created_at.desc())
    )
    return [
        WorkerViolationResponse(
            id=row.id,
            worker_id=row.worker_id,
            order_id=row.order_id,
            violation_type=row.violation_type,
            original_text=row.original_text,
            filtered_text=row.filtered_text,
            created_at=row.created_at.isoformat(),
        )
        for row in result.scalars().all()
    ]


@router.get("/{worker_id}")
async def get_worker(
    worker_id: int,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о воркере
    """
    
    # Получаем воркера из БД
    worker_query = select(Worker).where(Worker.id == worker_id)
    worker_result = await db.execute(worker_query)
    worker = worker_result.scalar_one_or_none()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Получаем статистику заказов для воркера
    orders_query = select(func.count(Order.id)).where(Order.worker_id == worker.id)
    orders_result = await db.execute(orders_query)
    orders_count = orders_result.scalar() or 0
    
    # Получаем общий заработок с учетом NF элементов
    total_earned = await calculate_worker_earnings(db, worker.id)

    return WorkerResponse(
        id=worker.id,
        telegram_id=worker.telegram_id,
        username=worker.username,
        categories=worker.categories or [],
        services=worker.services or [],
        is_active=worker.is_active,
        can_load_products=getattr(worker, 'can_load_products', False),
        balance=float(worker.balance),
        orders_count=orders_count,
        total_earned=total_earned,
        created_at=worker.created_at.isoformat() if worker.created_at else None,
        fixed_price=float(worker.fixed_price) if getattr(worker, 'fixed_price', None) else None,
        commission_percent=float(worker.commission_percent) if getattr(worker, 'commission_percent', None) else None,
        violation_count=int(getattr(worker, "violation_count", 0) or 0),
        is_suspended=bool(getattr(worker, "is_suspended", False)),
        suspended_at=worker.suspended_at.isoformat() if getattr(worker, "suspended_at", None) else None,
        suspended_reason=getattr(worker, "suspended_reason", None),
    )


@router.put("/{worker_id}")
async def update_worker(
    worker_id: int,
    worker_data: WorkerUpdate,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить воркера
    """
    
    # Получаем воркера из БД
    worker_query = select(Worker).where(Worker.id == worker_id)
    worker_result = await db.execute(worker_query)
    existing_worker = worker_result.scalar_one_or_none()
    
    if not existing_worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    next_fixed_price = worker_data.fixed_price if worker_data.fixed_price is not None else (
        float(existing_worker.fixed_price) if getattr(existing_worker, "fixed_price", None) is not None else None
    )
    next_commission = worker_data.commission_percent if worker_data.commission_percent is not None else existing_worker.commission_percent
    validate_worker_rate_fields(next_fixed_price, next_commission)

    # Обновляем данные воркера (только переданные поля)
    if worker_data.username is not None:
        existing_worker.username = worker_data.username
    if worker_data.categories is not None:
        existing_worker.categories = worker_data.categories
    if worker_data.services is not None:
        existing_worker.services = worker_data.services
    if worker_data.is_active is not None:
        existing_worker.is_active = worker_data.is_active
    if worker_data.can_load_products is not None:
        existing_worker.can_load_products = worker_data.can_load_products
    if worker_data.fixed_price is not None:
        existing_worker.fixed_price = Decimal(str(worker_data.fixed_price)) if worker_data.fixed_price else None
    if worker_data.commission_percent is not None:
        existing_worker.commission_percent = worker_data.commission_percent
    if worker_data.balance is not None:
        existing_worker.balance = Decimal(str(worker_data.balance))
    
    await db.commit()
    await db.refresh(existing_worker)
    
    # Получаем статистику заказов для воркера
    orders_query = select(func.count(Order.id)).where(Order.worker_id == existing_worker.id)
    orders_result = await db.execute(orders_query)
    orders_count = orders_result.scalar() or 0
    
    # Получаем общий заработок с учетом NF элементов
    total_earned = await calculate_worker_earnings(db, existing_worker.id)

    return WorkerResponse(
        id=existing_worker.id,
        telegram_id=existing_worker.telegram_id,
        username=existing_worker.username,
        categories=existing_worker.categories or [],
        services=existing_worker.services or [],
        is_active=existing_worker.is_active,
        can_load_products=getattr(existing_worker, 'can_load_products', False),
        balance=float(existing_worker.balance),
        orders_count=orders_count,
        total_earned=total_earned,
        created_at=existing_worker.created_at.isoformat() if existing_worker.created_at else None,
        fixed_price=float(existing_worker.fixed_price) if getattr(existing_worker, 'fixed_price', None) else None,
        commission_percent=float(existing_worker.commission_percent) if getattr(existing_worker, 'commission_percent', None) else None,
        violation_count=int(getattr(existing_worker, "violation_count", 0) or 0),
        is_suspended=bool(getattr(existing_worker, "is_suspended", False)),
        suspended_at=existing_worker.suspended_at.isoformat() if getattr(existing_worker, "suspended_at", None) else None,
        suspended_reason=getattr(existing_worker, "suspended_reason", None),
    )


@router.delete("/{worker_id}")
async def delete_worker(
    worker_id: int,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Удалить воркера
    """

    # Получаем воркера из БД
    worker_query = select(Worker).where(Worker.id == worker_id)
    worker_result = await db.execute(worker_query)
    worker = worker_result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )

    # Проверяем, есть ли у воркера активные заказы (pending или processing)
    active_orders_query = select(func.count(Order.id)).where(
        Order.worker_id == worker_id,
        Order.status.in_(["pending", "processing"])
    )
    active_orders_result = await db.execute(active_orders_query)
    active_orders_count = active_orders_result.scalar() or 0

    if active_orders_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete worker: {active_orders_count} active orders. Complete or cancel them first."
        )

    # Перед удалением воркера, обнуляем worker_id в его заказах
    # Это необходимо для избежания ошибки foreign key constraint
    from sqlalchemy import update as sql_update

    # Обновляем все заказы воркера, устанавливая worker_id в NULL
    await db.execute(
        sql_update(Order)
        .where(Order.worker_id == worker_id)
        .values(worker_id=None)
    )

    # Коммитим изменения в заказах
    await db.commit()

    # Теперь можно безопасно удалить воркера
    await db.delete(worker)
    await db.commit()

    return {"message": f"Worker {worker.username or worker.telegram_id} deleted"}


@router.get("/{worker_id}/analytics")
async def get_worker_analytics(
    worker_id: int,
    period_days: int = 30,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить аналитику воркера с детализацией по категориям и сервисам
    """

    # Проверяем, что воркер существует
    worker_query = select(Worker).where(Worker.id == worker_id)
    worker_result = await db.execute(worker_query)
    worker = worker_result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )

    # Получаем статистику заказов за указанный период
    from datetime import datetime, timedelt, timezone
    from web_panel.api.orders import calculate_order_income
    from web_panel.constants.categories import get_category_by_service

    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Общая статистика заказов
    orders_query = select(func.count(Order.id)).where(
        Order.worker_id == worker_id,
        Order.created_at >= start_date
    )
    orders_result = await db.execute(orders_query)
    total_orders = orders_result.scalar() or 0

    # Выполненные заказы
    completed_query = select(func.count(Order.id)).where(
        Order.worker_id == worker_id,
        Order.status == "completed",
        Order.created_at >= start_date
    )
    completed_result = await db.execute(completed_query)
    completed_orders = completed_result.scalar() or 0

    # Отмененные заказы
    cancelled_query = select(func.count(Order.id)).where(
        Order.worker_id == worker_id,
        Order.status == "cancelled",
        Order.created_at >= start_date
    )
    cancelled_result = await db.execute(cancelled_query)
    cancelled_orders = cancelled_result.scalar() or 0

    # Заработок с учетом NF элементов
    total_earnings = await calculate_worker_earnings(db, worker_id, from_date=start_date)

    # Получаем статистику заказов в работе
    processing_query = select(func.count(Order.id)).where(
        Order.worker_id == worker_id,
        Order.status.in_(["pending", "processing"]),
        Order.created_at >= start_date
    )
    processing_result = await db.execute(processing_query)
    processing_orders = processing_result.scalar() or 0

    # Средняя стоимость заказа
    avg_order_value = total_earnings / completed_orders if completed_orders > 0 else 0

    # === НОВАЯ ЧАСТЬ: Детализация по категориям и сервисам ===

    # Получаем все заказы воркера за период
    all_orders_query = select(Order).where(
        Order.worker_id == worker_id,
        Order.created_at >= start_date
    )
    all_orders_result = await db.execute(all_orders_query)
    all_orders = all_orders_result.scalars().all()

    # Словари для агрегации данных
    category_stats = {}
    service_stats = {}

    for order in all_orders:
        # Определяем категорию
        category = get_category_by_service(order.service_name) if order.service_name else "Неизвестно"
        service = order.service_name or "Неизвестно"

        # Инициализация статистики для категории
        if category not in category_stats:
            category_stats[category] = {
                "category": category,
                "total_orders": 0,
                "completed": 0,
                "processing": 0,
                "cancelled": 0,
                "earnings": 0.0
            }

        # Инициализация статистики для сервиса
        if service not in service_stats:
            service_stats[service] = {
                "service": service,
                "category": category,
                "total_orders": 0,
                "completed": 0,
                "processing": 0,
                "cancelled": 0,
                "earnings": 0.0
            }

        # Подсчет заказов
        category_stats[category]["total_orders"] += 1
        service_stats[service]["total_orders"] += 1

        # Подсчет по статусам
        if order.status == "completed":
            category_stats[category]["completed"] += 1
            service_stats[service]["completed"] += 1

            # Расчет заработка с учетом bulk и NF элементов
            if order.is_bulk:
                bulk_items_query = select(BulkOrderItem).where(BulkOrderItem.order_id == order.id)
                bulk_items_result = await db.execute(bulk_items_query)
                bulk_items = bulk_items_result.scalars().all()
                earnings = calculate_order_income(order, bulk_items)
            else:
                earnings = float(order.price)

            category_stats[category]["earnings"] += earnings
            service_stats[service]["earnings"] += earnings

        elif order.status in ["pending", "processing"]:
            category_stats[category]["processing"] += 1
            service_stats[service]["processing"] += 1

        elif order.status == "cancelled":
            category_stats[category]["cancelled"] += 1
            service_stats[service]["cancelled"] += 1

    # Преобразуем в список и округляем earnings
    categories_breakdown = []
    for cat_data in category_stats.values():
        cat_data["earnings"] = round(cat_data["earnings"], 2)
        categories_breakdown.append(cat_data)

    # Сортируем по количеству заказов
    categories_breakdown.sort(key=lambda x: x["total_orders"], reverse=True)

    services_breakdown = []
    for svc_data in service_stats.values():
        svc_data["earnings"] = round(svc_data["earnings"], 2)
        services_breakdown.append(svc_data)

    # Сортируем по количеству заказов
    services_breakdown.sort(key=lambda x: x["total_orders"], reverse=True)

    return {
        "worker_id": worker_id,
        "period_days": period_days,
        "worker_info": {
            "id": worker.id,
            "telegram_id": worker.telegram_id,
            "username": worker.username,
            "categories": worker.categories or [],
            "services": worker.services or [],
            "is_active": worker.is_active,
            "can_load_products": getattr(worker, 'can_load_products', False),
            "balance": float(worker.balance)
        },
        "general_stats": {
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "processing_orders": processing_orders,
            "cancelled_orders": cancelled_orders,
            "total_earnings": round(total_earnings, 2),
            "avg_order_value": round(avg_order_value, 2),
            "success_rate": round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 2)
        },
        "by_category": categories_breakdown,
        "by_service": services_breakdown
    }


@router.post("/{worker_id}/toggle")
async def toggle_worker_status(
    worker_id: int,
    current_user: dict = Depends(require_page_access("workers")),
    db: AsyncSession = Depends(get_db)
):
    """
    Переключить статус воркера (активен/неактивен)
    """
    
    # Проверяем, что воркер существует
    worker_query = select(Worker).where(Worker.id == worker_id)
    worker_result = await db.execute(worker_query)
    worker = worker_result.scalar_one_or_none()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Переключаем статус
    worker.is_active = not worker.is_active
    await db.commit()
    
    return {"message": f"Worker {'activated' if worker.is_active else 'deactivated'}"}