from __future__ import annotations

"""
Панель управления инвентарём аккаунтов — support_bot.

Возможности для системных администраторов:
  • Общая статистика инвентаря (в наличии / продано / всего)
  • Список категорий → позиций со счётчиком остатков
  • Детали конкретной позиции + последние продажи

Доступ: только actor.is_admin_like (system_admin / admin).
Загрузку аккаунтов воркерами — см. upload_product.py (UploadAccountStates).
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from support_bot.services.access_service import SupportBotActor
from support_bot.constants.buttons_accounts import AccountsAdminBtns
from shared.database.models import AccountCategory, AccountItem, AccountInventory

logger = logging.getLogger(__name__)
router = Router(name="admin_accounts")


# ─── Проверка доступа ─────────────────────────────────────────────────────────

def _is_admin(actor: SupportBotActor | None) -> bool:
    return actor is not None and actor.is_admin_like


# ─── Клавиатуры ───────────────────────────────────────────────────────────────

def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=AccountsAdminBtns.STATS,       callback_data="admin_accounts_stats")],
        [InlineKeyboardButton(text=AccountsAdminBtns.BY_CATEGORY, callback_data="admin_accounts_cats")],
        [InlineKeyboardButton(text=AccountsAdminBtns.REFRESH,     callback_data="admin_accounts_menu")],
        [InlineKeyboardButton(text=AccountsAdminBtns.MAIN_MENU,   callback_data="main_menu")],
    ])


def _cats_keyboard(cats: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{'✅' if c.is_active else '⏸'} {c.name}",
            callback_data=f"admin_accounts_cat:{c.code}",
        )]
        for c in cats
    ]
    rows.append([InlineKeyboardButton(text=AccountsAdminBtns.BACK, callback_data="admin_accounts_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _items_keyboard(items_with_counts: list[tuple]) -> InlineKeyboardMarkup:
    rows = []
    for item, avail, total in items_with_counts:
        status = "✅" if item.is_active else "⏸"
        rows.append([InlineKeyboardButton(
            text=f"{status} {item.name} — ${item.price}  [{avail}/{total}]",
            callback_data=f"admin_accounts_item:{item.id}",
        )])
    rows.append([InlineKeyboardButton(text=AccountsAdminBtns.BACK, callback_data="admin_accounts_cats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _item_keyboard(item_id: int, cat_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=AccountsAdminBtns.REFRESH, callback_data=f"admin_accounts_item:{item_id}")],
        [InlineKeyboardButton(text=AccountsAdminBtns.BACK,    callback_data=f"admin_accounts_cat:{cat_code}")],
    ])


# ─── Хэндлеры ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_accounts_menu")
async def accounts_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    total_inv = await session.scalar(select(func.count(AccountInventory.id))) or 0
    avail_inv = await session.scalar(
        select(func.count(AccountInventory.id)).where(AccountInventory.is_sold == False)
    ) or 0
    cats_count = await session.scalar(
        select(func.count(AccountCategory.id)).where(AccountCategory.is_active == True)
    ) or 0
    items_count = await session.scalar(
        select(func.count(AccountItem.id)).where(AccountItem.is_active == True)
    ) or 0

    text = (
        "📦 <b>Инвентарь аккаунтов</b>\n\n"
        f"📂 Активных категорий: <b>{cats_count}</b>\n"
        f"📋 Активных позиций: <b>{items_count}</b>\n"
        f"📦 Всего в инвентаре: <b>{total_inv}</b>\n"
        f"✅ В наличии: <b>{avail_inv}</b>\n"
        f"💸 Продано: <b>{total_inv - avail_inv}</b>"
    )
    await callback.message.edit_text(text, reply_markup=_main_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_accounts_stats")
async def accounts_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    stmt = (
        select(
            AccountItem.id,
            AccountItem.name,
            AccountItem.price,
            func.count(AccountInventory.id).label("total"),
            func.count(AccountInventory.id).filter(AccountInventory.is_sold == False).label("avail"),
        )
        .join(AccountInventory, AccountInventory.item_id == AccountItem.id, isouter=True)
        .where(AccountItem.is_active == True)
        .group_by(AccountItem.id, AccountItem.name, AccountItem.price)
        .order_by(AccountItem.category_code, AccountItem.position)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        text = "📊 <b>Статистика остатков</b>\n\n<i>Активных позиций не найдено.</i>"
    else:
        lines = ["📊 <b>Статистика остатков</b>\n"]
        for r in rows:
            avail = r.avail or 0
            total = r.total or 0
            bar = "✅" if avail > 5 else "⚠️" if avail > 0 else "🔴"
            lines.append(f"{bar} <b>{r.name}</b> — ${r.price}\n   {avail} в наличии / {total} всего")
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=AccountsAdminBtns.REFRESH, callback_data="admin_accounts_stats")],
        [InlineKeyboardButton(text=AccountsAdminBtns.BACK,    callback_data="admin_accounts_menu")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_accounts_cats")
async def accounts_cats(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    result = await session.execute(
        select(AccountCategory).order_by(AccountCategory.position, AccountCategory.id)
    )
    cats = result.scalars().all()

    if not cats:
        await callback.answer("Категорий нет — сначала заполните их через веб-панель", show_alert=True)
        return

    text = "📂 <b>Категории аккаунтов</b>\n\nВыберите категорию для просмотра позиций и остатков:"
    await callback.message.edit_text(text, reply_markup=_cats_keyboard(cats), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_accounts_cat:"))
async def accounts_cat_items(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    cat_code = callback.data.split(":", 1)[1]
    cat_result = await session.execute(
        select(AccountCategory).where(AccountCategory.code == cat_code)
    )
    cat = cat_result.scalar_one_or_none()
    if not cat:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    items_result = await session.execute(
        select(AccountItem)
        .where(AccountItem.category_code == cat_code)
        .order_by(AccountItem.position, AccountItem.id)
    )
    items = items_result.scalars().all()

    items_with_counts: list[tuple] = []
    for item in items:
        avail = await session.scalar(
            select(func.count(AccountInventory.id))
            .where(AccountInventory.item_id == item.id, AccountInventory.is_sold == False)
        ) or 0
        total = await session.scalar(
            select(func.count(AccountInventory.id))
            .where(AccountInventory.item_id == item.id)
        ) or 0
        items_with_counts.append((item, avail, total))

    text = f"📂 <b>{cat.name}</b>\n\nПозиции — <i>[в наличии / всего]</i>:"
    if not items_with_counts:
        text += "\n\n<i>В этой категории нет позиций.</i>"

    await callback.message.edit_text(
        text,
        reply_markup=_items_keyboard(items_with_counts),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_accounts_item:"))
async def accounts_item_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _is_admin(support_bot_actor):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    item_id = int(callback.data.split(":", 1)[1])
    item = await session.get(AccountItem, item_id)
    if not item:
        await callback.answer("Позиция не найдена", show_alert=True)
        return

    avail = await session.scalar(
        select(func.count(AccountInventory.id))
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
    ) or 0
    sold = await session.scalar(
        select(func.count(AccountInventory.id))
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == True)
    ) or 0
    total = avail + sold

    recent_result = await session.execute(
        select(AccountInventory)
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == True)
        .order_by(AccountInventory.sold_at.desc())
        .limit(5)
    )
    recent_sold = recent_result.scalars().all()

    stock_bar = "✅ Хороший запас" if avail > 5 else "⚠️ Мало осталось" if avail > 0 else "🔴 Нет в наличии"
    state_icon = "✅ Активна" if item.is_active else "⏸ Отключена"
    text = (
        f"📦 <b>{item.name}</b>\n"
        f"💰 Цена: <b>${item.price}</b>\n"
        f"📂 Категория: <code>{item.category_code}</code>\n"
        f"Статус: {state_icon}\n\n"
        f"📊 <b>Остаток:</b> {stock_bar}\n"
        f"   В наличии: <b>{avail}</b>\n"
        f"   Продано: <b>{sold}</b>\n"
        f"   Всего загружено: <b>{total}</b>\n"
    )
    if recent_sold:
        text += "\n🕐 <b>Последние продажи:</b>"
        for inv in recent_sold:
            sold_at = inv.sold_at.strftime("%d.%m %H:%M") if inv.sold_at else "?"
            text += f"\n   • Пользователь <code>{inv.sold_to_user_id}</code> — {sold_at}"

    await callback.message.edit_text(
        text,
        reply_markup=_item_keyboard(item_id, item.category_code),
        parse_mode="HTML",
    )
    await callback.answer()
