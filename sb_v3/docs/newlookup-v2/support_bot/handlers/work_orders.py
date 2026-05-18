"""
Хэндлеры для работы с заказами через систему уведомлений
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import logging
import asyncio

from support_bot.services.worker_service import WorkerService
from support_bot.services.order_service import OrderService, can_worker_access_order
from support_bot.services.notification_service import NotificationService
from support_bot.services.balance_service import BalanceService
from support_bot.services.support_logger import SupportLogger
from support_bot.services.order_delivery_service import OrderDeliveryService
from support_bot.keyboards.inline import (
    working_order_keyboard,
    bulk_item_working_keyboard,
    remind_later_keyboard,
    main_menu_keyboard
)
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from support_bot.config import support_bot_config
from support_bot.utils import safe_edit_message, safe_answer_callback
from support_bot.constants.service_names import get_full_service_name
from shared.database.models import Order, BulkOrderItem, User, WorkerOrder
from shared.database.tasks_session import tasks_session_maker
from shared.services.nocodb_service import NocoDBService
from shared.services.worker_reminder_task_service import WorkerReminderTaskService
from shared.services.worker_order_service import WorkerOrderService
from shared.utils.chat_filter import filter_and_log, filter_message, is_message_blocked

router = Router(name="work_orders")
logger = logging.getLogger(__name__)


class WorkStates(StatesGroup):
    """Состояния для работы с заказами"""
    waiting_for_result = State()


def format_order_data(data: dict) -> str:
    """Форматирование безопасных данных заказа без PII для воркера."""
    lines = []

    if data.get("state"):
        lines.append(f"   • 🏷️ <b>State:</b> <code>{data['state']}</code>")
    category = data.get("category")
    if category:
        lines.append(f"   • 📂 <b>Category:</b> <code>{category}</code>")
    service = data.get("service")
    if service:
        lines.append(f"   • 🔧 <b>Service code:</b> <code>{service}</code>")
    quantity = data.get("quantity")
    if quantity and int(quantity) > 1:
        lines.append(f"   • 📦 <b>Quantity:</b> <code>{quantity}</code>")

    present_keys = [
        key for key, value in data.items()
        if value and key not in {
            "first_name", "last_name", "address", "city", "zip_code", "zip", "dob",
            "ssn", "dl", "phone", "email", "mmn", "cs", "bg"
        }
    ]
    if present_keys:
        lines.append(f"   • 🧩 <b>Fields received:</b> <code>{', '.join(sorted(present_keys)[:8])}</code>")

    lines.append("   • 🔒 <b>PII:</b> <code>hidden for worker privacy</code>")
    return "\n".join(lines)


async def _get_buyer_label(session: AsyncSession, buyer_user_id: int | None) -> str:
    if not buyer_user_id:
        return "hidden"
    buyer = await session.scalar(select(User).where(User.user_id == buyer_user_id))
    if buyer and buyer.username:
        return f"@{buyer.username}"
    return "hidden"


@router.callback_query(F.data.startswith("notify_take:"))
async def take_single_order_from_notification(callback: CallbackQuery, session: AsyncSession):
    """
    Взять single заказ в работу из уведомления
    """
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    order = await OrderService.get_order(session, order_id)
    
    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
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
    
    # Сохраняем message_id и chat_id для возможности отвечать
    order.notification_message_id = callback.message.message_id
    order.support_chat_id = callback.from_user.id
    await session.commit()
    
    await callback.answer("✅ Order taken!", show_alert=True)
    
    # Обновляем сообщение - показываем кнопки управления
    customer_data = format_order_data(order.input_data)
    buyer_label = await _get_buyer_label(session, order.user_id)
    
    text = f"""🔄 <b>ORDER #{order.id} - IN WORK</b>

🔧 <b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}
📂 <b>Category:</b> {order.category.upper()}
👤 <b>Buyer:</b> <code>{buyer_label}</code>

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}
🔄 <b>Taken:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}

