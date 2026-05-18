from __future__ import annotations

"""Marketer bot — onboarding (language -> intro+rules -> accept) + dashboard"""
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer
from marketer_bot.constants.language_loader import get_texts, SUPPORTED_LANGUAGES
from marketer_bot.services.marketer_service import (
    get_or_create_marketer,
    get_total_users_across_bots,
    get_total_earned_across_bots,
    get_total_orders_across_bots,
    get_marketer_bots,
    get_tier,
    get_next_tier,
    update_marketer_tier,
    get_today_stats,
    get_30day_stats,
    TIERS,
)
from marketer_bot.services.analytics_service import get_daily_trend

logger = logging.getLogger(__name__)
router = Router(name="marketer_start")

LANG_FLAGS = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English", "zh": "🇨🇳 中文", "es": "🇪🇸 Español"}


def _lang_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="mlang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="mlang:en"),
        ],
        [
            InlineKeyboardButton(text="🇨🇳 中文", callback_data="mlang:zh"),
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="mlang:es"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _tier_progress_bar(current: int, next_tier_min, prev_tier_min: int) -> str:
    if next_tier_min is None:
        return "██████████ MAX"
    span = next_tier_min - prev_tier_min
    progress = min(current - prev_tier_min, span)
    filled = int((progress / span) * 10) if span > 0 else 10
    return "█" * filled + "░" * (10 - filled)


def _spark(values: list[float], width: int = 7) -> str:
    if not values or all(v == 0 for v in values):
        return "▁" * width
    mn, mx = min(values), max(values)
    blocks = "▁▂▃▄▅▆▇█"
    span = mx - mn if mx != mn else 1
    return "".join(blocks[min(int((v - mn) / span * 7), 7)] for v in values[-width:])


def _build_chart(trend: list[dict], t) -> str:
    """Строит текстовый мини-график за 7 дней: приглашения + пополнения."""
    if not trend:
        return ""

    regs = [float(d["registrations"]) for d in trend]
    topups = [d["topup"] for d in trend]

    spark_r = _spark(regs)
    spark_t = _spark(topups)

    total_r = sum(regs)
    total_t = sum(topups)

    lines = [
        f"<b>📊 {t.CHART_TITLE}:</b>",
        f"  👥 {spark_r}  {int(total_r)} {t.USERS_SHORT}",
        f"  💳 {spark_t}  ${total_t:.0f}",
        "",
    ]

    max_r = max(regs) if regs else 0
    for d in trend:
        day_label = d["date"].strftime("%d.%m")
        r = int(d["registrations"])
        tp = d["topup"]
        bar_len = int(r / max_r * 7) if max_r > 0 else 0
        bar = "█" * bar_len + "░" * (7 - bar_len)
        lines.append(f"  <code>{day_label}</code> {bar} 👥{r} 💳${tp:.0f}")

    return "\n".join(lines)


# ── /start ──────────────────────────────────────────

@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession, texts=None, **kwargs):
    marketer = await get_or_create_marketer(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        display_name=message.from_user.full_name,
    )

    if not getattr(marketer, "rules_accepted", False):
        t = texts or get_texts()
        await message.answer(t.CHOOSE_LANGUAGE, reply_markup=_lang_kb())
        return

    t = texts or get_texts(marketer.language)
    await show_dashboard(message, session, marketer, t)


# ── Language selection ──────────────────────────────

@router.callback_query(F.data.startswith("mlang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession, **kwargs):
    lang = callback.data.split(":")[1]
    if lang not in SUPPORTED_LANGUAGES:
        lang = "ru"

    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == callback.from_user.id)
    )
    marketer = result.scalar_one_or_none()
    if not marketer:
        marketer = await get_or_create_marketer(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            display_name=callback.from_user.full_name,
        )
    marketer.language = lang
    await session.commit()

    t = get_texts(lang)

    if not getattr(marketer, "rules_accepted", False):
        await _show_intro_and_rules(callback.message, t, edit=True)
    else:
        await show_dashboard(callback.message, session, marketer, t, edit=True)
    await callback.answer()


# ── Intro + Rules screen ───────────────────────────

async def _show_intro_and_rules(message, t, edit=False):
    text = f"{t.WELCOME_INTRO}\n\n{'━' * 30}\n\n{t.RULES_TEXT}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_ACCEPT_RULES, callback_data="marketer_accept_rules")],
        [InlineKeyboardButton(text=t.BTN_LANGUAGE, callback_data="marketer_language")],
    ])
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "marketer_accept_rules")
async def accept_rules(callback: CallbackQuery, session: AsyncSession, **kwargs):
    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == callback.from_user.id)
    )
    marketer = result.scalar_one_or_none()
    if not marketer:
        marketer = await get_or_create_marketer(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            display_name=callback.from_user.full_name,
        )
    marketer.rules_accepted = True
    await session.commit()

    t = get_texts(marketer.language)
    await show_dashboard(callback.message, session, marketer, t, edit=True)
    await callback.answer()


