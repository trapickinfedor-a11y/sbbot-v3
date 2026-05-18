"""
Сервис для работы с товарами.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelt, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.models import Product, ProductPurchase, ProductRating, Referral, Report, Seller, Transaction, User, TRANSACTION_STATUS_ON_HOLD
from shared.services.guarantee_policy_service import (
    get_product_guarantee_policy,
    is_guarantee_active,
)
from shared.services.ledger_service import LedgerService
from shared.services.nocodb_service import NocoDBService

logger = logging.getLogger(__name__)


def _catalog_visibility_filters() -> tuple:
    return (
        Product.is_available == True,  # noqa: E712
        Product.is_active == True,  # noqa: E712
        Product.moderation_status == "approved",
    )


def _serialize_product(product: Product) -> Dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": float(product.price),
        "file_type": product.file_type,
        "category": product.category,
        "service": product.service,
        "uploaded_by": product.uploaded_by,
    }


def _purchase_status(purchase: ProductPurchase) -> str:
    if purchase.report_status == "reported":
        return "reported"
    if purchase.delivered_at:
        return "delivered"
    return "purchased"


class ProductService:
    """Сервис для работы с товарами"""
    
    @staticmethod
    async def get_products_by_category_service_state(
        session: AsyncSession,
        category: str,
        service: str,
        state: str,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Получить товары по категории, сервису и штату с пагинацией
        """
        
        base_filters = [
            Product.category == category,
            Product.service == service,
            *_catalog_visibility_filters(),
        ]
        if state.upper() != "ANY":
            base_filters.append(Product.state == state.upper())

        query = select(Product).where(and_(*base_filters))
        count_query = select(func.count(Product.id)).where(and_(*base_filters))
        
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Пагинация
        offset = (page - 1) * per_page
        query = query.order_by(Product.created_at.desc()).offset(offset).limit(per_page)
        
        result = await session.execute(query)
        products = result.scalars().all()
        
        # Формируем ответ
        product_list = []
        for product in products:
            product_list.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "file_type": product.file_type,
            })
        
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        return {
            "products": product_list,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    
    @staticmethod
    async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
        """Получить товар по ID"""
        
        result = await session.execute(
            select(Product).where(
                and_(
                    Product.id == product_id,
                    *_catalog_visibility_filters(),
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def purchase_product(
        session: AsyncSession,
        product_id: int,
        user_id: int,
        mirror_bot_id: int
    ) -> Dict[str, Any]:
        """
        Купить товар
        """
        try:
            async with session.begin():
                # Lock the product row first so one item cannot be sold twice.
                result = await session.execute(
                    select(Product)
                    .where(Product.id == product_id)
                    .with_for_update()
                )
                product = result.scalar_one_or_none()
                if not product:
                    return {"success": False, "error": "Product not found or unavailable"}

                user_result = await session.execute(
                    select(User)
                    .where(
                        and_(
                            User.user_id == user_id,
                            User.mirror_bot_id == mirror_bot_id,
                        )
                    )
                    .with_for_update()
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return {"success": False, "error": "User not found"}

                existing_purchase_result = await session.execute(
                    select(ProductPurchase)
                    .where(
                        and_(
                            ProductPurchase.product_id == product_id,
                            ProductPurchase.user_id == user_id,
                        )
                    )
                    .order_by(ProductPurchase.id.desc())
                    .limit(1)
                )
                existing_purchase = existing_purchase_result.scalar_one_or_none()
                if existing_purchase:
                    policy = get_product_guarantee_policy(
                        category=product.category,
                        service=product.service,
                        file_type=product.file_type,
                    )
                    return {
                        "success": True,
                        "purchase_id": existing_purchase.id,
                        "product": _serialize_product(product),
                        "new_balance": float(user.balance),
                        "guarantee_minutes": policy.minutes,
                        "guarantee_until": existing_purchase.guarantee_until,
                        "report_requires_video": policy.report_requires_video,
                    }

                if not product.is_available:
                    return {"success": False, "error": "Product already sold"}

                if not product.is_active:
                    return {"success": False, "error": "Product not available"}

                if product.moderation_status != "approved":
                    return {"success": False, "error": "Product not available"}

                if user.balance < product.price:
                    return {
                        "success": False,
                        "error": "Insufficient balance",
                        "required": float(product.price),
                        "available": float(user.balance),
                    }

                policy = get_product_guarantee_policy(
                    category=product.category,
                    service=product.service,
                    file_type=product.file_type,
                )
                now = datetime.now(timezone.utc)

                guarantee_until = now + timedelta(minutes=policy.minutes)
                charge_tx = await LedgerService.debit_user_balance(
                    session,
                    user_id=user_id,
                    amount=product.price,
                    tx_type="purchase",
                    description=f"Product purchase #{product.id}: {product.name}",
                    related_entity_type="product_purchase",
                    related_entity_id=product_id,
                    status=TRANSACTION_STATUS_ON_HOLD,
                    effective_at=guarantee_until,
                    idempotency_key=LedgerService.build_idempotency_key("product-purchase", product_id, user_id),
                )
                if not charge_tx:
                    return {
                        "success": False,
                        "error": "Insufficient balance",
                        "required": float(product.price),
                        "available": float(user.balance),
                    }

                product.is_available = False
                purchase = ProductPurchase(
                    product_id=product_id,
                    user_id=user_id,
                    purchased_at=now,
                    guarantee_until=guarantee_until,
                )
                session.add(purchase)
                await ProductService._apply_referral_bonus(
                    session=session,
                    user_id=user_id,
                    purchase_amount=product.price,
                )
                await session.flush()

                purchase_id = purchase.id
                guarantee_until = purchase.guarantee_until
                new_balance = float(user.balance)
                product_payload = _serialize_product(product)
                log_payload = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": product.category,
                    "service": product.service,
                    "state": product.state,
                    "price": float(product.price),
                }

            NocoDBService.log_file_operation(
                user_id=user_id,
                action="sell",
                file_id=product_payload["id"],
                category=product_payload["category"],
                extra={
                    "purchase_id": purchase_id,
                    "product_name": product_payload["name"],
                    "service": product_payload["service"],
                    "state": log_payload["state"],
                    "price": log_payload["price"],
                },
            )
            NocoDBService.log_financial_operation(
                user_id=user_id,
                amount=log_payload["price"],
                payment_method="balance",
                tx_id=f"product_purchase:{purchase_id}",
                operation_type="product_purchase",
                extra=log_payload,
            )

            uploaded_by = product_payload.get("uploaded_by") or ""
            if uploaded_by.startswith("worker:"):
                try:
                    from shared.services.notification_service import NotificationService
                    worker_tg_id = int(uploaded_by.split(":")[1])
                    await NotificationService.send(
                        role="worker",
                        user_id=worker_tg_id,
                        text=(
                            f"💰 <b>Ваш товар продан!</b>\n\n"
                            f"📋 <b>{product_payload['name']}</b>\n"
                            f"💵 ${product_payload['price']:.2f}\n"
                            f"📦 Purchase #{purchase_id}"
                        ),
                        event_type="worker_product_sold",
                    )
                except Exception:
                    logger.warning("Failed to notify worker about product sale", exc_info=True)

            return {
                "success": True,
                "purchase_id": purchase_id,
                "product": product_payload,
                "new_balance": new_balance,
                "guarantee_minutes": policy.minutes,
                "guarantee_until": guarantee_until,
                "report_requires_video": policy.report_requires_video,
            }
        except Exception:
            logger.exception("Product purchase failed for product_id=%s user_id=%s", product_id, user_id)
            if session.in_transaction():
                await session.rollback()
            return {"success": False, "error": "Internal error, please try again"}

    @staticmethod
    async def purchase_multiple_by_criteria(
        session: AsyncSession,
        *,
        category: str,
        service: str,
        state: str,
        quantity: int,
        user_id: int,
        mirror_bot_id: int,
        override_unit_price: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Buy up to `quantity` products matching criteria from catalog.
        If override_unit_price is set, product prices are updated to that
        value before purchase so the user is charged the fixed rate.
        Returns {"purchased": [...purchase_ids], "count": N, "total_spent": Decimal, "new_balance": float}
        """
        filters = [
            Product.category == category,
            Product.service == service,
            *_catalog_visibility_filters(),
        ]
        if state.upper() != "ANY":
            filters.append(Product.state == state.upper())

        ids_result = await session.execute(
            select(Product.id)
            .where(and_(*filters))
            .order_by(Product.created_at.asc())
            .limit(quantity)
            .with_for_update(skip_locked=True)
        )
        product_ids = list(ids_result.scalars().all())

        if not product_ids:
            return {"purchased": [], "count": 0, "total_spent": Decimal("0"), "new_balance": 0.0}

        if override_unit_price is not None:
            from sqlalchemy import update as sa_update
            await session.execute(
                sa_update(Product)
                .where(Product.id.in_(product_ids))
                .values(price=override_unit_price)
            )
            await session.flush()

        purchased_ids = []
        total_spent = Decimal("0")
        for pid in product_ids:
            result = await ProductService.purchase_product(
                session=session,
                product_id=pid,
                user_id=user_id,
                mirror_bot_id=mirror_bot_id,
            )
            if result["success"]:
                purchased_ids.append(result["purchase_id"])
                total_spent += Decimal(str(result["product"]["price"]))

        user_result = await session.execute(
            select(User).where(and_(User.user_id == user_id, User.mirror_bot_id == mirror_bot_id))
        )
        user = user_result.scalar_one_or_none()

        return {
            "purchased": purchased_ids,
            "count": len(purchased_ids),
            "total_spent": total_spent,
            "new_balance": float(user.balance) if user else 0.0,
        }

    @staticmethod
    async def _apply_referral_bonus(
        session: AsyncSession,
        *,
        user_id: int,
        purchase_amount: Decimal,
    ) -> None:
        """4-level referral bonus on product purchases. Reuses OrderService chain logic."""
        from mirror_bot.services.order_service import OrderService
        await OrderService._credit_referral_commission(
            session,
            user_id=user_id,
            order_price=purchase_amount,
            order_id=0,
            commit=False,
        )


class ProductServiceV24(ProductService):
    """Compatibility alias for the archive v24 service name."""

    @staticmethod
    async def _apply_referral_bonus(
        session: AsyncSession,
        user_id: int,
        purchase_amount: Decimal,
        mirror_bot_id: Optional[int] = None,
    ) -> None:
        await ProductService._apply_referral_bonus(
            session=session,
            user_id=user_id,
            purchase_amount=purchase_amount,
        )

    @staticmethod
    async def get_purchase(
        session: AsyncSession,
        purchase_id: int,
        *,
        user_id: Optional[int] = None,
    ) -> Optional[ProductPurchase]:
        query = (
            select(ProductPurchase)
            .options(
                selectinload(ProductPurchase.product),
                selectinload(ProductPurchase.user),
            )
            .where(ProductPurchase.id == purchase_id)
        )
        if user_id is not None:
            query = query.where(ProductPurchase.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_purchase_history(
        session: AsyncSession,
        *,
        user_id: int,
        mirror_bot_id: int,
        page: int = 1,
        limit: int = 10,
        category_id: Optional[str] = None,
        seller_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        page = max(1, int(page or 1))
        limit = max(1, min(int(limit or 10), 50))
        filters = [
            ProductPurchase.user_id == user_id,
            User.mirror_bot_id == mirror_bot_id,
        ]
        normalized_category = (category_id or "").strip()
        if normalized_category and normalized_category != "all":
            filters.append(Product.category == normalized_category)
        if seller_id is not None:
            filters.append(Product.seller_id == seller_id)

        count_stmt = (
            select(func.count(ProductPurchase.id))
            .select_from(ProductPurchase)
            .join(User, User.user_id == ProductPurchase.user_id)
            .join(Product, Product.id == ProductPurchase.product_id)
            .where(and_(*filters))
        )
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(ProductPurchase, Seller.display_name, Seller.username)
            .join(User, User.user_id == ProductPurchase.user_id)
            .join(Product, Product.id == ProductPurchase.product_id)
            .outerjoin(Seller, Seller.id == Product.seller_id)
            .options(selectinload(ProductPurchase.product))
            .where(and_(*filters))
            .order_by(ProductPurchase.purchased_at.desc(), ProductPurchase.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()

        items: List[Dict[str, Any]] = []
        for purchase, seller_display_name, seller_username in rows:
            product = purchase.product
            seller_name = (
                seller_display_name
                or seller_username
                or (f"Seller #{product.seller_id}" if product and product.seller_id else "Store")
            )
            items.append(
                {
                    "id": purchase.id,
                    "amount": float(product.price),
                    "status": _purchase_status(purchase),
                    "created_at": purchase.purchased_at,
                    "seller": {
                        "id": product.seller_id,
                        "name": seller_name,
                    },
                    "product": {
                        "id": product.id,
                        "name": product.name,
                        "category_id": product.category,
                        "service_name": product.service,
                        "state": product.state,
                        "file_type": product.file_type,
                        "delivered_at": purchase.delivered_at,
                        "guarantee_until": purchase.guarantee_until,
                    },
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
        }

    @staticmethod
    async def get_user_purchase_filters(
        session: AsyncSession,
        *,
        user_id: int,
        mirror_bot_id: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        base_filters = [
            ProductPurchase.user_id == user_id,
            User.mirror_bot_id == mirror_bot_id,
        ]

        category_stmt = (
            select(Product.category, func.count(ProductPurchase.id))
            .select_from(ProductPurchase)
            .join(User, User.user_id == ProductPurchase.user_id)
            .join(Product, Product.id == ProductPurchase.product_id)
            .where(and_(*base_filters))
            .group_by(Product.category)
            .order_by(Product.category.asc())
        )
        seller_stmt = (
            select(Product.seller_id, Seller.display_name, Seller.username, func.count(ProductPurchase.id))
            .select_from(ProductPurchase)
            .join(User, User.user_id == ProductPurchase.user_id)
            .join(Product, Product.id == ProductPurchase.product_id)
            .outerjoin(Seller, Seller.id == Product.seller_id)
            .where(and_(*base_filters, Product.seller_id.is_not(None)))
            .group_by(Product.seller_id, Seller.display_name, Seller.username)
            .order_by(func.count(ProductPurchase.id).desc(), Product.seller_id.asc())
        )

        categories = [
            {
                "id": category,
                "name": category,
                "count": count,
            }
            for category, count in (await session.execute(category_stmt)).all()
        ]
        sellers = [
            {
                "id": seller_id,
                "name": display_name or username or f"Seller #{seller_id}",
                "count": count,
            }
            for seller_id, display_name, username, count in (await session.execute(seller_stmt)).all()
        ]
        return {"categories": categories, "sellers": sellers}

    @staticmethod
    async def set_archive_channel(
        session: AsyncSession,
        *,
        user_id: int,
        mirror_bot_id: int,
        channel_id: int,
    ) -> bool:
        user = await session.scalar(
            select(User)
            .where(
                and_(
                    User.user_id == user_id,
                    User.mirror_bot_id == mirror_bot_id,
                )
            )
            .with_for_update()
        )
        if not user:
            return False
        user.archive_channel_id = channel_id
        await session.commit()
        return True
    
    @staticmethod
    async def deliver_product_file(
        session: AsyncSession,
        purchase_id: int
    ) -> Dict[str, Any]:
        """
        Доставить файл товара пользователю
        """
        
        # Получаем покупку с товаром
        result = await session.execute(
            select(ProductPurchase)
            .options(selectinload(ProductPurchase.product))
            .where(ProductPurchase.id == purchase_id)
        )
        purchase = result.scalar_one_or_none()
        
        if not purchase:
            return {"success": False, "error": "Purchase not found"}
        
        product = purchase.product
        
        # Проверяем существование файла
        if not os.path.exists(product.file_path):
            return {"success": False, "error": "File not found on server"}

        return {
            "success": True,
            "purchase_id": purchase.id,
            "file_path": product.file_path,
            "file_name": product.file_name,
            "file_type": product.file_type,
            "guarantee_until": purchase.guarantee_until,
            "report_active": is_guarantee_active(purchase.guarantee_until),
        }

    @staticmethod
    async def mark_product_delivered(
        session: AsyncSession,
        purchase_id: int
    ) -> bool:
        result = await session.execute(
            select(ProductPurchase).where(ProductPurchase.id == purchase_id)
        )
        purchase = result.scalar_one_or_none()
        if not purchase or purchase.delivered_at:
            return False

        purchase.delivered_at = datetime.now(timezone.utc)
        await session.commit()
        return True

    @staticmethod
    async def save_rating(
        session: AsyncSession,
        purchase_id: int,
        user_id: int,
        rating: str,
    ) -> bool:
        if rating not in {"like", "dislike"}:
            return False

        purchase = await ProductService.get_purchase(session, purchase_id, user_id=user_id)
        if not purchase or not purchase.delivered_at:
            return False

        existing_result = await session.execute(
            select(ProductRating).where(
                ProductRating.purchase_id == purchase_id,
                ProductRating.user_id == user_id,
            )
        )
        if existing_result.scalar_one_or_none():
            return False

        session.add(
            ProductRating(
                purchase_id=purchase_id,
                user_id=user_id,
                rating=rating,
            )
        )
        await session.commit()
        return True

    @staticmethod
    async def create_report(
        session: AsyncSession,
        purchase_id: int,
        *,
        user_id: int,
        mirror_bot_id: int,
    ) -> Dict[str, Any]:
        purchase = await ProductService.get_purchase(session, purchase_id, user_id=user_id)
        if not purchase:
            return {"success": False, "error": "Purchase not found"}
        if not purchase.delivered_at:
            return {"success": False, "error": "Data has not been revealed yet"}
        if not is_guarantee_active(purchase.guarantee_until):
            return {"success": False, "error": "Guarantee window expired"}
        if purchase.report_status == "reported":
            return {"success": False, "error": "Report already created"}

        product = purchase.product
        report = Report(
            user_id=user_id,
            mirror_bot_id=mirror_bot_id,
            report_type="product",
            subject=f"Product dispute #{purchase.id}: {product.name}",
            message=(
                f"Product purchase #{purchase.id}\n"
                f"Product: {product.name}\n"
                f"Category: {product.category}/{product.service}\n"
                f"Guarantee until: {purchase.guarantee_until}\n"
                "Buyer opened a dispute from the purchase card."
            ),
        )
        purchase.report_status = "reported"
        purchase.reported_at = datetime.now(timezone.utc)
        session.add(report)
        await session.commit()
        return {"success": True, "report_id": report.id}
    
    @staticmethod
    async def _schedule_file_deletion(purchase_id: int, file_path: str):
        """
        Запланировать удаление файла через 1 час
        """
        
        # Ждем 1 час
        await asyncio.sleep(3600)  # 3600 секунд = 1 час
        
        try:
            # Удаляем файл
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"File deleted: {file_path}")
            
            # Обновляем запись в БД (нужна новая сессия)
            from web_panel.database import async_session_maker
            async with async_session_maker() as session:
                await session.execute(
                    update(ProductPurchase)
                    .where(ProductPurchase.id == purchase_id)
                    .values(file_deleted_at=datetime.now(timezone.utc))
                )
                await session.commit()
                
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
    
    @staticmethod
    async def get_available_states_for_service(
        session: AsyncSession,
        category: str,
        service: str
    ) -> List[str]:
        """
        Получить список штатов, для которых есть товары по данному сервису
        """
        
        result = await session.execute(
            select(Product.state)
            .where(
                and_(
                    Product.category == category,
                    Product.service == service,
                    *_catalog_visibility_filters(),
                )
            )
            .distinct()
            .order_by(Product.state)
        )
        
        return [state for state in result.scalars().all()]
    
    @staticmethod
    async def get_product_count_by_state(
        session: AsyncSession,
        category: str,
        service: str,
        state: str
    ) -> int:
        """
        Получить количество доступных товаров для штата
        """
        
        result = await session.execute(
            select(func.count(Product.id))
            .where(
                and_(
                    Product.category == category,
                    Product.service == service,
                    Product.state == state.upper(),
                    *_catalog_visibility_filters(),
                )
            )
        )
        
        return result.scalar() or 0


for _method_name in (
    "get_purchase",
    "get_user_purchase_history",
    "get_user_purchase_filters",
    "set_archive_channel",
    "deliver_product_file",
    "mark_product_delivered",
    "save_rating",
    "create_report",
):
    setattr(ProductService, _method_name, staticmethod(getattr(ProductServiceV24, _method_name)))