💬 <b>To send result:</b> Reply to this message with text/files
"""
    
    await safe_edit_message(
        callback,
        text,
        working_order_keyboard(order.id, False, order.category)
    )


@router.callback_query(F.data.startswith("notify_bulk_take:"))
async def take_bulk_item_from_notification(callback: CallbackQuery, session: AsyncSession):
    """
    Взять элемент bulk заказа в работу из уведомления
    """
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
        return
    
    # Проверяем доступ с учетом категории И сервиса
    if not can_worker_access_order(worker.categories, worker.services, order.category, order.service_name):
        await callback.answer("❌ You can't take this order (access denied)", show_alert=True)
        return
    
    # Если заказ еще не взят - берем его
    if not order.worker_id:
        success = await OrderService.take_order(session, order, worker)
        if not success:
            await callback.answer("❌ Order already taken by another worker", show_alert=True)
            return
        
        # Сохраняем message_id
        order.notification_message_id = callback.message.message_id
        order.support_chat_id = callback.from_user.id
        await session.commit()
    
    # Получаем элемент
    stmt = select(BulkOrderItem).where(
        BulkOrderItem.order_id == order_id,
        BulkOrderItem.item_number == item_number
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    
    if not item:
        await callback.answer("❌ Item not found", show_alert=True)
        return
    
    if item.status != "pending":
        await callback.answer(f"❌ Item already processed: {item.status.upper()}", show_alert=True)
        return
    
    await callback.answer(f"✅ Item #{item_number} ready to work!", show_alert=True)
    
    # Показываем данные элемента
    customer_data = format_order_data(item.input_data)
    buyer_label = await _get_buyer_label(session, order.user_id)
    
    text = f"""🔄 <b>BULK ITEM #{item_number} - ORDER #{order.id}</b>

🔧 <b>Service:</b> {get_full_service_name(order.service_name, order.input_data)}
📂 <b>Category:</b> {order.category.upper()}
📊 <b>Total items:</b> {order.bulk_count}
👤 <b>Buyer:</b> <code>{buyer_label}</code>

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
💬 <b>To send result:</b> Reply to this message with text/files
"""
    
    await callback.message.answer(
        text=text,
        reply_markup=bulk_item_working_keyboard(order.id, item_number, item.status, order.category)
    )


@router.callback_query(F.data.startswith("notify_take_all:"))
async def take_all_bulk_items(callback: CallbackQuery, session: AsyncSession):
    """
    Взять все элементы bulk заказа
    """
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
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
    
    # Сохраняем message_id
    order.notification_message_id = callback.message.message_id
    order.support_chat_id = callback.from_user.id
    await session.commit()
    
    await callback.answer("✅ All items taken!", show_alert=True)
    
    # Обновляем сообщение
    text = f"""🔄 <b>BULK ORDER #{order.id} - IN WORK</b>

📂 <b>Category:</b> {order.category.upper()}
📊 <b>Items:</b> {order.bulk_count}

━━━━━━━━━━━━━━━━━━
⏰ <b>Taken:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}

