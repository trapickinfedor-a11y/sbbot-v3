from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from shared.database.models import Order, BulkOrderItem, User, Referral, Transaction, TRANSACTION_STATUS_COMPLETED
from decimal import Decimal
from typing import Optional, List, Dict
from datetime import datetime
import logging
from shared.services.nocodb_service import NocoDBService
from shared.services.coupon_service import CouponApplication, CouponService
from shared.services.ledger_service import LedgerService
from shared.services.worker_order_service import WorkerOrderService

logger = logging.getLogger(__name__)

# Import category mapping
try:
    from web_panel.constants.categories import get_category_by_bot_category, get_esim_category
    logger.info("Successfully imported category mapping from web_panel")
except ImportError as e:
    logger.warning(f"Could not import category mapping from web_panel: {e}")
    def get_category_by_bot_category(bot_category: str) -> str:
        """Fallback category mapping"""
        logger.info(f"Using fallback mapping for category: {bot_category}")
        mapping = {
            "lookup": "🔎 Search",
            "lookup_ba": "🔎 Search",
            "credit": "📈 CREDIT REPORTS",
            "credit_reports": "📈 CREDIT REPORTS",  # Добавляем альтернативное название
            "documents": "📄 DOCUMENTS",
            "fullz": "🧰 PROS & FULLZ",
            "banks": "🏦 BANKS",
            "accounts": "🧾 Subscriptions / Accounts",
            "addinfo": "✍️ Add info in CR",
            "esim": "📶 eSIM",
        }
        result = mapping.get(bot_category, bot_category)
        logger.info(f"Fallback mapping: {bot_category} -> {result}")
        return result
    
    def get_esim_category(service_name: str) -> str:
        """Fallback eSIM category detection (синхронно с web_panel.constants.categories)"""
        if service_name.startswith(
            ("sms_", "data_", "esim_cfg_", "esim_gv_", "gv_", "esim_sms_", "esim_data_")
        ):
            return "📶 eSIM"
        return None


