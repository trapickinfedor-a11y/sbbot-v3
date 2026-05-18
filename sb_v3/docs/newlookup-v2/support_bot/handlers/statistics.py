"""
Хэндлеры статистики саппорта
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from support_bot.services.worker_service import WorkerService
from support_bot.keyboards.inline import statistics_keyboard, main_menu_keyboard
from support_bot.utils.message_utils import safe_edit_message

router = Router(name="statistics")


@router.callback_query(F.data == "statistics")
async def show_statistics_menu(callback: CallbackQuery, session: AsyncSession):
    """Показать меню статистики"""
    
    await safe_edit_message(
        callback,
        "📊 <b>Statistics</b>\n\n"
        "Choose time period:",
        reply_markup=statistics_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "stats_today")
async def show_today_stats(callback: CallbackQuery, session: AsyncSession):
    """Статистика за сегодня"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем статистику за сегодня
    stats = await WorkerService.get_worker_stats_today(session, worker.id)
    
    if not stats:
        await safe_edit_message(
            callback,
            "📊 <b>Today's Statistics</b>\n\n"
            "No orders completed today yet.",
            reply_markup=statistics_keyboard()
        )
        await callback.answer()
        return
    
    # Подсчитываем общую статистику
    total_done = sum(s.orders_done for s in stats)
    total_nf = sum(s.orders_nf for s in stats)
    total_cancelled = sum(s.orders_cancelled for s in stats)
    total_orders = sum(s.orders_total for s in stats)
    
    # Формируем текст по категориям
    categories_text = []
    for stat in stats:
        categories_text.append(
            f"   <b>{stat.category}:</b>\n"
            f"      ✅ Done: {stat.orders_done}\n"
            f"      ❌ NF: {stat.orders_nf}\n"
            f"      ⚠️ Cancelled: {stat.orders_cancelled}"
        )
    
    text = f"""📊 <b>Today's Statistics</b>
<b>Date:</b> {date.today().strftime('%Y-%m-%d')}

<b>Total:</b>
   ✅ Done: {total_done}
   ❌ NF: {total_nf}
   ⚠️ Cancelled: {total_cancelled}
   📊 Total: {total_orders}

━━━━━━━━━━━━━━━━━━
<b>By Category:</b>
{chr(10).join(categories_text)}
"""
    
    await safe_edit_message(callback, text, reply_markup=statistics_keyboard())
    await callback.answer()


@router.callback_query(F.data == "stats_week")
async def show_week_stats(callback: CallbackQuery, session: AsyncSession):
    """Статистика за неделю"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем статистику за неделю
    week_ago = date.today() - timedelta(days=7)
    stats = await WorkerService.get_worker_stats_period(session, worker.id, week_ago, date.today())
    
    if not stats:
        await safe_edit_message(
            callback,
            "📊 <b>This Week's Statistics</b>\n\n"
            "No orders completed this week yet.",
            reply_markup=statistics_keyboard()
        )
        await callback.answer()
        return
    
    # Подсчитываем общую статистику
    total_done = sum(s.orders_done for s in stats)
    total_nf = sum(s.orders_nf for s in stats)
    total_cancelled = sum(s.orders_cancelled for s in stats)
    total_orders = sum(s.orders_total for s in stats)
    
    # Формируем текст по категориям
    categories_text = []
    for stat in stats:
        categories_text.append(
            f"   <b>{stat.category}:</b>\n"
            f"      ✅ Done: {stat.orders_done}\n"
            f"      ❌ NF: {stat.orders_nf}\n"
            f"      ⚠️ Cancelled: {stat.orders_cancelled}"
        )
    
    text = f"""📊 <b>This Week's Statistics</b>
<b>Period:</b> {week_ago.strftime('%Y-%m-%d')} - {date.today().strftime('%Y-%m-%d')}

<b>Total:</b>
   ✅ Done: {total_done}
   ❌ NF: {total_nf}
   ⚠️ Cancelled: {total_cancelled}
   📊 Total: {total_orders}