💬 Use buttons below to view items
"""
    
    await safe_edit_message(
        callback,
        text,
        working_order_keyboard(order.id, True, order.category)
    )


@router.callback_query(F.data.startswith("reply_hint:"))
async def show_reply_hint(callback: CallbackQuery):
    """Показать подсказку как отправить результат"""
    await callback.answer(
        "💡 To send result: Reply (↩️) to the order message with:\n"
        "• Text result\n"
        "• Files (PDF, ZIP, TXT)\n"
        "• Text + Files",
        show_alert=True
    )


@router.callback_query(F.data.startswith("work_done:"))
async def mark_work_done(callback: CallbackQuery, session: AsyncSession):
    """Отметить заказ как выполненный (быстрая кнопка без результата)"""
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Завершаем заказ
    await OrderService.complete_order(session, order)
    
    # Обновляем статистику
    await WorkerService.increment_stat(session, worker.id, order.category, "done")
    worker.orders_completed += 1
    await session.commit()
    
    # Логируем завершение заказа как DONE
    await SupportLogger.log_order_completed(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id,
        result_status="done"
    )
    
    # Уведомляем клиента
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
        files=[],
        result_text=None,
        user_language=user_language
    )
    
    await callback.answer("✅ Order marked as DONE!", show_alert=True)
    
    await safe_edit_message(callback,
        f"✅ <b>ORDER #{order.id} - COMPLETED!</b>\n\n"
        f"Category: {order.category}\n"
        f"Status: DONE\n\n"
        f"Good job! 👍",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("work_nf:"))
async def mark_work_nf(callback: CallbackQuery, session: AsyncSession):
    """Отметить заказ как NF"""
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Возвращаем средства
    refund_success = await BalanceService.refund_order(session, order.user_id, order.price, order.id)

    if not refund_success:
        logger.error(f"Failed to refund order {order.id} (work_nf) — aborting, user funds not returned")
        await callback.answer("❌ Refund failed — order NOT closed. Contact developer.", show_alert=True)
        return

    # Завершаем заказ
    await OrderService.complete_order(session, order, result_data={"status": "nf", "refunded": True})
    
    # Обновляем статистику
    await WorkerService.increment_stat(session, worker.id, order.category, "nf")
    await session.commit()
    
    # Логируем завершение заказа как NF
    await SupportLogger.log_order_completed(
        worker_username=worker.username or str(worker.telegram_id),
        worker_id=worker.id,
        order_id=order.id,
        service_name=order.service_name,
        user_id=order.user_id,
        result_status="nf"
    )
    
    # Уведомляем клиента
    # Получаем язык пользователя
    user_language = await OrderDeliveryService.get_user_language(
        session, order.user_id, order.mirror_bot_id
    )
    
    await OrderDeliveryService.deliver_single_order_result(
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
    
    await callback.answer("✅ Marked as NF, refund processed", show_alert=True)
    
    await safe_edit_message(callback,
        f"❌ <b>ORDER #{order.id} - NF</b>\n\n"
        f"Category: {order.category}\n"
        f"Status: Not Found\n"
        f"Refund: {'✅ Success' if refund_success else '❌ Failed'}",
        reply_markup=main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("work_bulk_done:"))
async def mark_bulk_item_done(callback: CallbackQuery, session: AsyncSession):
    """Отметить элемент bulk как выполненный"""
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Обновляем статус элемента
    stmt = select(BulkOrderItem).where(
        BulkOrderItem.order_id == order_id,
        BulkOrderItem.item_number == item_number
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    
    if item:
        item.status = "done"
        item.completed_at = datetime.now(timezone.utc)
        await session.commit()
        
        # Обновляем статистику
        await WorkerService.increment_stat(session, worker.id, order.category, "done")
        
        # Логируем завершение bulk элемента как DONE
        await SupportLogger.log_bulk_item_completed(
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            order_id=order.id,
            item_number=item_number,
            service_name=order.service_name,
            user_id=order.user_id,
            result_status="done"
        )
    
    await callback.answer(f"✅ Item #{item_number} marked as DONE!", show_alert=True)
    
    # Возвращаемся к bulk заказу для продолжения работы с другими элементами
    from support_bot.handlers.orders import view_order
    
    class TempCallback:
        def __init__(self, order_id, original_callback):
            self.data = f"order_view:{order_id}"
            self.message = original_callback.message
            self.from_user = original_callback.from_user
        async def answer(self, *args, **kwargs):
            pass
    
    temp_callback = TempCallback(order.id, callback)
    
    await safe_edit_message(callback,
        f"✅ <b>ITEM #{item_number} - DONE</b>\n\n"
        f"Order: #{order.id}\n"
        f"Category: {order.category}\n\n"
        f"Good job! 👍\n\n"
        f"Returning to bulk order..."
    )
    
    await asyncio.sleep(1)
    await view_order(temp_callback, session)


@router.callback_query(F.data.startswith("work_bulk_nf:"))
async def mark_bulk_item_nf(callback: CallbackQuery, session: AsyncSession):
    """Отметить элемент bulk как NF"""
    parts = callback.data.split(":")
    order_id = int(parts[1])
    item_number = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Обновляем статус элемента
    stmt = select(BulkOrderItem).where(
        BulkOrderItem.order_id == order_id,
        BulkOrderItem.item_number == item_number
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    
    if item:
        # Рассчитываем цену за один элемент для возврата
        item_price = order.price / order.bulk_count
        
        # Возвращаем средства за NF элемент
        refund_success = await BalanceService.refund_order(session, order.user_id, item_price, order.id)
        
        if not refund_success:
            logger.warning(f"Failed to refund bulk item {item_number} for order {order.id}")
        
        item.status = "nf"
        item.completed_at = datetime.now(timezone.utc)
        await session.commit()
        
        # Обновляем статистику
        await WorkerService.increment_stat(session, worker.id, order.category, "nf")
        
        # Логируем завершение bulk элемента как NF
        await SupportLogger.log_bulk_item_completed(
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            order_id=order.id,
            item_number=item_number,
            service_name=order.service_name,
            user_id=order.user_id,
            result_status="nf",
            refund_amount=item_price if refund_success else None
        )
        
        # Уведомляем пользователя о NF элементе через mirror bot
        await OrderDeliveryService.notify_bulk_item_completed(
            user_id=order.user_id,
            mirror_bot_id=order.mirror_bot_id,
            order_id=order.id,
            item_number=item_number,
            service_name=order.service_name,
            result_status="nf",
            customer_data=item.input_data,
            refund_amount=item_price if refund_success else 0,
            files=[],
            result_text=None
        )
    
    await callback.answer(f"✅ Item #{item_number} marked as NF!", show_alert=True)
    
    # Возвращаемся к bulk заказу для продолжения работы с другими элементами
    from support_bot.handlers.orders import view_order
    
    class TempCallback:
        def __init__(self, order_id, original_callback):
            self.data = f"order_view:{order_id}"
            self.message = original_callback.message
            self.from_user = original_callback.from_user
        async def answer(self, *args, **kwargs):
            pass
    
    temp_callback = TempCallback(order.id, callback)
    
    await safe_edit_message(callback,
        f"❌ <b>ITEM #{item_number} - NF</b>\n\n"
        f"Order: #{order.id}\n"
        f"Category: {order.category}\n\n"
        f"Returning to bulk order..."
    )
    
    await asyncio.sleep(1)
    await view_order(temp_callback, session)


@router.callback_query(F.data.startswith("work_remind:"))
async def remind_later(callback: CallbackQuery):
    """Напомнить о заказе позже"""
    order_id = int(callback.data.split(":")[1])
    
    await safe_edit_message(callback,
        f"⏰ <b>Remind Later - Order #{order_id}</b>\n\n"
        f"Select when to remind you:",
        reply_markup=remind_later_keyboard(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remind_time:"))
async def set_remind_time(callback: CallbackQuery, session: AsyncSession):
    """Установить время напоминания"""
    parts = callback.data.split(":")
    order_id = int(parts[1])
    hours = int(parts[2])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Оставляем заказ в работе и откладываем следующее авто-напоминание.
    order.last_worker_reminder_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    worker_order = await WorkerOrderService.ensure_from_order(session, order)
    await session.commit()
    async with tasks_session_maker() as task_session:
        await WorkerReminderTaskService.schedule(
            task_session,
            order_id=order.id,
            worker_order_id=worker_order.id,
            worker_id=worker.id,
            worker_telegram_id=worker.telegram_id,
            delay_hours=hours,
            payload_json={"source": "work_orders_snooze"},
        )
    
    await callback.answer(f"⏰ Reminder snoozed for {hours}h", show_alert=True)
    
    await safe_edit_message(callback,
        f"⏰ <b>ORDER #{order.id} - POSTPONED</b>\n\n"
        f"The order stays assigned to you.\n"
        f"Next reminder in: {hours} hours",
        reply_markup=main_menu_keyboard()
    )


REPORT_WRONG_DATA_REASON = (
    "The provided customer data is incorrect or insufficient to complete this order. "
    "Please verify and resubmit with accurate information."
)


@router.callback_query(F.data.startswith("work_report:"))
async def report_wrong_data(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Репорт на неверные данные — стандартный текст для всех сервисов"""
    order_id = int(callback.data.split(":")[1])

    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)

    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return

    reason = REPORT_WRONG_DATA_REASON

    # Уведомляем клиента
    try:
        from support_bot.services.worker_notification_service import WorkerNotificationService
        bot = WorkerNotificationService._bot

        await bot.send_message(
            chat_id=order.user_id,
            text=(
                f"⚠️ <b>Data Issue - Order #{order.id}</b>\n\n"
                f"{reason}\n\n"
                f"Please check your information and contact support if needed."
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to notify user about data report: {e}")

    # Уведомляем админов
    try:
        from support_bot.services.worker_notification_service import WorkerNotificationService
        bot = WorkerNotificationService._bot
        from support_bot.config import support_bot_config
        for admin_id in support_bot_config.system_admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"⚠️ <b>Data Report from Worker</b>\n\n"
                        f"Order: #{order.id}\n"
                        f"Worker: {worker.username or worker.telegram_id}\n"
                        f"Category: {order.category}\n\n"
                        f"<b>Issue:</b>\n{reason}\n\n"
                        f"<b>Customer Data:</b>\n{format_order_data(order.input_data)}"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to notify admins about data report: {e}")

    # Возвращаем заказ в очередь
    order.worker_id = None
    order.taken_at = None
    order.status = "pending"
    order.notes = f"Data report: {reason}"
    await WorkerOrderService.ensure_from_order(session, order)
    await session.commit()
    async with tasks_session_maker() as task_session:
        await WorkerReminderTaskService.cancel_for_order(task_session, order.id)

    await callback.answer("✅ Report sent!", show_alert=True)

    await safe_edit_message(
        callback,
        f"✅ <b>Report Sent!</b>\n\n"
        f"Order #{order.id} returned to queue.\n"
        f"Customer and admins have been notified.",
        reply_markup=main_menu_keyboard()
    )



@router.callback_query(F.data.startswith("work_cancel:"))
async def cancel_work_order(callback: CallbackQuery, session: AsyncSession):
    """Отменить заказ с возвратом средств"""
    order_id = int(callback.data.split(":")[1])
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Возвращаем средства
    refund_success = await BalanceService.refund_order(session, order.user_id, order.price, order.id)
    
    # Отменяем заказ
    await OrderService.cancel_order(session, order)
    
    # Обновляем статистику
    await WorkerService.increment_stat(session, worker.id, order.category, "cancelled")
    await session.commit()
    
    # Уведомляем клиента
    await NotificationService.notify_order_cancelled(order)
    
    await callback.answer("✅ Order cancelled, refund processed", show_alert=True)
    
    await safe_edit_message(callback,
        f"❌ <b>ORDER #{order.id} - CANCELLED</b>\n\n"
        f"Category: {order.category}\n"
        f"Refund: {'✅ Success' if refund_success else '❌ Failed'}",
        reply_markup=main_menu_keyboard()
    )


# Обработчик ответов на сообщения с заказами
@router.message(F.reply_to_message)
async def handle_order_reply(message: Message, session: AsyncSession):
    """
    Обработка ответа на сообщение с заказом
    Саппорт отправляет результат reply-ом на сообщение с заказом
    """
    try:
        # Проверяем, что это ответ на сообщение от бота
        if not message.reply_to_message.from_user.is_bot:
            return
        
        # Пытаемся найти заказ по message_id
        replied_message_id = message.reply_to_message.message_id
        
        stmt = select(Order).where(
            Order.notification_message_id == replied_message_id,
            Order.support_chat_id == message.from_user.id
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        
        if not order:
            # Это не ответ на заказ
            return
        
        worker = await WorkerService.get_worker(session, message.from_user.id)
        
        if not worker or order.worker_id != worker.id:
            await message.answer("❌ You don't have access to this order")
            return
        
        # Собираем результат
        result_text = message.text or message.caption or ""
        if result_text and is_message_blocked(result_text):
            await message.answer("❌ Message contains only contact information and was blocked.")
            return
        if result_text:
            result_text, violated = await filter_and_log(
                text=result_text,
                worker_id=worker.id,
                order_id=order.id,
                session=session,
            )
        else:
            violated = False
        files = []
        
        # Обрабатываем файлы
        if message.document:
            raw_file_name = message.document.file_name or ""
            if raw_file_name:
                _, file_name_violated = await filter_and_log(
                    text=raw_file_name,
                    worker_id=worker.id,
                    order_id=order.id,
                    session=session,
                )
            else:
                file_name_violated = False
            if file_name_violated:
                await message.answer("❌ File name contains contact information and was blocked.")
                return
            files.append({
                "type": "document",
                "file_id": message.document.file_id,
                "file_name": message.document.file_name or "document",
            })
        
        if message.photo:
            files.append({
                "type": "photo",
                "file_id": message.photo[-1].file_id
            })
        
        # Сохраняем результат
        order.result_data = {"text": result_text}
        order.files = files if files else None
        NocoDBService.log_order_message(
            order_id=order.id,
            worker_id=worker.id,
            message=result_text,
            files=files,
            extra={
                "category": order.category,
                "service_name": order.service_name,
                "user_id": order.user_id,
            },
        )
        
        # Завершаем заказ
        await OrderService.complete_order(session, order)
        
        # Обновляем статистику
        await WorkerService.increment_stat(session, worker.id, order.category, "done")
        worker.orders_completed += 1
        await session.commit()
        
        # Логируем завершение заказа
        await SupportLogger.log_order_completed(
            worker_username=worker.username or str(worker.telegram_id),
            worker_id=worker.id,
            order_id=order.id,
            service_name=order.service_name,
            user_id=order.user_id,
            result_status="done"
        )

        if violated:
            await message.answer("⚠️ Contact information was removed from your message.")
        
        # Отправляем результат клиенту
        # Получаем язык пользователя
        user_language = await OrderDeliveryService.get_user_language(
            session, order.user_id, order.mirror_bot_id
        )
        
        if files:
            await OrderDeliveryService.deliver_single_order_result(
                user_id=order.user_id,
                mirror_bot_id=order.mirror_bot_id,
                order_id=order.id,
                service_name=order.service_name,
                result_status="done",
                customer_data=order.input_data,
                files=files,
                result_text=result_text or None,
                user_language=user_language
            )
        else:
            await OrderDeliveryService.deliver_single_order_result(
                user_id=order.user_id,
                mirror_bot_id=order.mirror_bot_id,
                order_id=order.id,
                service_name=order.service_name,
                result_status="done",
                customer_data=order.input_data,
                files=[],
                result_text=result_text or None,
                user_language=user_language
            )
        
        await message.answer(
            f"✅ <b>ORDER #{order.id} - RESULT SENT!</b>\n\n"
            f"The result has been delivered to the customer.\n"
            f"Great job! 🎉"
        )
    
    except Exception as e:
        logger.error(f"Error handling order reply: {e}")



# ── Intermediate order status buttons ─────────────────────────────────────

WORKER_STATUS_LABELS = {
    "in_progress": "⏳ In Progress",
    "searching": "🔍 Searching for data",
    "problem": "❗ Problem encountered",
}

BUYER_STATUS_TEXTS = {
    "in_progress": "⏳ Your order #{order_id} is currently <b>in progress</b>. We'll notify you when it's done.",
    "searching": "🔍 Your order #{order_id}: the worker is <b>searching for the required data</b>. Please wait.",
    "problem": "❗ Your order #{order_id}: the worker encountered a <b>problem</b> and is working to resolve it. You'll be notified shortly.",
}


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Stub for status-display-only buttons."""
    await callback.answer()


@router.callback_query(F.data.startswith("wstatus:"))
async def cb_worker_status_update(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Worker sets an intermediate status visible to the buyer."""
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Invalid status", show_alert=True)
        return

    order_id = int(parts[1])
    new_status = parts[2]  # in_progress | searching | problem

    order = await session.get(Order, order_id)
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return

    # Update WorkerOrder intermediate_status
    wo = await session.scalar(select(WorkerOrder).where(WorkerOrder.order_id == order_id))
    if wo:
        wo.intermediate_status = new_status
        await session.commit()

    label = WORKER_STATUS_LABELS.get(new_status, new_status)
    await callback.answer(f"Status updated: {label}", show_alert=False)

    # Notify buyer
    buyer_text_tmpl = BUYER_STATUS_TEXTS.get(new_status)
    if buyer_text_tmpl and order.user_id:
        try:
            from support_bot.config import support_bot_config
            from aiogram import Bot as AiogramBot
            mirror_token = getattr(support_bot_config, "mirror_bot_token", None)
            if mirror_token:
                mirror_bot = AiogramBot(token=mirror_token)
                await mirror_bot.send_message(
                    order.user_id,
                    buyer_text_tmpl.format(order_id=order_id),
                    parse_mode="HTML",
                )
                await mirror_bot.session.close()
        except Exception as exc:
            logger.warning("Failed to notify buyer of status update: %s", exc)
