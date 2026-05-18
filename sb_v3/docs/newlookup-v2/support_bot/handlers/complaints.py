from __future__ import annotations

"""
Handler для жалоб на пользователей
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from support_bot.services.worker_service import WorkerService
from support_bot.services.complaint_service import ComplaintService
from shared.database.models import Order, User
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

router = Router(name="complaints")
logger = logging.getLogger(__name__)


class ComplaintStates(StatesGroup):
    """Состояния для создания жалобы"""
    selecting_reason = State()
    writing_description = State()


def complaint_reason_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора причины жалобы с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Ban Request", callback_data=f"complaint_reason:ban:{order_id}")],
        [InlineKeyboardButton(text="❌ Invalid Data", callback_data=f"complaint_reason:invalid_data:{order_id}")],
        [InlineKeyboardButton(text="⚠️ Abuse", callback_data=f"complaint_reason:abuse:{order_id}")],
        [InlineKeyboardButton(text="📝 Other", callback_data=f"complaint_reason:other:{order_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_complaint_creation:{order_id}")]
    ])


def complaint_description_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для ввода описания жалобы с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_complaint_creation:{order_id}")]
    ])


@router.callback_query(F.data.startswith("complaint:"))
async def start_complaint(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс создания жалобы"""
    order_id = int(callback.data.split(":")[1])
    
    # Получаем заказ
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
        return
    
    # Проверяем что это воркер этого заказа
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker or order.worker_id != worker.id:
        await callback.answer("❌ You are not the worker of this order", show_alert=True)
        return
    
    # Сохраняем данные
    await state.update_data(order_id=order_id, user_id=order.user_id)
    await state.set_state(ComplaintStates.selecting_reason)
    
    text = f"""⚠️ <b>Creating Complaint</b>

<b>Order:</b> #{order_id}
<b>Buyer:</b> hidden

<b>Select reason:</b>"""
    
    await callback.message.edit_text(text, reply_markup=complaint_reason_keyboard(order_id))
    await callback.answer()


@router.callback_query(F.data.startswith("complaint_reason:"))
async def select_complaint_reason_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор причины жалобы через кнопку"""
    
    parts = callback.data.split(":")
    reason = parts[1]
    order_id = int(parts[2])
    
    await state.update_data(reason=reason)
    await state.set_state(ComplaintStates.writing_description)
    
    await callback.message.edit_text(
        "📝 <b>Describe the problem in detail:</b>\n\n"
        "Please provide as much information as possible.\n"
        "Minimum 20 characters required.",
        reply_markup=complaint_description_keyboard(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_complaint_creation:"))
async def cancel_complaint_creation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Отмена создания жалобы"""
    
    order_id = int(callback.data.split(":")[1])
    
    # Очищаем состояние
    await state.clear()
    
    # Возвращаемся к заказу
    from support_bot.handlers.orders import show_order_details
    await show_order_details(callback, session, order_id)
    await callback.answer("❌ Complaint creation cancelled")


@router.message(ComplaintStates.selecting_reason)
async def select_complaint_reason(message: Message, state: FSMContext):
    """Выбор причины жалобы"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Complaint cancelled")
        return
    
    reason_map = {
        "/ban": "ban_request",
        "/invalid_data": "invalid_data",
        "/abuse": "abuse",
        "/other": "other"
    }
    
    reason = reason_map.get(message.text)
    
    if not reason:
        await message.answer("❌ Invalid reason. Please select from the options above.")
        return
    
    await state.update_data(reason=reason)
    await state.set_state(ComplaintStates.writing_description)
    
    await message.answer(
        "📝 <b>Describe the problem in detail:</b>\n\n"
        "Please provide as much information as possible.\n"
        "Include evidence, screenshots description, etc.\n\n"
        "<i>Type /cancel to abort</i>"
    )


@router.message(ComplaintStates.writing_description)
async def write_complaint_description(message: Message, state: FSMContext, session: AsyncSession):
    """Написание описания жалобы"""
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Complaint cancelled")
        return
    
    if not message.text or len(message.text) < 20:
        data = await state.get_data()
        order_id = data.get("order_id")
        await message.answer(
            "❌ Description is too short. Please provide more details (minimum 20 characters).",
            reply_markup=complaint_description_keyboard(order_id) if order_id else None
        )
        return
    
    data = await state.get_data()
    order_id = data.get("order_id")
    user_id = data.get("user_id")
    reason = data.get("reason")
    
    # Получаем воркера
    worker = await WorkerService.get_worker(session, message.from_user.id)
    
    if not worker:
        await state.clear()
        await message.answer("❌ Worker not found")
        return
    
    # Создаем жалобу
    try:
        complaint = await ComplaintService.create_complaint(
            session=session,
            worker_id=worker.id,
            user_id=user_id,
            order_id=order_id,
            reason=reason,
            description=message.text
        )
        
        await state.clear()
        
        text = f"""✅ <b>Complaint Created</b>

<b>Complaint ID:</b> #{complaint.id}
<b>Order:</b> #{order_id}
<b>User:</b> {user_id}
<b>Reason:</b> {reason}

<b>Your complaint has been sent to administrators.</b>
They will review it and take appropriate action.

You will be notified about the decision.
"""
        
        from support_bot.keyboards.inline import back_to_menu_keyboard
        await message.answer(text, reply_markup=back_to_menu_keyboard())
        
        logger.info(f"Complaint #{complaint.id} created by worker {worker.id} against user {user_id}")
        
    except Exception as e:
        logger.error(f"Error creating complaint: {e}")
        await state.clear()
        await message.answer(f"❌ Error creating complaint: {str(e)}")


@router.message(F.text == "/my_complaints")
async def view_my_complaints(message: Message, session: AsyncSession):
    """Просмотр своих жалоб"""
    
    worker = await WorkerService.get_worker(session, message.from_user.id)
    
    if not worker:
        await message.answer("❌ You are not registered as a worker")
        return
    
    complaints = await ComplaintService.get_worker_complaints(session, worker.id, limit=10)
    
    if not complaints:
        await message.answer("📋 You have no complaints")
        return
    
    text = "📋 <b>Your Complaints (last 10):</b>\n\n"
    
    for complaint in complaints:
        status_emoji = {
            "pending": "⏳",
            "reviewed": "👀",
            "resolved": "✅",
            "rejected": "❌"
        }.get(complaint.status, "❓")
        
        text += f"{status_emoji} <b>#{complaint.id}</b> - {complaint.reason}\n"
        text += f"   User: {complaint.user_id} | Order: #{complaint.order_id or 'N/A'}\n"
        text += f"   Status: {complaint.status}\n"
        
        if complaint.admin_response:
            text += f"   Admin: {complaint.admin_response[:50]}...\n"
        
        text += f"   {complaint.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await message.answer(text)

