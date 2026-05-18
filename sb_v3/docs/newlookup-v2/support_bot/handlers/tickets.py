from __future__ import annotations

"""Support Bot — тикеты с SLA маршрутизацией, приоритетами и CSAT-оценкой"""
import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from shared.database.models import SupportTicket, SupportTicketMessage, User, Worker, KnowledgeBaseArticle

logger = logging.getLogger(__name__)
router = Router(name="support_tickets")

# SLA limits in minutes per priority
SLA_FIRST_RESPONSE = {
    "CRITICAL": 15,
    "HIGH": 60,
    "NORMAL": 240,
    "LOW": 1440,
}

PRIORITY_LABELS = {
    "CRITICAL": "🔴 КРИТИЧЕСКИЙ",
    "HIGH": "🟠 ВЫСОКИЙ",
    "NORMAL": "🟡 ОБЫЧНЫЙ",
    "LOW": "🟢 НИЗКИЙ",
}

CATEGORY_PRIORITY_MAP = {
    "financial": "CRITICAL",
    "technical": "HIGH",
    "general": "NORMAL",
    "suggestion": "LOW",
}


class CreateTicketFSM(StatesGroup):
    choose_category = State()
    write_message = State()
    kb_suggested = State()   # waiting for user to accept/skip KB suggestion


class ReplyTicketFSM(StatesGroup):
    writing_reply = State()


# ── Answer Bot KB search helper ─────────────────────────────────────────────

async def _search_kb(session: AsyncSession, text: str, category: str, limit: int = 2) -> list:
    """Keyword-match search in KnowledgeBaseArticle for user's question."""
    words = {w.lower().strip(".,?!") for w in text.split() if len(w) > 3}
    r = await session.execute(
        select(KnowledgeBaseArticle).where(
            KnowledgeBaseArticle.is_active == True,
            KnowledgeBaseArticle.audience.in_(["user", "all"]),
        ).limit(100)
    )
    articles = list(r.scalars().all())
    scored = []
    for art in articles:
        haystack = f"{art.title} {art.keywords or ''} {art.body[:300]}".lower()
        score = sum(1 for w in words if w in haystack)
        cat_bonus = 1 if art.category == category else 0
        scored.append((score + cat_bonus, art))
    scored.sort(key=lambda x: -x[0])
    return [a for s, a in scored if s > 0][:limit]


# ── keyboards ──────────────────────────────────────────────────────────────

def _category_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Финансовый вопрос", callback_data="tkt_cat:financial")],
        [InlineKeyboardButton(text="⚙️ Техническая проблема", callback_data="tkt_cat:technical")],
        [InlineKeyboardButton(text="❓ Общий вопрос", callback_data="tkt_cat:general")],
        [InlineKeyboardButton(text="💡 Предложение", callback_data="tkt_cat:suggestion")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="tkt_cancel")],
    ])


def _ticket_detail_kb(ticket_id: int, is_support: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if is_support:
        rows.append([
            InlineKeyboardButton(text="✅ Решено", callback_data=f"tkt_resolve:{ticket_id}"),
            InlineKeyboardButton(text="📩 Ответить", callback_data=f"tkt_reply:{ticket_id}"),
        ])
        rows.append([InlineKeyboardButton(text="🔺 Эскалировать", callback_data=f"tkt_escalate:{ticket_id}")])
    else:
        rows.append([InlineKeyboardButton(text="📩 Добавить сообщение", callback_data=f"tkt_reply:{ticket_id}")])
        rows.append([InlineKeyboardButton(text="✅ Закрыть тикет", callback_data=f"tkt_close:{ticket_id}")])
    rows.append([InlineKeyboardButton(text="◀️ Мои тикеты", callback_data="tkt_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _csat_kb(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Отлично", callback_data=f"tkt_csat:{ticket_id}:3"),
            InlineKeyboardButton(text="😐 Нормально", callback_data=f"tkt_csat:{ticket_id}:2"),
            InlineKeyboardButton(text="👎 Плохо", callback_data=f"tkt_csat:{ticket_id}:1"),
        ]
    ])


# ── helpers ────────────────────────────────────────────────────────────────

