"""
Хэндлеры для работы с single заказами
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from datetime import datetime

from support_bot.services.worker_service import WorkerService
from support_bot.services.order_service import OrderService, can_worker_access_order_category, can_worker_access_order
from support_bot.services.notification_service import NotificationService
from support_bot.services.balance_service import BalanceService
from support_bot.services.support_logger import SupportLogger
from support_bot.services.order_delivery_service import OrderDeliveryService
from support_bot.keyboards.inline import (
    order_list_keyboard,
    single_order_keyboard,
    bulk_order_keyboard,
    main_menu_keyboard,
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from support_bot.config import support_bot_config
from support_bot.utils import safe_edit_message, safe_answer_callback
from support_bot.constants.service_names import get_full_service_name
from shared.database.tasks_session import tasks_session_maker
from shared.services.worker_reminder_task_service import WorkerReminderTaskService
from shared.services.worker_order_service import WorkerOrderService
from shared.utils.chat_filter import filter_and_log, is_message_blocked

router = Router(name="orders")
logger = logging.getLogger(__name__)


class OrderStates(StatesGroup):
    """Состояния для работы с заказами"""
    waiting_for_info = State()
    waiting_for_complaint = State()
    waiting_for_text_result = State()


def complaint_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для ввода жалобы с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_complaint:{order_id}")]
    ])


def format_order_data(data: dict) -> str:
    """Форматирование данных заказа для отображения"""
    lines = []
    
    # Определяем порядок и форматирование для известных полей
    field_order = [
        ('first_name', '👤 Name'),
        ('last_name', None),  # Объединяем с first_name
        ('address', '📍 Address'),
        ('city', '🏙️ City'),
        ('state', None),  # Объединяем с city
        ('zip_code', None),  # Объединяем с city
        ('dob', '🎂 DOB'),
        ('ssn', '🆔 SSN'),
        ('dl', '🚗 DL'),
        ('phone', '📞 Phone'),
        ('email', '📧 Email'),
        ('mmn', '👩 MMN'),
        ('cs', '💳 Credit Score'),
        ('bg', '📋 Background'),
        ('business_name', '🏢 Business'),
        ('ein', '🏭 EIN'),
    ]
    
    # Обрабатываем поля в определенном порядке
    processed_keys = set()
    
    # Имя (объединяем first и last)
    if 'first_name' in data or 'last_name' in data:
        name_parts = []
        if 'first_name' in data and data['first_name']:
            name_parts.append(data['first_name'])
            processed_keys.add('first_name')
        if 'last_name' in data and data['last_name']:
            name_parts.append(data['last_name'])
            processed_keys.add('last_name')
        if name_parts:
            lines.append(f"👤 <b>Name:</b> <code>{' '.join(name_parts)}</code>")
    
    # Адрес
    if 'address' in data and data['address']:
        lines.append(f"📍 <b>Address:</b> <code>{data['address']}</code>")
        processed_keys.add('address')
    
    # Город, штат, индекс (объединяем)
    location_parts = []
    if 'city' in data and data['city']:
        location_parts.append(data['city'])
        processed_keys.add('city')
    if 'state' in data and data['state']:
        location_parts.append(data['state'])
        processed_keys.add('state')
    if 'zip_code' in data and data['zip_code']:
        location_parts.append(str(data['zip_code']))
        processed_keys.add('zip_code')
    elif 'zip' in data and data['zip']:
        location_parts.append(str(data['zip']))
        processed_keys.add('zip')
    if location_parts:
        lines.append(f"🏙️ <b>Location:</b> <code>{', '.join(location_parts)}</code>")
    
    # Опциональные поля (показываем только если есть)
    if 'dob' in data and data['dob']:
        lines.append(f"🎂 <b>DOB:</b> <code>{data['dob']}</code>")
        processed_keys.add('dob')
    
    if 'ssn' in data and data['ssn']:
        lines.append(f"🆔 <b>SSN:</b> <code>{data['ssn']}</code>")
        processed_keys.add('ssn')
    
    if 'dl' in data and data['dl']:
        lines.append(f"🚗 <b>DL:</b> <code>{data['dl']}</code>")
        processed_keys.add('dl')
    
    if 'phone' in data and data['phone']:
        lines.append(f"📞 <b>Phone:</b> <code>{data['phone']}</code>")
        processed_keys.add('phone')
    
    if 'email' in data and data['email']:
        lines.append(f"📧 <b>Email:</b> <code>{data['email']}</code>")
        processed_keys.add('email')
    
    if 'mmn' in data and data['mmn']:
        lines.append(f"👩 <b>MMN:</b> <code>{data['mmn']}</code>")
        processed_keys.add('mmn')
    
    if 'cs' in data and data['cs']:
        lines.append(f"💳 <b>Credit Score:</b> <code>{data['cs']}</code>")
        processed_keys.add('cs')
    
    if 'bg' in data and data['bg']:
        lines.append(f"📋 <b>Background:</b> <code>{data['bg']}</code>")
        processed_keys.add('bg')
    
    if 'business_name' in data and data['business_name']:
        lines.append(f"🏢 <b>Business:</b> <code>{data['business_name']}</code>")
        processed_keys.add('business_name')
    
    if 'ein' in data and data['ein']:
        lines.append(f"🏭 <b>EIN:</b> <code>{data['ein']}</code>")
        processed_keys.add('ein')
    
    # Показываем количество если больше 1
    if 'quantity' in data and data['quantity'] and int(data.get('quantity', 1)) > 1:
        lines.append(f"📦 <b>Quantity:</b> <code>{data['quantity']}</code>")
        processed_keys.add('quantity')
    
    # Добавляем все остальные поля, которые не были обработаны
    for key, value in data.items():
        if key not in processed_keys and value:
            # Пропускаем служебные поля и поля связанные с ценой
            if key in ['quantity', 'price', 'service', 'category', 'status', 'id', 
                       'base_price', 'total_price', 'unit_price', 'final_price']:
                continue
            key_formatted = key.replace("_", " ").title()
            lines.append(f"<b>{key_formatted}:</b> <code>{value}</code>")
    
    return "\n".join(lines) if lines else "No data available"


def format_hidden_customer_data() -> str:
    return "👤 Client Data: [hidden]\nTake the order to reveal client data."


@router.callback_query(F.data == "orders_available")
async def show_available_orders(callback: CallbackQuery, session: AsyncSession, worker=None):
    """Показать доступные заказы"""
    
    # Получаем воркера из middleware или запрашиваем из БД
    if not worker:
        worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Добавляем отладочную информацию
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.id} requesting orders. Categories: {worker.categories}, Services: {worker.services}")
    
    # Получаем доступные заказы с учётом сервисов и Worker Score (Smart Queue)
    worker_score = float(getattr(worker, 'worker_score', 0.0) or 0.0)
    orders = await OrderService.get_available_orders(
        session, worker.categories, worker.services, worker_score=worker_score
    )
    
    if not orders:
        await safe_edit_message(callback,
            "📦 <b>Available Orders</b>\n\n"
            "No orders available at the moment.\n"
            "Check back later!",
            reply_markup=main_menu_keyboard()
        )
        await safe_answer_callback(callback)
        return
    
    # Форматируем список заказов
    orders_data = []
    for order in orders:
        orders_data.append({
            "id": order.id,
            "category": order.category,
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count
        })
    
    await safe_edit_message(callback,
        f"📦 <b>Available Orders ({len(orders)})</b>\n\n"
        f"Click on an order to view details:",
        reply_markup=order_list_keyboard(orders_data)
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data == "orders_my_processing")
async def show_my_orders(callback: CallbackQuery, session: AsyncSession):
    """Показать мои заказы в работе"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем заказы в работе
    orders = await OrderService.get_worker_orders(
        session,
        worker.id,
        status=support_bot_config.ORDER_STATUS_PROCESSING
    )
    
    if not orders:
        await safe_edit_message(callback,
            "🔄 <b>My Orders (Processing)</b>\n\n"
            "You have no orders in progress.",
            reply_markup=main_menu_keyboard()
        )
        await safe_answer_callback(callback)
        return
    
    # Форматируем список
    orders_data = []
    for order in orders:
        orders_data.append({
            "id": order.id,
            "category": order.category,
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count
        })
    
    await safe_edit_message(callback,
        f"🔄 <b>My Orders ({len(orders)})</b>\n\n"
        f"Orders you're currently working on:",
        reply_markup=order_list_keyboard(orders_data)
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("order_view:"))
async def view_order(callback: CallbackQuery, session: AsyncSession):
    """Просмотр конкретного заказа"""
    
    order_id = int(callback.data.split(":")[1])
    
    order = await OrderService.get_order(session, order_id)
    
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    # Проверяем доступ воркера к этому заказу (категория + сервис)
    # Разрешаем просмотр только если:
    # 1. Заказ взят этим воркером ИЛИ
    # 2. Воркер имеет доступ к категории И сервису заказа
    is_taken_by_worker = (order.worker_id == worker.id) if order.worker_id else False
    
    if not is_taken_by_worker:
        # Если заказ не взят этим воркером, проверяем права доступа
        if not can_worker_access_order(worker.categories, worker.services, order.category, order.service_name):
            await callback.answer("❌ Access denied to this order", show_alert=True)
            return
    
    # Проверяем, взят ли заказ этим воркером
    is_taken = is_taken_by_worker
    is_available = order.worker_id is None
    
    # Форматируем данные
    if not order.is_bulk:
        # Single заказ
        reveal_customer_data = is_taken
        data_text = format_order_data(order.input_data) if reveal_customer_data else None
        
        text = f"""📦 <b>ORDER #{order.id}</b>

<b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}
<b>Category:</b> {order.category}
<b>Status:</b> {order.status.upper()}

━━━━━━━━━━━━━━━━━━
<b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}
"""
        if reveal_customer_data:
            text += f"\n👤 <b>Customer Data:</b>\n{data_text}\n"
        else:
            text += "\n👤 Client Data: [hidden]\nTake the order to reveal client data.\n"
        
        if is_taken:
            text += f"\n✅ <b>Taken by you</b> at {order.taken_at.strftime('%d.%m.%Y %H:%M')}"
        elif not is_available:
            text += f"\n⚠️ <b>Taken by another worker</b>"
        
        keyboard = single_order_keyboard(order.id, is_taken, order.result_data, order.status)
        
    else:
        # Bulk заказ
        summary = await OrderService.get_bulk_item_summary(order)
        
        text = f"""📦 <b>BULK ORDER #{order.id}</b>

<b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}
<b>Category:</b> {order.category}
<b>Items:</b> {order.bulk_count}
<b>Status:</b> {order.status.upper()}

━━━━━━━━━━━━━━━━━━
<b>Progress:</b>
   ✅ DONE: {summary['done']}
   ❌ NF: {summary['nf']}
   ⏳ Pending: {summary['pending']}

<b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}

💡 <b>Quick View:</b>"""
        
        # Добавляем краткий список первых 5 элементов
        if order.bulk_items:
            quick_items = []
            for item in sorted(order.bulk_items, key=lambda x: x.item_number)[:5]:
                status_emoji = {
                    "pending": "⏳",
                    "done": "✅",
                    "nf": "❌"
                }[item.status]
                
                # До взятия заказа скрываем данные клиента даже в quick view.
                if not is_taken:
                    quick_items.append(f"{item.item_number}. {status_emoji} [hidden]")
                elif item.input_data:
                    first_key = list(item.input_data.keys())[0]
                    first_value = str(item.input_data[first_key])[:15]
                    quick_items.append(f"{item.item_number}. {status_emoji} {first_value}...")
                else:
                    quick_items.append(f"{item.item_number}. {status_emoji} No data")
            
            text += "\n" + "\n".join(quick_items)
            
            if len(order.bulk_items) > 5:
                text += f"\n... and {len(order.bulk_items) - 5} more items"
        
        text += "\n\n👆 <b>Click number buttons to work on individual items</b>"
        
        if is_taken and order.taken_at:
            text += f"\n✅ <b>Taken by you</b> at {order.taken_at.strftime('%d.%m.%Y %H:%M')}"
        elif is_taken:
            text += f"\n✅ <b>Taken by you</b>"
        elif is_available:
            text += "\n👤 Client Data: [hidden]\nTake the order to reveal item details."
        
        keyboard = bulk_order_keyboard(order.id, order.bulk_count, is_taken, order.bulk_items)
    
    await safe_edit_message(callback, text, keyboard)
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("order_take:"))
async def take_order(callback: CallbackQuery, session: AsyncSession):
    """Взять заказ в работу"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    
    # Проверяем доступ с учетом категории И сервиса
    if not can_worker_access_order(worker.categories, worker.services, order.category, order.service_name):
        await callback.answer("❌ You can't take this order (access denied)", show_alert=True)
        return
    
    # Пытаемся взять заказ
    success = await OrderService.take_order(session, order, worker)
    
    if not success:
        await callback.answer("❌ Order already taken by another worker", show_alert=True)
        return
    
    # Уведомляем других воркеров что заказ взят
    try:
        from support_bot.services.order_notification_service import OrderNotificationService
        await OrderNotificationService.notify_worker_order_taken(
            session, order, worker.id
        )
    except Exception as e:
        logger.warning(f"Failed to notify workers about taken order: {e}")
    
    # Логируем взятие заказа
    await SupportLogger.log_order_taken(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id
    )
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_order_taken(
            order_id=order.id,
            service_name=order.service_name,
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            user_id=order.user_id
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
    
    await callback.answer("✅ Order taken!", show_alert=True)
    
    # Обновляем отображение заказа
    await view_order(callback, session)


@router.callback_query(F.data.startswith("order_done:"))
async def mark_order_done(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отметить заказ как выполненный"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Завершаем заказ
    await OrderService.complete_order(session, order)
    
    # Обновляем статистику
    await WorkerService.increment_stat(session, worker.id, order.category, "done")
    
    # Увеличиваем счетчик выполненных заказов
    worker.orders_completed += 1
    await session.commit()
    
    # Отправляем уведомление клиенту через новую систему
    try:
        # Получаем язык пользователя
        user_language = await OrderDeliveryService.get_user_language(
            session, order.user_id, order.mirror_bot_id
        )
        
        success = await OrderDeliveryService.deliver_single_order_result(
            user_id=order.user_id,
            mirror_bot_id=order.mirror_bot_id,
            order_id=order.id,
            service_name=order.service_name,
            result_status="done",
            customer_data=order.input_data,
            files=[],
            result_text=None,
            user_language=user_language
        )
        
        # Fallback на старую систему если новая не сработала
        if not success:
            logger.warning(f"New notification system failed for order {order.id}, using fallback")
            await NotificationService.notify_order_completed(
                order, 
                result_status="done",
                session=session
            )
    except Exception as e:
        logger.error(f"Failed to notify user about order completion: {e}")
        # Пытаемся использовать fallback систему
        try:
            await NotificationService.notify_order_completed(
                order, 
                result_status="done",
                session=session
            )
        except Exception as fallback_error:
            logger.error(f"Fallback notification also failed: {fallback_error}")
    
    # Логируем завершение заказа
    await SupportLogger.log_order_completed(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id,
        result_status="done"
    )
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_order_completed(
            order_id=order.id,
            service_name=order.service_name,
            result_status="done",
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            user_id=order.user_id,
            price=float(order.price)
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
    
    await callback.answer("✅ Order marked as DONE!", show_alert=True)
    
    await safe_edit_message(callback,
        f"✅ <b>Order #{order.id} Completed!</b>\n\n"
        f"Status: DONE\n"
        f"Category: {order.category}\n\n"
        f"Good job! 👍",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("order_reset:"))
async def reset_order_to_pending(callback: CallbackQuery, session: AsyncSession):
    """Сбросить заказ в статус pending"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Полный reset должен вернуть заказ обратно в общую очередь.
    old_status = order.status
    order.status = support_bot_config.ORDER_STATUS_PENDING
    order.completed_at = None
    order.worker_id = None
    order.taken_at = None
    await WorkerOrderService.ensure_from_order(session, order)
    await session.commit()
    async with tasks_session_maker() as task_session:
        await WorkerReminderTaskService.cancel_for_order(task_session, order.id)
    
    # Логируем действие
    await SupportLogger.log_order_reset(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        old_status=old_status
    )
    
    await callback.answer("✅ Order returned to pending queue")
    
    # Обновляем отображение
    await view_order(callback, session)


