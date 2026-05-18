import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import SellerOrder, SellerBank
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_finance_service import SellerFinanceService
from seller_bot.keyboards.inline import seller_main_menu
from seller_bot.utils import get_seller_unread_count

logger = logging.getLogger(__name__)
router = Router(name="seller_profile")


@router.callback_query(F.data == "seller_profile")
async def profile_handler(callback: CallbackQuery, session: AsyncSession, seller, texts, buttons, **kwargs):
    if not seller:
        await callback.answer(texts.NOT_AUTHORIZED, show_alert=True)
        return
    
    # Count banks
    banks_result = await session.execute(
        select(func.count(SellerBank.id)).where(
            and_(SellerBank.seller_id == seller.id, SellerBank.is_active == True)
        )
    )
    total_banks = banks_result.scalar() or 0
    
    in_stock_result = await session.execute(
        select(func.count(SellerBank.id)).where(
            and_(
                SellerBank.seller_id == seller.id,
                SellerBank.is_active == True,
                SellerBank.is_in_stock == True
            )
        )
    )
    in_stock_banks = in_stock_result.scalar() or 0
    
    # Count orders by status
    completed_result = await session.execute(
        select(func.count(SellerOrder.id)).where(
            and_(SellerOrder.seller_id == seller.id, SellerOrder.status == "completed")
        )
    )
    completed_orders = completed_result.scalar() or 0
    
    active_result = await session.execute(
        select(func.count(SellerOrder.id)).where(
            and_(
                SellerOrder.seller_id == seller.id,
                SellerOrder.status.in_(["approved", "in_progress"])
            )
        )
    )
    active_orders = active_result.scalar() or 0
    
    type_label = "🔵 Internal" if seller.seller_type == "internal" else "🟢 External"
    
    deposit = float(seller.deposit_balance or 0)
    pending_balance = float(SellerFinanceService.pending_balance(seller))
    withdrawable_balance = float(SellerFinanceService.withdrawable_balance(seller))
    text = texts.PROFILE_TEXT.format(
        name=seller.display_name,
        username=seller.username or "N/A",
        seller_type=type_label,
        markup=seller.markup_percent,
        total_banks=total_banks,
        in_stock_banks=in_stock_banks,
        active_orders=active_orders,
        completed_orders=completed_orders,
        total_orders=seller.total_orders,
        total_earned=seller.total_earned,
        deposit=deposit,
        pending=pending_balance,
        withdrawable=withdrawable_balance,
        registered=seller.created_at.strftime('%Y-%m-%d'),
    )
    deposit_categories = ", ".join(sorted(SellerDepositService.allowed_categories(seller))) or "none"
    text += (
        f"\n\n🔐 Security deposit status: <b>{getattr(seller, 'security_deposit_status', 'unpaid')}</b>"
        f"\n🔓 Seller access: <b>{getattr(seller, 'access_status', 'pending_deposit')}</b>"
        f"\n📦 Deposit packages: <b>{deposit_categories}</b>"
        f"\n💵 Refundable held deposit: <b>${float(getattr(seller, 'security_deposit_balance', 0) or 0):.2f}</b>"
    )
    
    unread = await get_seller_unread_count(session, seller.id)
    seller_actor = kwargs.get("seller_actor")
    await callback.message.edit_text(
        text,
        reply_markup=seller_main_menu(
            unread_count=unread,
            buttons=buttons,
            actor_role=seller_actor.role if seller_actor else None,
            is_on_vacation=bool(getattr(seller, "is_on_vacation", False)),
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "seller_vacation_toggle")
async def seller_vacation_toggle(callback: CallbackQuery, session: AsyncSession, seller, texts, buttons, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    seller_actor = kwargs.get("seller_actor")
    if seller_actor and seller_actor.role not in (None, "owner", "manager_helper"):
        await callback.answer("❌ Only the seller owner can toggle vacation mode.", show_alert=True)
        return

    is_now_vacation = not bool(getattr(seller, "is_on_vacation", False))
    seller.is_on_vacation = is_now_vacation
    if is_now_vacation:
        seller.vacation_started_at = datetime.now(timezone.utc)
        seller.vacation_ends_at = None
        msg = "🏖 <b>Vacation mode enabled.</b>\n\nYour listings are hidden from buyers. Orders will not be created."
    else:
        seller.vacation_started_at = None
        seller.vacation_ends_at = None
        msg = "🔔 <b>Vacation mode disabled.</b>\n\nYour listings are now visible to buyers again."

    await session.commit()
    unread = await get_seller_unread_count(session, seller.id)
    await callback.message.edit_text(
        msg,
        reply_markup=seller_main_menu(
            unread_count=unread,
            buttons=buttons,
            actor_role=seller_actor.role if seller_actor else None,
            is_on_vacation=is_now_vacation,
        ),
    )
    await callback.answer("✅ Vacation mode " + ("ON" if is_now_vacation else "OFF"))


@router.callback_query(F.data == "seller_leave_system")
async def seller_leave_system(callback: CallbackQuery, session: AsyncSession, seller, texts, buttons, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_manage_finance():
        await callback.answer(texts.NOT_AUTHORIZED, show_alert=True)
        return
    try:
        await SellerDepositService.request_exit(
            session,
            seller,
            actor_id=seller.telegram_id,
            source="seller_bot",
        )
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.message.edit_text(
        "🚪 <b>Exit requested.</b>\n\n"
        "Your seller access is now closed.\n"
        "The security deposit was moved to refund review.",
    )
    await callback.answer("Exit requested", show_alert=True)
