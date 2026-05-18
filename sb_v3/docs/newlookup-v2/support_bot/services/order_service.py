"""
Сервис для работы с заказами
"""

from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from shared.database.models import Order, BulkOrderItem, Worker
from shared.database.tasks_session import tasks_session_maker
from shared.services.pricing_config_service import PricingConfigService
from shared.services.worker_reminder_task_service import WorkerReminderTaskService
from shared.services.worker_order_service import WorkerOrderService
from support_bot.config import support_bot_config

# Маппинг старых категорий воркеров на новые категории заказов
CATEGORY_MAPPING = {
    # Старые категории воркеров -> Новые категории заказов
    "accounts_addinfo": "✍️ Add info in CR",
    "lookup_ssn": "🔎 Search",
    "lookup_dl": "🔎 Search",
    "lookup_mvr": "🔎 Search",
    "lookup_fullmvr": "🔎 Search",
    "lookup_credit": "🔎 Search",
    "lookup_bg": "🔎 Search",
    "lookup_mmn": "🔎 Search",
    "lookup_ein": "🔎 Search",
    "phone_name": "🔎 Search",
    "phone_ssn": "🔎 Search",
    "phone_full": "🔎 Search",
    "cr_transunion": "📈 CREDIT REPORTS",
    "cr_experian": "📈 CREDIT REPORTS",
    "cr_equifax": "📈 CREDIT REPORTS",
    "cr_lexisnexis": "📈 CREDIT REPORTS",
    "cr_wallet": "📈 CREDIT REPORTS",
    "fullz": "🧰 PROS & FULLZ",
    "fullz_biz": "🧰 PROS & FULLZ",
    "fullz_personal": "🧰 PROS & FULLZ",
    "fullz_cs": "🧰 PROS & FULLZ",  # Исправлено с fullz_personal_cs на fullz_cs
    "fullz_military": "🧰 PROS & FULLZ",
    "fullz_work": "🧰 PROS & FULLZ",
    "fullz_young": "🧰 PROS & FULLZ",
    "fullz_random": "🧰 PROS & FULLZ",
    "fullz_business": "🧰 PROS & FULLZ",
    "personal_random": "🧰 PROS & FULLZ",
    "banks": "🏦 BANKS",
    "esim": "📶 eSIM",
    "lookup": "🔎 Search",  # Добавляем маппинг общей категории
    "lookup_ba": "🔎 Search",
    "credit_reports": "📈 CREDIT REPORTS",
    "documents": "📄 DOCUMENTS",
    "accounts": "🧾 Subscriptions / Accounts",
    "addinfo": "✍️ Add info in CR",
}


def can_worker_access_order_category(worker_categories: List[str], order_category: str) -> bool:
    """
    Проверить, может ли воркер обрабатывать заказ данной категории
    
    Args:
        worker_categories: Категории воркера
        order_category: Категория заказа
        
    Returns:
        bool: True если может обрабатывать
    """
    # Прямое совпадение
    if order_category in worker_categories:
        return True
    
    # Проверяем через маппинг (старые категории воркера -> новые категории заказов)
    for worker_cat in worker_categories:
        if worker_cat in CATEGORY_MAPPING and CATEGORY_MAPPING[worker_cat] == order_category:
            return True
    
    return False