@router.callback_query(F.data.startswith("order_add_files:"))
async def add_files_to_order(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Добавить файлы к выполненному заказу"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Устанавливаем состояние для загрузки файлов
    from support_bot.handlers.files import FileStates
    await state.set_state(FileStates.waiting_for_file)
    await state.update_data(order_id=order_id, item_number=None)
    
    await safe_edit_message(
        callback,
        f"📎 <b>Add Files to Order #{order_id}</b>\n\n"
        f"Please send files (documents, photos, etc.) for this order.\n"
        f"You can send multiple files at once.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"order_view:{order_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_nav:"))
async def navigate_orders(callback: CallbackQuery, session: AsyncSession):
    """Навигация между заказами"""
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    direction = parts[2]
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    # Получаем все заказы воркера
    orders = await OrderService.get_worker_orders(session, worker.id, status="done")
    orders.extend(await OrderService.get_worker_orders(session, worker.id, status="nf"))
    orders.sort(key=lambda x: x.id)
    
    # Находим текущий заказ
    current_index = next((i for i, o in enumerate(orders) if o.id == order_id), None)
    
    if current_index is None:
        await callback.answer("Order not found", show_alert=True)
        return
    
    # Определяем следующий заказ
    if direction == "prev":
        new_index = (current_index - 1) % len(orders)
    else:  # next
        new_index = (current_index + 1) % len(orders)
    
    new_order = orders[new_index]
    
    class TempCallback:
        def __init__(self, order_id, original_callback):
            self.data = f"order_view:{order_id}"
            self.message = original_callback.message
            self.from_user = original_callback.from_user
        async def answer(self, *args, **kwargs):
            pass
    
    temp_callback = TempCallback(new_order.id, callback)
    await view_order(temp_callback, session)
    
    await callback.answer(f"Order #{new_order.id}")


@router.callback_query(F.data.startswith("order_nf:"))
async def mark_order_nf(callback: CallbackQuery, session: AsyncSession):
    """Отметить заказ как NF (не найдено)"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Возвращаем средства пользователю
    refund_success = await BalanceService.refund_order(session, order.user_id, order.price, order.id)

    if not refund_success:
        logger.error(f"Failed to refund order {order.id} — aborting NF, user funds not returned")
        await callback.answer("❌ Refund failed — order NOT closed. Contact developer.", show_alert=True)
        return
    
    # Завершаем заказ с результатом NF
    await OrderService.complete_order(session, order, result_data={"status": "nf", "refunded": refund_success})
    
    # Обновляем статистику
    await WorkerService.increment_stat(session, worker.id, order.category, "nf")
    
    # Отправляем уведомление клиенту через новую систему
    # Получаем язык пользователя
    user_language = await OrderDeliveryService.get_user_language(
        session, order.user_id, order.mirror_bot_id
    )
    
    success = await OrderDeliveryService.deliver_single_order_result(
        user_id=order.user_id,
        mirror_bot_id=order.mirror_bot_id,
        order_id=order.id,
        service_name=order.service_name,
        result_status="nf",
        customer_data=order.input_data,
        refund_amount=float(order.price),
        files=[],
        result_text=None,
        user_language=user_language
    )
    
    # Fallback на старую систему если новая не сработала
    if not success:
        logger.warning(f"New notification system failed for order {order.id}, using fallback")
        await NotificationService.notify_order_completed(
            order, 
            result_status="nf",
            session=session
        )
    
    # Логируем завершение заказа как NF
    await SupportLogger.log_order_completed(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id,
        result_status="nf"
    )
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_order_completed(
            order_id=order.id,
            service_name=order.service_name,
            result_status="nf",
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            user_id=order.user_id,
            refund_amount=float(order.price)
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
    
    await callback.answer("Order marked as NF, balance refunded", show_alert=True)
    
    await safe_edit_message(callback,
        f"❌ <b>Order #{order.id} - NF</b>\n\n"
        f"Status: Not Found\n"
        f"Category: {order.category}\n"
        f"Balance refunded: {'✅ Yes' if refund_success else '❌ Failed'}",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("order_reply_text:"))
async def reply_with_text_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик для кнопки 'Reply with Text' - отправка текстового результата"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Устанавливаем состояние для ожидания текста
    await state.set_state(OrderStates.waiting_for_text_result)
    await state.update_data(order_id=order_id, is_bulk=False)
    
    await safe_edit_message(callback,
        f"💬 <b>Send Text Result</b>\n\n"
        f"📦 <b>Order #{order.id}</b>\n"
        f"🔧 <b>Service:</b> {order.service_name}\n\n"
        f"📝 Please send your text result for this order:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"order_view:{order_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bulk_reply_text:"))
async def bulk_reply_with_text_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Обработчик для кнопки 'Reply with Text' для bulk items"""
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Устанавливаем состояние для ожидания текста
    await state.set_state(OrderStates.waiting_for_text_result)
    await state.update_data(order_id=order_id, item_number=item_number, is_bulk=True)
    
    await safe_edit_message(callback,
        f"💬 <b>Send Text Result</b>\n\n"
        f"📦 <b>Order #{order.id} - Item #{item_number}</b>\n"
        f"🔧 <b>Service:</b> {order.service_name}\n\n"
        f"📝 Please send your text result for this item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"bulk_item:{order_id}:{item_number}")]
        ])
    )
    await callback.answer()


@router.message(OrderStates.waiting_for_text_result)
async def receive_text_result(message: Message, session: AsyncSession, state: FSMContext):
    """Получение текстового результата от воркера"""
    
    data = await state.get_data()
    order_id = data.get("order_id")
    item_number = data.get("item_number")
    is_bulk = data.get("is_bulk", False)
    
    if not order_id:
        await message.answer("❌ Error: Order ID not found")
        await state.clear()
        return
    
    worker = await WorkerService.get_worker(session, message.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await message.answer("❌ Access denied")
        await state.clear()
        return
    
    text_result = (message.text or "").strip()
    if not text_result or len(text_result) < 5:
        await message.answer("❌ Text result is too short (min 5 characters). Please send the actual result.")
        return
    if is_message_blocked(text_result):
        await message.answer("❌ Message contains only contact information and was blocked.")
        return
    text_result, violated = await filter_and_log(
        text=text_result,
        worker_id=worker.id,
        order_id=order.id,
        session=session,
    )
    
    if is_bulk and item_number:
        # Обработка bulk item
        bulk_item = await OrderService.get_bulk_item(session, order_id, item_number)
        if not bulk_item:
            await message.answer("❌ Bulk item not found")
            await state.clear()
            return
        
        # Отмечаем элемент как выполненный
        bulk_item.status = "done"
        bulk_item.result_text = text_result
        await session.commit()
        
        # Обновляем статистику
        await WorkerService.increment_stat(session, worker.id, order.category, "done")
        
        # Отправляем уведомление клиенту
        await OrderDeliveryService.notify_bulk_item_completed(
            user_id=order.user_id,
            mirror_bot_id=order.mirror_bot_id,
            order_id=order.id,
            item_number=item_number,
            service_name=order.service_name,
            result_status="done",
            customer_data=bulk_item.input_data,
            files=[],  # Нет файлов, только текст
            result_text=text_result
        )
        
        # Логируем завершение элемента
        await SupportLogger.log_bulk_item_completed(
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            order_id=order.id,
            item_number=item_number,
            service_name=order.service_name,
            user_id=order.user_id,
            result_status="done"
        )
        
        # Уведомляем админов
        try:
            from shared.services.admin_notification_service import AdminNotificationService
            await AdminNotificationService.notify_bulk_item_completed(
                order_id=order.id,
                item_number=item_number,
                service_name=order.service_name,
                result_status="done",
                worker_username=worker.username or str(worker.telegram_id),
                worker_id=worker.id,
                user_id=order.user_id
            )
        except Exception as e:
            logger.warning(f"Failed to send admin notification: {e}")
        
        warning_text = "⚠️ Contact information was removed.\n" if violated else ""
        await message.answer(
            f"✅ <b>Bulk Item #{item_number} Completed!</b>\n\n"
            f"📝 Text result sent to customer.\n"
            f"{warning_text}"
            f"Great work! 👍"
        )
        
        await state.clear()
        
    else:
        # Обработка single order
        await OrderService.complete_order(session, order)
        order.result_text = text_result
        await session.commit()
        
        # Обновляем статистику
        await WorkerService.increment_stat(session, worker.id, order.category, "done")
        
        # Увеличиваем счетчик выполненных заказов
        worker.orders_completed += 1
        await session.commit()
        
        # Отправляем уведомление клиенту
        # Получаем язык пользователя
        user_language = await OrderDeliveryService.get_user_language(
            session, order.user_id, order.mirror_bot_id
        )
        
        await OrderDeliveryService.deliver_single_order_result(
            user_id=order.user_id,
            mirror_bot_id=order.mirror_bot_id,
            order_id=order.id,
            service_name=order.service_name,
            result_status="done",
            customer_data=order.input_data,
            files=[],  # Нет файлов, только текст
            result_text=text_result,
            user_language=user_language
        )
        
        # Логируем завершение заказа
        await SupportLogger.log_order_completed(
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            order_id=order.id,
            service_name=order.service_name,
            user_id=order.user_id,
            result_status="done"
        )
        
        # Уведомляем админов
        try:
            from shared.services.admin_notification_service import AdminNotificationService
            await AdminNotificationService.notify_order_completed(
                order_id=order.id,
                service_name=order.service_name,
                result_status="done",
                worker_username=worker.username or str(worker.telegram_id),
                worker_id=worker.id,
                user_id=order.user_id,
                price=float(order.price)
            )
        except Exception as e:
            logger.warning(f"Failed to send admin notification: {e}")
        
        warning_text = "⚠️ Contact information was removed.\n" if violated else ""
        await message.answer(
            f"✅ <b>Order #{order.id} Completed!</b>\n\n"
            f"📝 Text result sent to customer.\n"
            f"{warning_text}"
            f"Great work! 👍"
        )
    
        await state.clear()



@router.callback_query(F.data.startswith("cancel_complaint:"))
async def cancel_complaint(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отмена жалобы"""
    
    order_id = int(callback.data.split(":")[1])
    
    # Очищаем состояние
    await state.clear()
    
    # Возвращаемся к заказу
    await show_order_details(callback, session, order_id)
    await callback.answer("❌ Complaint cancelled")


# Вспомогательная функция для возврата к заказу
async def show_order_details(callback: CallbackQuery, session: AsyncSession, order_id: int):
    """Показать детали заказа"""
    class TempCallback:
        def __init__(self, order_id, original_callback):
            self.data = f"order_view:{order_id}"
            self.message = original_callback.message
            self.from_user = original_callback.from_user
        async def answer(self, *args, **kwargs):
            pass
    
    temp_callback = TempCallback(order_id, callback)
    await view_order(temp_callback, session)


@router.callback_query(F.data.startswith("order_cancel:"))
async def cancel_order(callback: CallbackQuery, session: AsyncSession):
    """Отменить заказ"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Возвращаем средства пользователю
    refund_success = await BalanceService.refund_order(session, order.user_id, order.price, order.id)
    
    if not refund_success:
        logger.warning(f"Failed to refund order {order.id}, but cancelling anyway")
    
    # Отменяем заказ
    await OrderService.cancel_order(session, order)
    
    # Обновляем статистику
    await WorkerService.increment_stat(session, worker.id, order.category, "cancelled")
    
    # Уведомляем клиента
    await NotificationService.notify_order_cancelled(order)
    
    # Логируем отмену заказа
    await SupportLogger.log_order_cancelled(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id,
        reason="Cancelled by support worker"
    )
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_order_cancelled(
            order_id=order.id,
            service_name=order.service_name,
            user_id=order.user_id,
            refund_amount=float(order.price),
            reason="Cancelled by support worker",
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
    
    await callback.answer("Order cancelled, balance refunded", show_alert=True)
    
    await safe_edit_message(callback,
        f"❌ <b>Order #{order.id} Cancelled</b>\n\n"
        f"The order has been cancelled.\n"
        f"Balance refunded: {'✅ Yes' if refund_success else '❌ Failed'}",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("order_complaint:"))
async def report_client(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Подать жалобу на клиента"""
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Сохраняем order_id в state для последующего использования
    await state.update_data(complaint_order_id=order_id)
    await state.set_state(OrderStates.waiting_for_complaint)
    
    await safe_edit_message(callback,
        f"⚠️ <b>Report Client - Order #{order.id}</b>\n\n"
        f"<b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}\n"
        f"<b>Client:</b> hidden\n\n"
        f"Please describe the issue with this client:\n"
        f"(e.g., rude behavior, unreasonable demands, spam, etc.)\n\n"
        f"Type your complaint message:",
        reply_markup=complaint_keyboard(order_id)
    )
    await callback.answer()


@router.message(OrderStates.waiting_for_complaint)
async def process_complaint(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка жалобы на клиента"""
    
    try:
        data = await state.get_data()
        order_id = data.get("complaint_order_id")
        
        if not order_id:
            await message.answer("❌ Error: Order not found")
            await state.clear()
            return
        
        worker = await WorkerService.get_worker(session, message.from_user.id)
        order = await OrderService.get_order(session, order_id)
        
        if not order or order.worker_id != worker.id:
            await message.answer("❌ Access denied")
            await state.clear()
            return
        
        complaint_text = message.text.strip()
        
        if len(complaint_text) < 10:
            data = await state.get_data()
            order_id = data.get("complaint_order_id")
            await message.answer(
                "❌ Complaint too short!\n"
                "Please provide more details (minimum 10 characters).",
                reply_markup=complaint_keyboard(order_id) if order_id else None
            )
            return
        
        # Создаем жалобу в БД
        from support_bot.services.complaint_service import ComplaintService
        complaint = await ComplaintService.create_complaint(
            session=session,
            worker_id=worker.id,
            user_id=order.user_id,
            order_id=order.id,
            reason="client_behavior",
            description=complaint_text
        )
        
        # Логируем жалобу в админский чат
        await SupportLogger.log_complaint_filed(
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            order_id=order.id,
            user_id=order.user_id,
            complaint_text=complaint_text
        )
        
        # Уведомляем админов
        try:
            from shared.services.admin_notification_service import AdminNotificationService
            await AdminNotificationService.notify_new_complaint(
                complaint_id=complaint.id,
                worker_username=worker.username or str(worker.telegram_id),
                worker_id=worker.id,
                user_id=order.user_id,
                order_id=order.id,
                complaint_text=complaint_text
            )
        except Exception as e:
            logger.warning(f"Failed to send admin notification: {e}")
        
        await message.answer(
            f"✅ <b>Complaint Submitted</b>\n\n"
            f"<b>Complaint ID:</b> #{complaint.id}\n"
            f"Your complaint about the buyer has been recorded.\n"
            f"Order: #{order.id}\n\n"
            f"Administrators will review this case.\n"
            f"Thank you for reporting! 🙏",
            reply_markup=main_menu_keyboard()
        )
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error processing complaint: {e}")
        await message.answer("❌ Error processing complaint")
        await state.clear()


@router.callback_query(F.data == "orders_refresh")
async def refresh_orders(callback: CallbackQuery, session: AsyncSession):
    """Обновить список заказов"""
    await show_available_orders(callback, session)

