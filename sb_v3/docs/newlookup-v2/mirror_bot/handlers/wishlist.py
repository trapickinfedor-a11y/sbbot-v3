from __future__ import annotations

"""Mirror Bot — Wishlist (Список желаний) и уведомления о снижении цены"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete

from shared.database.models import WishlistItem, User

logger = logging.getLogger(__name__)
router = Router(name="mirror_wishlist")

PAGE_SIZE = 8


def _wishlist_kb(items: list[WishlistItem], page: int = 0) -> InlineKeyboardMarkup:
    rows = []
    start = page * PAGE_SIZE
    page_items = items[start: start + PAGE_SIZE]
    for item in page_items:
        rows.append([
            InlineKeyboardButton(
                text=f"❤️ {item.product_name or item.product_type} #{item.product_id}",
                callback_data=f"wl_view:{item.product_type}:{item.product_id}"
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"wl_remove:{item.id}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"wl_page:{page-1}"))
    if start + PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"wl_page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_user(session: AsyncSession, telegram_id: int) -> User | None:
    r = await session.execute(select(User).where(User.user_id == telegram_id))
    return r.scalar_one_or_none()


async def _get_wishlist(session: AsyncSession, user_id: int) -> list[WishlistItem]:
    r = await session.execute(
        select(WishlistItem)
        .where(WishlistItem.user_id == user_id)
        .order_by(WishlistItem.added_at.desc())
    )
    return list(r.scalars().all())


# ── Show wishlist ──────────────────────────────────────────────────────────

@router.message(Command("wishlist"))
async def cmd_wishlist(message: Message, session: AsyncSession, **kwargs):
    user = await _get_user(session, message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    await _show_wishlist(message, session, user, page=0)


@router.callback_query(F.data == "wishlist")
async def cb_wishlist(callback: CallbackQuery, session: AsyncSession, **kwargs):
    user = await _get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Not found", show_alert=True)
        return
    await _show_wishlist(callback.message, session, user, page=0, edit=True)
    await callback.answer()


@router.callback_query(F.data == "wishlist_view")
async def cb_wishlist_view(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Handler for wishlist_view callback from wishlist_notifier notification"""
    user = await _get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Not found", show_alert=True)
        return
    await _show_wishlist(callback.message, session, user, page=0, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("wl_page:"))
async def cb_wishlist_page(callback: CallbackQuery, session: AsyncSession, **kwargs):
    page = int(callback.data.split(":")[1])
    user = await _get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Not found", show_alert=True)
        return
    await _show_wishlist(callback.message, session, user, page=page, edit=True)
    await callback.answer()


async def _show_wishlist(message, session, user, page=0, edit=False):
    items = await _get_wishlist(session, user.id)
    text = f"❤️ <b>Список желаний</b> ({len(items)} товаров)\n\n"
    if not items:
        text += "Ваш вишлист пуст.\nДобавляйте товары кнопкой <b>❤️ В вишлист</b> на карточке товара."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
    else:
        text += "Нажмите на товар чтобы перейти к нему, 🗑 для удаления."
        kb = _wishlist_kb(items, page)

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ── Add to wishlist ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("wl_add:"))
async def cb_wishlist_add(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Формат: wl_add:{product_type}:{product_id}:{product_name}:{price}"""
    parts = callback.data.split(":", 4)
    if len(parts) < 4:
        await callback.answer("Ошибка", show_alert=True)
        return

    product_type = parts[1]
    product_id = int(parts[2])
    product_name = parts[3] if len(parts) > 3 else None
    price = None
    try:
        price = float(parts[4]) if len(parts) > 4 else None
    except (ValueError, IndexError):
        pass

    user = await _get_user(session, callback.from_user.id)
    if not user:
        await callback.answer("Not found", show_alert=True)
        return

    # Check duplicate
    exists = await session.execute(
        select(WishlistItem).where(
            and_(
                WishlistItem.user_id == user.id,
                WishlistItem.product_type == product_type,
                WishlistItem.product_id == product_id,
            )
        )
    )
    if exists.scalar_one_or_none():
        await callback.answer("Уже в вишлисте!", show_alert=True)
        return

    item = WishlistItem(
        user_id=user.id,
        product_type=product_type,
        product_id=product_id,
        product_name=product_name,
        price_at_add=price,
    )
    session.add(item)
    await session.commit()
    await callback.answer("❤️ Добавлено в вишлист!", show_alert=True)


# ── Remove from wishlist ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("wl_remove:"))
async def cb_wishlist_remove(callback: CallbackQuery, session: AsyncSession, **kwargs):
    item_id = int(callback.data.split(":")[1])
    await session.execute(delete(WishlistItem).where(WishlistItem.id == item_id))
    await session.commit()
    await callback.answer("Удалено из вишлиста")

    user = await _get_user(session, callback.from_user.id)
    if user:
        await _show_wishlist(callback.message, session, user, edit=True)


# ── Service: notify about price drop ──────────────────────────────────────

async def notify_wishlist_price_drop(
    bot,
    session: AsyncSession,
    product_type: str,
    product_id: int,
    product_name: str,
    new_price: float,
    old_price: float,
):
    """Вызывается когда цена на товар снизилась — уведомляем всех пользователей из вишлиста"""
    r = await session.execute(
        select(WishlistItem).where(
            and_(
                WishlistItem.product_type == product_type,
                WishlistItem.product_id == product_id,
                WishlistItem.notified_price_drop == False,
            )
        )
    )
    items = list(r.scalars().all())
    if not items:
        return

    # Get user telegram_ids
    user_ids = [item.user_id for item in items]
    users_r = await session.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = {u.id: u for u in users_r.scalars().all()}

    sent = 0
    for item in items:
        user = users.get(item.user_id)
        if not user:
            continue
        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=(
                    f"💸 <b>Цена снижена!</b>\n\n"
                    f"Товар <b>{product_name}</b> из вашего вишлиста\n"
                    f"теперь стоит <b>${new_price:.2f}</b> вместо ${old_price:.2f}\n\n"
                    f"Нажмите чтобы купить:"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🛒 Перейти к товару",
                        callback_data=f"wl_view:{product_type}:{product_id}"
                    )],
                    [InlineKeyboardButton(text="❤️ Мой вишлист", callback_data="wishlist")],
                ])
            )
            item.notified_price_drop = True
            sent += 1
        except Exception as e:
            logger.warning("Failed to notify user %s about price drop: %s", user.user_id, e)

    if sent:
        await session.commit()
    logger.info("Notified %d users about price drop on %s#%d", sent, product_type, product_id)
