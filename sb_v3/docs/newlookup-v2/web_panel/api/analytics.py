"""
API для аналитики
"""

from datetime import datetime, timedelt, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    BruteBankItem,
    BruteBankOrder,
    MirrorBot,
    Order,
    Product,
    ProductPurchase,
    Seller,
    SellerBank,
    SellerCCItem,
    SellerCCOrder,
    SellerOrder,
    SupportTicket,
    Transaction,
    User,
    Worker,
)
from web_panel.auth import get_current_user, require_page_access
from web_panel.constants.categories import (
    CATEGORIES_DATA,
    PRODUCT_CATEGORY_MAPPING,
    get_category_by_bot_category,
    get_category_by_service,
)
from web_panel.database import get_db

router = APIRouter()

SELLER_COMPLETED_STATUSES = {"completed", "settled"}
SELLER_ACTIVE_STATUSES = {"pending_admin", "approved", "in_progress"}


def _resolve_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
    period_days: int,
):
    now = datetime.now(timezone.utc)

    if date_from:
        start_dt = datetime.strptime(date_from, "%Y-%m-%d")
    elif date_to:
        end_base = datetime.strptime(date_to, "%Y-%m-%d")
        start_dt = end_base - timedelta(days=max(period_days - 1, 0))
    else:
        start_dt = now - timedelta(days=period_days)

    if date_to:
        end_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
    else:
        end_dt = now + timedelta(seconds=1)

    # VAL-1: Validate date range to prevent DoS via expensive queries
    # Max range: 365 days (1 year)
    MAX_DATE_RANGE_DAYS = 365
    date_range = end_dt - start_dt
    if date_range.days > MAX_DATE_RANGE_DAYS:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Date range cannot exceed {MAX_DATE_RANGE_DAYS} days (requested: {date_range.days} days)"
        )

    return start_dt, end_dt


def _period_payload(start_date: datetime, end_date: datetime) -> dict:
    return {
        "date_from": start_date.strftime("%Y-%m-%d"),
        "date_to": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
    }


def _float(value) -> float:
    return float(value or 0)


def _seller_name(seller: Optional[Seller]) -> str:
    if not seller:
        return "Unknown seller"
    return seller.display_name or seller.username or f"seller_{seller.id}"


def _worker_name(worker: Optional[Worker]) -> str:
    if not worker:
        return "Unknown worker"
    return worker.username or f"worker_{worker.telegram_id}"


def _empty_seller_bucket(seller: Seller) -> dict:
    return {
        "seller_id": seller.id,
        "seller_name": _seller_name(seller),
        "orders_total": 0,
        "completed_orders": 0,
        "items_sold": 0,
        "gross_sales": 0.0,
        "seller_payout": 0.0,
        "active_listings": 0,
    }


async def _count_active_users(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
) -> int:
    user_ids: set[int] = set()
    sources = [
        select(User.user_id).where(User.created_at >= start_date, User.created_at < end_date),
        select(Order.user_id).where(Order.created_at >= start_date, Order.created_at < end_date),
        select(Transaction.user_id).where(Transaction.created_at >= start_date, Transaction.created_at < end_date),
        select(ProductPurchase.user_id).where(ProductPurchase.purchased_at >= start_date, ProductPurchase.purchased_at < end_date),
        select(SupportTicket.user_id).where(SupportTicket.created_at >= start_date, SupportTicket.created_at < end_date),
        select(SellerOrder.buyer_user_id).where(SellerOrder.created_at >= start_date, SellerOrder.created_at < end_date),
        select(SellerCCOrder.buyer_user_id).where(SellerCCOrder.created_at >= start_date, SellerCCOrder.created_at < end_date),
        select(BruteBankOrder.buyer_user_id).where(BruteBankOrder.created_at >= start_date, BruteBankOrder.created_at < end_date),
    ]

    for stmt in sources:
        result = await db.execute(stmt)
        user_ids.update(int(value) for value in result.scalars().all() if value is not None)

    return len(user_ids)