# ── Language menu (from dashboard) ──────────────────

@router.callback_query(F.data == "marketer_language")
async def language_menu(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    t = texts or get_texts()
    await callback.message.edit_text(t.CHOOSE_LANGUAGE, reply_markup=_lang_kb())
    await callback.answer()


# ── Dashboard ──────────────────────────────────────

@router.callback_query(F.data == "marketer_dashboard")
async def dashboard_callback(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == callback.from_user.id)
    )
    marketer = result.scalar_one_or_none()
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    await show_dashboard(callback.message, session, marketer, t, edit=True)
    await callback.answer()


async def show_dashboard(message, session, marketer, t, edit=False):
    total_users = await get_total_users_across_bots(session, marketer.id)
    total_earned = await get_total_earned_across_bots(session, marketer.id)
    total_orders = await get_total_orders_across_bots(session, marketer.id)
    bots = await get_marketer_bots(session, marketer.id)

    tier = await update_marketer_tier(session, marketer)
    next_tier = get_next_tier(total_users)

    today = await get_today_stats(session, marketer.id)
    stats30 = await get_30day_stats(session, marketer.id)
    trend = await get_daily_trend(session, marketer.id, days=7)

    progress = _tier_progress_bar(
        total_users,
        next_tier["min_users"] if next_tier else None,
        tier["min_users"],
    )

    if next_tier:
        left = next_tier["min_users"] - total_users
        tier_line = (
            f"{tier['icon']} {t.TIER_LEVEL}: <b>{tier['name']}</b> — {tier['display_percent']}%\n"
            f"   {progress}  {total_users}/{next_tier['min_users']}\n"
            f"   {t.TIER_NEXT.format(name=next_tier['name'], percent=next_tier['display_percent'], left=left)}"
        )
    else:
        tier_line = (
            f"{tier['icon']} {t.TIER_LEVEL}: <b>{tier['name']}</b> — {tier['display_percent']}%\n"
            f"   {progress}  {t.TIER_MAX}"
        )

    tiers_info = "  ".join(f"{x['icon']}{x['display_percent']}% ({x['min_users']}+)" for x in TIERS)
    chart = _build_chart(trend, t)

    text = (
        f"{t.DASHBOARD_TITLE}\n\n"
        f"{tier_line}\n\n"
        f"{t.TOTAL_USERS}: <b>{total_users}</b>\n"
        f"{t.BOTS_COUNT}: <b>{len(bots)}/10</b>\n"
        f"{t.ORDERS_COUNT}: <b>{total_orders}</b>\n"
        f"{t.TOTAL_EARNED}: <b>${float(total_earned):.2f}</b>\n\n"
        f"<b>{t.TODAY}:</b>\n"
        f"  {t.REGISTRATIONS}: {today['registrations']}\n"
        f"  {t.BUYERS}: {today.get('buyers_count', 0)} | {t.SALES}: {today.get('sales_count', 0)}\n"
        f"  {t.EARNED}: ${today['earned']:.2f}\n\n"
        f"{chart}\n\n"
        f"<b>{t.LAST_30D}:</b>\n"
        f"  {t.REG_SHORT}: {stats30['registrations']} | {t.SALES}: {stats30.get('sales_count', 0)}\n"
        f"  {t.BUYERS}: {stats30.get('buyers_count', 0)} | 💰 ${stats30['earned']:.2f}\n\n"
        f"<b>{t.TIERS_LABEL}:</b> {tiers_info}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_MY_BOTS, callback_data="mbot_list")],
        [InlineKeyboardButton(text=t.BTN_ANALYTICS, callback_data="marketer_analytics")],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_MENU, callback_data="ref_main")],
        [
            InlineKeyboardButton(text=t.BTN_WITHDRAW, callback_data="marketer_withdraw"),
            InlineKeyboardButton(text=t.BTN_LOGS, callback_data="marketer_logs"),
        ],
        [
            InlineKeyboardButton(text=t.BTN_LANGUAGE, callback_data="marketer_language"),
            InlineKeyboardButton(text=t.BTN_REFRESH, callback_data="marketer_dashboard"),
        ],
    ])
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
