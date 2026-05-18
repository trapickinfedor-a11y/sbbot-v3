from __future__ import annotations

"""Mirror Bot — Корзина покупателя (Shopping Cart)"""
import logging
from decimal import Decimal
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import User, ShoppingCart, CartItem, SellerBank

logger = logging.getLogger(__name__)
router = Router(name="cart")

PAGE_SIZE = 5


# ── helpers ────────────────────────────────────────────────────────────────

async def _get_or_create_cart(session: AsyncSession, user: User) -> ShoppingCart:
    """Get or create a shopping cart for the user."""
    r = await session.execute(
        select(ShoppingCart).where(
            ShoppingCart.user_id == user.id,
            ShoppingCart.status == "active",
        )
    )
    cart = r.scalar_one_or_none()
    if not cart:
        cart = ShoppingCart(user_id=user.id, status="active")
        session.add(cart)
        await session.flush()
    return cart


def _cart_keyboard(cart: ShoppingCart, items: list[CartItem], page: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    for item in items[start:end]:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {item.product_name or 'Item'} — ${float(item.price):.2f}",
                callback_data=f"cart_remove:{item.id}",
            )
        ])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cart_page:{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cart_page:{page+1}"))
    if nav:
        buttons.append(nav)

    total = sum(float(i.price) for i in items)
    if items:
        buttons.append([InlineKeyboardButton(
            text=f"✅ Checkout (${total:.2f})",
            callback_data="cart_checkout",
        )])
        buttons.append([InlineKeyboardButton(text="🗑 Clear Cart", callback_data="cart_clear")])
    buttons.append([InlineKeyboardButton(text="◀️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _fmt_cart(items: list[CartItem], page: int = 0) -> str:
    if not items:
        return (
            "🛒 <b>Your cart is empty</b>\n\n"
            "Browse the catalog and tap <b>Add to Cart</b> on any product."
        )
    total = sum(float(i.price) for i in items)
    lines = [f"🛒 <b>Your Cart</b> ({len(items)} items)\n"]
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    for idx, item in enumerate(items[start:end], start + 1):
        lines.append(f"{idx}. {item.product_name or 'Unknown'} — <b>${float(item.price):.2f}</b>")
    lines.append(f"\n💰 <b>Total: ${total:.2f}</b>")
    lines.append("\nTap an item name to remove it, or <b>Checkout</b> to buy all at once.")
    return "\n".join(lines)


# ── handlers ───────────────────────────────────────────────────────────────

@router.message(F.text.in_({"🛒 Cart", "🛒 Корзина"}))
@router.callback_query(F.data == "cart_view")
async def show_cart(event, session: AsyncSession, mirror_bot_id: int = 0, **kwargs):
    """Show the user's shopping cart."""
    user_id = event.from_user.id
    is_cb = isinstance(event, CallbackQuery)

    r = await session.execute(select(User).where(User.user_id == user_id))
    user = r.scalar_one_or_none()
    if not user:
        text = "Please /start first."
        if is_cb:
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return

    cart = await _get_or_create_cart(session, user)
    r2 = await session.execute(
        select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.added_at.asc())
    )
    items = list(r2.scalars().all())
    text = _fmt_cart(items)
    kb = _cart_keyboard(cart, items)

    if is_cb:
        try:
            await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await event.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("cart_page:"))
async def cart_page(callback: CallbackQuery, session: AsyncSession, **kwargs):
    page = int(callback.data.split(":")[1])
    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await callback.answer("Not found", show_alert=True)
        return
    cart = await _get_or_create_cart(session, user)
    r2 = await session.execute(
        select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.added_at.asc())
    )
    items = list(r2.scalars().all())
    try:
        await callback.message.edit_text(
            _fmt_cart(items, page), parse_mode="HTML",
            reply_markup=_cart_keyboard(cart, items, page)
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("cart_add:"))
async def cart_add(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Add a product to cart. Format: cart_add:{product_type}:{product_id}"""
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Invalid data", show_alert=True)
        return
    product_type, product_id = parts[1], int(parts[2])

    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await callback.answer("Please /start first", show_alert=True)
        return

    # Get product name and price from SellerBank
    product_name = f"Product #{product_id}"
    price = Decimal("0")
    try:
        product = await session.get(SellerBank, product_id)
        if product:
            product_name = getattr(product, "bank_name", product_name) or product_name
            price = Decimal(str(getattr(product, "buyer_price", 0) or 0))
    except Exception as exc:
        logger.warning("Could not fetch product for cart: %s", exc)

    cart = await _get_or_create_cart(session, user)

    # Check if already in cart
    existing = await session.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_type == product_type,
            CartItem.product_id == product_id,
        )
    )
    if existing:
        await callback.answer("Already in cart!", show_alert=True)
        return

    item = CartItem(
        cart_id=cart.id,
        product_type=product_type,
        product_id=product_id,
        product_name=product_name,
        price=price,
    )
    session.add(item)
    cart.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await callback.answer(f"✅ Added to cart: {product_name}")


@router.callback_query(F.data.startswith("cart_remove:"))
async def cart_remove(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Remove item from cart by CartItem.id"""
    item_id = int(callback.data.split(":")[1])
    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await callback.answer("Not found", show_alert=True)
        return

    item = await session.get(CartItem, item_id)
    if item:
        await session.delete(item)
        await session.commit()
        await callback.answer("🗑 Removed from cart")
    else:
        await callback.answer("Item not found", show_alert=True)
        return

    # Refresh cart view
    cart = await _get_or_create_cart(session, user)
    r2 = await session.execute(
        select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.added_at.asc())
    )
    items = list(r2.scalars().all())
    try:
        await callback.message.edit_text(
            _fmt_cart(items), parse_mode="HTML",
            reply_markup=_cart_keyboard(cart, items)
        )
    except Exception:
        pass


@router.callback_query(F.data == "cart_clear")
async def cart_clear(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Clear all items from cart."""
    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await callback.answer("Not found", show_alert=True)
        return
    cart = await _get_or_create_cart(session, user)
    r2 = await session.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    items = list(r2.scalars().all())
    for item in items:
        await session.delete(item)
    await session.commit()
    await callback.answer("🗑 Cart cleared")
    try:
        await callback.message.edit_text(
            _fmt_cart([]), parse_mode="HTML",
            reply_markup=_cart_keyboard(cart, [])
        )
    except Exception:
        pass


@router.callback_query(F.data == "cart_checkout")
async def cart_checkout(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Initiate checkout for all items in cart."""
    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await callback.answer("Not found", show_alert=True)
        return

    cart = await _get_or_create_cart(session, user)
    r2 = await session.execute(
        select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.added_at.asc())
    )
    items = list(r2.scalars().all())
    if not items:
        await callback.answer("Cart is empty!", show_alert=True)
        return

    total = sum(float(i.price) for i in items)
    balance = float(getattr(user, "balance", 0) or 0)

    if balance < total:
        await callback.answer(
            f"Insufficient balance!\n"
            f"Required: ${total:.2f}\n"
            f"Your balance: ${balance:.2f}",
            show_alert=True
        )
        return

    # Mark cart as checked_out (actual purchase processing per product would go here)
    cart.status = "checked_out"
    await session.commit()

    await callback.message.edit_text(
        f"✅ <b>Checkout initiated!</b>\n\n"
        f"{len(items)} items · Total: <b>${total:.2f}</b>\n\n"
        f"Your orders are being processed. Check <b>📦 My Orders</b> for status.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 My Orders", callback_data="my_purchases")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ])
    )
    await callback.answer()
