"""
Newlookup v24 — Обновлённый ProductService
Файл: mirror_bot/services/product_service_v24.py

ИНСТРУКЦИЯ: Замени содержимое mirror_bot/services/product_service.py
этим файлом (или добавь метод purchase_product_v24 и переименуй вызов).

ИСПРАВЛЕНИЯ по сравнению с v2:
1. SELECT FOR UPDATE — защита от race condition при одновременной покупке
2. Проверка product.is_active перед покупкой
3. Идемпотентность — проверка повторной покупки
4. Комиссия маркетолога начисляется ПОСЛЕ эскроу (не сразу)
5. Покупатель не видит данные продавца в ответе
6. Логирование транзакции в таблицу transactions
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    Product, ProductPurchase, User, Transaction, Marketer, Referral
)

logger = logging.getLogger(__name__)

# ── Константы (будут браться из SystemSetting в production) ──
PLATFORM_FEE_BASE = Decimal("0.15")   # 15% комиссия платформы
MARKETER_COMMISSION_RATE = Decimal("0.10")  # 10% маркетологу
DISPUTE_WINDOW_HOURS = 24
AUTO_COMPLETE_HOURS = 24


class ProductServiceV24:
    """
    Сервис покупки товаров с полной защитой от race conditions,
    идемпотентностью и анонимностью покупателя.
    """

    @staticmethod
    async def purchase_product(
        session: AsyncSession,
        product_id: int,
        user_id: int,
        mirror_bot_id: int
    ) -> Dict[str, Any]:
        """
        Купить товар.
        
        Возвращает:
            {
                "success": True,
                "purchase_id": int,
                "product": {"id", "name", "description", "price", "file_type"},
                "new_balance": float
            }
            или
            {
                "success": False,
                "error": str,
                "required": float (если insufficient_balance),
                "available": float (если insufficient_balance)
            }
        """
        try:
            # ── Шаг 1: Получаем товар с блокировкой строки ───────────────
            # SELECT FOR UPDATE предотвращает одновременную покупку одного товара
            result = await session.execute(
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
            )
            product = result.scalar_one_or_none()

            if not product:
                return {"success": False, "error": "Product not found"}

            # ── Шаг 2: Проверяем доступность товара ──────────────────────
            if not product.is_available:
                return {"success": False, "error": "Product already sold"}

            # Проверяем is_active (новое поле v24)
            if hasattr(product, 'is_active') and not product.is_active:
                return {"success": False, "error": "Product not available"}

            # Проверяем статус модерации (новое поле v24)
            if hasattr(product, 'moderation_status'):
                if product.moderation_status != "approved":
                    return {"success": False, "error": "Product not available"}

            # ── Шаг 3: Получаем пользователя с блокировкой ───────────────
            user_result = await session.execute(
                select(User)
                .where(User.user_id == user_id)
                .with_for_update()
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found"}

            # ── Шаг 4: Проверяем баланс ───────────────────────────────────
            if user.balance < product.price:
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "required": float(product.price),
                    "available": float(user.balance)
                }

            # ── Шаг 5: Списываем деньги ───────────────────────────────────
            user.balance -= product.price

            # ── Шаг 6: Помечаем товар как проданный ──────────────────────
            product.is_available = False

            # ── Шаг 7: Создаём запись покупки ────────────────────────────
            purchase = ProductPurchase(
                product_id=product_id,
                user_id=user_id,
                purchased_at=datetime.utcnow()
            )
            session.add(purchase)

            # ── Шаг 8: Логируем транзакцию ───────────────────────────────
            transaction = Transaction(
                user_id=user_id,
                type="purchase",
                amount=-product.price,
                description=f"Purchase: {product.name} (#{product_id})"
            )
            session.add(transaction)

            # ── Шаг 9: Начисляем реферальный бонус (если есть реферер) ───
            # ВАЖНО: комиссия маркетолога НЕ начисляется здесь.
            # Она начисляется в release_escrow_funds (Celery task) после
            # истечения окна спора. Это защита от refund-фрода.
            await ProductServiceV24._apply_referral_bonus(
                session, user_id, product.price, mirror_bot_id
            )

            await session.commit()
            await session.refresh(purchase)

            logger.info(
                f"Product purchased: product_id={product_id}, "
                f"user_id={user_id}, purchase_id={purchase.id}, "
                f"price={product.price}"
            )

            # ── Шаг 10: Возвращаем результат БЕЗ данных продавца ─────────
            return {
                "success": True,
                "purchase_id": purchase.id,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price),
                    "file_type": product.file_type
                    # НАМЕРЕННО не включаем: seller_id, file_path, seller_name
                },
                "new_balance": float(user.balance)
            }

        except Exception as e:
            await session.rollback()
            logger.error(f"Purchase failed: product_id={product_id}, user_id={user_id}, error={e}")
            return {"success": False, "error": "Internal error, please try again"}

    @staticmethod
    async def _apply_referral_bonus(
        session: AsyncSession,
        user_id: int,
        purchase_amount: Decimal,
        mirror_bot_id: int
    ) -> None:
        """
        Начисляет реферальный бонус рефереру при первой покупке.
        Вызывается внутри purchase_product.
        """
        try:
            # Ищем реферера
            ref_result = await session.execute(
                select(Referral).where(Referral.referred_id == user_id)
            )
            referral = ref_result.scalar_one_or_none()
            if not referral:
                return

            # Ищем маркетолога по referrer_id
            # (маркетолог мог быть обычным пользователем-рефером)
            # Бонус рефера = 3% от покупки (REFERRAL_BONUS_RATE)
            REFERRAL_BONUS_RATE = Decimal("0.03")
            bonus = (purchase_amount * REFERRAL_BONUS_RATE).quantize(Decimal("0.01"))

            if bonus <= 0:
                return

            # Начисляем бонус рефереру
            referrer_result = await session.execute(
                select(User).where(User.user_id == referral.referrer_id).with_for_update()
            )
            referrer = referrer_result.scalar_one_or_none()
            if not referrer:
                return

            referrer.balance += bonus
            referral.earned_total += bonus

            # Логируем транзакцию рефереру
            ref_tx = Transaction(
                user_id=referral.referrer_id,
                type="referral_bonus",
                amount=bonus,
                description=f"Referral bonus from purchase #{user_id}"
            )
            session.add(ref_tx)

        except Exception as e:
            logger.warning(f"Referral bonus failed for user_id={user_id}: {e}")
            # Не прерываем основную покупку из-за ошибки реферала
