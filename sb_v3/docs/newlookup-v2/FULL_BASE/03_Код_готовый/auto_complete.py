"""
Newlookup v24 — Celery задачи для автозавершения и эскроу
Файл: shared/tasks/auto_complete.py

ИНСТРУКЦИЯ:
1. Установи Celery: pip install celery[redis]
2. Создай файл shared/tasks/__init__.py
3. Добавь в docker-compose.yml сервис celery_worker (см. ниже)
4. Добавь в docker-compose.yml сервис celery_beat (см. ниже)

DOCKER-COMPOSE ДОБАВЛЕНИЕ:
  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile  # общий Dockerfile
    container_name: newlookup_celery_worker
    command: celery -A shared.tasks.celery_app worker --loglevel=info
    env_file: .env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./data:/app/data
    networks:
      - bot_network
    restart: unless-stopped

  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: newlookup_celery_beat
    command: celery -A shared.tasks.celery_app beat --loglevel=info
    env_file: .env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - celery_worker
    networks:
      - bot_network
    restart: unless-stopped
"""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# ── Инициализация Celery ──────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "newlookup",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,           # Задача подтверждается после выполнения
    task_reject_on_worker_lost=True,  # Перезапуск при падении воркера
    beat_schedule={
        # Каждые 5 минут проверяем заказы на автозавершение
        "auto-complete-orders": {
            "task": "shared.tasks.auto_complete.check_auto_complete_orders",
            "schedule": crontab(minute="*/5"),
        },
        # Каждый час проверяем нарушения воркеров
        "check-worker-violations": {
            "task": "shared.tasks.auto_complete.check_worker_violation_limits",
            "schedule": crontab(minute=0),
        },
    }
)


