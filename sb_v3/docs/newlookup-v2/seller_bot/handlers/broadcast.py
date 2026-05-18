"""Рассылка всем селлерам — только для админов"""
import logging
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.database.models import Seller
from seller_bot.config import seller_bot_config

logger = logging.getLogger(__name__)
router = Router(name="seller_broadcast")


class BroadcastStates(StatesGroup):
    waiting_message = State()


def is_admin(user_id: int) -> bool:
    return user_id in (seller_bot_config.admin_ids or [])


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Начать рассылку всем селлерам — только админ"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Access denied.")
        return
    await state.set_state(BroadcastStates.waiting_message)
    await message.answer(
        "📢 <b>Broadcast to all sellers</b>\n\n"
        "Send the message text for the broadcast.\n"
        "To cancel: /cancel"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Cancelled.")
    else:
        await message.answer("Nothing to cancel.")


@router.message(BroadcastStates.waiting_message, F.text)
async def process_broadcast_message(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = message.text
    if not text or len(text.strip()) < 2:
        await message.answer("❌ Text too short. Send again or /cancel")
        return

    await state.clear()
    status_msg = await message.answer("⏳ Broadcasting...")

    prefix = "📢 <b>Broadcast from Administration:</b>\n\n"
    full_text = f"{prefix}{text}"

    sent = 0
    failed = 0

    try:
        result = await session.execute(
            select(Seller).where(
                and_(Seller.is_approved == True, Seller.is_active == True)
            )
        )
        sellers = list(result.scalars().all())

        for seller in sellers:
            try:
                await message.bot.send_message(
                    seller.telegram_id,
                    full_text,
                    parse_mode="HTML"
                )
                sent += 1
            except Exception as e:
                logger.warning(f"Broadcast to seller {seller.telegram_id}: {e}")
                failed += 1
            await asyncio.sleep(0.05)

        await status_msg.edit_text(
            f"✅ <b>Broadcast completed</b>\n\n"
            f"📤 Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )
    except Exception as e:
        logger.exception("Broadcast failed")
        await status_msg.edit_text(f"❌ Broadcast error: {e}")