def _classify_priority(text: str, category: str) -> str:
    """Автоклассификация приоритета по тексту и категории"""
    base = CATEGORY_PRIORITY_MAP.get(category, "NORMAL")
    text_lower = text.lower()
    critical_keywords = ["не могу вывести", "взлом", "украли", "возврат", "вывод заблокирован"]
    high_keywords = ["не работает", "ошибка", "не приходит", "потерял", "платеж"]
    if any(kw in text_lower for kw in critical_keywords):
        return "CRITICAL"
    if any(kw in text_lower for kw in high_keywords) and base == "NORMAL":
        return "HIGH"
    return base


async def _get_or_create_ticket(session, user: User, category: str, first_message: str) -> SupportTicket:
    priority = _classify_priority(first_message, category)
    # SupportTicket.user_id FK points to users.user_id
    ticket = SupportTicket(
        user_id=user.user_id,
        mirror_bot_id=user.mirror_bot_id,
        category=category,
        priority=priority,
        status="new",
        subject=first_message[:500],
    )
    session.add(ticket)
    await session.flush()

    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_type="user",
        sender_id=user.user_id,
        message=first_message,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(ticket)
    return ticket


# ── User: create ticket ────────────────────────────────────────────────────

@router.message(Command("ticket"))
async def cmd_new_ticket(message: Message, state: FSMContext, **kwargs):
    await state.set_state(CreateTicketFSM.choose_category)
    await message.answer(
        "🎫 <b>Создание тикета поддержки</b>\n\nВыберите категорию обращения:",
        reply_markup=_category_kb()
    )


@router.callback_query(F.data.startswith("tkt_cat:"))
async def cb_choose_category(callback: CallbackQuery, state: FSMContext, **kwargs):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(CreateTicketFSM.write_message)
    await callback.message.edit_text(
        f"📝 Опишите вашу проблему подробно:\n\n"
        f"<i>Категория: {category}</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="tkt_cancel")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "tkt_cancel")
async def cb_cancel_ticket(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.message.edit_text("Создание тикета отменено.")
    await callback.answer()


@router.message(CreateTicketFSM.write_message)
async def fsm_ticket_message(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    data = await state.get_data()
    category = data.get("category", "general")
    user_text = (message.text or "").strip()

    r = await session.execute(select(User).where(User.user_id == message.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await state.clear()
        await message.answer("Сначала зарегистрируйтесь через Mirror Bot.")
        return

    # Answer Bot: search KB before creating ticket
    kb_articles = await _search_kb(session, user_text, category)
    if kb_articles:
        # Increment views
        for art in kb_articles:
            art.views = (art.views or 0) + 1
        await session.commit()

        await state.update_data(pending_text=user_text, kb_article_ids=[a.id for a in kb_articles])
        await state.set_state(CreateTicketFSM.kb_suggested)

        suggestions = "\n\n".join(
            f"📖 <b>{art.title}</b>\n{art.body[:300]}{'…' if len(art.body) > 300 else ''}"
            for art in kb_articles
        )
        kb_buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проблема решена", callback_data="tkt_kb_solved")],
            [InlineKeyboardButton(text="🆘 Всё равно связаться с поддержкой", callback_data="tkt_kb_skip")],
        ])
        await message.answer(
            f"🔍 <b>Возможно, это поможет вам:</b>\n\n{suggestions}\n\n"
            f"Решила ли эта информация вашу проблему?",
            parse_mode="HTML",
            reply_markup=kb_buttons,
        )
        return

    # No KB match — create ticket immediately
    ticket = await _get_or_create_ticket(session, user, category, user_text)
    await state.clear()

    sla_min = SLA_FIRST_RESPONSE.get(ticket.priority, 240)
    await message.answer(
        f"✅ <b>Тикет #{ticket.id} создан!</b>\n\n"
        f"Приоритет: {PRIORITY_LABELS[ticket.priority]}\n"
        f"SLA (первый ответ): {sla_min} минут\n\n"
        f"Мы ответим как можно скорее.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои тикеты", callback_data="tkt_list")]
        ])
    )


