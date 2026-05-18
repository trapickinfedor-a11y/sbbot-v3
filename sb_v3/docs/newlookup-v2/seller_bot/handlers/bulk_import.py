from __future__ import annotations

"""Seller Bot — массовый CSV/JSON импорт товаров + авто-выплаты по порогу"""
import csv
import json
import io
import logging
from decimal import Decimal
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Seller, SellerBank, SellerCCItem

logger = logging.getLogger(__name__)
router = Router(name="seller_bulk_import")

MIN_WITHDRAWAL_AUTO = Decimal("500.00")  # auto-approve threshold from spec


class BulkImportFSM(StatesGroup):
    waiting_file = State()
    confirming = State()


# ── keyboards ──────────────────────────────────────────────────────────────

def _import_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить CSV/JSON", callback_data="bulk_import_start")],
        [InlineKeyboardButton(text="📋 Шаблон CSV", callback_data="bulk_import_template")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="seller_main_menu")],
    ])


# ── CSV template ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "bulk_import_template")
async def cb_csv_template(callback: CallbackQuery, **kwargs):
    template = (
        "bank_code,buyer_price,base_price,state,city,zip_code,phone,email\n"
        "CHASE,150.00,120.00,CA,Los Angeles,90001,+13105551234,user@example.com\n"
        "BOA,130.00,100.00,NY,New York,10001,+12125555678,user2@example.com\n"
    )
    await callback.message.answer_document(
        document=("template.csv", template.encode()),
        caption=(
            "📋 <b>Шаблон CSV для импорта банков</b>\n\n"
            "Колонки: bank_code, buyer_price, base_price, state, city, zip_code, phone, email\n\n"
            "Отредактируйте и загрузите обратно."
        )
    )
    await callback.answer()


# ── Start import ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "bulk_import_start")
async def cb_bulk_import_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(BulkImportFSM.waiting_file)
    await callback.message.edit_text(
        "📥 <b>Массовый импорт товаров</b>\n\n"
        "Отправьте файл CSV или JSON с вашими товарами.\n\n"
        "<b>CSV формат:</b> bank_code, buyer_price, base_price, state, city, zip_code, phone, email\n"
        "<b>JSON формат:</b> [{\"bank_code\": \"CHASE\", \"buyer_price\": 150.00, ...}, ...]\n\n"
        "Лимит: 1000 товаров за раз.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="bulk_import_cancel")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "bulk_import_cancel")
async def cb_cancel_import(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.message.edit_text(
        "Импорт отменён.",
        reply_markup=_import_menu_kb()
    )
    await callback.answer()


@router.message(BulkImportFSM.waiting_file)
async def fsm_receive_file(message: Message, session: AsyncSession, state: FSMContext, bot: Bot, **kwargs):
    if not message.document:
        await message.answer("Пожалуйста, отправьте файл (.csv или .json)")
        return

    seller_r = await session.execute(select(Seller).where(Seller.telegram_id == message.from_user.id))
    seller = seller_r.scalar_one_or_none()
    if not seller:
        await state.clear()
        return

    # Download file
    try:
        file = await bot.get_file(message.document.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        buf.seek(0)
        content = buf.read().decode("utf-8", errors="replace")
    except Exception as e:
        await message.answer(f"❌ Ошибка загрузки файла: {e}")
        return

    # Parse
    records = []
    filename = message.document.file_name or ""
    try:
        if filename.endswith(".json"):
            records = json.loads(content)
        else:
            reader = csv.DictReader(io.StringIO(content))
            records = list(reader)
    except Exception as e:
        await message.answer(f"❌ Ошибка парсинга файла: {e}")
        return

    if not records:
        await message.answer("❌ Файл пустой или не содержит данных.")
        return

    records = records[:1000]  # max 1000
    await state.update_data(records=records)
    await state.set_state(BulkImportFSM.confirming)

    preview_lines = []
    for r in records[:5]:
        bc = r.get("bank_code", "?")
        bp = r.get("buyer_price", "?")
        preview_lines.append(f"• {bc} — ${bp}")
    preview = "\n".join(preview_lines)
    if len(records) > 5:
        preview += f"\n<i>...и ещё {len(records) - 5} позиций</i>"

    await message.answer(
        f"📦 <b>Готово к импорту: {len(records)} товаров</b>\n\n{preview}\n\nПодтвердить загрузку?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Импортировать", callback_data="bulk_import_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="bulk_import_cancel"),
            ]
        ])
    )


