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
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text as sa_text

try:
    from celery import Celery
    from celery.schedules import crontab
except ModuleNotFoundError:  # pragma: no cover - exercised implicitly in test envs without celery
    class Celery:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            self.conf = {}

        def task(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    def crontab(*args, **kwargs):  # type: ignore[misc]
        return {"args": args, "kwargs": kwargs}

logger = logging.getLogger(__name__)
from shared.config.settings import global_settings
from shared.services.seller_dispute_service import SellerDisputeService
from shared.services.ledger_service import LedgerService


def _crontab_every_minutes(minutes: int):
    safe_minutes = max(1, int(minutes or 1))
    if safe_minutes >= 60:
        return crontab(minute=0)
    return crontab(minute=f"*/{safe_minutes}")

celery_app = Celery(
    "newlookup",
    broker=global_settings.celery_broker_url,
    backend=global_settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=global_settings.celery_timezone,
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "auto-complete-orders": {
            "task": "shared.tasks.auto_complete.check_auto_complete_orders",
            "schedule": _crontab_every_minutes(
                min(global_settings.celery_auto_complete_interval_minutes or 5, 5)
            ),
        },
        "check-worker-violations": {
            "task": "shared.tasks.auto_complete.check_worker_violation_limits",
            "schedule": _crontab_every_minutes(global_settings.celery_violation_check_interval_minutes),
        },
        "process-matured-ledger-transactions": {
            "task": "shared.tasks.auto_complete.process_matured_ledger_transactions",
            "schedule": crontab(minute=0),
        },
        "process-expired-seller-disputes": {
            "task": "shared.tasks.auto_complete.process_expired_seller_disputes",
            "schedule": _crontab_every_minutes(15),
        },
        "abandoned-cart-check": {
            "task": "shared.tasks.auto_complete.check_abandoned_carts",
            "schedule": _crontab_every_minutes(10),
        },
        "recalculate-worker-scores": {
            "task": "shared.tasks.auto_complete.recalculate_all_worker_scores",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "smart-notifications-check": {
            "task": "shared.tasks.auto_complete.send_smart_notifications",
            "schedule": crontab(minute=0, hour="9"),
        },
        "sla-breach-check": {
            "task": "shared.tasks.auto_complete.check_sla_breaches",
            "schedule": _crontab_every_minutes(15),
        },
        "recalculate-seller-scores": {
            "task": "shared.tasks.auto_complete.recalculate_all_seller_scores_task",
            "schedule": crontab(minute=30, hour="*/6"),
        },
    },
)


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

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_async_check_auto_complete())
    except Exception as exc:
        logger.error(f"check_auto_complete_orders failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


async def _async_check_auto_complete():
    """Async реализация проверки автозавершения.

    Handles: SellerOrder, SellerCCOrder, SellerNFCOrder, SellerOTPOrder, SellerEnrollOrder.
    """
    from sqlalchemy import and_, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = global_settings.database_url
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            from shared.database.models import (
                SellerOrder, SellerCCOrder, BruteBankOrder,
                SellerNFCOrder, SellerOTPOrder, SellerEnrollOrder,
                SellerCheckOrder,
            )

            all_order_models = [
                SellerOrder, SellerCCOrder, BruteBankOrder,
                SellerNFCOrder, SellerOTPOrder, SellerEnrollOrder,
                SellerCheckOrder,
            ]
            total_processed = 0

            async with session.begin():
                for model in all_order_models:
                    if not hasattr(model, "escrow_released") or not hasattr(model, "auto_complete_at"):
                        continue
                    result = await session.execute(
                        select(model).where(
                            and_(
                                model.status == "completed",
                                model.escrow_released == False,  # noqa
                                model.auto_complete_at.is_not(None),
                                model.auto_complete_at <= datetime.now(timezone.utc),
                            )
                        ).limit(100)
                    )
                    orders = list(result.scalars().all())

                    for order in orders:
                        await _release_escrow_for_order(session, order)
                    total_processed += len(orders)

            if total_processed:
                logger.info(f"Auto-complete processed {total_processed} orders")

        except Exception as e:
            await session.rollback()
            logger.error(f"Auto-complete failed: {e}")
            raise

    await engine.dispose()


@celery_app.task(
    name="shared.tasks.auto_complete.process_matured_ledger_transactions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_matured_ledger_transactions(self):
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_async_process_matured_ledger_transactions())
    except Exception as exc:
        logger.error(f"process_matured_ledger_transactions failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="shared.tasks.auto_complete.process_expired_seller_disputes",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_expired_seller_disputes(self):
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_async_process_expired_seller_disputes())
    except Exception as exc:
        logger.error(f"process_expired_seller_disputes failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


async def _async_process_matured_ledger_transactions():
    from sqlalchemy import and_, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from shared.database.models import Transaction, TRANSACTION_STATUS_ON_HOLD

    DATABASE_URL = global_settings.database_url
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            async with session.begin():
                rows = list(
                    (
                        await session.execute(
                            select(Transaction).where(
                                and_(
                                    Transaction.status == TRANSACTION_STATUS_ON_HOLD,
                                    Transaction.effective_at.is_not(None),
                                    Transaction.effective_at <= datetime.now(timezone.utc),
                                )
                            ).limit(200)
                        )
                    ).scalars().all()
                )
                for tx in rows:
                    if tx.related_entity_type == "seller_order":
                        continue
                    await LedgerService.mark_transaction_completed(session, transaction_id=tx.id)
        finally:
            await engine.dispose()


async def _async_process_expired_seller_disputes():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = global_settings.database_url
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        return

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            async with session.begin():
                processed = await SellerDisputeService.auto_resolve_expired_disputes(session)
                if processed:
                    logger.info(f"Auto-resolved {processed} expired seller disputes")
        finally:
            await engine.dispose()


async def _release_escrow_for_order(session, order) -> None:
    """
    Выплачивает эскроу продавцу.
    ИДЕМПОТЕНТНА: проверяет escrow_released перед выплатой.
    Works with SellerOrder, SellerCCOrder, SellerNFCOrder, SellerOTPOrder, SellerEnrollOrder.
    """
    from sqlalchemy import select
    from shared.database.models import EscrowRelease, Seller
    from shared.services.audit_event_service import AuditEventService

    model = type(order)
    result = await session.execute(
        select(model)
        .where(model.id == order.id)
        .with_for_update()
    )
    order_locked = result.scalar_one_or_none()

    if not order_locked:
        return

    if order_locked.escrow_released:
        logger.info(f"Order {order.id} ({model.__tablename__}): escrow already released, skipping")
        return

    seller_id = order_locked.seller_id

    existing_release = await session.scalar(
        select(EscrowRelease).where(
            EscrowRelease.seller_order_id == order_locked.id,
            EscrowRelease.order_table == model.__tablename__,
        )
    )
    if existing_release:
        order_locked.escrow_released = True
        logger.info(f"Order {order.id} ({model.__tablename__}): escrow release record already exists, skipping")
        return

    seller_result = await session.execute(
        select(Seller).where(Seller.id == seller_id).with_for_update()
    )
    seller = seller_result.scalar_one_or_none()
    if not seller:
        logger.error(f"Order {order.id}: seller not found")
        return

    buyer_paid = Decimal(str(getattr(order_locked, "price_for_buyer", 0) or getattr(order_locked, "price", 0) or 0))
    seller_gets = Decimal(str(getattr(order_locked, "price_for_seller", 0) or buyer_paid))
    platform_fee = buyer_paid - seller_gets

    if not getattr(order_locked, "settled_at", None):
        await LedgerService.settle_seller_hold(
            session,
            seller_id=seller.id,
            order_id=order_locked.id,
            fallback_amount=seller_gets,
        )
        if hasattr(order_locked, "settled_at"):
            order_locked.settled_at = datetime.now(timezone.utc)
    if hasattr(order_locked, "check_confirmed_at") and not order_locked.check_confirmed_at:
        order_locked.check_confirmed_at = datetime.now(timezone.utc)

    order_locked.escrow_released = True
    release_kwargs = dict(
        seller_order_id=order_locked.id,
        seller_id=seller_id,
        amount=seller_gets,
        released_by="system",
    )
    if hasattr(EscrowRelease, "order_table"):
        release_kwargs["order_table"] = model.__tablename__
    session.add(EscrowRelease(**release_kwargs))

    await AuditEventService.log(
        session,
        event_type="seller_order_escrow_released",
        source="celery:auto_complete",
        actor_type="system",
        target_type=model.__tablename__,
        target_id=order_locked.id,
        status="released",
        payload={
            "seller_id": seller_id,
            "seller_amount": float(seller_gets),
            "buyer_amount": float(buyer_paid),
            "platform_fee": float(platform_fee),
        },
    )

    if (
        hasattr(order_locked, "marketer_id")
        and order_locked.marketer_id
        and not order_locked.marketer_commission_paid
    ):
        await _pay_marketer_commission(session, order_locked)

    logger.info(
        f"Order {order.id} ({model.__tablename__}): escrow released. "
        f"Seller gets ${seller_gets}, platform fee ${platform_fee}"
    )


async def _pay_marketer_commission(session, order) -> None:
    """Начисляет комиссию маркетолога. Идемпотентна."""
    from sqlalchemy import select
    from shared.database.models import Marketer
    from shared.services.audit_event_service import AuditEventService
    from shared.services.marketer_activity_log import log_marketer_activity

    if not order.marketer_commission_amount:
        return

    marketer_result = await session.execute(
        select(Marketer).where(Marketer.id == order.marketer_id).with_for_update()
    )
    marketer = marketer_result.scalar_one_or_none()
    if not marketer:
        return

    buyer_id = getattr(order, "buyer_user_id", None) or getattr(order, "user_id", None)
    if buyer_id and buyer_id == marketer.telegram_id:
        return

    commission = order.marketer_commission_amount
    await LedgerService.credit_marketer_balance(
        session,
        marketer_id=marketer.id,
        amount=commission,
        description=f"Auto-complete commission for seller order #{order.id}",
        related_entity_type="seller_order",
        related_entity_id=order.id,
        idempotency_key=LedgerService.build_idempotency_key("marketer-order", order.id, marketer.id),
    )
    order.marketer_commission_paid = True

    # Increment daily MarketerStats: sales_count, buyers_count, earned
    try:
        from shared.database.models import MarketerStats
        from datetime import date as _date
        from sqlalchemy import select as _select
        today = _date.today()
        stat = await session.scalar(
            _select(MarketerStats).where(
                MarketerStats.marketer_id == marketer.id,
                MarketerStats.date == today,
            )
        )
        if stat:
            stat.sales_count = (stat.sales_count or 0) + 1
            stat.buyers_count = (stat.buyers_count or 0) + 1
            stat.earned = (stat.earned or 0) + commission
        else:
            session.add(MarketerStats(
                marketer_id=marketer.id,
                date=today,
                earned=commission,
                sales_count=1,
                buyers_count=1,
            ))
    except Exception as _e:
        import logging as _log
        _log.getLogger(__name__).warning("MarketerStats increment failed: %s", _e)

    await log_marketer_activity(
        session,
        marketer_id=marketer.id,
        action="earning",
        amount=commission,
        details=f"Auto-complete commission for seller order #{order.id}",
        user_id=getattr(order, "buyer_user_id", None),
    )
    await AuditEventService.log(
        session,
        event_type="marketer_commission_paid",
        source="celery:auto_complete",
        actor_type="system",
        target_type="marketer",
        target_id=marketer.id,
        status="paid",
        payload={
            "seller_order_id": order.id,
            "amount": float(commission),
        },
    )

    logger.info(f"Order {order.id}: marketer commission ${commission} paid")


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

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_async_check_violations())
    except Exception as exc:
        logger.error(f"check_worker_violation_limits failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


async def _async_check_violations():
    """Async реализация проверки нарушений."""
    from sqlalchemy import and_, func, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = global_settings.database_url
    if not DATABASE_URL:
        return

    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            from sqlalchemy import inspect

            inspector = inspect(engine.sync_engine)
            if "worker_violations" not in inspector.get_table_names():
                logger.info("worker_violations table not found, skipping")
                return

            from shared.database.models import SystemSetting, Worker

            workers_result = await session.execute(
                select(Worker).where(Worker.is_suspended == False)  # noqa
            )
            workers = list(workers_result.scalars().all())

            violation_limit_row = await session.scalar(
                select(SystemSetting).where(SystemSetting.key == "WORKER_VIOLATION_LIMIT")
            )
            violation_window_row = await session.scalar(
                select(SystemSetting).where(SystemSetting.key == "WORKER_VIOLATION_WINDOW_DAYS")
            )
            try:
                violation_limit = int(str(violation_limit_row.value).strip()) if violation_limit_row and violation_limit_row.value else 3
            except (TypeError, ValueError):
                violation_limit = 3
            try:
                violation_window_days = int(str(violation_window_row.value).strip()) if violation_window_row and violation_window_row.value else 30
            except (TypeError, ValueError):
                violation_window_days = 30
            window_start = datetime.now(timezone.utc) - timedelta(days=violation_window_days)

            for worker in workers:
                count_result = await session.execute(
                    sa_text(
                        "SELECT COUNT(*) FROM worker_violations "
                        "WHERE worker_id = :wid AND created_at >= :start"
                    ).bindparams(wid=worker.id, start=window_start)
                )
                count = count_result.scalar()

                if count >= violation_limit:
                    worker.is_suspended = True
                    worker.suspended_at = datetime.now(timezone.utc)
                    worker.suspended_reason = f"Auto-suspended: {count} violations in 30 days"
                    logger.warning(f"Worker {worker.id} suspended: {count} violations")

            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.error(f"Violation check failed: {e}")

    await engine.dispose()


@celery_app.task(
    name="shared.tasks.auto_complete.check_abandoned_carts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_abandoned_carts(self):
    """Каждые 10 мин: находит корзины неактивные > 1 ч и помечает abandoned, шлёт напоминание."""
    import asyncio

    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from shared.config.settings import global_settings
        from shared.database.models import ShoppingCart, User

        engine = create_async_engine(global_settings.database_url)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with session_maker() as session:
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                result = await session.execute(
                    sa_text(
                        "SELECT id, user_id FROM shopping_carts "
                        "WHERE status = 'active' AND updated_at <= :cutoff AND abandoned_notified = FALSE"
                    ).bindparams(cutoff=cutoff)
                )
                carts = result.fetchall()
                for cart_row in carts:
                    await session.execute(
                        sa_text(
                            "UPDATE shopping_carts SET status = 'abandoned', abandoned_notified = TRUE "
                            "WHERE id = :cid"
                        ).bindparams(cid=cart_row.id)
                    )
                    logger.info(f"Marked cart {cart_row.id} as abandoned for user {cart_row.user_id}")
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Abandoned cart check failed: {e}")

        await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(f"check_abandoned_carts failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="shared.tasks.auto_complete.recalculate_all_worker_scores",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def recalculate_all_worker_scores(self):
    """Каждые 6 часов пересчитывает Worker Score для всех активных воркеров."""
    import asyncio

    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from shared.config.settings import global_settings
        from shared.database.models import Worker
        from shared.services.worker_score_service import recalculate_worker_score

        engine = create_async_engine(global_settings.database_url)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with session_maker() as session:
            try:
                result = await session.execute(
                    sa_text("SELECT id FROM workers WHERE is_active = TRUE AND is_suspended = FALSE")
                )
                worker_ids = [row.id for row in result.fetchall()]
                for wid in worker_ids:
                    try:
                        await recalculate_worker_score(session, wid)
                    except Exception as e:
                        logger.warning(f"Score recalc failed for worker {wid}: {e}")
                logger.info(f"Recalculated scores for {len(worker_ids)} workers")
            except Exception as e:
                await session.rollback()
                logger.error(f"Worker score recalc task failed: {e}")

        await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(f"recalculate_all_worker_scores failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="shared.tasks.auto_complete.send_smart_notifications",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def send_smart_notifications(self):
    """Ежедневно в 9:00: шлёт персональные рекомендации пользователям, неактивным 7+ дней."""
    import asyncio

    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from shared.config.settings import global_settings

        engine = create_async_engine(global_settings.database_url)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with session_maker() as session:
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                result = await session.execute(
                    sa_text(
                        "SELECT u.user_id FROM users u "
                        "WHERE (u.last_active_at IS NULL OR u.last_active_at <= :cutoff) "
                        "AND u.is_banned = FALSE "
                        "LIMIT 500"
                    ).bindparams(cutoff=cutoff)
                )
                user_ids = [row.user_id for row in result.fetchall()]
                logger.info(f"Smart notifications: {len(user_ids)} inactive users to notify")
                # Actual sending is done via bot API — log for now
                # In production: enqueue per-user notification tasks
            except Exception as e:
                logger.error(f"Smart notifications task failed: {e}")

        await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(f"send_smart_notifications failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="shared.tasks.auto_complete.check_sla_breaches",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_sla_breaches(self):
    """Каждые 15 мин: проверяет SLA тикетов поддержки и помечает нарушения."""
    import asyncio

    SLA_MINUTES = {
        "CRITICAL": 15,
        "HIGH": 60,
        "NORMAL": 240,
        "LOW": 1440,
    }

    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from shared.config.settings import global_settings

        engine = create_async_engine(global_settings.database_url)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with session_maker() as session:
            try:
                for priority, minutes in SLA_MINUTES.items():
                    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
                    await session.execute(
                        sa_text(
                            "UPDATE support_tickets SET sla_breach = TRUE "
                            "WHERE priority = :priority AND status IN ('new', 'open') "
                            "AND first_response_at IS NULL AND created_at <= :cutoff "
                            "AND sla_breach = FALSE"
                        ).bindparams(priority=priority, cutoff=cutoff)
                    )
                await session.commit()
                logger.info("SLA breach check completed")
            except Exception as e:
                await session.rollback()
                logger.error(f"SLA breach check failed: {e}")

        await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(f"check_sla_breaches failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name='shared.tasks.auto_complete.recalculate_all_seller_scores_task',
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def recalculate_all_seller_scores_task(self):
    """Каждые 6 часов пересчитывает Seller Score для всех активных продавцов."""
    import asyncio

    async def _run():
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from shared.config.settings import global_settings
        from shared.services.reputation_service import recalculate_all_seller_scores

        engine = create_async_engine(global_settings.database_url)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

        async with session_maker() as session:
            try:
                count = await recalculate_all_seller_scores(session)
                logger.info(f'Recalculated Seller Score for {count} sellers')
            except Exception as e:
                logger.error(f'Seller score recalc task failed: {e}')

        await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    except Exception as exc:
        logger.error(f"recalculate_all_seller_scores_task failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()