@router.callback_query(F.data == "tkt_kb_solved")
async def cb_kb_solved(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    """User says KB article solved the problem — mark helpful and close."""
    data = await state.get_data()
    for art_id in (data.get("kb_article_ids") or []):
        art = await session.get(KnowledgeBaseArticle, art_id)
        if art:
            art.helpful_votes = (art.helpful_votes or 0) + 1
    await session.commit()
    await state.clear()
    await callback.message.edit_text(
        "🎉 Отлично! Рады, что смогли помочь.\n\n"
        "Если возникнут другие вопросы, используйте /ticket.",
        parse_mode="HTML",
    )
    await callback.answer("✅ Marked as helpful!")


@router.callback_query(F.data == "tkt_kb_skip")
async def cb_kb_skip(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    """User wants human support despite KB suggestion."""
    data = await state.get_data()
    category = data.get("category", "general")
    user_text = data.get("pending_text", "")

    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await state.clear()
        await callback.message.edit_text("Пожалуйста, пройдите регистрацию через Mirror Bot.")
        return

    ticket = await _get_or_create_ticket(session, user, category, user_text)
    await state.clear()

    sla_min = SLA_FIRST_RESPONSE.get(ticket.priority, 240)
    await callback.message.edit_text(
        f"✅ <b>Тикет #{ticket.id} создан!</b>\n\n"
        f"Приоритет: {PRIORITY_LABELS[ticket.priority]}\n"
        f"SLA (первый ответ): {sla_min} минут\n\n"
        f"Мы ответим как можно скорее.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои тикеты", callback_data="tkt_list")]
        ])
    )
    await callback.answer()


# ── User: list tickets ─────────────────────────────────────────────────────

@router.callback_query(F.data == "tkt_list")
async def cb_ticket_list(callback: CallbackQuery, session: AsyncSession, **kwargs):
    r = await session.execute(select(User).where(User.user_id == callback.from_user.id))
    user = r.scalar_one_or_none()
    if not user:
        await callback.answer("Not found", show_alert=True)
        return

    tickets_r = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.created_at.desc())
        .limit(10)
    )
    tickets = list(tickets_r.scalars().all())

    if not tickets:
        await callback.message.edit_text(
            "У вас нет тикетов.\n/ticket — создать новый",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return

    rows = []
    for t in tickets:
        status_emoji = {"new": "🆕", "open": "📂", "pending": "⏳", "solved": "✅", "closed": "🔒"}.get(t.status, "📋")
        rows.append([InlineKeyboardButton(
            text=f"{status_emoji} #{t.id} [{t.priority}] {t.subject[:30]}",
            callback_data=f"tkt_detail:{t.id}"
        )])
    rows.append([InlineKeyboardButton(text="➕ Новый тикет", callback_data="tkt_new")])

    await callback.message.edit_text(
        f"🎫 <b>Мои тикеты</b> ({len(tickets)})",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router.callback_query(F.data == "tkt_new")
async def cb_new_ticket_from_menu(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(CreateTicketFSM.choose_category)
    await callback.message.edit_text(
        "🎫 <b>Новый тикет</b>\n\nВыберите категорию:",
        reply_markup=_category_kb()
    )
    await callback.answer()


# ── Ticket detail ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("tkt_detail:"))
async def cb_ticket_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    ticket_id = int(callback.data.split(":")[1])
    r = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = r.scalar_one_or_none()
    if not ticket:
        await callback.answer("Тикет не найден", show_alert=True)
        return

    msgs_r = await session.execute(
        select(SupportTicketMessage)
        .where(SupportTicketMessage.ticket_id == ticket_id)
        .order_by(SupportTicketMessage.created_at.asc())
        .limit(5)
    )
    msgs = list(msgs_r.scalars().all())

    text = (
        f"🎫 <b>Тикет #{ticket.id}</b>\n"
        f"Статус: {ticket.status} | Приоритет: {PRIORITY_LABELS.get(ticket.priority, ticket.priority)}\n"
        f"{'⚠️ SLA нарушен!' if ticket.sla_breach else ''}\n\n"
        f"<b>Переписка:</b>\n"
    )
    for m in msgs[-3:]:
        sender = "Вы" if m.sender_type == "user" else "Поддержка"
        text += f"<b>{sender}:</b> {m.message[:200]}\n"

    is_closed = ticket.status in ("solved", "closed")
    await callback.message.edit_text(
        text,
        reply_markup=_ticket_detail_kb(ticket.id, is_support=False) if not is_closed else
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Мои тикеты", callback_data="tkt_list")]
        ])
    )
    await callback.answer()


# ── Reply to ticket ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("tkt_reply:"))
async def cb_reply_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    ticket_id = int(callback.data.split(":")[1])
    await state.set_state(ReplyTicketFSM.writing_reply)
    await state.update_data(ticket_id=ticket_id)
    await callback.message.edit_text(
        f"📩 Введите сообщение для тикета #{ticket_id}:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"tkt_detail:{ticket_id}")]
        ])
    )
    await callback.answer()