@router.callback_query(F.data == "bulk_import_confirm", BulkImportFSM.confirming)
async def cb_confirm_import(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    data = await state.get_data()
    records = data.get("records", [])
    await state.clear()

    seller_r = await session.execute(select(Seller).where(Seller.telegram_id == callback.from_user.id))
    seller = seller_r.scalar_one_or_none()
    if not seller:
        await callback.answer("Not found", show_alert=True)
        return

    await callback.message.edit_text(f"⏳ Импортирую {len(records)} товаров...")

    created = 0
    errors = 0
    for rec in records:
        try:
            bank_code = str(rec.get("bank_code", "")).strip().upper()
            if not bank_code:
                errors += 1
                continue
            buyer_price = Decimal(str(rec.get("buyer_price", 0)))
            base_price = Decimal(str(rec.get("base_price", buyer_price * Decimal("0.8"))))

            bank = SellerBank(
                seller_id=seller.id,
                bank_code=bank_code,
                buyer_price=buyer_price,
                base_price=base_price,
                final_price=buyer_price,
                state=str(rec.get("state", "")).strip() or None,
                city=str(rec.get("city", "")).strip() or None,
                zip_code=str(rec.get("zip_code", "")).strip() or None,
                phone=str(rec.get("phone", "")).strip() or None,
                email=str(rec.get("email", "")).strip() or None,
                status="available",
            )
            session.add(bank)
            created += 1
        except Exception as e:
            logger.warning(f"Import row error: {e}")
            errors += 1

    await session.commit()
    await callback.message.edit_text(
        f"✅ <b>Импорт завершён!</b>\n\n"
        f"Загружено: <b>{created}</b> товаров\n"
        f"Ошибок: <b>{errors}</b>",
        reply_markup=_import_menu_kb()
    )


# ── Auto-payout check ──────────────────────────────────────────────────────

async def check_seller_auto_payout(session: AsyncSession, seller: Seller, bot: Bot):
    """
    Если withdrawable_balance >= MIN_WITHDRAWAL_AUTO и авто-выплаты включены,
    создаём заявку на вывод автоматически.
    """
    if float(seller.withdrawable_balance or 0) < float(MIN_WITHDRAWAL_AUTO):
        return

    from shared.database.models import SellerWithdrawal
    # Check if pending withdrawal already exists
    existing_r = await session.execute(
        select(SellerWithdrawal).where(
            SellerWithdrawal.seller_id == seller.id,
            SellerWithdrawal.status == "pending"
        )
    )
    if existing_r.scalar_one_or_none():
        return  # already pending

    withdrawal = SellerWithdrawal(
        seller_id=seller.id,
        amount=seller.withdrawable_balance,
        status="pending",
        notes="Auto-withdrawal (threshold reached)",
    )
    session.add(withdrawal)
    seller.withdrawable_balance = Decimal("0.00")
    await session.commit()

    try:
        await bot.send_message(
            chat_id=seller.telegram_id,
            text=(
                f"💸 <b>Авто-вывод создан!</b>\n\n"
                f"Сумма: <b>${float(withdrawal.amount):.2f}</b>\n"
                f"Заявка #{withdrawal.id} создана автоматически.\n"
                f"Ожидайте подтверждения от администратора."
            )
        )
    except Exception as e:
        logger.warning(f"Failed to notify seller {seller.id} about auto-payout: {e}")