# ══════════════════════════════════════════════════════════════
# ЗАДАЧА 1: Проверка автозавершения заказов
# ══════════════════════════════════════════════════════════════
@celery_app.task(
    name="shared.tasks.auto_complete.check_auto_complete_orders",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_auto_complete_orders(self):
    """
    Каждые 5 минут:
    1. Находит завершённые заказы, у которых истёк auto_complete_at
    2. Выплачивает эскроу продавцу (идемпотентно)
    3. Начисляет комиссию маркетолога (если есть)
    """
    import asyncio
    try:
        asyncio.run(_async_check_auto_complete())
    except Exception as exc:
        logger.error(f"check_auto_complete_orders failed: {exc}")
        raise self.retry(exc=exc)


async def _async_check_auto_complete():
    """Async реализация проверки автозавершения."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, and_

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            from shared.database.models import SellerOrder, Seller, Marketer

            # Находим заказы для автозавершения
            result = await session.execute(
                select(SellerOrder).where(
                    and_(
                        SellerOrder.status == "completed",
                        SellerOrder.escrow_released == False,  # noqa
                        SellerOrder.auto_complete_at <= datetime.utcnow()
                    )
                ).limit(100)
            )
            orders = list(result.scalars().all())

            if not orders:
                return

            logger.info(f"Processing {len(orders)} orders for auto-complete")

            for order in orders:
                await _release_escrow_for_order(session, order)

            await session.commit()
            logger.info(f"Auto-complete processed {len(orders)} orders")

        except Exception as e:
            await session.rollback()
            logger.error(f"Auto-complete failed: {e}")
            raise

    await engine.dispose()


async def _release_escrow_for_order(session, order) -> None:
    """
    Выплачивает эскроу продавцу.
    ИДЕМПОТЕНТНА: проверяет escrow_released перед выплатой.
    """
    from sqlalchemy import select
    from shared.database.models import SellerOrder, Seller, Marketer, Transaction

    # Повторная проверка с блокировкой строки
    result = await session.execute(
        select(SellerOrder)
        .where(SellerOrder.id == order.id)
        .with_for_update()
    )
    order_locked = result.scalar_one_or_none()

    if not order_locked:
        return

    # ИДЕМПОТЕНТНОСТЬ: если уже выплачено — пропускаем
    if order_locked.escrow_released:
        logger.info(f"Order {order.id}: escrow already released, skipping")
        return

    # Получаем продавца
    seller_result = await session.execute(
        select(Seller).where(Seller.id == order_locked.seller_id).with_for_update()
    )
    seller = seller_result.scalar_one_or_none()
    if not seller:
        logger.error(f"Order {order.id}: seller not found")
        return

    # Рассчитываем суммы
    buyer_paid = order_locked.price_for_buyer
    seller_gets = order_locked.price_for_seller
    platform_fee = buyer_paid - seller_gets  # Разница = комиссия платформы

    # Выплачиваем продавцу
    seller.total_earned += seller_gets
    seller.deposit_balance += seller_gets

    # Помечаем эскроу как выплаченный
    order_locked.escrow_released = True

    # Логируем транзакцию продавца
    seller_tx = Transaction(
        user_id=seller.telegram_id,
        type="seller_payout",
        amount=seller_gets,
        description=f"Payout for order #{order.id}"
    )
    session.add(seller_tx)

    # Начисляем комиссию маркетолога (если есть и ещё не начислена)
    if (
        hasattr(order_locked, 'marketer_id') and
        order_locked.marketer_id and
        not order_locked.marketer_commission_paid
    ):
        await _pay_marketer_commission(session, order_locked)

    logger.info(
        f"Order {order.id}: escrow released. "
        f"Seller gets ${seller_gets}, platform fee ${platform_fee}"
    )


async def _pay_marketer_commission(session, order) -> None:
    """Начисляет комиссию маркетолога. Идемпотентна."""
    from sqlalchemy import select
    from shared.database.models import Marketer, Transaction

    if not order.marketer_commission_amount:
        return

    marketer_result = await session.execute(
        select(Marketer).where(Marketer.id == order.marketer_id).with_for_update()
    )
    marketer = marketer_result.scalar_one_or_none()
    if not marketer:
        return

    commission = order.marketer_commission_amount
    marketer.balance += commission
    marketer.total_earned += commission
    order.marketer_commission_paid = True

    marketer_tx = Transaction(
        user_id=marketer.telegram_id,
        type="marketer_commission",
        amount=commission,
        description=f"Commission for order #{order.id}"
    )
    session.add(marketer_tx)

    logger.info(f"Order {order.id}: marketer commission ${commission} paid")


# ══════════════════════════════════════════════════════════════
# ЗАДАЧА 2: Проверка лимита нарушений воркеров
# ══════════════════════════════════════════════════════════════
@celery_app.task(
    name="shared.tasks.auto_complete.check_worker_violation_limits",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_worker_violation_limits(self):
    """
    Каждый час:
    1. Считает нарушения каждого воркера за последние 30 дней
    2. Если >= 3 нарушений — приостанавливает воркера
    """
    import asyncio
    try:
        asyncio.run(_async_check_violations())
    except Exception as exc:
        logger.error(f"check_worker_violation_limits failed: {exc}")
        raise self.retry(exc=exc)


async def _async_check_violations():
    """Async реализация проверки нарушений."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, func, and_

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        return

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Проверяем только если таблица worker_violations существует
            from sqlalchemy import inspect
            inspector = inspect(engine.sync_engine)
            if 'worker_violations' not in inspector.get_table_names():
                logger.info("worker_violations table not found, skipping")
                return

            from shared.database.models import Worker

            # Получаем всех активных воркеров
            workers_result = await session.execute(
                select(Worker).where(Worker.is_suspended == False)  # noqa
            )
            workers = list(workers_result.scalars().all())

            window_start = datetime.utcnow() - timedelta(days=30)
            VIOLATION_LIMIT = 3

            for worker in workers:
                # Считаем нарушения за 30 дней
                # (используем raw SQL для совместимости)
                count_result = await session.execute(
                    sa_text(
                        "SELECT COUNT(*) FROM worker_violations "
                        "WHERE worker_id = :wid AND created_at >= :start"
                    ).bindparams(wid=worker.id, start=window_start)
                )
                count = count_result.scalar()

                if count >= VIOLATION_LIMIT:
                    worker.is_suspended = True
                    worker.suspended_at = datetime.utcnow()
                    worker.suspended_reason = f"Auto-suspended: {count} violations in 30 days"
                    logger.warning(f"Worker {worker.id} suspended: {count} violations")

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"Violation check failed: {e}")

    await engine.dispose()


# Импорт для raw SQL
from sqlalchemy import text as sa_text