def _ensure_category_bucket(categories_stats: dict, category: str) -> dict:
    if category not in categories_stats:
        categories_stats[category] = {
            "category": category,
            "total_orders": 0,
            "completed": 0,
            "pending": 0,
            "processing": 0,
            "cancelled": 0,
            "revenue": 0.0,
            "product_purchases": 0,
            "product_revenue": 0.0,
        }
    return categories_stats[category]


@router.get("/stats/summary")
async def get_summary_stats(
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить суммарную статистику по периодам
    """

    async def get_period_stats(start_date: datetime, end_date: datetime):
        new_users_result = await db.execute(
            select(func.count(User.id)).where(User.created_at >= start_date, User.created_at < end_date)
        )
        new_users = new_users_result.scalar() or 0

        new_bots_result = await db.execute(
            select(func.count(MirrorBot.id)).where(
                and_(MirrorBot.is_active == True, MirrorBot.created_at >= start_date, MirrorBot.created_at < end_date)
            )
        )
        new_bots = new_bots_result.scalar() or 0

        orders_result = await db.execute(
            select(func.count(Order.id)).where(Order.created_at >= start_date, Order.created_at < end_date)
        )
        total_orders = orders_result.scalar() or 0

        revenue_result = await db.execute(
            select(func.sum(Order.price)).where(
                and_(Order.created_at >= start_date, Order.status == "completed"),
                Order.created_at < end_date,
            )
        )
        revenue = _float(revenue_result.scalar())

        product_purchases_result = await db.execute(
            select(func.count(ProductPurchase.id)).where(
                ProductPurchase.purchased_at >= start_date,
                ProductPurchase.purchased_at < end_date,
            )
        )
        product_purchases = product_purchases_result.scalar() or 0

        product_revenue_result = await db.execute(
            select(func.sum(Product.price))
            .join(ProductPurchase, ProductPurchase.product_id == Product.id)
            .where(ProductPurchase.purchased_at >= start_date, ProductPurchase.purchased_at < end_date)
        )
        product_revenue = _float(product_revenue_result.scalar())

        new_users_balance_result = await db.execute(
            select(func.sum(User.balance)).where(User.created_at >= start_date, User.created_at < end_date)
        )
        new_users_balance = _float(new_users_balance_result.scalar())

        return {
            "new_users": new_users,
            "new_bots": new_bots,
            "total_orders": total_orders,
            "revenue": revenue,
            "product_purchases": product_purchases,
            "product_revenue": product_revenue,
            "total_revenue": revenue + product_revenue,
            "new_users_balance": new_users_balance,
        }

    start_dt, end_dt = _resolve_date_range(date_from, date_to, period_days)
    stats = await get_period_stats(start_dt, end_dt)

    return {
        "period": _period_payload(start_dt, end_dt),
        "stats": stats,
    }


async def _build_enhanced_overview(
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    db: Optional[AsyncSession] = None,
):
    if db is None:
        raise RuntimeError("Database session is required")
    start_date, end_date = _resolve_date_range(date_from, date_to, period_days)

    core_gmv_result = await db.execute(
        select(func.sum(Order.price)).where(
            Order.status == "completed",
            Order.created_at >= start_date,
            Order.created_at < end_date,
        )
    )
    core_gmv = _float(core_gmv_result.scalar())

    product_gmv_result = await db.execute(
        select(func.sum(Product.price))
        .join(ProductPurchase, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.purchased_at >= start_date, ProductPurchase.purchased_at < end_date)
    )
    product_gmv = _float(product_gmv_result.scalar())

    seller_bank_gmv_result = await db.execute(
        select(func.sum(SellerOrder.price_for_buyer)).where(
            SellerOrder.status.in_(sorted(SELLER_COMPLETED_STATUSES)),
            SellerOrder.created_at >= start_date,
            SellerOrder.created_at < end_date,
        )
    )
    seller_bank_gmv = _float(seller_bank_gmv_result.scalar())
    seller_bank_payout_result = await db.execute(
        select(func.sum(SellerOrder.price_for_seller)).where(
            SellerOrder.status.in_(sorted(SELLER_COMPLETED_STATUSES)),
            SellerOrder.created_at >= start_date,
            SellerOrder.created_at < end_date,
        )
    )
    seller_bank_payout = _float(seller_bank_payout_result.scalar())

    seller_cc_gmv_result = await db.execute(
        select(func.sum(SellerCCOrder.price_for_buyer)).where(
            SellerCCOrder.status.in_(sorted(SELLER_COMPLETED_STATUSES)),
            SellerCCOrder.created_at >= start_date,
            SellerCCOrder.created_at < end_date,
        )
    )
    seller_cc_gmv = _float(seller_cc_gmv_result.scalar())
    seller_cc_payout_result = await db.execute(
        select(func.sum(SellerCCOrder.price_for_seller)).where(
            SellerCCOrder.status.in_(sorted(SELLER_COMPLETED_STATUSES)),
            SellerCCOrder.created_at >= start_date,
            SellerCCOrder.created_at < end_date,
        )
    )
    seller_cc_payout = _float(seller_cc_payout_result.scalar())

    brute_gmv_result = await db.execute(
        select(func.sum(BruteBankOrder.price_for_buyer)).where(
            BruteBankOrder.status == "completed",
            BruteBankOrder.created_at >= start_date,
            BruteBankOrder.created_at < end_date,
        )
    )
    brute_gmv = _float(brute_gmv_result.scalar())
    brute_payout_result = await db.execute(
        select(func.sum(BruteBankOrder.price_for_seller)).where(
            BruteBankOrder.status == "completed",
            BruteBankOrder.created_at >= start_date,
            BruteBankOrder.created_at < end_date,
        )
    )
    brute_payout = _float(brute_payout_result.scalar())

    topups_result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.type == "topup",
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date,
        )
    )
    topups_total = _float(topups_result.scalar())

    category_revenue: dict[str, float] = {}

    order_category_result = await db.execute(
        select(Order.category, Order.service_name, func.sum(Order.price))
        .where(
            Order.status == "completed",
            Order.created_at >= start_date,
            Order.created_at < end_date,
        )
        .group_by(Order.category, Order.service_name)
    )
    for bot_category, service_name, revenue in order_category_result.fetchall():
        category = get_category_by_service(service_name)
        if category == "Неизвестно":
            category = get_category_by_bot_category(bot_category)
        category_revenue[category] = category_revenue.get(category, 0.0) + _float(revenue)

    product_category_result = await db.execute(
        select(Product.category, func.sum(Product.price))
        .join(ProductPurchase, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.purchased_at >= start_date, ProductPurchase.purchased_at < end_date)
        .group_by(Product.category)
    )
    for product_category, revenue in product_category_result.fetchall():
        category = PRODUCT_CATEGORY_MAPPING.get(product_category, product_category or "Товары")
        category_revenue[category] = category_revenue.get(category, 0.0) + _float(revenue)

    seller_bank_category_result = await db.execute(
        select(SellerBank.category, func.sum(SellerOrder.price_for_buyer))
        .join(SellerBank, SellerOrder.seller_bank_id == SellerBank.id)
        .where(
            SellerOrder.status.in_(sorted(SELLER_COMPLETED_STATUSES)),
            SellerOrder.created_at >= start_date,
            SellerOrder.created_at < end_date,
        )
        .group_by(SellerBank.category)
    )
    for category_key, revenue in seller_bank_category_result.fetchall():
        label = f"Seller Bank / {category_key or 'other'}"
        category_revenue[label] = category_revenue.get(label, 0.0) + _float(revenue)

    seller_cc_category_result = await db.execute(
        select(SellerCCItem.category_code, func.sum(SellerCCOrder.price_for_buyer))
        .join(SellerCCItem, SellerCCOrder.seller_cc_item_id == SellerCCItem.id)
        .where(
            SellerCCOrder.status.in_(sorted(SELLER_COMPLETED_STATUSES)),
            SellerCCOrder.created_at >= start_date,
            SellerCCOrder.created_at < end_date,
        )
        .group_by(SellerCCItem.category_code)
    )
    for category_key, revenue in seller_cc_category_result.fetchall():
        label = f"Seller CC / {category_key or 'other'}"
        category_revenue[label] = category_revenue.get(label, 0.0) + _float(revenue)

    brute_category_result = await db.execute(
        select(BruteBankItem.category, func.sum(BruteBankOrder.price_for_buyer))
        .join(BruteBankItem, BruteBankOrder.brute_bank_item_id == BruteBankItem.id)
        .where(
            BruteBankOrder.status == "completed",
            BruteBankOrder.created_at >= start_date,
            BruteBankOrder.created_at < end_date,
        )
        .group_by(BruteBankItem.category)
    )
    for category_key, revenue in brute_category_result.fetchall():
        label = f"Brute Bank / {category_key or 'other'}"
        category_revenue[label] = category_revenue.get(label, 0.0) + _float(revenue)

    seller_leaderboard: dict[int, dict] = {}

    seller_order_result = await db.execute(
        select(SellerOrder, Seller)
        .join(Seller, SellerOrder.seller_id == Seller.id)
        .where(SellerOrder.created_at >= start_date, SellerOrder.created_at < end_date)
    )
    for order, seller in seller_order_result.fetchall():
        bucket = seller_leaderboard.setdefault(seller.id, _empty_seller_bucket(seller))
        bucket["orders_total"] += 1
        if order.status in SELLER_COMPLETED_STATUSES:
            bucket["completed_orders"] += 1
            bucket["items_sold"] += 1
            bucket["gross_sales"] += _float(order.price_for_buyer)
            bucket["seller_payout"] += _float(order.price_for_seller)

    seller_cc_result = await db.execute(
        select(SellerCCOrder, Seller)
        .join(Seller, SellerCCOrder.seller_id == Seller.id)
        .where(SellerCCOrder.created_at >= start_date, SellerCCOrder.created_at < end_date)
    )
    for order, seller in seller_cc_result.fetchall():
        bucket = seller_leaderboard.setdefault(seller.id, _empty_seller_bucket(seller))
        bucket["orders_total"] += 1
        if order.status in SELLER_COMPLETED_STATUSES:
            bucket["completed_orders"] += 1
            bucket["items_sold"] += 1
            bucket["gross_sales"] += _float(order.price_for_buyer)
            bucket["seller_payout"] += _float(order.price_for_seller)

    brute_order_result = await db.execute(
        select(BruteBankOrder, Seller)
        .join(Seller, BruteBankOrder.seller_id == Seller.id)
        .where(BruteBankOrder.created_at >= start_date, BruteBankOrder.created_at < end_date)
    )
    for order, seller in brute_order_result.fetchall():
        bucket = seller_leaderboard.setdefault(seller.id, _empty_seller_bucket(seller))
        bucket["orders_total"] += 1
        if order.status == "completed":
            bucket["completed_orders"] += 1
            bucket["items_sold"] += 1
            bucket["gross_sales"] += _float(order.price_for_buyer)
            bucket["seller_payout"] += _float(order.price_for_seller)

    listing_sources = [
        (
            await db.execute(
                select(SellerBank.seller_id, func.count(SellerBank.id))
                .where(SellerBank.is_active == True)
                .group_by(SellerBank.seller_id)
                .limit(5000)
            )
        ).fetchall(),
        (
            await db.execute(
                select(SellerCCItem.seller_id, func.count(SellerCCItem.id))
                .where(SellerCCItem.is_active == True)
                .group_by(SellerCCItem.seller_id)
                .limit(5000)
            )
        ).fetchall(),
        (
            await db.execute(
                select(BruteBankItem.seller_id, func.count(BruteBankItem.id))
                .where(BruteBankItem.is_active == True)
                .group_by(BruteBankItem.seller_id)
                .limit(5000)
            )
        ).fetchall(),
    ]
    for rows in listing_sources:
        for seller_id, count in rows:
            if seller_id not in seller_leaderboard:
                seller = await db.get(Seller, seller_id)
                if not seller:
                    continue
                seller_leaderboard[seller_id] = _empty_seller_bucket(seller)
            seller_leaderboard[seller_id]["active_listings"] += int(count or 0)

    seller_rows = []
    for bucket in seller_leaderboard.values():
        orders_total = bucket["orders_total"]
        completed_orders = bucket["completed_orders"]
        bucket["completion_rate"] = round((completed_orders / orders_total * 100) if orders_total else 0, 2)
        bucket["avg_order_value"] = round((bucket["gross_sales"] / completed_orders) if completed_orders else 0, 2)
        bucket["gross_sales"] = round(bucket["gross_sales"], 2)
        bucket["seller_payout"] = round(bucket["seller_payout"], 2)
        seller_rows.append(bucket)
    seller_rows.sort(key=lambda item: (item["gross_sales"], item["completed_orders"]), reverse=True)
    seller_by_volume = seller_rows[:10]
    seller_by_items = sorted(
        seller_rows,
        key=lambda item: (item["items_sold"], item["gross_sales"], item["active_listings"]),
        reverse=True,
    )[:10]

    worker_rows: dict[int, dict] = {}
    worker_orders_result = await db.execute(
        select(Order, Worker)
        .join(Worker, Order.worker_id == Worker.id)
        .where(
            Order.worker_id.is_not(None),
            Order.created_at >= start_date,
            Order.created_at < end_date,
        )
    )
    for order, worker in worker_orders_result.fetchall():
        bucket = worker_rows.setdefault(
            worker.id,
            {
                "worker_id": worker.id,
                "worker_name": _worker_name(worker),
                "orders_total": 0,
                "completed_orders": 0,
                "cancelled_orders": 0,
                "processing_orders": 0,
                "revenue_processed": 0.0,
                "completion_hours_total": 0.0,
                "completion_samples": 0,
            },
        )
        bucket["orders_total"] += 1
        if order.status == "completed":
            bucket["completed_orders"] += 1
            bucket["revenue_processed"] += _float(order.price)
            started_at = order.taken_at or order.created_at
            if order.completed_at and started_at:
                bucket["completion_hours_total"] += max(
                    (order.completed_at - started_at).total_seconds() / 3600,
                    0,
                )
                bucket["completion_samples"] += 1
        elif order.status == "cancelled":
            bucket["cancelled_orders"] += 1
        elif order.status in {"pending", "processing"}:
            bucket["processing_orders"] += 1

    worker_efficiency = []
    effective_days = max((end_date - start_date).days, 1)
    for bucket in worker_rows.values():
        orders_total = bucket["orders_total"]
        completed_orders = bucket["completed_orders"]
        completion_samples = bucket.pop("completion_samples")
        completion_hours_total = bucket.pop("completion_hours_total")
        bucket["success_rate"] = round((completed_orders / orders_total * 100) if orders_total else 0, 2)
        bucket["avg_completion_hours"] = round(
            (completion_hours_total / completion_samples) if completion_samples else 0,
            2,
        )
        bucket["throughput_per_day"] = round(completed_orders / effective_days, 2)
        bucket["revenue_processed"] = round(bucket["revenue_processed"], 2)
        worker_efficiency.append(bucket)
    worker_efficiency.sort(
        key=lambda item: (item["success_rate"], item["completed_orders"], item["revenue_processed"]),
        reverse=True,
    )

    active_users = {
        "daily": await _count_active_users(db, end_date - timedelta(days=1), end_date),
        "weekly": await _count_active_users(db, end_date - timedelta(days=7), end_date),
        "monthly": await _count_active_users(db, end_date - timedelta(days=30), end_date),
    }

    total_sellers_result = await db.execute(select(func.count(Seller.id)))
    active_sellers_result = await db.execute(
        select(func.count(Seller.id)).where(
            Seller.is_active == True,
            Seller.is_approved == True,
        )
    )
    active_workers_result = await db.execute(select(func.count(Worker.id)).where(Worker.is_active == True))
    open_marketplace_orders_result = await db.execute(
        select(func.count(SellerOrder.id)).where(SellerOrder.status.in_(sorted(SELLER_ACTIVE_STATUSES)))
    )

    total_gmv = core_gmv + product_gmv + seller_bank_gmv + seller_cc_gmv + brute_gmv
    marketplace_gmv = seller_bank_gmv + seller_cc_gmv + brute_gmv
    marketplace_payout_total = seller_bank_payout + seller_cc_payout + brute_payout
    marketplace_margin = marketplace_gmv - marketplace_payout_total
    monthly_active_users = active_users["monthly"]
    arpu_monthly_active = round((total_gmv / monthly_active_users) if monthly_active_users else 0, 2)
    topup_to_gmv_ratio = round((total_gmv / topups_total) if topups_total else 0, 4)

    return {
        "period": _period_payload(start_date, end_date),
        "summary": {
            "gmv_total": round(total_gmv, 2),
            "gmv_core_orders": round(core_gmv, 2),
            "gmv_products": round(product_gmv, 2),
            "gmv_marketplace": round(seller_bank_gmv + seller_cc_gmv + brute_gmv, 2),
            "gmv_seller_banks": round(seller_bank_gmv, 2),
            "gmv_seller_cc": round(seller_cc_gmv, 2),
            "gmv_brute_bank": round(brute_gmv, 2),
            "marketplace_payout_total": round(marketplace_payout_total, 2),
            "marketplace_margin": round(marketplace_margin, 2),
            "marketplace_margin_percent": round((marketplace_margin / marketplace_gmv * 100) if marketplace_gmv else 0, 2),
            "topups_total": round(topups_total, 2),
            "arpu_monthly_active": arpu_monthly_active,
            "topup_to_gmv_ratio": topup_to_gmv_ratio,
            "active_users": active_users,
            "tracked_sellers": total_sellers_result.scalar() or 0,
            "active_sellers": active_sellers_result.scalar() or 0,
            "active_workers": active_workers_result.scalar() or 0,
            "open_marketplace_orders": open_marketplace_orders_result.scalar() or 0,
        },
        "revenue_by_category": [
            {"category": category, "revenue": round(revenue, 2)}
            for category, revenue in sorted(category_revenue.items(), key=lambda item: item[1], reverse=True)
        ],
        "seller_leaderboard": seller_by_volume,
        "seller_leaderboards": {
            "by_sales_volume": seller_by_volume,
            "by_items_sold": seller_by_items,
        },
        "worker_efficiency": worker_efficiency[:10],
    }


@router.get("/overview/enhanced")
async def get_enhanced_overview(
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    return await _build_enhanced_overview(date_from=date_from, date_to=date_to, period_days=period_days, db=db)


@router.get("/overview/detailed")
async def get_detailed_overview(
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    period_days: int = Query(30, description="Период в днях, если даты не заданы"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    return await _build_enhanced_overview(date_from=date_from, date_to=date_to, period_days=period_days, db=db)


@router.get("/orders/by-category")
async def get_orders_by_category(
    period_days: int = Query(7, description="Период в днях"),
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить статистику заказов по категориям
    """

    start_date, end_date = _resolve_date_range(date_from, date_to, period_days)

    orders_result = await db.execute(
        select(
            Order.category,
            Order.service_name,
            Order.status,
            func.count(Order.id).label("count"),
            func.sum(Order.price).label("revenue"),
        )
        .where(Order.created_at >= start_date, Order.created_at < end_date)
        .group_by(Order.category, Order.service_name, Order.status)
    )

    categories_stats = {}

    for bot_category, service_name, status, count, revenue in orders_result.fetchall():
        category = get_category_by_service(service_name)
        if category == "Неизвестно":
            category = get_category_by_bot_category(bot_category)

        bucket = _ensure_category_bucket(categories_stats, category)
        bucket["total_orders"] += int(count or 0)

        if status == "completed":
            bucket["completed"] += int(count or 0)
            bucket["revenue"] += _float(revenue)
        elif status == "pending":
            bucket["pending"] += int(count or 0)
        elif status == "processing":
            bucket["processing"] += int(count or 0)
        elif status == "cancelled":
            bucket["cancelled"] += int(count or 0)

    product_purchases_result = await db.execute(
        select(
            Product.category,
            func.count(ProductPurchase.id).label("count"),
            func.sum(Product.price).label("revenue"),
        )
        .join(ProductPurchase, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.purchased_at >= start_date, ProductPurchase.purchased_at < end_date)
        .group_by(Product.category)
    )

    for product_category, count, revenue in product_purchases_result.fetchall():
        category = PRODUCT_CATEGORY_MAPPING.get(product_category, product_category)
        bucket = _ensure_category_bucket(categories_stats, category)
        bucket["product_purchases"] += int(count or 0)
        bucket["product_revenue"] += _float(revenue)
        bucket["revenue"] += _float(revenue)

    for category in CATEGORIES_DATA.keys():
        _ensure_category_bucket(categories_stats, category)

    return {
        "period": _period_payload(start_date, end_date),
        "categories": list(categories_stats.values()),
    }


@router.get("/orders/timeline")
async def get_orders_timeline(
    period_days: int = Query(30, description="Период в днях"),
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить временную линию заказов
    """

    start_date, end_date = _resolve_date_range(date_from, date_to, period_days)

    orders_result = await db.execute(
        select(
            func.date(Order.created_at).label("date"),
            func.count(Order.id).label("count"),
            func.sum(Order.price).label("revenue"),
        )
        .where(Order.created_at >= start_date, Order.created_at < end_date)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )

    timeline_data = [
        {
            "date": date.strftime("%Y-%m-%d"),
            "orders": count,
            "revenue": _float(revenue),
        }
        for date, count, revenue in orders_result.fetchall()
    ]

    return {
        "period": _period_payload(start_date, end_date),
        "timeline": timeline_data,
    }


@router.get("/users/growth")
async def get_users_growth(
    period_days: int = Query(30, description="Период в днях"),
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить рост пользователей
    """

    start_date, end_date = _resolve_date_range(date_from, date_to, period_days)

    users_result = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(User.created_at >= start_date, User.created_at < end_date)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )

    growth_data = [
        {
            "date": date.strftime("%Y-%m-%d"),
            "new_users": count,
        }
        for date, count in users_result.fetchall()
    ]

    return {
        "period": _period_payload(start_date, end_date),
        "growth": growth_data,
    }


@router.get("/revenue/breakdown")
async def get_revenue_breakdown(
    period_days: int = Query(30, description="Период в днях"),
    date_from: Optional[str] = Query(None, description="Дата начала YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата окончания YYYY-MM-DD"),
    current_user: dict = Depends(require_page_access("analytics")),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить разбивку доходов
    """

    start_date, end_date = _resolve_date_range(date_from, date_to, period_days)

    status_result = await db.execute(
        select(
            Order.status,
            func.count(Order.id).label("count"),
            func.sum(Order.price).label("revenue"),
        )
        .where(Order.created_at >= start_date, Order.created_at < end_date)
        .group_by(Order.status)
    )

    status_breakdown = [
        {
            "status": status,
            "orders": count,
            "revenue": _float(revenue),
        }
        for status, count, revenue in status_result.fetchall()
    ]

    product_revenue_result = await db.execute(
        select(func.sum(Product.price))
        .join(ProductPurchase, ProductPurchase.product_id == Product.id)
        .where(ProductPurchase.purchased_at >= start_date, ProductPurchase.purchased_at < end_date)
    )
    product_revenue_total = _float(product_revenue_result.scalar())

    product_count_result = await db.execute(
        select(func.count(ProductPurchase.id)).where(
            ProductPurchase.purchased_at >= start_date,
            ProductPurchase.purchased_at < end_date,
        )
    )
    product_count = product_count_result.scalar() or 0

    bot_result = await db.execute(
        select(
            MirrorBot.bot_username,
            func.count(Order.id).label("count"),
            func.sum(Order.price).label("revenue"),
        )
        .join(Order, Order.mirror_bot_id == MirrorBot.id)
        .where(Order.created_at >= start_date, Order.created_at < end_date)
        .group_by(MirrorBot.bot_username)
    )

    bot_breakdown = [
        {
            "bot": bot_name or "Unknown",
            "orders": count,
            "revenue": _float(revenue),
        }
        for bot_name, count, revenue in bot_result.fetchall()
    ]

    return {
        "period": _period_payload(start_date, end_date),
        "by_status": status_breakdown,
        "by_bot": bot_breakdown,
        "product_purchases": product_count,
        "product_revenue": product_revenue_total,
    }