@router.message(ReplyTicketFSM.writing_reply)
async def fsm_ticket_reply(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    await state.clear()

    r = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = r.scalar_one_or_none()
    if not ticket or ticket.status in ("solved", "closed"):
        await message.answer("Тикет не найден или уже закрыт.")
        return

    msg = SupportTicketMessage(
        ticket_id=ticket_id,
        sender_type="user",
        sender_id=message.from_user.id,
        message=message.text or "",
    )
    ticket.status = "open"
    ticket.updated_at = datetime.now(timezone.utc)
    session.add(msg)
    await session.commit()
    await message.answer(
        f"✅ Сообщение добавлено в тикет #{ticket_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К тикету", callback_data=f"tkt_detail:{ticket_id}")]
        ])
    )


# ── Close ticket ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("tkt_close:"))
async def cb_ticket_close(callback: CallbackQuery, session: AsyncSession, **kwargs):
    ticket_id = int(callback.data.split(":")[1])
    r = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = r.scalar_one_or_none()
    if not ticket:
        await callback.answer("Не найден", show_alert=True)
        return

    ticket.status = "closed"
    ticket.resolved_at = datetime.now(timezone.utc)
    await session.commit()

    # Request CSAT
    await callback.message.edit_text(
        f"✅ Тикет #{ticket_id} закрыт.\n\n"
        f"⭐ Пожалуйста, оцените качество поддержки:",
        reply_markup=_csat_kb(ticket_id)
    )
    await callback.answer()


# ── CSAT rating ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("tkt_csat:"))
async def cb_csat(callback: CallbackQuery, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    ticket_id = int(parts[1])
    score = int(parts[2])

    r = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = r.scalar_one_or_none()
    if ticket:
        ticket.csat_score = score
        ticket.csat_requested_at = datetime.now(timezone.utc)
        await session.commit()

    score_text = {1: "👎 Плохо", 2: "😐 Нормально", 3: "👍 Отлично"}[score]
    await callback.message.edit_text(
        f"Спасибо за оценку: <b>{score_text}</b>\n\nМы постоянно улучшаем качество поддержки!"
    )
    await callback.answer("Оценка сохранена!")


# ── Resolve / Escalate (support staff) ────────────────────────────────────

@router.callback_query(F.data.startswith("tkt_resolve:"))
async def cb_resolve_ticket(callback: CallbackQuery, session: AsyncSession, **kwargs):
    ticket_id = int(callback.data.split(":")[1])
    r = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = r.scalar_one_or_none()
    if not ticket:
        await callback.answer("Не найден", show_alert=True)
        return

    ticket.status = "solved"
    ticket.resolved_at = datetime.now(timezone.utc)
    ticket.assigned_to = callback.from_user.id
    if not ticket.first_response_at:
        ticket.first_response_at = datetime.now(timezone.utc)
    await session.commit()
    await callback.answer("✅ Тикет отмечен как решённый", show_alert=True)


@router.callback_query(F.data.startswith("tkt_escalate:"))
async def cb_escalate_ticket(callback: CallbackQuery, session: AsyncSession, **kwargs):
    ticket_id = int(callback.data.split(":")[1])
    r = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = r.scalar_one_or_none()
    if not ticket:
        await callback.answer("Не найден", show_alert=True)
        return

    ticket.priority = "CRITICAL"
    ticket.escalated_at = datetime.now(timezone.utc)
    await session.commit()
    await callback.answer("🔺 Тикет эскалирован до CRITICAL", show_alert=True)