def can_worker_access_order(worker_categories: List[str], worker_services: Optional[List[str]], 
                            order_category: str, order_service: str) -> bool:
    """
    Проверить, может ли воркер получить доступ к заказу
    
    Args:
        worker_categories: Категории воркера
        worker_services: Сервисы воркера (может быть None или пустой список)
        order_category: Категория заказа
        order_service: Сервис заказа (service_name)
        
    Returns:
        bool: True если может получить доступ
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Проверяем категорию
    if not can_worker_access_order_category(worker_categories, order_category):
        return False
    
    # Если у воркера нет указанных сервисов, он не может видеть заказы
    if not worker_services:
        return False
    
    # Прямое совпадение сервиса
    if order_service in worker_services:
        return True

    # Проверяем гибкие правила совпадения только для особых случаев

    # 1. eSIM: проверяем по базовому коду (например sms_tmobile_1 -> sms_tmobile)
    # Это нужно потому что заказы могут иметь разные периоды (_1, _3, _6, _12)
    if order_category == "📶 eSIM":
        for worker_service in worker_services:
            # Убираем суффиксы с месяцами (_1, _3, _6, _12) для сравнения
            order_base = order_service.rsplit('_', 1)[0] if '_' in order_service and order_service.split('_')[-1].isdigit() else order_service
            worker_base = worker_service.rsplit('_', 1)[0] if '_' in worker_service and worker_service.split('_')[-1].isdigit() else worker_service

            if order_base == worker_base:
                logger.info(f"eSIM match: order={order_service} (base={order_base}) matches worker={worker_service} (base={worker_base})")
                return True

    # 2. Accounts: service_name "db_123" matches worker service "acc_db_123" and vice versa
    if order_category in ("accounts", "🧾 Subscriptions / Accounts"):
        for worker_service in worker_services:
            if worker_service.startswith("acc_") and order_service == worker_service[4:]:
                return True
            if order_service.startswith("acc_") and worker_service == order_service[4:]:
                return True
            if worker_service == f"acc_{order_service}":
                return True

    # 3. Проверяем алиасы для обратной совместимости
    # Например: воркер с "dl" может видеть заказы "lookup_dl"
    # или воркер с "lookup_dl" может видеть заказы "dl"
    lookup_aliases = {
        "ssn_dob": "lookup_ssn",
        "lookup_ssn": "ssn_dob",
        "dl": "lookup_dl",
        "lookup_dl": "dl",
        "credit": "lookup_credit",
        "lookup_credit": "credit",
        "mvr": "lookup_mvr",
        "lookup_mvr": "mvr",
        "fullmvr": "lookup_fullmvr",
        "lookup_fullmvr": "fullmvr",
        "bg": "lookup_bg",
        "lookup_bg": "bg",
        "mmn": "lookup_mmn",
        "lookup_mmn": "mmn",
        "ein": "lookup_ein",
        "lookup_ein": "ein",
        "fullz_cs": "fullz_personal_cs",
        "fullz_personal_cs": "fullz_cs",
        "fullz_random": "personal_random",
        "personal_random": "fullz_random",
        "phone_name": "phone_name",
        "phone_ssn": "phone_ssn",
        "phone_full": "phone_full",
        # Bank Lookup (BA)
        "lookup_ba_an_rn": "lookup_ba_an_rn",
        "lookup_ba_transactions": "lookup_ba_transactions",
        "lookup_ba_balance": "lookup_ba_balance",
        "lookup_ba_name": "lookup_ba_name",
        "lookup_ba_an_rn_name": "lookup_ba_an_rn_name",
    }

    # Проверяем алиасы
    if order_service in lookup_aliases:
        alias = lookup_aliases[order_service]
        if alias in worker_services:
            logger.info(f"Alias match: order={order_service} matches worker service={alias}")
            return True

    return False


class OrderService:
    """Сервис для управления заказами"""
    
    @staticmethod
    async def get_available_orders(
        session: AsyncSession,
        categories: List[str],
        services: Optional[List[str]] = None,
        limit: int = 50,
        worker_score: float = 0.0,
    ) -> List[Order]:
        """
        Получить доступные заказы для воркера.
        Применяет Smart Queue: воркеры с высоким worker_score видят сложные/дорогие заказы первыми.

        Args:
            session: Сессия БД
            categories: Категории, которые может обрабатывать воркер
            services: Сервисы, которые может обрабатывать воркер (опционально)
            limit: Максимальное количество заказов
            worker_score: Рейтинг воркера (1.0–5.0); влияет на приоритет показа заказов
        
        Returns:
            Список заказов, отсортированных по приоритету
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Searching orders for worker categories: {categories}, services: {services}")
        
        # Маппим старые категории воркеров на новые категории заказов
        mapped_categories = []
        for category in categories:
            if category in CATEGORY_MAPPING:
                mapped_categories.append(CATEGORY_MAPPING[category])
            else:
                mapped_categories.append(category)  # Если маппинга нет, используем как есть
        
        # Убираем дубликаты
        mapped_categories = list(set(mapped_categories))
        
        logger.info(f"Mapped to order categories: {mapped_categories}")
        logger.info(f"Using status: {support_bot_config.ORDER_STATUS_PENDING}")
        
        # Базовые условия фильтрации
        conditions = [
            Order.category.in_(mapped_categories),
            Order.status == support_bot_config.ORDER_STATUS_PENDING,
            Order.worker_id.is_(None)
        ]
        
        # Если сервисы НЕ указаны или список пуст, воркер не должен видеть заказы
        if not services:
            logger.info("Worker has no services configured, returning empty list")
            return []
        
        # Получаем все заказы по категориям без фильтра по сервисам
        result = await session.execute(
            select(Order)
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .limit(limit * 3)  # Берем больше, чтобы отфильтровать потом
            .options(selectinload(Order.bulk_items))
        )
        all_orders = result.scalars().all()
        
        logger.info(f"Found {len(all_orders)} orders before service filtering")
        
        # Фильтруем заказы по сервисам используя гибкую логику
        filtered_orders = []
        for order in all_orders:
            # Проверяем доступ через can_worker_access_order
            if can_worker_access_order(categories, services, order.category, order.service_name):
                filtered_orders.append(order)
                if len(filtered_orders) >= limit:
                    break
        
        logger.info(f"Found {len(filtered_orders)} available orders after service filtering")

        # Smart Queue: sort by priority based on worker_score
        # High-score workers (>=4.5) get expensive/complex orders first
        # New workers (score<2.0) get cheaper orders first
        def _priority_key(order: Order):
            price = float(getattr(order, 'worker_payout', 0) or getattr(order, 'price', 0) or 0)
            created_ts = getattr(order, 'created_at', None)
            age_mins = 0
            if created_ts:
                try:
                    from datetime import datetime, timezone
                    age_mins = (datetime.now(timezone.utc) - created_ts).total_seconds() / 60
                except Exception:
                    pass
            if worker_score >= 4.5:
                # High-score: expensive orders first, then by age
                return (-price, -age_mins)
            elif worker_score < 2.0:
                # Low-score / new: cheap orders first
                return (price, -age_mins)
            else:
                # Mid-range: oldest orders first (FIFO, fair)
                return (0, -age_mins)

        filtered_orders.sort(key=_priority_key)
        return filtered_orders
    
    @staticmethod
    async def get_worker_orders(
        session: AsyncSession,
        worker_id: int,
        status: Optional[str] = None
    ) -> List[Order]:
        """Получить заказы воркера"""
        query = select(Order).where(Order.worker_id == worker_id)
        
        if status:
            query = query.where(Order.status == status)
        
        query = query.order_by(Order.taken_at.desc()).options(selectinload(Order.bulk_items))
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_order(session: AsyncSession, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        result = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.bulk_items))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def take_order(
        session: AsyncSession,
        order: Order,
        worker: Worker
    ) -> bool:
        """
        Взять заказ в работу
        
        Returns:
            True если успешно взят, False если уже занят
        """
        # Проверяем, что заказ еще не взят
        await session.refresh(order)
        
        if order.worker_id is not None or order.status != support_bot_config.ORDER_STATUS_PENDING:
            return False
        
        # Блокируем заказ
        order.worker_id = worker.id
        order.status = support_bot_config.ORDER_STATUS_PROCESSING
        order.taken_at = datetime.now(timezone.utc)
        await WorkerOrderService.ensure_from_order(session, order)
        
        await session.commit()
        worker_order = await WorkerOrderService.ensure_from_order(session, order)
        await session.commit()
        reminder_hours = await PricingConfigService.get_value(session, "worker_order_reminder_hours", 2)
        async with tasks_session_maker() as task_session:
            await WorkerReminderTaskService.schedule(
                task_session,
                order_id=order.id,
                worker_order_id=worker_order.id,
                worker_id=worker.id,
                worker_telegram_id=worker.telegram_id,
                delay_hours=float(reminder_hours or 2),
                payload_json={"category": order.category, "service_name": order.service_name},
            )
        return True
    
    @staticmethod
    async def complete_order(
        session: AsyncSession,
        order: Order,
        result_data: Optional[dict] = None,
        notes: Optional[str] = None
    ):
        """Завершить заказ (все элементы DONE)"""
        order.status = support_bot_config.ORDER_STATUS_COMPLETED
        order.completed_at = datetime.now(timezone.utc)
        
        if result_data:
            order.result_data = result_data
        if notes:
            order.notes = notes

        # Учёт spent для владельца бота
        from shared.services.bot_owner_stats import record_owner_spent
        from shared.services.worker_earnings_service import credit_worker_on_order_complete
        from decimal import Decimal
        amount = order.price
        if result_data:
            if result_data.get("status") == "nf":
                amount = Decimal("0")  # NF = полный возврат
            elif "done" in result_data and "total" in result_data:
                done, total = result_data["done"], result_data["total"]
                if total and total > 0:
                    amount = (order.price * Decimal(str(done))) / Decimal(str(total))
        await record_owner_spent(session, order.mirror_bot_id, amount)

        # Начисление воркеру (fixed_price / commission_percent / 100%)
        if order.worker_id and amount > 0:
            await credit_worker_on_order_complete(
                session, order.worker_id, order,
                order_income_override=amount,
            )

        await WorkerOrderService.ensure_from_order(session, order)
        await session.commit()
        async with tasks_session_maker() as task_session:
            await WorkerReminderTaskService.cancel_for_order(task_session, order.id)
    
    @staticmethod
    async def set_addinfo_waiting(
        session: AsyncSession,
        order: Order,
        wait_hours: int,
        notes: Optional[str] = None
    ):
        """Установить Add Info заказ в режим ожидания (не завершать)"""
        # Не меняем статус на completed, оставляем processing
        # Но сохраняем информацию о времени ожидания
        order.wait_time_hours = wait_hours
        order.result_data = {
            "status": "info_added", 
            "wait_hours": wait_hours,
            "added_at": datetime.now(timezone.utc).isoformat()
        }
        
        if notes:
            order.notes = notes
        
        await WorkerOrderService.ensure_from_order(session, order)
        await session.commit()
        async with tasks_session_maker() as task_session:
            await WorkerReminderTaskService.cancel_for_order(task_session, order.id)
    
    @staticmethod
    async def cancel_order(session: AsyncSession, order: Order):
        """Отменить заказ"""
        order.status = support_bot_config.ORDER_STATUS_CANCELLED
        order.completed_at = datetime.now(timezone.utc)
        await WorkerOrderService.ensure_from_order(session, order)
        await session.commit()
        async with tasks_session_maker() as task_session:
            await WorkerReminderTaskService.cancel_for_order(task_session, order.id)
    
    @staticmethod
    async def update_bulk_item_status(
        session: AsyncSession,
        item: BulkOrderItem,
        status: str,
        result_data: Optional[dict] = None
    ):
        """Обновить статус элемента bulk заказа"""
        item.status = status
        item.completed_at = datetime.now(timezone.utc)
        
        if result_data:
            item.result_data = result_data
        
        await session.commit()
    
    @staticmethod
    async def check_bulk_order_completion(
        session: AsyncSession,
        order: Order
    ) -> bool:
        """
        Проверить, завершен ли bulk заказ
        
        Returns:
            True если все элементы обработаны (done или nf)
        """
        if not order.is_bulk:
            return False
        
        await session.refresh(order, ['bulk_items'])
        
        for item in order.bulk_items:
            if item.status == support_bot_config.ITEM_STATUS_PENDING:
                return False
        
        return True
    
    @staticmethod
    async def get_bulk_item(session: AsyncSession, order_id: int, item_number: int):
        """Получить конкретный элемент bulk заказа"""
        from sqlalchemy import select
        from shared.database.models import BulkOrderItem
        
        stmt = select(BulkOrderItem).where(
            BulkOrderItem.order_id == order_id,
            BulkOrderItem.item_number == item_number
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_bulk_item_summary(order: Order) -> dict:
        """Получить сводку по bulk заказу"""
        done_count = sum(1 for item in order.bulk_items if item.status == "done")
        nf_count = sum(1 for item in order.bulk_items if item.status == "nf")
        pending_count = sum(1 for item in order.bulk_items if item.status == "pending")
        
        return {
            "done": done_count,
            "nf": nf_count,
            "pending": pending_count,
            "total": len(order.bulk_items)
        }

