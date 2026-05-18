"""
Хэндлеры для истории заказов
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
import logging

from support_bot.services.worker_service import WorkerService
from support_bot.services.order_service import OrderService
from support_bot.keyboards.inline import (
    order_list_keyboard,
    main_menu_keyboard,
    history_bulk_order_keyboard,
    history_item_keyboard,
    back_to_menu_keyboard
)
from support_bot.config import support_bot_config
from support_bot.utils import safe_edit_message, safe_answer_callback
from shared.database.models import Order, BulkOrderItem

router = Router(name="history")
logger = logging.getLogger(__name__)


def format_order_data(data: dict) -> str:
    """Форматирование данных заказа"""
    lines = []
    for key, value in data.items():
        key_formatted = key.replace("_", " ").title()
        lines.append(f"   • <b>{key_formatted}:</b> <code>{value}</code>")
    return "\n".join(lines)




@router.callback_query(F.data == "orders_history")
async def show_history(callback: CallbackQuery, session: AsyncSession):
    """Показать историю завершенных заказов"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем завершенные заказы
    orders = await OrderService.get_worker_orders(
        session,
        worker.id,
        status=support_bot_config.ORDER_STATUS_COMPLETED
    )
    
    if not orders:
        text = "✅ <b>Completed Orders</b>\n\n" \
               "You have no completed orders yet."
        
        await safe_edit_message(callback, text, main_menu_keyboard())
        
        await safe_answer_callback(callback)
        return
    
    # Форматируем список
    orders_data = []
    for order in orders[:20]:  # Показываем последние 20
        orders_data.append({
            "id": order.id,
            "category": order.category,
            "is_bulk": order.is_bulk,
            "bulk_count": order.bulk_count
        })
    
    await safe_edit_message(
        callback,
        f"✅ <b>Completed Orders ({len(orders)})</b>\n\n"
        f"Showing last {len(orders_data)} orders:",
        order_list_keyboard(orders_data)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("history_view:"))
async def view_history_order(callback: CallbackQuery, session: AsyncSession):
    """
    Просмотр заказа из истории
    
    Формат: history_view:{order_id}:{show_items}
    """
    parts = callback.data.split(":")
    order_id = int(parts[1])
    show_items = int(parts[2]) == 1 if len(parts) > 2 else False
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    order = await OrderService.get_order(session, order_id)
    
    if not order or order.worker_id != worker.id:
        await callback.answer("Access denied", show_alert=True)
        return
    
    if not order.is_bulk:
        # Single заказ
        customer_data = format_order_data(order.input_data)
        
        text = f"""✅ <b>ORDER #{order.id} - COMPLETED</b>

🔧 <b>Service:</b> {order.service_name}
📂 <b>Category:</b> {order.category.upper()}

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}
✅ <b>Completed:</b> {order.completed_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        if order.result_data:
            result_text = order.result_data.get("text", "")
            if result_text:
                text += f"\n📝 <b>Result:</b>\n{result_text[:200]}..."
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        history_back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to History", callback_data="orders_history")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        ])
        await safe_edit_message(callback, text, history_back_kb)
    
    else:
        # Bulk заказ
        stmt = select(BulkOrderItem).where(
            BulkOrderItem.order_id == order_id
        ).order_by(BulkOrderItem.item_number)
        
        result = await session.execute(stmt)
        items = result.scalars().all()
        
        # Подсчитываем статистику
        done_count = sum(1 for item in items if item.status == "done")
        nf_count = sum(1 for item in items if item.status == "nf")
        
        text = f"""✅ <b>BULK ORDER #{order.id} - COMPLETED</b>

📂 <b>Category:</b> {order.category.upper()}
📊 <b>Items:</b> {order.bulk_count}

━━━━━━━━━━━━━━━━━━
<b>Results:</b>
   ✅ DONE: {done_count}
   ❌ NF: {nf_count}

⏰ <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}
✅ <b>Completed:</b> {order.completed_at.strftime('%Y-%m-%d %H:%M')}
"""
        
        await safe_edit_message(
            callback,
            text,
            history_bulk_order_keyboard(order.id, items, show_items)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("history_expand:"))
async def expand_bulk_history(callback: CallbackQuery, session: AsyncSession):
    """Развернуть список элементов bulk заказа"""
    order_id = int(callback.data.split(":")[1])
    
    # Перенаправляем на просмотр с раскрытым списком
    await view_history_order(
        CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            message=callback.message,
            data=f"history_view:{order_id}:1",
            chat_instance=callback.chat_instance
        ),
        session
    )


@router.callback_query(F.data.startswith("history_collapse:"))
async def collapse_bulk_history(callback: CallbackQuery, session: AsyncSession):
    """Свернуть список элементов bulk заказа"""
    order_id = int(callback.data.split(":")[1])
    
    # Перенаправляем на просмотр со свернутым списком
    await view_history_order(
        CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            message=callback.message,
            data=f"history_view:{order_id}:0",
            chat_instance=callback.chat_instance
        ),
        session
    )


@router.callback_query(F.data.startswith("history_item:"))
async def view_history_item(callback: CallbackQuery, session: AsyncSession):
    """
    Просмотр элемента bulk заказа из истории
    
    Формат: history_item:{order_id}:{item_number}
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
    stmt = select(BulkOrderItem).where(
        and_(
            BulkOrderItem.order_id == order_id,
            BulkOrderItem.item_number == item_number
        )
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    
    # Форматируем данные
    customer_data = format_order_data(item.input_data)
    
    status_emoji = {
        "pending": "⏳",
        "done": "✅",
        "nf": "❌"
    }
    
    text = f"""📦 <b>ORDER #{order.id} - ITEM #{item_number}</b>

<b>Status:</b> {status_emoji.get(item.status, '')} {item.status.upper()}

👤 <b>Customer Data:</b>
{customer_data}

━━━━━━━━━━━━━━━━━━
📂 <b>Category:</b> {order.category}
"""
    
    if item.completed_at:
        text += f"✅ <b>Completed:</b> {item.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
    
    if item.result_data:
        result_text = item.result_data.get("text", "")
        if result_text:
            text += f"\n📝 <b>Result:</b>\n{result_text[:200]}..."
    
    await safe_edit_message(
        callback,
        text,
        history_item_keyboard(order.id, item_number)
    )
    await callback.answer()