class OrderService:
    
    @staticmethod
    async def create_order(
        session: AsyncSession,
        user_id: int,
        mirror_bot_id: int,
        category: str,
        service_name: str,
        input_data: dict,
        price: Decimal,
        original_price: Optional[Decimal] = None,
        coupon_code: Optional[str] = None,
        discount_amount: Optional[Decimal] = None,
        coupon_application: Optional[CouponApplication] = None,
        bulk_items: Optional[List[dict]] = None,
        notify_workers: bool = True,
        notify_channel: bool = True,
        order_type: str = "order",
        eta_minutes: Optional[int] = None,
    ) -> Order:
        started_here = not session.in_transaction()
        auto_refund_discount = False
        if coupon_application is None and coupon_code is None and discount_amount is None:
            coupon_application = await CouponService.calculate_discount(
                session,
                user_id=user_id,
                category=category,
                service_name=service_name,
                amount=price,
            )
            if coupon_application.applied:
                original_price = coupon_application.original_amount
                coupon_code = coupon_application.code
                discount_amount = coupon_application.discount_amount
                price = coupon_application.final_amount
                auto_refund_discount = True

        # Map bot category to support bot category
        logger.info(f"Creating order with bot_category: '{category}', service_name: '{service_name}'")
        
        # Special handling for eSIM (dynamic service names)
        if category == "esim":
            esim_cat = get_esim_category(service_name)
            if esim_cat:
                mapped_category = esim_cat
                logger.info(f"eSIM category mapping: {category} -> {mapped_category}")
            else:
                mapped_category = get_category_by_bot_category(category)
                logger.info(f"eSIM fallback mapping: {category} -> {mapped_category}")
        else:
            mapped_category = get_category_by_bot_category(category)
            logger.info(f"Standard category mapping: {category} -> {mapped_category}")
        
        logger.info(f"Final order category: {mapped_category}")

        async def _build_order() -> Order:
            order = Order(
                user_id=user_id,
                mirror_bot_id=mirror_bot_id,
                category=mapped_category,
                service_name=service_name,
                input_data=input_data,
                price=price,
                original_price=original_price,
                coupon_code=coupon_code,
                discount_amount=discount_amount,
                status="pending",
                is_bulk=bool(bulk_items),
                bulk_count=len(bulk_items) if bulk_items else 1,
                order_type=order_type,
                eta_minutes=eta_minutes,
            )

            session.add(order)
            await session.flush()

            if bulk_items:
                for i, item_data in enumerate(bulk_items, 1):
                    bulk_item = BulkOrderItem(
                        order_id=order.id,
                        item_number=i,
                        input_data=item_data,
                        status="pending"
                    )
                    session.add(bulk_item)

            await WorkerOrderService.ensure_from_order(session, order)

            if auto_refund_discount and coupon_application and coupon_application.discount_amount > 0:
                await OrderService.refund_balance(
                    session,
                    user_id,
                    coupon_application.discount_amount,
                    description=f"Coupon {coupon_application.code} discount for order #{order.id}",
                    commit=False,
                )

            if coupon_application and coupon_application.applied:
                await CouponService.record_redemption(
                    session,
                    user_id=user_id,
                    mirror_bot_id=mirror_bot_id,
                    order=order,
                    application=coupon_application,
                    commit=False,
                )

            await OrderService._credit_referral_commission(
                session,
                user_id,
                order.price,
                order.id,
                commit=False,
            )
            await session.flush()
            return order

        try:
            order = await _build_order()
            if started_here:
                await session.commit()
        except Exception:
            if started_here and session.in_transaction():
                await session.rollback()
            raise

        # Перезагружаем заказ с bulk_items
        if bulk_items:
            result = await session.execute(
                select(Order).where(Order.id == order.id).options(selectinload(Order.bulk_items))
            )
            order = result.scalar_one()
        else:
            await session.refresh(order)

        if coupon_application and coupon_application.applied:
            NocoDBService.log_event(
                event_type="coupon_applied",
                actor_type="buyer",
                actor_id=user_id,
                target_type="order",
                target_id=order.id,
                status="applied",
                payload={
                    "coupon_code": coupon_application.code,
                    "category": category,
                    "service_name": service_name,
                    "original_amount": float(coupon_application.original_amount),
                    "discount_amount": float(coupon_application.discount_amount),
                    "final_amount": float(coupon_application.final_amount),
                },
                timestamp=order.created_at,
            )
        
        # Отправляем уведомления о заказе
        try:
            from shared.services.order_notification_service import OrderNotificationService
            
            # Подготавливаем данные заказа
            order_data = {
                "id": order.id,
                "user_id": order.user_id,
                "mirror_bot_id": order.mirror_bot_id,
                "category": order.category,
                "service_name": order.service_name,
                "price": float(order.price),
                "is_bulk": order.is_bulk,
                "bulk_count": order.bulk_count,
                "created_at": order.created_at.isoformat(),
                "input_data": order.input_data or {}
            }
            
            if notify_workers:
                await OrderNotificationService.notify_new_order(order_data)

            if notify_channel:
                await OrderNotificationService.send_order_to_channel(order_data)
            
        except Exception as e:
            logger.warning(f"Failed to send order notifications: {e}")
        
        # Уведомляем админов о новом заказе
        try:
            from shared.services.admin_notification_service import AdminNotificationService
            await AdminNotificationService.notify_new_order(
                order_id=order.id,
                user_id=order.user_id,
                service_name=order.service_name,
                category=order.category,
                price=float(order.price),
                is_bulk=order.is_bulk,
                bulk_count=order.bulk_count or 1,
                input_data=order.input_data
            )
        except Exception as e:
            logger.warning(f"Failed to send admin notification: {e}")
        
        NocoDBService.log_event(
            event_type="order_created",
            actor_type="buyer",
            actor_id=user_id,
            target_type="order",
            target_id=order.id,
            status=order.status,
            payload={
                "mirror_bot_id": mirror_bot_id,
                "category": order.category,
                "service_name": order.service_name,
                "price": float(order.price),
                "original_price": float(order.original_price) if order.original_price is not None else None,
                "coupon_code": order.coupon_code,
                "discount_amount": float(order.discount_amount) if order.discount_amount is not None else None,
                "is_bulk": order.is_bulk,
                "bulk_count": order.bulk_count,
            },
            timestamp=order.created_at,
        )
        
        return order

    @staticmethod
    async def get_order_pricing(
        session: AsyncSession,
        *,
        user_id: int,
        category: str,
        service_name: str,
        amount: Decimal,
        coupon_code: Optional[str] = None,
        allow_auto_coupon: bool = True,
    ) -> CouponApplication:
        return await CouponService.calculate_discount(
            session,
            user_id=user_id,
            category=category,
            service_name=service_name,
            amount=amount,
            coupon_code=coupon_code,
            allow_auto_coupon=allow_auto_coupon,
        )
    
    @staticmethod
    async def _get_referral_rates(session: AsyncSession) -> dict:
        """Load 4-level referral rates from SystemSetting (key: referral_rates JSON).
        Falls back to defaults: L1=10%, L2=7%, L3=5%, L4=3%."""
        defaults = {"1": 10.0, "2": 7.0, "3": 5.0, "4": 3.0}
        try:
            from shared.database.models import SystemSetting
            import json
            row = await session.scalar(
                select(SystemSetting).where(SystemSetting.key == "referral_rates")
            )
            if row:
                return {**defaults, **json.loads(row.value)}
        except Exception:
            pass
        return defaults

    @staticmethod
    async def _credit_referral_commission(
        session: AsyncSession,
        user_id: int,
        order_price: Decimal,
        order_id: int,
        *,
        commit: bool = True,
    ):
        """4-level referral commission chain.
        Walks up referrer_id chain up to 4 levels, crediting each with
        a configurable % of the purchase amount (stored in SystemSetting.referral_rates).
        """
        rates = await OrderService._get_referral_rates(session)

        current_user_id = user_id
        seen = {user_id}

        for level in range(1, 5):
            rate = float(rates.get(str(level), 0))
            if rate <= 0:
                continue

            user_result = await session.execute(
                select(User).where(User.user_id == current_user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user or not user.referrer_id or user.referrer_id in seen:
                break

            referrer_id = user.referrer_id
            seen.add(referrer_id)

            referrer_result = await session.execute(
                select(User).where(User.user_id == referrer_id).with_for_update()
            )
            referrer = referrer_result.scalar_one_or_none()
            if not referrer or referrer.is_banned:
                break

            commission = (order_price * Decimal(str(rate))) / Decimal("100")
            commission = commission.quantize(Decimal("0.01"))
            if commission <= 0:
                current_user_id = referrer_id
                continue

            await LedgerService.credit_user_balance(
                session,
                user_id=referrer.user_id,
                amount=commission,
                tx_type="referral_commission",
                description=f"Referral L{level} {rate}% from order #{order_id} (buyer {user_id})",
                related_entity_type="order",
                related_entity_id=order_id,
                idempotency_key=LedgerService.build_idempotency_key(
                    f"referral-l{level}-order", order_id, referrer.user_id
                ),
            )

            if level == 1:
                referral_result = await session.execute(
                    select(Referral).where(
                        Referral.referrer_id == referrer.user_id,
                        Referral.referred_id == user_id,
                    )
                )
                referral = referral_result.scalar_one_or_none()
                if referral:
                    referral.earned_total = Decimal(str(referral.earned_total or 0)) + commission

            logger.info(
                "Referral L%d: $%s (%.1f%%) → user %d from order #%d (buyer %d)",
                level, commission, rate, referrer.user_id, order_id, user_id,
            )

            try:
                from shared.services.admin_notification_service import AdminNotificationService
                await AdminNotificationService.notify_balance_update(
                    user_id=referrer.user_id,
                    amount=float(commission),
                    reason=f"Referral L{level} {rate}% from order #{order_id}",
                    admin_username="system/referral",
                )
            except Exception:
                pass

            try:
                from mirror_bot.services.user_service import UserService as _US
                import asyncio as _aio
                _aio.ensure_future(
                    _US._notify_referrer_commission(
                        referrer.user_id, referrer.mirror_bot_id,
                        commission, rate, level,
                        order_price, user_id,
                    )
                )
            except Exception:
                pass

            current_user_id = referrer_id

        if commit:
            await session.commit()

    @staticmethod
    async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 10) -> List[Order]:
        result = await session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def deduct_balance(session: AsyncSession, user_id: int, amount: Decimal) -> bool:
        return await OrderService.charge_balance(
            session,
            user_id,
            amount,
            description=f"Purchase charge ${amount:.2f}",
            commit=True,
        )

    @staticmethod
    async def charge_balance(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        *,
        description: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        status: str = TRANSACTION_STATUS_COMPLETED,
        effective_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = False,
    ) -> bool:
        amount = Decimal(str(amount))

        async def _apply_charge() -> bool:
            tx = await LedgerService.debit_user_balance(
                session,
                user_id=user_id,
                amount=amount,
                tx_type="purchase",
                description=description,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                status=status,
                effective_at=effective_at,
                idempotency_key=idempotency_key,
            )
            if not tx:
                return False
            if not commit:
                await session.flush()
            return True

        if commit and not session.in_transaction():
            async with session.begin():
                success = await _apply_charge()
        else:
            success = await _apply_charge()
            if commit:
                await session.commit()

        if not success:
            return False

        if commit:
            NocoDBService.log_financial_operation(
                user_id=user_id,
                amount=amount,
                payment_method="balance",
                tx_id=description,
                operation_type="purchase",
                extra={"description": description},
            )
        return True
    
    @staticmethod
    async def refund_balance(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        *,
        description: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ):
        amount = Decimal(str(amount))

        async def _apply_refund() -> bool:
            tx = await LedgerService.refund_user_transaction(
                session,
                user_id=user_id,
                amount=amount,
                description=description or f"Refund ${amount:.2f}",
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                idempotency_key=idempotency_key,
            )
            if not tx:
                return False
            if not commit:
                await session.flush()
            return True

        if commit and not session.in_transaction():
            async with session.begin():
                success = await _apply_refund()
        else:
            success = await _apply_refund()
            if commit:
                await session.commit()

        if success and commit:
            NocoDBService.log_financial_operation(
                user_id=user_id,
                amount=amount,
                payment_method="balance",
                tx_id=description or f"refund:{user_id}:{amount}",
                operation_type="refund",
                extra={"description": description or f"Refund ${amount:.2f}"},
            )
        return success

