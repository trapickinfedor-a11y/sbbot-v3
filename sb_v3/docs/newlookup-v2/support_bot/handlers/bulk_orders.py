"""
Хэндлеры для работы с bulk заказами
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from support_bot.services.worker_service import WorkerService
from support_bot.services.order_service import OrderService
from support_bot.services.notification_service import NotificationService
from support_bot.services.balance_service import BalanceService
from support_bot.services.support_logger import SupportLogger
from support_bot.services.order_delivery_service import OrderDeliveryService
from support_bot.keyboards.inline import (
    bulk_item_keyboard,
    bulk_summary_keyboard,
    bulk_order_keyboard,
    main_menu_keyboard
)
from support_bot.config import support_bot_config

router = Router(name="bulk_orders")
logger = logging.getLogger(__name__)


def format_order_data(data: dict) -> str:
    """Форматирование данных для отображения"""
    lines = []
    
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
    
    # Добавляем все остальные поля
    for key, value in data.items():
        if key not in processed_keys and value:
            # Пропускаем служебные поля и поля связанные с ценой
            if key in ['quantity', 'price', 'service', 'category', 'status', 'id',
                       'base_price', 'total_price', 'unit_price', 'final_price']:
                continue
            key_formatted = key.replace("_", " ").title()
            lines.append(f"<b>{key_formatted}:</b> <code>{value}</code>")
    
    return "\n".join(lines) if lines else "No data available"


@router.callback_query(F.data.startswith("bulk_item:"))
async def view_bulk_item(callback: CallbackQuery, session: AsyncSession):
    """
    Просмотр отдельного элемента bulk заказа
    
    Формат: bulk_item:{order_id}:{item_number}
    """
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Находим нужный элемент
    item = next((i for i in order.bulk_items if i.item_number == item_number), None)
    
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    
    # Форматируем данные
    data_text = format_order_data(item.input_data)
    
    # Эмодзи статуса
    status_emoji = {
        "pending": "⏳",
        "done": "✅",
        "nf": "❌"
    }
    
    text = f"""📦 <b>ORDER #{order.id} - Item {item_number}/{order.bulk_count}</b>

<b>Status:</b> {status_emoji.get(item.status, '')} {item.status.upper()}

👤 <b>Data:</b>
{data_text}

