"""
Хэндлер старта Worker Bot
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from support_bot.services.worker_service import WorkerService
from support_bot.keyboards.inline import main_menu_keyboard, back_to_menu_keyboard

router = Router(name="worker_start")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """Команда /start"""
    worker = await WorkerService.get_worker(session, message.from_user.id)

    if not worker:
        await message.answer(
            "❌ <b>Access Denied</b>\n\n"
            "You are not registered as a worker.\n"
            "Contact administrator to get access.",
        )
        return

    if not worker.is_active:
        await message.answer(
            "❌ <b>Account Disabled</b>\n\n"
            "Your worker account has been disabled.\n"
            "Contact administrator for details."
        )
        return

    categories_text = "\n".join([f"   • {cat}" for cat in worker.categories])
    balance = float(worker.balance or 0)

    await message.answer(
        f"👋 <b>Welcome, {message.from_user.first_name}!</b>\n\n"
        f"🆔 Worker ID: <code>{worker.id}</code>\n"
        f"💰 Balance: <b>${balance:.2f}</b>\n"
        f"📊 Total Orders: {worker.orders_completed}\n\n"
        f"📋 <b>Your Categories:</b>\n{categories_text}\n\n"
        f"Choose an option:",
        reply_markup=main_menu_keyboard(worker),
    )


BOT_DESCRIPTION = """📋 <b>Описание Worker Bot</b>

<b>Назначение:</b>
Бот для воркеров, которые принимают, выполняют и сдают заказы.

<b>Основные функции:</b>
• 📦 <b>Available Orders</b> — доступные заказы
• 🔄 <b>My Orders</b> — заказы в работе
• 📚 <b>Order History</b> — история заказов
• 📊 <b>Statistics</b> — статистика
• 👤 <b>Profile</b> — профиль и категории

<b>Действия с заказом:</b>
• Take Order — взять в работу
• DONE / NF — завершить
• DONE + Files / TXT — отправить результат
• WRITE CLIENT — Add Info (24h/48h/72h)
• Report Client — жалоба на клиента"""


@router.callback_query(F.data == "bot_description")
async def callback_bot_description(callback: CallbackQuery, session: AsyncSession):
    """Показать описание бота"""
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.message.edit_text(
        BOT_DESCRIPTION,
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    worker = await WorkerService.get_worker(session, callback.from_user.id)

    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return

    categories_text = "\n".join([f"   • {cat}" for cat in worker.categories])
    balance = float(worker.balance or 0)

    await callback.message.edit_text(
        f"👋 <b>Welcome, {callback.from_user.first_name}!</b>\n\n"
        f"🆔 Worker ID: <code>{worker.id}</code>\n"
        f"💰 Balance: <b>${balance:.2f}</b>\n"
        f"📊 Total Orders: {worker.orders_completed}\n\n"
        f"📋 <b>Your Categories:</b>\n{categories_text}\n\n"
        f"Choose an option:",
        reply_markup=main_menu_keyboard(worker),
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Глобальный /cancel — сбросить FSM и вернуть приветствие"""
    await state.clear()
    await message.answer("✅ Cancelled. Use /start to go back to the main menu.")
