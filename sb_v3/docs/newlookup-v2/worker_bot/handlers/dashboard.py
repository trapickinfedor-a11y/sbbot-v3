from __future__ import annotations

"""Worker Bot v2 — KPI Dashboard, промежуточные статусы, запрос инфо у клиента"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from support_bot.services.worker_service import WorkerService
from shared.database.models import WorkerOrder
from shared.services.worker_score_service import get_worker_dashboard, recalculate_worker_score

logger = logging.getLogger(__name__)
router = Router(name="worker_dashboard")


# ── keyboards ──────────────────────────────────────────────────────────────

def _dashboard_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="worker_dashboard")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")],
    ])


def _order_status_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ В работе", callback_data=f"wkr_status:{order_id}:processing")],
        [InlineKeyboardButton(text="🔍 Ищу данные", callback_data=f"wkr_status:{order_id}:searching")],
        [InlineKeyboardButton(text="❗ Проблема", callback_data=f"wkr_status:{order_id}:problem")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])


# ── Dashboard ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "worker_dashboard")
async def cb_worker_dashboard(callback: CallbackQuery, session: AsyncSession, **kwargs):
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return

    kpi = await get_worker_dashboard(session, worker.id)
    if not kpi:
        await callback.answer("Нет данных", show_alert=True)
        return

    score = kpi["worker_score"]
    score_emoji = "🏆" if score >= 4.8 else ("⭐" if score >= 4.0 else ("⚠️" if score >= 3.5 else "❌"))
    success_pct = round(kpi["success_rate"] * 100, 1)
    avg_min = round(kpi["avg_minutes"], 1)
    target_status = "✅ Цель выполнена" if avg_min <= 6 else f"⚠️ Цель: < 6 мин"

    text = (
        f"📊 <b>KPI Dashboard</b>\n\n"
        f"{score_emoji} <b>Worker Score:</b> {score}/5.0\n"
        f"⏱ <b>Среднее время:</b> {avg_min} мин ({target_status})\n"
        f"✅ <b>Процент успеха:</b> {success_pct}%\n"
        f"💰 <b>Доход за месяц:</b> ${kpi['month_earnings']:.2f}\n"
        f"💵 <b>Баланс:</b> ${kpi['balance']:.2f}\n\n"
        f"<b>Сегодня:</b>\n"
        f"  Взято: {kpi['today_total']} | Выполнено: {kpi['today_done']}\n"
        f"  В работе сейчас: {kpi['active_orders']}\n\n"
        f"<b>Всего выполнено:</b> {kpi['total_completed']}\n"
    )

    if score >= 4.8:
        text += "\n🏆 <b>Top Worker!</b> +5% к доле с каждого заказа"
    elif score < 3.5:
        text += "\n⚠️ Низкий рейтинг. Старайтесь выполнять заказы быстрее и качественнее."

    await callback.message.edit_text(text, reply_markup=_dashboard_kb())
    await callback.answer()


# ── Промежуточные статусы заказа ───────────────────────────────────────────

@router.callback_query(F.data.startswith("wset_status:"))
async def cb_set_status_menu(callback: CallbackQuery, **kwargs):
    order_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "📌 <b>Установить статус заказа</b>\n\nВыберите текущий статус:",
        reply_markup=_order_status_kb(order_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wkr_status:"))
async def cb_apply_status(callback: CallbackQuery, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status = parts[2]

    r = await session.execute(select(WorkerOrder).where(WorkerOrder.id == order_id))
    wo = r.scalar_one_or_none()
    if not wo:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    wo.intermediate_status = new_status
    await session.commit()

    status_labels = {
        "processing": "⏳ В работе",
        "searching": "🔍 Ищу данные",
        "problem": "❗ Проблема",
    }
    label = status_labels.get(new_status, new_status)
    await callback.answer(f"Статус обновлён: {label}", show_alert=True)
    await callback.message.edit_text(
        f"✅ Статус заказа #{order_id} обновлён: <b>{label}</b>\n\n"
        f"Клиент видит этот статус в реальном времени.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
    )