━━━━━━━━━━━━━━━━━━
<b>Order Type:</b> {order.service_name}
<b>Category:</b> {order.category}
"""
    
    if item.status != "pending" and item.completed_at:
        text += f"\n<b>Completed:</b> {item.completed_at.strftime('%Y-%m-%d %H:%M')}"
    
    keyboard = bulk_item_keyboard(order.id, item_number, item.status)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("bulk_done:"))
async def mark_bulk_item_done(callback: CallbackQuery, session: AsyncSession):
    """
    Отметить элемент bulk заказа как DONE
    
    Формат: bulk_done:{order_id}:{item_number}
    """
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Находим элемент
    item = next((i for i in order.bulk_items if i.item_number == item_number), None)
    
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    
    # Обновляем статус
    await OrderService.update_bulk_item_status(
        session,
        item,
        support_bot_config.ITEM_STATUS_DONE,
        result_data={"status": "done"}
    )
    
    # Логируем завершение bulk элемента как DONE
    worker = await WorkerService.get_worker(session, callback.from_user.id)
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
    
    await callback.answer("✅ Item marked as DONE!", show_alert=False)
    
    # Проверяем, завершен ли весь bulk заказ
    is_completed = await OrderService.check_bulk_order_completion(session, order)
    
    if is_completed:
        # Если все элементы обработаны - показываем summary
        await show_bulk_summary(callback, session, order_id)
    else:
        # Возвращаемся к элементу, чтобы показать обновленный статус
        await view_bulk_item(callback, session)


@router.callback_query(F.data.startswith("bulk_nf:"))
async def mark_bulk_item_nf(callback: CallbackQuery, session: AsyncSession):
    """
    Отметить элемент bulk заказа как NF
    
    Формат: bulk_nf:{order_id}:{item_number}
    """
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Находим элемент
    item = next((i for i in order.bulk_items if i.item_number == item_number), None)
    
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    
    # Рассчитываем цену за один элемент для возврата
    item_price = order.price / order.bulk_count
    
    # Возвращаем средства за NF элемент
    refund_success = await BalanceService.refund_order(session, order.user_id, item_price, order.id)

    if not refund_success:
        logger.error(f"Failed to refund bulk item {item_number} order {order.id} — aborting NF, user funds not returned")
        await callback.answer("❌ Refund failed — item NOT marked NF. Contact developer.", show_alert=True)
        return
    
    # Обновляем статус
    await OrderService.update_bulk_item_status(
        session,
        item,
        support_bot_config.ITEM_STATUS_NF,
        result_data={"status": "nf"}
    )
    
    # Логируем завершение bulk элемента как NF
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    await SupportLogger.log_bulk_item_completed(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        item_number=item_number,
        service_name=order.service_name,
        user_id=order.user_id,
        result_status="nf",
        refund_amount=item_price
    )
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_bulk_item_completed(
            order_id=order.id,
            item_number=item_number,
            service_name=order.service_name,
            result_status="nf",
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            user_id=order.user_id,
            refund_amount=float(item_price)
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
    
    await callback.answer("Item marked as NF", show_alert=False)
    
    # Проверяем завершение
    is_completed = await OrderService.check_bulk_order_completion(session, order)
    
    if is_completed:
        await show_bulk_summary(callback, session, order_id)
    else:
        await view_bulk_item(callback, session)


@router.callback_query(F.data.startswith("bulk_reset:"))
async def reset_bulk_item(callback: CallbackQuery, session: AsyncSession):
    """
    Сбросить статус элемента bulk заказа в pending
    
    Формат: bulk_reset:{order_id}:{item_number}
    """
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Находим элемент
    item = next((i for i in order.bulk_items if i.item_number == item_number), None)
    
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    
    old_status = item.status
    
    # Сбрасываем статус
    await OrderService.update_bulk_item_status(session, item, "pending")
    
    # Логируем действие
    await SupportLogger.log_bulk_item_reset(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        item_number=item_number,
        old_status=old_status
    )
    
    await callback.answer("✅ Status reset to pending")
    
    # Обновляем отображение
    await view_bulk_item(callback, session)


@router.callback_query(F.data.startswith("bulk_nav:"))
async def navigate_bulk_items(callback: CallbackQuery, session: AsyncSession):
    """
    Навигация между элементами bulk заказа
    
    Формат: bulk_nav:{order_id}:{current_item}:{direction}
    """
    
    parts = callback.data.split(":")
    order_id = int(parts[1])
    current_item = int(parts[2])
    direction = parts[3]  # "prev" или "next"
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Определяем новый номер элемента
    if direction == "prev":
        new_item = current_item - 1 if current_item > 1 else order.bulk_count
    else:  # direction == "next"
        new_item = current_item + 1 if current_item < order.bulk_count else 1
    
    # Создаем новый callback для перехода
    new_callback_data = f"bulk_item:{order_id}:{new_item}"
    
    # Имитируем новый callback
    class FakeCallback:
        def __init__(self, data, message):
            self.data = data
            self.message = message
            self.from_user = callback.from_user
        
        def answer(self, *args, **kwargs):
            return callback.answer(*args, **kwargs)
    
    fake_callback = FakeCallback(new_callback_data, callback.message)
    await view_bulk_item(fake_callback, session)


@router.callback_query(F.data.startswith("bulk_summary:"))
async def show_bulk_summary(callback: CallbackQuery, session: AsyncSession, order_id: int = None):
    
    if order_id is None:
        order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем сводку
    summary = await OrderService.get_bulk_item_summary(order)
    
    # Формируем детальный список
    items_text = []
    for item in sorted(order.bulk_items, key=lambda x: x.item_number):
        status_emoji = {
            "pending": "⏳",
            "done": "✅",
            "nf": "❌"
        }
        emoji = status_emoji.get(item.status, "")
        
        # Берем первые данные для краткого отображения
        first_key = list(item.input_data.keys())[0] if item.input_data else "data"
        first_value = str(item.input_data.get(first_key, ""))[:20]
        
        items_text.append(
            f"{item.item_number}. {emoji} {first_value}..."
        )
    
    items_display = "\n".join(items_text[:10])  # Показываем первые 10
    if len(items_text) > 10:
        items_display += f"\n... and {len(items_text) - 10} more"
    
    text = f"""📊 <b>BULK ORDER #{order.id} - SUMMARY</b>

