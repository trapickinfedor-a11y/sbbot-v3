from __future__ import annotations

"""
Admin handlers for Education PDF watermarking: /addmanual, /findleak.
Admin-only. Uses ADMIN_IDS from env.
"""

import logging
import os
import re
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.env_utils import parse_int_list_env
from shared.database.models import EducationCategory, EducationManual, ManualDelivery, User

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = parse_int_list_env("ADMIN_IDS")
MANUALS_ORIGINALS_DIR = os.path.join(os.getcwd(), "manuals", "originals")


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _slugify(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.lower())
    s = re.sub(r"[-\s]+", "_", s).strip("_")
    return s[:80] or "manual"


@router.message(F.document, F.caption)
async def admin_addmanual_handler(message: Message, session: AsyncSession):
    """Admin sends PDF with caption /addmanual [title] or /addmanual [title] [price]"""
    if not _is_admin(message.from_user.id):
        return

    caption = (message.caption or "").strip()
    if not caption.lower().startswith("/addmanual"):
        return

    rest = caption[len("/addmanual"):].strip()
    if not rest:
        title, price = "Untitled Manual", Decimal("0")
    else:
        parts = rest.rsplit(maxsplit=1)
        if len(parts) == 2:
            try:
                price = Decimal(parts[1])
                title = parts[0]
            except Exception:
                title, price = rest, Decimal("0")
        else:
            title, price = rest, Decimal("0")

    doc = message.document
    if not doc or not doc.file_name:
        await message.reply("❌ Please send a PDF file with caption: /addmanual [title] [price]")
        return
    if not doc.file_name.lower().endswith(".pdf"):
        await message.reply("❌ Only PDF files are accepted.")
        return

    try:
        bot = message.bot
        file = await bot.get_file(doc.file_id)
        downloaded = await bot.download_file(file.file_path)
        data = downloaded.getvalue() if hasattr(downloaded, "getvalue") else downloaded.read()

        # Ensure category exists
        result = await session.execute(
            select(EducationCategory).where(
                EducationCategory.code == "guides",
                EducationCategory.item_type == "manual",
            )
        )
        cat = result.scalar_one_or_none()
        if not cat:
            cat = EducationCategory(
                code="guides",
                name="Guides & How-To",
                item_type="manual",
                position=0,
            )
            session.add(cat)
            await session.flush()

        code = _slugify(title)
        existing = await session.execute(select(EducationManual).where(EducationManual.code == code))
        if existing.scalar_one_or_none():
            code = f"{code}_{cat.id}"

        manual = EducationManual(
            code=code,
            name=title,
            category_code=cat.code,
            price=price,
            file_path="",
            file_name=doc.file_name,
            file_type="pdf",
            is_available=True,
            position=0,
        )
        session.add(manual)
        await session.flush()

        os.makedirs(MANUALS_ORIGINALS_DIR, exist_ok=True)
        save_path = os.path.join(MANUALS_ORIGINALS_DIR, f"{manual.id}.pdf")
        with open(save_path, "wb") as f:
            f.write(data)

        manual.file_path = save_path
        await session.commit()

        await message.reply(
            f"✅ Manual added: *{title}*\n"
            f"ID: {manual.id} | Code: {code}\n"
            f"Price: ${price:.2f}\n"
            f"Path: `{save_path}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("addmanual failed: %s", e)
        await message.reply(f"❌ Error: {e}")


@router.message(F.text.startswith("/findleak"))
async def admin_findleak_handler(message: Message, session: AsyncSession):
    """Admin pastes leaked text: /findleak <text> — extracts user_id from zero-width fingerprint."""
    if not _is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    snippet = text[len("/findleak"):].strip()
    if not snippet:
        await message.reply("Usage: /findleak <paste leaked text snippet here>")
        return

    from shared.services.pdf_watermark import decode_user_id_from_text

    user_id = decode_user_id_from_text(snippet)
    if user_id is None:
        await message.reply("No fingerprint found in the text.")
        return

    # Look up delivery record for username and date
    result = await session.execute(
        select(ManualDelivery)
        .where(ManualDelivery.user_id == user_id)
        .order_by(ManualDelivery.delivered_at.desc())
        .limit(1)
    )
    delivery = result.scalar_one_or_none()

    if delivery:
        username = delivery.username or "unknown"
        date_str = delivery.delivered_at.strftime("%Y-%m-%d %H:%M") if delivery.delivered_at else "N/A"
        await message.reply(
            f"Leaked by: @{username} (ID: {user_id}), purchased on {date_str}"
        )
    else:
        # Try User table as fallback
        result = await session.execute(select(User).where(User.user_id == user_id).limit(1))
        user = result.scalar_one_or_none()
        username = user.username if user else "unknown"
        await message.reply(
            f"Leaked by: @{username} (ID: {user_id}), no delivery record found"
        )
