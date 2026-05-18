from __future__ import annotations

"""
Shared chat rendering for buyer/seller chat with pagination and truncation
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerChat

CHAT_MSG_LIMIT = 25
MAX_CHAT_TEXT_LEN = 3500
DATE_FMT = "%d.%m %H:%M"
MSG_SEP = "\n───\n"


def _escape_markdown(text: str) -> str:
    """Escape special chars for Markdown to prevent parse errors"""
    if not text:
        return ""
    for c in ["\\", "_", "*", "[", "]", "(", ")", "`", "~"]:
        text = text.replace(c, f"\\{c}")
    return text


def _escape_html(text: str) -> str:
    """Escape for HTML"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def get_chat_messages(
    session: AsyncSession,
    conversation_id: int | None,
    order_id: int | None = None,
    offset: int = 0,
    limit: int = CHAT_MSG_LIMIT
) -> tuple[list, int]:
    """
    Fetch messages. Приоритет: conversation_id. Если нет — по order_id (legacy).
    """
    if conversation_id:
        count_result = await session.execute(
            select(func.count(SellerChat.id)).where(SellerChat.seller_conversation_id == conversation_id)
        )
        total = count_result.scalar_one() or 0
        result = await session.execute(
            select(SellerChat)
            .where(SellerChat.seller_conversation_id == conversation_id)
            .order_by(SellerChat.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    elif order_id:
        count_result = await session.execute(
            select(func.count(SellerChat.id)).where(SellerChat.seller_order_id == order_id)
        )
        total = count_result.scalar_one() or 0
        result = await session.execute(
            select(SellerChat)
            .where(SellerChat.seller_order_id == order_id)
            .order_by(SellerChat.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    else:
        return [], 0
    messages = list(reversed(list(result.scalars().all())))
    return messages, total


async def get_chat_messages_by_order(
    session: AsyncSession,
    order_id: int,
    offset: int = 0,
    limit: int = CHAT_MSG_LIMIT
) -> tuple[list, int]:
    """Legacy: сообщения по order_id (для миграции и support_bot)"""
    count_result = await session.execute(
        select(func.count(SellerChat.id)).where(SellerChat.seller_order_id == order_id)
    )
    total = count_result.scalar_one() or 0
    result = await session.execute(
        select(SellerChat)
        .where(SellerChat.seller_order_id == order_id)
        .order_by(SellerChat.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    messages = list(reversed(list(result.scalars().all())))
    return messages, total


def build_chat_text(
    messages: list,
    sender_labels: dict,
    parse_mode: str = "Markdown",
    has_older: bool = False,
    older_count: int = 0
) -> str:
    """
    Build chat text from messages.
    sender_labels: {"buyer": "...", "seller": "...", "admin": "..."}
    """
    lines = []
    current_len = 0

    for msg in messages:
        sender = sender_labels.get(msg.sender_type, "?")
        time_str = msg.created_at.strftime(DATE_FMT)
        body = (msg.message_text or "[file]")
        if parse_mode == "Markdown":
            body = _escape_markdown(body) if body != "[file]" else body
        else:
            body = _escape_html(body) if body != "[file]" else body

        line = f"**{sender}** [{time_str}]:\n{body}" if parse_mode == "Markdown" else f"<b>{sender}</b> [{time_str}]:\n{body}"
        line += MSG_SEP
        line_len = len(line)

        if current_len + line_len > MAX_CHAT_TEXT_LEN and lines:
            break
        lines.append(line)
        current_len += line_len

    if has_older and older_count:
        prefix = f"_... {older_count} older messages_\n\n" if parse_mode == "Markdown" else f"<i>... {older_count} older messages</i>\n\n"
    else:
        prefix = ""
    return prefix + "\n".join(lines) if lines else ""


# Быстрые ответы для покупателя
BUYER_QUICK_REPLIES = [
    ("⏳ When ready?", "When will it be ready?"),
    ("📦 Status?", "What's the status of my order?"),
    ("✅ Got it", "Got it, thanks!"),
]


def buyer_chat_keyboard(conv_id: int, offset: int = 0, total: int = 0, can_dispute: bool = False, order_id: int | None = None) -> "InlineKeyboardMarkup":
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    oid = order_id or 0
    buttons = []
    next_offset = offset + CHAT_MSG_LIMIT
    if total > next_offset:
        buttons.append([InlineKeyboardButton(text="↩ Load older", callback_data=f"buyer_chat_load:{conv_id}:{next_offset}")])
    qr_btns = [InlineKeyboardButton(text=txt, callback_data=f"buyer_qr:{conv_id}:{i}") for i, (txt, _) in enumerate(BUYER_QUICK_REPLIES)]
    buttons.append(qr_btns)
    if can_dispute and order_id:
        buttons.append([InlineKeyboardButton(text="⚠️ Open Dispute", callback_data=f"buyer_dispute:{order_id}")])
    buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=f"buyer_chat_conv:{conv_id}:{oid}")])
    buttons.append([InlineKeyboardButton(text="❌ End Chat", callback_data=f"buyer_end_chat:{conv_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Быстрые ответы для селлера (шаблоны): (текст кнопки, текст сообщения)
SELLER_QUICK_REPLIES = [
    ("✅ Got it", "Got it, working on it."),
    ("📦 Soon", "Will send result soon."),
    ("❓ Info", "Need more info from you."),
    ("✅ Done", "Order completed, check result."),
]


def seller_chat_keyboard(conv_id: int, offset: int = 0, total: int = 0) -> "InlineKeyboardMarkup":
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    next_offset = offset + CHAT_MSG_LIMIT
    if total > next_offset:
        buttons.append([InlineKeyboardButton(text="↩ Load older", callback_data=f"seller_chat_load:{conv_id}:{next_offset}")])
    qr_row1 = [InlineKeyboardButton(text=txt, callback_data=f"seller_qr:{conv_id}:{i}") for i, (txt, _) in enumerate(SELLER_QUICK_REPLIES[:2])]
    qr_row2 = [InlineKeyboardButton(text=txt, callback_data=f"seller_qr:{conv_id}:{i+2}") for i, (txt, _) in enumerate(SELLER_QUICK_REPLIES[2:])]
    buttons.append(qr_row1)
    buttons.append(qr_row2)
    buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=f"seller_chat:{conv_id}")])
    buttons.append([InlineKeyboardButton(text="❌ End Chat", callback_data=f"seller_end_chat:{conv_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