<b>Total Items:</b> {summary['total']}
<b>Progress:</b>
   ✅ DONE: {summary['done']}
   ❌ NF: {summary['nf']}
   ⏳ Pending: {summary['pending']}

━━━━━━━━━━━━━━━━━━
<b>Items:</b>
{items_display}

━━━━━━━━━━━━━━━━━━
"""
    
    # Проверяем, все ли элементы обработаны
    is_completed = summary['pending'] == 0
    
    if is_completed:
        text += "\n✅ <b>All items processed!</b>\nYou can complete the order now."
        keyboard = bulk_summary_keyboard(order.id)
    else:
        text += f"\n⏳ <b>{summary['pending']} items remaining</b>"
        keyboard = bulk_order_keyboard(order.id, order.bulk_count, is_taken=True)
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("order_complete:"))
async def complete_bulk_order(callback: CallbackQuery, session: AsyncSession):
    """
    Завершить bulk заказ
    
    Формат: order_complete:{order_id}
    """
    
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Проверяем, все ли элементы обработаны
    is_completed = await OrderService.check_bulk_order_completion(session, order)
    
    if not is_completed:
        await callback.answer(
            "❌ Not all items are processed!\n"
            "Complete all items before finishing the order.",
            show_alert=True
        )
        return
    
    # Получаем сводку для статистики
    summary = await OrderService.get_bulk_item_summary(order)
    
    # Завершаем заказ
    await OrderService.complete_order(
        session,
        order,
        result_data={
            "done": summary['done'],
            "nf": summary['nf'],
            "total": summary['total']
        }
    )
    
    # Элементы bulk уже учитываются по мере обработки каждого item,
    # здесь увеличиваем только счетчик завершенных заказов.
    worker.orders_completed += 1
    await session.commit()
    
    # Логируем завершение bulk заказа
    await SupportLogger.log_order_completed(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id,
        result_status="bulk_completed",
        result_text=f"BULK ORDER: {summary['done']} DONE, {summary['nf']} NF, {summary['total']} Total"
    )
    
    # Уведомляем клиента через новую систему
    success = await OrderDeliveryService.notify_bulk_order_completed(session, order, summary)
    
    # Fallback на старую систему если новая не сработала
    if not success:
        logger.warning(f"New bulk notification system failed for order {order.id}, using fallback")
        await NotificationService.notify_bulk_order_completed(order, summary)
    
    # Уведомляем админов
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        price_per_item = float(order.price) / order.bulk_count if order.bulk_count else 0
        await AdminNotificationService.notify_bulk_order_completed(
            order_id=order.id,
            service_name=order.service_name,
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            user_id=order.user_id,
            done_count=summary['done'],
            nf_count=summary['nf'],
            total_count=summary['total'],
            total_income=price_per_item * summary['done'],
            total_refund=price_per_item * summary['nf']
        )
    except Exception as e:
        logger.warning(f"Failed to send admin notification: {e}")
    
    await callback.answer("✅ Bulk order completed!", show_alert=True)
    
    await callback.message.edit_text(
        f"✅ <b>Bulk Order #{order.id} Completed!</b>\n\n"
        f"<b>Results:</b>\n"
        f"   ✅ DONE: {summary['done']}\n"
        f"   ❌ NF: {summary['nf']}\n"
        f"   📊 Total: {summary['total']}\n\n"
        f"Great work! 👍",
        reply_markup=main_menu_keyboard()
    )