━━━━━━━━━━━━━━━━━━
<b>By Category:</b>
{chr(10).join(categories_text)}
"""
    
    await safe_edit_message(callback, text, reply_markup=statistics_keyboard())
    await callback.answer()


@router.callback_query(F.data == "stats_month")
async def show_month_stats(callback: CallbackQuery, session: AsyncSession):
    """Статистика за месяц"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем статистику за месяц
    month_ago = date.today() - timedelta(days=30)
    stats = await WorkerService.get_worker_stats_period(session, worker.id, month_ago, date.today())
    
    if not stats:
        await safe_edit_message(
            callback,
            "📊 <b>This Month's Statistics</b>\n\n"
            "No orders completed this month yet.",
            reply_markup=statistics_keyboard()
        )
        await callback.answer()
        return
    
    # Подсчитываем общую статистику
    total_done = sum(s.orders_done for s in stats)
    total_nf = sum(s.orders_nf for s in stats)
    total_cancelled = sum(s.orders_cancelled for s in stats)
    total_orders = sum(s.orders_total for s in stats)
    
    # Формируем текст по категориям
    categories_text = []
    for stat in stats:
        categories_text.append(
            f"   <b>{stat.category}:</b>\n"
            f"      ✅ Done: {stat.orders_done}\n"
            f"      ❌ NF: {stat.orders_nf}\n"
            f"      ⚠️ Cancelled: {stat.orders_cancelled}"
        )
    
    text = f"""📊 <b>This Month's Statistics</b>
<b>Period:</b> {month_ago.strftime('%Y-%m-%d')} - {date.today().strftime('%Y-%m-%d')}

<b>Total:</b>
   ✅ Done: {total_done}
   ❌ NF: {total_nf}
   ⚠️ Cancelled: {total_cancelled}
   📊 Total: {total_orders}

━━━━━━━━━━━━━━━━━━
<b>By Category:</b>
{chr(10).join(categories_text)}
"""
    
    await safe_edit_message(callback, text, reply_markup=statistics_keyboard())
    await callback.answer()


@router.callback_query(F.data == "orders_completed_today")
async def show_completed_today(callback: CallbackQuery, session: AsyncSession):
    """Показать завершенные заказы за сегодня"""
    
    # Просто отвечаем на callback, не вызываем show_today_stats
    await callback.answer("Statistics are available in the Statistics menu", show_alert=True)



# ── Worker KPI Dashboard ───────────────────────────────────────────────────

@router.callback_query(F.data == "worker_stats_dashboard")
async def show_worker_kpi_dashboard(callback: CallbackQuery, session: AsyncSession):
    """Full KPI dashboard for the current worker."""
    from support_bot.services.worker_service import WorkerService
    from shared.database.models import WorkerOrder, Order
    from sqlalchemy import select, func as sqlfunc
    from datetime import date, timedelta, datetime

    worker = await WorkerService.get_worker_by_user_id(session, callback.from_user.id)
    if not worker:
        await callback.answer("Worker not found", show_alert=True)
        return

    today = date.today()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Counts
    total_done = await session.scalar(
        select(sqlfunc.count(WorkerOrder.id)).where(
            WorkerOrder.worker_id == worker.id,
            WorkerOrder.status == "completed",
        )
    ) or 0
    total_nf = await session.scalar(
        select(sqlfunc.count(WorkerOrder.id)).where(
            WorkerOrder.worker_id == worker.id,
            WorkerOrder.status == "not_found",
        )
    ) or 0
    total_cancelled = await session.scalar(
        select(sqlfunc.count(WorkerOrder.id)).where(
            WorkerOrder.worker_id == worker.id,
            WorkerOrder.status == "cancelled",
        )
    ) or 0
    week_done = await session.scalar(
        select(sqlfunc.count(WorkerOrder.id)).where(
            WorkerOrder.worker_id == worker.id,
            WorkerOrder.status == "completed",
            WorkerOrder.completed_at >= week_ago,
        )
    ) or 0
    month_done = await session.scalar(
        select(sqlfunc.count(WorkerOrder.id)).where(
            WorkerOrder.worker_id == worker.id,
            WorkerOrder.status == "completed",
            WorkerOrder.completed_at >= month_ago,
        )
    ) or 0

    score = float(worker.worker_score or 0)
    balance = float(worker.balance or 0)
    total = total_done + total_nf + total_cancelled
    success_rate = round(total_done / total * 100, 1) if total > 0 else 0

    # Score emoji
    if score >= 4.8:
        score_badge = "🏆 TOP WORKER"
        bonus_info = "+5% earnings bonus"
    elif score < 3.5:
        score_badge = "⚠️ LOW RATING"
        bonus_info = "-5% earnings penalty"
    else:
        score_badge = "✅ Standard"
        bonus_info = "Standard rate"

    text = (
        f"📊 <b>Your KPI Dashboard</b>\n\n"
        f"⭐ <b>Worker Score:</b> {score:.2f} — {score_badge}\n"
        f"💰 <b>Balance:</b> ${balance:.2f}\n"
        f"📈 <b>Earnings tier:</b> {bonus_info}\n\n"
        f"<b>All Time:</b>\n"
        f"   ✅ Completed: {total_done}\n"
        f"   ❌ Not Found: {total_nf}\n"
        f"   ⚠️ Cancelled: {total_cancelled}\n"
        f"   📊 Success Rate: {success_rate}%\n\n"
        f"<b>This Week:</b> ✅ {week_done} orders\n"
        f"<b>This Month:</b> ✅ {month_done} orders"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistics", callback_data="statistics")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
