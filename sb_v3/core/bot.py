"""
SBBot v3 — Multi-search Telegram bot
Enformion API (phone, address, background, email) + Usfull.pro (SSN, DL, Credit)
"""

import asyncio
import aiosqlite
import io
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, BotCommand,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

import database as db
from sb_engine import pool as enf_pool, SBResult
from usfull_engine import usfull_engine as uf_engine
from formatters import (
    fmt_enformion_result, fmt_phone_identify, fmt_phone_verify,
    fmt_address_verify, fmt_email_verify, fmt_emailrep,
    fmt_batch_summary, export_csv, export_txt, export_json,
)
from matching import match_fullz, deduplicate_persons, extract_all_phones_from_person
from payments import PaymentManager
from typing import Optional
from validators import parse_phone_list

# ── Payment manager ─────────────────────────────────────────────────
payment_mgr = PaymentManager()

# ── Logging ─────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("sbbot.bot")

# ── Config ──────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")
EMAILREP_KEY = os.getenv("EMAILREP_KEY", "")
BATCH_SIZE   = int(os.getenv("BATCH_SIZE", "5"))


# ── Keyboards ───────────────────────────────────────────────────────

def kb_main(is_admin: bool = False):
    rows = [
        [InlineKeyboardButton("🔍 Smart Search",  callback_data="sec_smart"),
         InlineKeyboardButton("📋 Batch Phones",  callback_data="sec_batch_phones")],
        [InlineKeyboardButton("📞 Phone",          callback_data="sec_phone"),
         InlineKeyboardButton("🏠 Address",        callback_data="sec_addr")],
        [InlineKeyboardButton("🔍 Background",     callback_data="sec_bg"),
         InlineKeyboardButton("📧 Email",          callback_data="sec_email")],
        [InlineKeyboardButton("🆔 SSN/DOB",        callback_data="sec_ssn"),
         InlineKeyboardButton("🪪 Driver License", callback_data="sec_dl")],
        [InlineKeyboardButton("💳 Credit Report",  callback_data="sec_cr"),
         InlineKeyboardButton("👤 Профиль",        callback_data="profile")],
        [InlineKeyboardButton("📜 История",        callback_data="history"),
         InlineKeyboardButton("💰 Баланс/Пополнить", callback_data="balance_menu")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="adm_main")])
    return InlineKeyboardMarkup(rows)


def kb_phone():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Reverse Lookup",  callback_data="ph_lookup"),
         InlineKeyboardButton("📋 Batch Lookup",    callback_data="ph_batch")],
        [InlineKeyboardButton("📡 Identify Type",   callback_data="ph_identify"),
         InlineKeyboardButton("✅ Verify Active",   callback_data="ph_verify")],
        [InlineKeyboardButton("◀️ Назад",           callback_data="main")],
    ])


def kb_addr():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Reverse Lookup",   callback_data="ad_lookup"),
         InlineKeyboardButton("📋 Batch Lookup",     callback_data="ad_batch")],
        [InlineKeyboardButton("🔢 Number+Address",   callback_data="ad_numaddr"),
         InlineKeyboardButton("✅ Verify Address",   callback_data="ad_verify")],
        [InlineKeyboardButton("◀️ Назад",            callback_data="main")],
    ])


def kb_bg():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 By Name",          callback_data="bg_name"),
         InlineKeyboardButton("📋 Batch Names",      callback_data="bg_batch")],
        [InlineKeyboardButton("◀️ Назад",            callback_data="main")],
    ])


def kb_email():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Email Lookup",     callback_data="em_lookup"),
         InlineKeyboardButton("✅ Verify Email",     callback_data="em_verify")],
        [InlineKeyboardButton("🌐 EmailRep Check",   callback_data="em_rep"),
         InlineKeyboardButton("📋 Batch Emails",      callback_data="em_batch")],
        [InlineKeyboardButton("◀️ Назад",            callback_data="main")],
    ])


def kb_back(target="main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=target)]
    ])


def kb_export(batch_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 CSV",   callback_data=f"exp_csv_{batch_key}"),
         InlineKeyboardButton("📄 TXT",   callback_data=f"exp_txt_{batch_key}"),
         InlineKeyboardButton("🗂 JSON",  callback_data=f"exp_json_{batch_key}")],
    ])


def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Пользователи",     callback_data="adm_users"),
         InlineKeyboardButton("🔎 Найти юзера",      callback_data="adm_user_search")],
        [InlineKeyboardButton("💳 Добавить баланс",  callback_data="adm_balance"),
         InlineKeyboardButton("🛡 Забанить",       callback_data="adm_ban_user")],
        [InlineKeyboardButton("🔧 ENF Аккаунты",     callback_data="adm_enf"),
         InlineKeyboardButton("🌐 Usfull Аккаунты",  callback_data="adm_uf")],
        [InlineKeyboardButton("➕ Добавить ENF",     callback_data="adm_add_enf"),
         InlineKeyboardButton("🔄 Добавить Usfull",   callback_data="adm_add_uf")],
        [InlineKeyboardButton("💰 Наценка",          callback_data="adm_markup"),
         InlineKeyboardButton("📊 Статистика",       callback_data="adm_stats")],
        [InlineKeyboardButton("📢 Рассылка",         callback_data="adm_broadcast"),
         InlineKeyboardButton("⚙️ Цены",             callback_data="adm_prices")],
        [InlineKeyboardButton("📋 Логи админа",      callback_data="adm_logs"),
         InlineKeyboardButton("🔗 Webhook логи",      callback_data="adm_webhook_logs")],
        [InlineKeyboardButton("🔢 Лимиты",           callback_data="adm_limits"),
         InlineKeyboardButton("👤 Лимит юзера",      callback_data="adm_user_limit")],
        [InlineKeyboardButton("💰 Доход",            callback_data="adm_revenue"),
         InlineKeyboardButton("🏆 Топ юзеров",       callback_data="adm_top_users")],
        [InlineKeyboardButton("🔑 Доступы",           callback_data="adm_access"),
         InlineKeyboardButton("⚡ Управление",       callback_data="adm_control")],
        [InlineKeyboardButton("◀️ Назад",            callback_data="main")],
    ])


def kb_usfull_ssn():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 By Name/DOB",   callback_data="uf_ssn_name"),
         InlineKeyboardButton("🔎 By SSN",        callback_data="uf_ssn_direct")],
        [InlineKeyboardButton("📋 Batch (до 20)", callback_data="sec_ssn_batch")],
        [InlineKeyboardButton("◀️ Назад",         callback_data="main")],
    ])


def kb_usfull_dl():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪪 DL Lookup",     callback_data="uf_dl")],
        [InlineKeyboardButton("◀️ Назад",         callback_data="main")],
    ])


def kb_usfull_cr():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Credit Report",  callback_data="uf_cr")],
        [InlineKeyboardButton("◀️ Назад",         callback_data="main")],
    ])


def kb_usfull_cs():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад",         callback_data="main")],
    ])


def kb_balance_menu(providers: list) -> InlineKeyboardMarkup:
    rows = []
    if "cryptobot" in providers:
        rows.append([InlineKeyboardButton("🤖 CryptoBot (Telegram)", callback_data="pay_cryptobot")])
    if "heleket" in providers:
        rows.append([InlineKeyboardButton("🔐 Heleket (Crypto)",     callback_data="pay_heleket")])
    if "btcpay" in providers:
        rows.append([InlineKeyboardButton("₿ BTCPay Server",         callback_data="pay_btcpay")])
    if not rows:
        rows.append([InlineKeyboardButton("ℹ️ Нет способов оплаты", callback_data="main")])
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(rows)


def kb_upsell(search_type: str) -> InlineKeyboardMarkup:
    suggestions = {
        "phone":         [("🏠 Address Lookup", "sec_addr"), ("🔍 Background", "sec_bg")],
        "phone_identify":[("🔎 Full Reverse",   "ph_lookup")],
        "address":       [("🔍 Background",     "sec_bg"),   ("📞 Phone Lookup", "sec_phone")],
        "background":    [("🆔 SSN/DOB Search", "sec_ssn"),  ("🪪 Driver License", "sec_dl")],
        "ssn_dob":       [("🪪 Driver License", "sec_dl"),   ("💳 Credit Report", "sec_cr")],
        "driver_license":[("💳 Credit Report",  "sec_cr"),   ("📞 Phone Lookup", "sec_phone")],
        "credit_report": [("🪪 Driver License", "sec_dl"),   ("📞 Phone Lookup", "sec_phone")],
        "email":         [("🔍 Background",     "sec_bg")],
    }
    btns = suggestions.get(search_type, [])
    rows = []
    if btns:
        rows.append([InlineKeyboardButton(t, callback_data=c) for t, c in btns])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main")])
    return InlineKeyboardMarkup(rows)


def kb_deposit_amounts(provider: str, currency: str = "USDT") -> InlineKeyboardMarkup:
    from payments import DEPOSIT_AMOUNTS
    row1, row2 = [], []
    for i, amt in enumerate(DEPOSIT_AMOUNTS):
        btn = InlineKeyboardButton(f"${amt}", callback_data=f"dep_{provider}_{amt}_{currency}")
        if i < 3:
            row1.append(btn)
        else:
            row2.append(btn)
    return InlineKeyboardMarkup([row1, row2, [InlineKeyboardButton("◀️ Назад", callback_data="balance_menu")]])


def kb_currencies(provider: str) -> InlineKeyboardMarkup:
    from payments import CRYPTOBOT_ASSETS, HELEKET_CURRENCIES
    curs = CRYPTOBOT_ASSETS if provider == "cryptobot" else HELEKET_CURRENCIES
    rows = []
    row = []
    for i, cur in enumerate(curs[:12]):
        row.append(InlineKeyboardButton(cur, callback_data=f"cur_{provider}_{cur}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data="balance_menu")])
    return InlineKeyboardMarkup(rows)


# ── Usfull result formatters ───────────────────────────────────────

def fmt_usfull_ssn(result: dict) -> str:
    if not result.get("ok"):
        return f"❌ *Ошибка:* {result.get('error', 'Unknown error')}"
    records = result.get("results", [])
    count = result.get("count", len(records))
    if not records:
        return "💭 *Нет результатов*"
    lines = [f"✅ *Найдено {count} записей*\n"]
    for i, rec in enumerate(records[:10], 1):
        lines.append(f"*── Запись {i} ──*")
        fn = rec.get("firstname", "") or ""
        mn = rec.get("middlename", "") or ""
        ln = rec.get("lastname", "") or ""
        suff = rec.get("name_suff", "") or ""
        full = " ".join(p for p in [fn, mn, ln, suff] if p and p != "NULL")
        if full:
            lines.append(f"👤 *Имя:* {full}")
        dob = rec.get("dob", "") or ""
        if dob and dob != "NULL":
            if len(dob) == 8:
                dob = f"{dob[4:6]}/{dob[6:8]}/{dob[:4]}"
            lines.append(f"🎂 *DOB:* {dob}")
        ssn = str(rec.get("ssn", "") or "")
        if ssn and ssn != "NULL" and len(ssn) >= 9:
            ssn = f"{ssn[:3]}-{ssn[3:5]}-{ssn[5:]}"
            lines.append(f"🆔 *SSN:* `{ssn}`")
        addr_parts = []
        for fld in ["address", "city", "st", "zip"]:
            v = rec.get(fld, "") or ""
            if v and v != "NULL":
                addr_parts.append(v)
        if addr_parts:
            lines.append(f"🏠 *Адрес:* {', '.join(addr_parts)}")
        phone = rec.get("phone", "") or ""
        if phone and phone != "NULL":
            lines.append(f"📞 *Тел:* {phone}")
        lines.append("")
    return "\n".join(lines)


def fmt_usfull_dl(result: dict) -> str:
    if not result.get("ok"):
        return f"❌ *Ошибка:* {result.get('error', 'Unknown error')}"
    data = result.get("data", {})
    if not data:
        return "💭 *Нет результатов*"
    lines = ["🪪 *Driver License Found*\n"]
    for k, v in data.items():
        if v and str(v) != "NULL":
            lines.append(f"*{k.replace('_',' ').title()}:* {v}")
    return "\n".join(lines)


def fmt_usfull_cr(result: dict) -> str:
    if not result.get("ok"):
        return f"❌ *Ошибка:* {result.get('error', 'Unknown error')}"
    data = result.get("data", {})
    if not data:
        return "💭 *Нет данных*"
    lines = ["💳 *Credit Report*\n"]
    for k, v in data.items():
        if v and str(v) != "NULL":
            lines.append(f"*{k.replace('_',' ').title()}:* {v}")
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────── ─────────────────────────────────────────────────────────

async def ensure_user(update: Update) -> dict:
    u = update.effective_user
    return await db.upsert_user(u.id, u.username or "", u.full_name or "")


async def is_admin(user_id: int) -> bool:
    user = await db.get_user(user_id)
    return bool(user and user.get("is_admin"))


async def get_price(key: str) -> float:
    val = await db.get_setting(key)
    try:
        return float(val)
    except Exception:
        return 0.0


async def user_price(user_id: int, base_key: str) -> float:
    base = await get_price(base_key)
    user = await db.get_user(user_id)
    markup = user.get("markup_pct", 0.0) if user else 0.0
    return round(base * (1 + markup / 100), 4)


async def check_daily_limit_or_block(uid: int, chat_id: int, price: float, context) -> tuple[bool, int, int]:
    """
    Returns (allowed, remaining, limit).
    If over limit → sends message to user.
    If wallet override allowed → allows (returns True).
    """
    allowed, remaining, limit = await db.check_subscription_limit(uid)
    allow_pay = await db.get_setting("allow_pay_over_limit")
    allow_pay = (allow_pay not in (None, "0", "false", "False"))
    over_limit = (remaining == 0)

    if over_limit and not allow_pay:
        reset_in = await db.get_daily_limit_reset_seconds()
        hours = reset_in // 3600
        mins = (reset_in % 3600) // 60
        await context.bot.send_message(
            chat_id,
            f"⛔ *Дневной лимит исчерпан*\n\n"
            f"📊 Лимит: *{limit}* запросов/день\n"
            f"⏰ Сброс через: *{hours}ч {mins}мин*",
            parse_mode=ParseMode.MARKDOWN
        )
        return False, remaining, limit

    if remaining > 0 and remaining <= 3:
        await context.bot.send_message(
            chat_id,
            f"⚠️ Осталось *{remaining}* из *{limit}* запросов на сегодня.",
            parse_mode=ParseMode.MARKDOWN
        )

    return True, remaining, limit


async def check_balance(user_id: int, price: float) -> bool:
    user = await db.get_user(user_id)
    return bool(user and user.get("balance", 0) >= price)


async def send_main(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    user = await ensure_user(update)
    if user.get("is_banned"):
        await update.effective_message.reply_text("⛔ Вы заблокированы.")
        return
    active = enf_pool.active_count()
    total  = len(enf_pool.accounts)
    text = (
        f"🔍 *LookupBot*\n\n"
        f"👤 {update.effective_user.full_name}\n"
        f"💰 Баланс: *${user.get('balance', 0):.2f}*\n"
        f"📊 Поисков: {user.get('searches', 0)}\n"
        f"🔧 ENF аккаунты: {active}/{total} активных\n\n"
        f"Выберите раздел:"
    )
    markup = kb_main(is_admin=bool(user.get("is_admin")))
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.effective_message.reply_text(
            text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN
        )


# ── Alert callback ─────────────────────────────────────────────────

_app_ref: Application = None


async def _alert_admin(email: str, reason: str):
    admin_chat_id = await db.get_setting("admin_chat_id")
    if not admin_chat_id or not _app_ref:
        return
    try:
        cid = int(admin_chat_id)
    except Exception:
        return

    if reason == "blocked":
        text = f"⛔ *ENF Аккаунт заблокирован!*\n\n📧 `{email}`"
    elif reason == "no_balance":
        text = f"❌ *ENF Аккаунт без баланса!*\n\n📧 `{email}`"
    elif reason.startswith("low_balance:"):
        pct = reason.split(":")[1]
        text = f"⚠️ *Низкий баланс ENF аккаунта!*\n\n📧 `{email}`\n📊 Осталось: *{pct}*"
    else:
        text = f"⚠️ ENF аккаунт `{email}`: `{reason}`"

    try:
        await _app_ref.bot.send_message(cid, text, parse_mode=ParseMode.MARKDOWN)
    except TelegramError as e:
        logger.error(f"[Alert] Failed to send alert: {e}")


async def _alert_usfull(account, reason: str):
    """Alert callback for Usfull account status changes."""
    admin_chat_id = await db.get_setting("admin_chat_id")
    if not admin_chat_id or not _app_ref:
        return
    try:
        cid = int(admin_chat_id)
    except Exception:
        return

    username = getattr(account, "username", str(account))

    if reason == "blocked":
        text = f"⛔ *Usfull аккаунт заблокирован!*\n👤 `{username}`"
    elif reason == "no_balance":
        text = f"❌ *Usfull аккаунт без баланса!*\n👤 `{username}`"
    elif reason == "low_balance":
        pct = getattr(account, "balance_pct", 0)
        text = f"⚠️ *Низкий баланс Usfull аккаунта!*\n👤 `{username}`\n📊 Осталось: *{pct:.1f}%*"
    else:
        text = f"⚠️ Usfull аккаунт `{username}`: `{reason}`"

    try:
        await _app_ref.bot.send_message(cid, text, parse_mode=ParseMode.MARKDOWN)
    except TelegramError as e:
        logger.error(f"[Alert] Usfull alert failed: {e}")


# ── Batch processor (Enformion-based) ───────────────────────────────

# Retryable error codes — these benefit from a retry on a different account
_RETRYABLE_ERRORS = {"TIMEOUT", "RETRIES_EXHAUSTED", "CIRCUIT_OPEN", "POOL_SUSPENDED"}
_MAX_RETRIES = 2  # max total passes (1 initial + 1 retry)


async def process_batch(
    items: list,
    search_type: str,
    parse_fn,
    price_key: str,
    user_id: int,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    batch_key: str,
) -> list:
    # Dedup items preserving order
    seen = set()
    unique_items = []
    for item in items:
        key = item.strip().lower()
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    items = unique_items

    total = len(items)
    if total == 0:
        return [{"ok": False, "error": "No valid items", "query": {}, "people": [], "parsed": {}}]

    price = await user_price(user_id, price_key)

    # Subscription limit check — per-user daily limit > plan limit > default
    allowed, remaining, limit = await db.check_subscription_limit(user_id)
    over_limit = (remaining == 0)
    allow_pay = await db.get_setting("allow_pay_over_limit")
    allow_pay = (allow_pay not in (None, "0", "false", "False"))

    # Cap batch to available balance
    max_items = 0
    try:
        user = await db.get_user(user_id)
        balance = user.get("balance", 0) if user else 0
        if price > 0:
            max_items = int(balance / price)
    except Exception:
        pass
    if max_items > 0 and total > max_items:
        context.user_data["max_items"] = max_items
        items = items[:max_items]
        total = len(items)

    # Block if over limit AND wallet override disabled
    if over_limit and not allow_pay:
        reset_in = await db.get_daily_limit_reset_seconds()
        hours = reset_in // 3600
        mins = (reset_in % 3600) // 60
        await context.bot.send_message(
            chat_id,
            f"⛔ *Дневной лимит исчерпан*\n\n"
            f"📊 Лимит: *{limit}* запросов/день\n"
            f"⏰ Сброс через: *{hours}ч {mins}мин*\n\n"
            f"💰 Пополните баланс для разовых покупок сверх лимита.",
            parse_mode=ParseMode.MARKDOWN
        )
        return [{"ok": False, "error": "DAILY_LIMIT_EXCEEDED"}]

    # Warn if approaching limit
    if remaining > 0 and remaining <= 3:
        await context.bot.send_message(
            chat_id,
            f"⚠️ Осталось *{remaining}* из *{limit}* запросов на сегодня.\n"
            f"После исчерпания лимита поиск будет возможен за счёт баланса.",
            parse_mode=ParseMode.MARKDOWN
        )

    prog_msg = await context.bot.send_message(
        chat_id,
        f"⏳ Обработка *{total}* запросов...\n`[{'░' * 20}]` 0/{total}",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Results dict: item_index -> result
    # We'll process in passes, replacing retryable failures
    results: list = [None] * len(items)
    retryable_indices = set(range(len(items)))  # all indices initially retryable
    pass_num = 0

    while retryable_indices and pass_num < _MAX_RETRIES:
        pass_num += 1
        pass_label = f"[pass {pass_num}/{_MAX_RETRIES}]"

        sem = asyncio.Semaphore(BATCH_SIZE)
        done_in_pass = 0
        pass_total = len(retryable_indices)
        lock = asyncio.Lock()

        async def process_one(idx: int, item: str) -> tuple:
            nonlocal done_in_pass
            async with sem:
                # Check balance (skip if already deducted in a previous pass)
                if results[idx] is None or results[idx].get("error") not in _RETRYABLE_ERRORS:
                    if not await check_balance(user_id, price):
                        return idx, {
                            "ok": False, "query": {"input": item},
                            "error": "INSUFFICIENT_BALANCE",
                            "type": search_type, "people": [], "parsed": {},
                        }

                params = parse_fn(item)
                result = await enf_pool.search(search_type, params)
                rd = result.to_dict()

                if result.ok and not (result.parsed.get("message") == "No results found"):
                    deducted = await db.deduct_balance(
                        user_id, price, f"{search_type}:{item}"
                    )
                    if deducted:
                        await db.save_search(
                            user_id, search_type, item,
                            json.dumps(rd), price, result.tokens_cost
                        )
                        await db.increment_subscription_usage(user_id)
                        if result.account:
                            await db.increment_sb_searches(result.account)
                        # Create guarantee
                        searches = await db.get_user_searches(user_id, limit=1)
                        if searches:
                            try:
                                sid = searches[0].get("id", 0) or 0
                                await db.create_guarantee(user_id, sid, search_type, item[:100], price, days=8)
                            except Exception:
                                pass
                        # Low balance alert
                        new_user = await db.get_user(user_id)
                        new_bal = new_user.get("balance", 0) if new_user else 0
                        min_dep = float(await db.get_setting("min_deposit") or "5")
                        if new_bal > 0 and new_bal < min_dep:
                            await db.create_user_alert(user_id, "low_balance",
                                f"⚠️ Низкий баланс: ${new_bal:.2f}. Пополните для продолжения.")

                async with lock:
                    done_in_pass += 1
                    if done_in_pass % max(1, pass_total // 10) == 0 or done_in_pass == pass_total:
                        filled = int(done_in_pass / pass_total * 20)
                        bar = "█" * filled + "░" * (20 - filled)
                        try:
                            await prog_msg.edit_text(
                                f"⏳ Обработка *{total}* запросов... {pass_label}\n`[{bar}]` {done_in_pass}/{pass_total}",
                                parse_mode=ParseMode.MARKDOWN,
                            )
                        except Exception:
                            pass
                return idx, rd

        # Build tasks only for retryable indices
        tasks = [process_one(idx, items[idx]) for idx in sorted(retryable_indices)]
        pass_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update results and find next retryable set
        next_retryable = set()
        for r in pass_results:
            if isinstance(r, Exception):
                idx, rd = -1, {"ok": False, "error": str(r),
                               "query": {}, "type": search_type, "people": [], "parsed": {}}
            else:
                idx, rd = r

            if idx >= 0:
                results[idx] = rd
                # Mark for retry if failed with a retryable error
                if not rd.get("ok") and rd.get("error") in _RETRYABLE_ERRORS:
                    next_retryable.add(idx)

        retryable_indices = next_retryable

        if retryable_indices:
            logger.info(
                f"[Batch] {pass_label} {len(retryable_indices)} retryable items, "
                f"retrying on fresh accounts..."
            )

    # Handle remaining retryable (exhausted retries)
    for idx in retryable_indices:
        if results[idx] is None or results[idx].get("error") in _RETRYABLE_ERRORS:
            results[idx] = {
                "ok": False, "error": "RETRIES_EXHAUSTED",
                "query": {"input": items[idx]},
                "type": search_type, "people": [], "parsed": {},
            }

    # Convert None to empty results (shouldn't happen, but safety net)
    results = [
        r if r is not None
        else {"ok": False, "error": "PROCESSED_NONE", "query": {},
              "type": search_type, "people": [], "parsed": {}}
        for r in results
    ]

    context.bot_data.setdefault("batch_results", {})[batch_key] = results

    try:
        await prog_msg.delete()
    except Exception:
        pass

    return results


# ── Person list builder ──────────────────────────────────────────────

def _build_person_list(results: list) -> list:
    """
    Extract all persons from batch results into a flat numbered list.
    Each person gets _idx, _query, _stype for later callbacks.
    """
    persons = []
    for r in results:
        if not r.get("ok") or not r.get("people"):
            continue
        query_str = " ".join(str(v) for v in r.get("query", {}).values() if v) or "?"
        for p in r["people"]:
            entry = dict(p)
            entry["_idx"] = len(persons)
            entry["_query"] = query_str
            entry["_stype"] = r.get("type", "unknown")
            persons.append(entry)
    return persons


def _fmt_person_card(p: dict) -> str:
    """Format a single person card for display."""
    L = []
    name = p.get("name", "Unknown") or "Unknown"
    age = p.get("age", 0)
    L.append(f"*{name}*")
    if age:
        L.append(f"Возраст: {age}")

    # Phones
    if p.get("phone"):
        L.append(f"📞 {p['phone']}")

    # Address / Location
    addr = p.get("address", "")
    loc = p.get("location", "") or p.get("addresses", [None])
    if isinstance(loc, list) and loc:
        loc = loc[0]
    for label, val in [("🏠 Address", addr), ("📍 Location", loc)]:
        if val and val != "Unknown":
            L.append(f"{label}: {val}")

    # Emails
    if p.get("em"):
        L.append(f"📧 Email: {p['em']}")
    if p.get("emails"):
        L.append(f"📧 Emails: {', '.join(p['emails'][:3])}")

    # Akas/Aliases
    if p.get("ma"):
        L.append(f"👤 Alias: {', '.join(p['ma'][:5])}")

    # Relatives
    rel = p.get("relatives", "") or ""
    if rel:
        L.append(f"👨‍👩‍👧 Relatives: {rel[:150]}")

    return "\n".join(L)


# ── Send results (multi-person selection) ────────────────────────────

async def send_results(update, context, results, stype, batch_key, fmt_fn,
                       chat_id=None, fullz_input: str = None):
    """Send batch results with numbered person selection."""
    if chat_id is None:
        if update.message and update.message.chat:
            chat_id = update.message.chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id
        else:
            logger.error("[send_results] Cannot determine chat_id")
            return

    # Handle no-results
    no_results = []
    for r in results:
        if not r.get("ok"):
            err = r.get("error", "Unknown error")
            query_str = " ".join(str(v) for v in r.get("query", {}).values() if v) or "?"
            no_results.append(f"❌ `{query_str}` → {err}")
        elif r.get("parsed", {}).get("message") == "No results found":
            query_str = " ".join(str(v) for v in r.get("query", {}).values() if v) or "?"
            no_results.append(f"🔍 `{query_str}` → не найдено")
    if no_results:
        await context.bot.send_message(
            chat_id,
            "*Нет результатов:*\n" + "\n".join(no_results[:10]),
            parse_mode=ParseMode.MARKDOWN
        )

    persons = deduplicate_persons(_build_person_list(results))
    if not persons:
        if not no_results:
            await context.bot.send_message(
                chat_id, "🔍 Результатов не найдено.",
                parse_mode=ParseMode.MARKDOWN
            )
        return

    # Apply address matching if we have fullz input (name-based searches)
    if fullz_input:
        persons = match_fullz(persons, fullz_input)

    # Store persons for callbacks
    context.bot_data.setdefault("person_cache", {})[batch_key] = persons

    # Build summary
    icon = {"phone": "📞", "address": "🏠", "background": "🔍",
            "email": "📧", "phone_identify": "📡", "phone_verify": "✅"}.get(stype, "🔍")

    L = [f"{icon} *Найдено {len(persons)} персон*\n"]
    for i, p in enumerate(persons[:15], 1):
        conf = p.get("_confidence_icon", "")
        line = f"  [{i}]"
        if conf:
            line += f" {conf}"
        line += f" {p.get('name', 'Unknown')}"
        if p.get("age"):
            line += f" ({p['age']})"
        score = p.get("_score", 0)
        if score:
            line += f" [Score: {score}]"
        loc = p.get("location", "") or p.get("address", "") or p.get("_matched_addr", {}).get("raw", "")
        if loc:
            line += f" — {loc[:30]}"
        L.append(line)
    if len(persons) > 15:
        L.append(f"  _...ещё {len(persons)-15}_")

    L.append("\nВыберите персону:")

    # Selection buttons
    sel_rows = []
    for i, p in enumerate(persons[:10]):  # max 10 buttons
        label = f"#{i+1}"
        conf = p.get("_confidence_icon", "")
        if conf:
            label += f" {conf}"
        label += f" {p.get('name', 'Unknown')}"
        if p.get("age"):
            label += f" ({p['age']})"
        sel_rows.append([InlineKeyboardButton(label, callback_data=f"person:{batch_key}:{p['_idx']}")])
    # Add chain_all button when 2+ persons
    if len(persons) >= 2:
        sel_rows.insert(-2, [InlineKeyboardButton(
            f"⚡ Chain ALL ({min(len(persons), 5)})",
            callback_data=f"chain_all:{batch_key}"
        )])
    sel_rows.append([InlineKeyboardButton("📁 Экспорт (CSV/TXT)", callback_data=f"exp_csv_{batch_key}"),
                     InlineKeyboardButton("🗂 JSON", callback_data=f"exp_json_{batch_key}")])
    sel_rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main")])

    await context.bot.send_message(
        chat_id, "\n".join(L),
        reply_markup=InlineKeyboardMarkup(sel_rows),
        parse_mode=ParseMode.MARKDOWN
    )


def kb_chain_actions(idx: int, batch_key: str) -> InlineKeyboardMarkup:
    """Chain actions for a selected person: SSN → CR → DL"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆔 SSN/DOB",  callback_data=f"chain_ssn:{batch_key}:{idx}")],
        [InlineKeyboardButton("💳 Credit Report", callback_data=f"chain_cr:{batch_key}:{idx}")],
        [InlineKeyboardButton("🪪 Driver License", callback_data=f"chain_dl:{batch_key}:{idx}")],
        [InlineKeyboardButton("◀️ Назад к списку",  callback_data=f"pback:{batch_key}")],
        [InlineKeyboardButton("🏠 Главное меню",    callback_data="main")],
    ])


# ── Commands ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ensure_user(update)
    await send_main(update, context)


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    await update.message.reply_text(
        "🛠 *Панель администратора*",
        reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN
    )


async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    await update.message.reply_text(
        f"💰 Ваш баланс: *${user.get('balance', 0):.2f}*",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_enfstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return

    # ENF Pool
    report = enf_pool.status_report()
    lines = [f"🔧 *ENF Account Pool* ({len(report)})"]
    if report:
        STATUS_ICON = {
            "active":      "✅",
            "low_balance": "⚠️",
            "no_balance":  "❌",
            "blocked":     "⛔",
            "failed":      "🔴",
            "unknown":     "❓",
        }
        for a in report:
            icon = STATUS_ICON.get(a["status"], "❓")
            bal_str = f"{a['balance']:.0f}$T ({a['pct']}%)" if a["init_balance"] else f"{a['balance']:.0f}$T"
            logged = "🟢" if a["logged_in"] else "🔴"
            lines.append(
                f"{icon}{logged} `{a['email']}`\n"
                f"   💰 {bal_str} | 🔍 {a['searches']}\n"
                f"   🔗 {a['proxy']}"
            )
    else:
        lines.append("❌ Нет загруженных аккаунтов")

    # CB state
    cb_state = enf_pool._cb.state
    cb_icon = "🟢" if cb_state == "closed" else ("🟡" if cb_state == "half_open" else "🔴")
    error_rate = sum(enf_pool._error_window) / max(1, len(enf_pool._error_window))
    lines.append(f"\n{cb_icon} CircuitBreaker: *{cb_state.upper()}* | Error rate: *{error_rate:.0%}*")

    lines.append("\n" + "─" * 20)
    lines.append("\n🔷 *Usfull Account Pool*")

    # Usfull Pool
    uf_status = uf_engine.get_pool_status()
    uf_accounts = [s for s in uf_status if "circuit_breaker" not in s]
    if uf_accounts:
        for a in uf_accounts:
            icon = STATUS_ICON.get(a.get("status", "unknown"), "❓")
            health = a.get("health_score", 0)
            h_icon = "🟢" if health > 70 else ("🟡" if health > 40 else "🔴")
            lines.append(
                f"{icon}{h_icon} `{a['username']}`\n"
                f"   💰 ${a['balance']:.2f} ({a['balance_pct']}%) | 🔍 {a['requests_done']}"
            )
    else:
        lines.append("❌ Нет загруженных аккаунтов")

    # Usfull CB
    uf_cb_entry = next((s for s in uf_status if "circuit_breaker" in s), {})
    uf_cb_state = uf_cb_entry.get("circuit_breaker", "closed")
    uf_cb_icon = "🟢" if uf_cb_state == "closed" else ("🟡" if uf_cb_state == "half_open" else "🔴")
    uf_cb_rate = uf_cb_entry.get("cb_failure_rate", 0)
    lines.append(f"\n{uf_cb_icon} CircuitBreaker: *{uf_cb_state.upper()}* | Failure rate: *{uf_cb_rate:.1f}%*")

    text = "\n".join(lines)
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


async def cmd_addaccount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: `/addaccount email password [proxy]`\n\n"
            "Пример:\n`/addaccount user@mail.com pass123 http://user:pass@proxy:8080`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    email, password = args[0], args[1]
    proxy = args[2] if len(args) > 2 else ""
    await _add_single_account(update, email, password, proxy)


async def _add_single_account(update, email: str, password: str, proxy: str):
    await db.upsert_sb_account(email, password, proxy)
    accounts = await db.get_sb_accounts()
    enf_pool.load(accounts)
    new_acc = next((a for a in enf_pool.accounts if a.email == email), None)
    if new_acc:
        msg = await update.effective_message.reply_text(f"⏳ Проверка `{email}`...", parse_mode=ParseMode.MARKDOWN)
        ok = await enf_pool.login(new_acc)
        if ok:
            await db.update_sb_account_status(
                email, new_acc.status, new_acc.balance, new_acc.init_balance
            )
        status = "✅ OK" if ok else "❌ Ошибка"
        await msg.edit_text(
            f"{status}\n📧 `{email}`\n🔗 Прокси: `{proxy or 'нет'}`\n"
            f"💰 Баланс: {new_acc.balance:.0f}$T",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.effective_message.reply_text(f"✅ Добавлен: `{email}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_loadaccounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "📂 *Загрузка аккаунтов из файла*\n\n"
        "Отправьте `.txt` файл в формате:\n"
        "```\n"
        "email:password:proxy\n"
        "email:password\n"
        "```",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data["admin_state"] = "awaiting_accounts_file"


async def cmd_reloadpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    msg = await update.message.reply_text("⏳ Перезагрузка пула аккаунтов...")
    accounts = await db.get_sb_accounts()
    enf_pool.load(accounts)
    stats = await enf_pool.login_all()
    for acc in enf_pool.accounts:
        await db.update_sb_account_status(
            acc.email, acc.status, acc.balance, acc.init_balance
        )
    await msg.edit_text(
        f"✅ Пул перезагружен\n\n"
        f"✅ Активных: {stats['ok']}/{stats['total']}\n"
        f"❌ Ошибок: {stats['failed']}",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await db.get_all_users()
    admins = [u for u in users if u.get("is_admin")]
    caller_id = update.effective_user.id
    if admins and not any(u["user_id"] == caller_id for u in admins):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    args = context.args
    target_id = int(args[0]) if args else caller_id
    await db.set_admin(target_id, True)
    await update.message.reply_text(
        f"✅ Пользователь `{target_id}` теперь администратор.",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_setadminchat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    chat_id = str(update.effective_chat.id)
    await db.set_setting("admin_chat_id", chat_id)
    await update.message.reply_text(
        f"✅ Этот чат (`{chat_id}`) установлен для алертов.",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /ban USER_ID")
        return
    target_id = int(args[0])
    await db.set_banned(target_id, True)
    await update.message.reply_text(f"🚫 Пользователь `{target_id}` заблокирован.", parse_mode=ParseMode.MARKDOWN)


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /unban USER_ID")
        return
    target_id = int(args[0])
    await db.set_banned(target_id, False)
    await update.message.reply_text(f"✅ Пользователь `{target_id}` разблокирован.", parse_mode=ParseMode.MARKDOWN)


async def cmd_setufkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    args = context.args
    if not args:
        current = await db.get_setting("usfull_api_key")
        masked = (current[:6] + "..." + current[-4:]) if current and len(current) > 10 else (current or "не установлен")
        await update.message.reply_text(
            f"🔑 *Usfull API Key*\n\nТекущий: `{masked}`\n\nИспользование: `/setufkey YOUR_API_KEY`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    api_key = args[0]
    await db.set_setting("usfull_api_key", api_key)
    uf_engine.api_key = api_key
    await update.message.reply_text(
        f"✅ *Usfull API Key установлен*\n\nKey: `{api_key[:6]}...{api_key[-4:]}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_setpayment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚙️ *Настройка платежей*\n\n"
            "`/setpayment cryptobot TOKEN`\n"
            "`/setpayment heleket API_KEY SECRET_KEY`\n"
            "`/setpayment btcpay URL API_KEY STORE_ID`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    provider = args[0].lower()
    if provider == "cryptobot":
        token = args[1]
        await db.set_setting("cryptobot_token", token)
        payment_mgr.setup_cryptobot(token)
        await update.message.reply_text("✅ CryptoBot token установлен.", parse_mode=ParseMode.MARKDOWN)
    elif provider == "heleket":
        if len(args) < 3:
            await update.message.reply_text("❌ Нужно: `/setpayment heleket API_KEY SECRET_KEY`", parse_mode=ParseMode.MARKDOWN)
            return
        api_key, secret = args[1], args[2]
        await db.set_setting("heleket_api_key", api_key)
        await db.set_setting("heleket_secret", secret)
        payment_mgr.setup_heleket(api_key, secret)
        await update.message.reply_text("✅ Heleket настроен.", parse_mode=ParseMode.MARKDOWN)
    elif provider == "btcpay":
        if len(args) < 4:
            await update.message.reply_text(
                "❌ Нужно: `/setpayment btcpay URL API_KEY STORE_ID`\n\n"
                "Пример:\n"
                "`/setpayment btcpay https://pay.example.com api_key store_123`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        base_url, api_key, store_id = args[1], args[2], args[3]
        await db.set_setting("btcpay_base_url", base_url)
        await db.set_setting("btcpay_api_key", api_key)
        await db.set_setting("btcpay_store_id", store_id)
        payment_mgr.setup_btcpay(base_url, api_key, store_id)
        await update.message.reply_text(
            f"✅ *BTCPay Server настроен*\n\nURL: `{base_url}`\nStore: `{store_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Неизвестный провайдер. cryptobot, heleket или btcpay")


async def chain_all_persons(persons: list, batch_key: str, uid: int, q, context) -> None:
    """Run SSN chain on ALL persons in parallel. Show top 5 results."""
    uf_key = await db.get_setting("usfull_api_key")
    if not uf_key:
        await q.edit_message_text("❌ API ключ Usfull не настроен")
        return

    uf_engine.api_key = uf_key
    price = await user_price(uid, "ssn_dob_price")

    await q.edit_message_text(f"⏳ Chain ALL: запуск на {len(persons)} персон...")

    async def chain_one(idx: int, p: dict) -> dict:
        name_parts = p.get("name", "").split()
        fn = p.get("first_name") or (name_parts[0] if name_parts else "")
        ln = name_parts[-1] if len(name_parts) > 1 else ""
        loc = p.get("location", "") or ""
        st = ""
        if loc:
            parts_loc = [pt.strip().upper() for pt in loc.split(",")]
            for pt in reversed(parts_loc):
                if len(pt) == 2 and pt.isalpha():
                    st = pt
                    break
        matched_addr = p.get("_matched_addr", {})
        result = await uf_engine.search_ssn_dob(
            first_name=fn.strip(), last_name=ln.strip(),
            state=st, street_address=matched_addr.get("street", ""),
            city=matched_addr.get("city", ""), zip_code=matched_addr.get("zip", ""),
        )
        ded_ok = await db.deduct_balance(uid, price, f"chain_all:{fn} {ln}")
        if ded_ok:
            await db.save_search(uid, "ssn_dob", f"{fn} {ln}", json.dumps(result), price, 0, source="usfull")
        return {"idx": idx, "person": p, "ssn_result": result, "deducted": ded_ok}

    # Run top 5 in parallel
    targets = persons[:5]
    results = await asyncio.gather(*[chain_one(i, p) for i, p in enumerate(targets)])

    # Build response
    found = [r for r in results if r["ssn_result"].get("ok") and r["ssn_result"].get("results")]
    lines = [f"⚡ *Chain ALL результат*\n\nНайдено SSN: {len(found)}/{len(targets)}\n"]
    for r in found:
        p = r["person"]
        ssn_res = r["ssn_result"]
        name = p.get("name", "Unknown")
        count = ssn_res.get("count", len(ssn_res.get("results", [])))
        lines.append(f"👤 {name}")
        lines.append(f"  ✅ SSN/DOB: найдено {count} записей")
        if ssn_res.get("results"):
            rec = ssn_res["results"][0]
            lines.append(f"  📍 {rec.get('address', '')} {rec.get('city', '')} {rec.get('st', '')}")
        lines.append("")

    if found:
        # Store results for CR/DL chain
        context.bot_data.setdefault("chain_data", {})[f"chain_all:{batch_key}"] = {
            r["idx"]: r["ssn_result"] for r in found
        }

    not_found = len(targets) - len(found)
    if not_found:
        lines.append(f"❌ Не найдено: {not_found}")

    lines.append(f"\n_Chain на остальных персон доступен по выбору_")

    await q.edit_message_text(
        "\n".join(lines)[:4000],
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main")]]),
        parse_mode=ParseMode.MARKDOWN
    )


# ── Callback router ─────────────────────────────────────────────────

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid  = q.from_user.id

    # Navigation
    if data == "main":
        await send_main(update, context, edit=True)
        return

    if data == "sec_phone":
        await q.edit_message_text(
            "📞 *Phone*\n\nВыберите операцию:",
            reply_markup=kb_phone(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "sec_addr":
        await q.edit_message_text(
            "🏠 *Address*\n\nВыберите операцию:",
            reply_markup=kb_addr(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "sec_bg":
        await q.edit_message_text(
            "🔍 *Background Check*\n\nВыберите операцию:",
            reply_markup=kb_bg(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "sec_email":
        await q.edit_message_text(
            "📧 *Email*\n\nВыберите операцию:",
            reply_markup=kb_email(), parse_mode=ParseMode.MARKDOWN
        )
        return

    # Profile
    if data == "profile":
        user = await db.get_user(uid)
        markup = user.get("markup_pct", 0) if user else 0
        prices = await db.get_all_settings()
        def p(key):
            return round(float(prices.get(key, 0)) * (1 + markup / 100), 2)
        text = (
            f"👤 *Ваш профиль*\n\n"
            f"🆔 ID: `{uid}`\n"
            f"💰 Баланс: *${user.get('balance', 0):.2f}*\n"
            f"📊 Поисков: {user.get('searches', 0)}\n"
            f"💸 Потрачено: ${user.get('total_spent', 0):.2f}\n"
            f"📅 С: {user.get('created_at','')[:10]}\n\n"
            f"*Ваши цены:*\n"
            f"  📞 Phone Lookup: ${p('phone_price')}\n"
            f"  📡 Phone Identify: ${p('phone_verify_price')}\n"
            f"  ✅ Phone Verify: ${p('phone_verify_price')}\n"
            f"  🏠 Address Lookup: ${p('address_price')}\n"
            f"  🔢 Number+Address: ${p('number_address_price')}\n"
            f"  📍 Address Verify: ${p('address_verify_price')}\n"
            f"  🔍 Background: ${p('background_price')}\n"
            f"  📧 Email Lookup: ${p('phone_price')}\n"
            f"  📧 Email Verify: ${p('email_verify_price')}\n"
            f"  🌐 EmailRep: ${p('emailrep_price')}\n"
            f"  🆔 SSN/DOB: ${p('ssn_dob_price')}\n"
            f"  🪪 DL: ${p('driver_license_price')}\n"
            f"  💳 Credit Report: ${p('credit_report_price')}\n"
        )
        await q.edit_message_text(text, reply_markup=kb_back(), parse_mode=ParseMode.MARKDOWN)
        return

    # History
    if data == "history":
        searches = await db.get_user_searches(uid, limit=20)
        if not searches:
            await q.edit_message_text("📊 Нет поисков.", reply_markup=kb_back(), parse_mode=ParseMode.MARKDOWN)
            return
        lines = ["📊 *Последние поиски* (20)\n"]
        for s in searches:
            dt = s["created_at"][:16]
            src = s.get("source", "enf")
            lines.append(f"`{dt}` | {src} | {s['search_type']} — `{s['query'][:25]}` — ${s['cost_user']:.2f}")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_back(), parse_mode=ParseMode.MARKDOWN)
        return

    # Balance / Payments
    if data == "balance_menu":
        user = await db.get_user(uid)
        payments = await db.get_user_payments(uid, 3)
        text = (
            f"💰 *Баланс*\n\n"
            f"Баланс: *${user.get('balance',0):.2f}*\n"
            f"Потрачено: ${user.get('total_spent',0):.2f}\n"
            f"Поисков: {user.get('searches',0)}\n"
        )
        if payments:
            text += "\n*Последние платежи:*\n"
            for p in payments:
                icon = "✅" if p["status"] == "confirmed" else "⏳"
                text += f"{icon} ${p['amount']:.2f} {p['currency']} via {p['provider']} — {p['status']}\n"
        await q.edit_message_text(
            text,
            reply_markup=kb_balance_menu(payment_mgr.available_providers),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "pay_cryptobot":
        await q.edit_message_text(
            "🤖 *CryptoBot — Выберите валюту*",
            reply_markup=kb_currencies("cryptobot"), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "pay_heleket":
        await q.edit_message_text(
            "🔐 *Heleket — Выберите валюту*",
            reply_markup=kb_currencies("heleket"), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "pay_btcpay":
        await q.edit_message_text(
            "₿ *BTCPayServer — Выберите валюту*\n\nДоступны: BTC, USDT, USDC, ETH, LTC, DOGE",
            reply_markup=kb_currencies("btcpay"), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("cur_"):
        parts = data.split("_", 2)
        provider = parts[1]
        currency = parts[2]
        await q.edit_message_text(
            f"💵 *Выберите сумму*\nВалюта: *{currency}*",
            reply_markup=kb_deposit_amounts(provider, currency), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("dep_"):
        parts = data.split("_")
        provider = parts[1]
        amount = float(parts[2])
        currency = parts[3] if len(parts) > 3 else "USDT"
        msg = await q.edit_message_text("⏳ Создаю инвойс...", parse_mode=ParseMode.MARKDOWN)
        invoice = await payment_mgr.create_invoice(
            provider=provider, amount=amount, user_id=uid,
            currency=currency, description=f"Balance top-up ${amount}"
        )
        if not invoice:
            await msg.edit_text(
                "❌ Ошибка создания инвойса. Платёжный провайдер не настроен.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await db.create_payment(uid, provider, invoice["invoice_id"], amount, currency, f"uid:{uid}")
        pay_url = invoice.get("pay_url", "")
        await msg.edit_text(
            f"💳 *Инвойс создан*\n\n"
            f"Сумма: *${amount:.2f} {currency}*\n"
            f"Провайдер: *{provider}*\n"
            f"ID: `{invoice['invoice_id']}`\n\n"
            f"Нажмите кнопку для оплаты:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💳 Оплатить ${amount} {currency}", url=pay_url)],
                [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"chk_{provider}_{invoice['invoice_id']}")],
                [InlineKeyboardButton("◀️ Назад", callback_data="balance_menu")],
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("chk_"):
        parts = data.split("_", 2)
        provider = parts[1]
        invoice_id = parts[2]
        invoice = await payment_mgr.check_invoice(provider, invoice_id)
        if not invoice:
            await q.answer("❌ Не удалось проверить статус", show_alert=True)
            return
        status = invoice.get("status", "unknown")
        if status == "paid":
            payment = await db.confirm_payment(invoice_id)
            if payment:
                user = await db.get_user(uid)
                await q.edit_message_text(
                    f"✅ *Оплата подтверждена!*\n\n"
                    f"Пополнено: *${payment['amount']:.2f}*\n"
                    f"Новый баланс: *${user['balance']:.2f}*",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main")]]),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await q.answer("Уже обработано", show_alert=True)
        elif status == "active":
            await q.answer("⏳ Оплата ещё не получена. Завершите оплату.", show_alert=True)
        elif status == "expired":
            await q.answer("❌ Инвойс истёк. Создайте новый.", show_alert=True)
        else:
            await q.answer(f"Статус: {status}", show_alert=True)
        return

    # Phone operations
    if data == "ph_lookup":
        price = await user_price(uid, "phone_price")
        await q.edit_message_text(
            f"📞 *Phone Reverse Lookup*\n\n"
            f"💰 Цена: *${price}* за номер\n\n"
            f"Отправьте номер(а):\n`2125551234`",
            reply_markup=kb_back("sec_phone"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ph_lookup", "price_key": "phone_price"})
        return

    if data == "ph_batch":
        price = await user_price(uid, "phone_price")
        await q.edit_message_text(
            f"📋 *Phone Batch Lookup*\n\n"
            f"💰 Цена: *${price}* за номер\n\n"
            f"Отправьте список номеров (по одному на строке):",
            reply_markup=kb_back("sec_phone"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ph_batch", "price_key": "phone_price"})
        return

    if data == "ph_identify":
        price = await user_price(uid, "phone_verify_price")
        await q.edit_message_text(
            f"📡 *Phone Identify*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Тип оператора, город, штат.\n\n"
            f"Отправьте номер(а):",
            reply_markup=kb_back("sec_phone"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ph_identify", "price_key": "phone_verify_price"})
        return

    if data == "ph_verify":
        price = await user_price(uid, "phone_verify_price")
        await q.edit_message_text(
            f"✅ *Phone Verify*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Проверяет активен ли номер.\n\n"
            f"Отправьте номер(а):",
            reply_markup=kb_back("sec_phone"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ph_verify", "price_key": "phone_verify_price"})
        return

    # Address
    if data == "ad_lookup":
        price = await user_price(uid, "address_price")
        await q.edit_message_text(
            f"🏠 *Address Lookup*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Поиск адресов по имени.\n"
            f"Формат:\n`First Last ST`\n"
            f"Пример:\n`John Smith CA`",
            reply_markup=kb_back("sec_addr"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ad_lookup", "price_key": "address_price"})
        return

    if data == "ad_batch":
        price = await user_price(uid, "address_price")
        await q.edit_message_text(
            f"📋 *Address Batch*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Отправьте имена (по одному на строку):\n"
            f"`John Smith CA`\n`Jane Doe NY`",
            reply_markup=kb_back("sec_addr"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ad_batch", "price_key": "address_price"})
        return

    if data == "ad_numaddr":
        price = await user_price(uid, "number_address_price")
        await q.edit_message_text(
            f"🔢 *Number + Address*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Формат: `FirstName LastName`\n"
            f"Пример:\n`John Smith`",
            reply_markup=kb_back("sec_addr"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ad_numaddr", "price_key": "number_address_price"})
        return

    if data == "ad_verify":
        price = await user_price(uid, "address_verify_price")
        await q.edit_message_text(
            f"📍 *Address Verify*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Проверка адреса через PersonSearch\n\n"
            f"Отправьте имя:",
            reply_markup=kb_back("sec_addr"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "ad_verify", "price_key": "address_verify_price"})
        return

    # Background
    if data == "bg_name":
        price = await user_price(uid, "background_price")
        await q.edit_message_text(
            f"🔍 *Background Check by Name*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Формат: `Имя Фамилия [Штат]`\n"
            f"Примеры:\n`John Smith NY`\n`Jane Doe CA`",
            reply_markup=kb_back("sec_bg"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "bg_name", "price_key": "background_price"})
        return

    if data == "bg_batch":
        price = await user_price(uid, "background_price")
        await q.edit_message_text(
            f"📋 *Background Batch*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Отправьте имена (по одному на строке):",
            reply_markup=kb_back("sec_bg"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "bg_batch", "price_key": "background_price"})
        return

    # Email
    if data == "em_lookup":
        price = await user_price(uid, "phone_price")
        await q.edit_message_text(
            f"📧 *Email Lookup*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Отправьте email(ы):\n`john@example.com`",
            reply_markup=kb_back("sec_email"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "em_lookup", "price_key": "phone_price"})
        return

    if data == "em_verify":
        price = await user_price(uid, "email_verify_price")
        await q.edit_message_text(
            f"✅ *Email Verify*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Отправьте email(ы):",
            reply_markup=kb_back("sec_email"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "em_verify", "price_key": "email_verify_price"})
        return

    if data == "em_rep":
        price = await user_price(uid, "emailrep_price")
        await q.edit_message_text(
            f"🌐 *EmailRep Check*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Репутация, спам, blacklist.\n\n"
            f"Отправьте email(ы):",
            reply_markup=kb_back("sec_email"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "em_rep", "price_key": "emailrep_price"})
        return

    # Smart Search
    if data == "sec_smart":
        price_id = await user_price(uid, "phone_verify_price")
        price_ssn = await user_price(uid, "ssn_dob_price")
        total = price_id + price_ssn
        await q.edit_message_text(
            f"🔍 *Smart Search*\n\n"
            f"Автоматически:\n"
            f"1️⃣ Phone Identify (Enformion)\n"
            f"2️⃣ SSN/DOB по имени (Usfull)\n\n"
            f"💡 *Цена: ~${total:.2f}*\n\n"
            f"📱 Введите номер телефона:",
            reply_markup=kb_back("main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "smart_phone", "price_key": "phone_verify_price"})
        return

    # Batch Phones
    if data == "sec_batch_phones":
        price = await user_price(uid, "phone_price")
        await q.edit_message_text(
            f"📋 *Batch Phone Lookup*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"1–20 номеров, по одному на строке:",
            reply_markup=kb_back("main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "batch_phones", "price_key": "phone_price"})
        return

    # Usfull SSN
    if data == "sec_ssn":
        price = await user_price(uid, "ssn_dob_price")
        await q.edit_message_text(
            f"🆔 *SSN / DOB Search*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Поиск по имени, DOB. Поддерживается *usfull.pro*",
            reply_markup=kb_usfull_ssn(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "uf_ssn_name":
        price = await user_price(uid, "ssn_dob_price")
        await q.edit_message_text(
            f"🆔 *SSN by Name/DOB*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Примеры:\n"
            f"`John Smith`\n"
            f"`John Smith NY 1985`",
            reply_markup=kb_back("sec_ssn"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "uf_ssn_name", "price_key": "ssn_dob_price"})
        return

    if data == "uf_ssn_direct":
        price = await user_price(uid, "ssn_dob_price")
        await q.edit_message_text(
            f"🆔 *SSN Direct*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Введите SSN:\n`123-45-6789`",
            reply_markup=kb_back("sec_ssn"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "uf_ssn_direct", "price_key": "ssn_dob_price"})
        return

    # Usfull DL
    if data == "sec_dl":
        price = await user_price(uid, "driver_license_price")
        await q.edit_message_text(
            f"🪪 *Driver License*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Поиск через *usfull.pro*",
            reply_markup=kb_usfull_dl(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "uf_dl":
        price = await user_price(uid, "driver_license_price")
        await q.edit_message_text(
            f"🪪 *DL Lookup*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"По одному на строку:\n"
            f"`First Name: John`\n`Last Name: Smith`\n`Address: 123 Main St`\n`ZIP: 90210`\n`DOB: 01/15/1980`",
            reply_markup=kb_back("sec_dl"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "uf_dl", "price_key": "driver_license_price"})
        return

    # Usfull Credit Report
    if data == "sec_cr":
        price = await user_price(uid, "credit_report_price")
        await q.edit_message_text(
            f"💳 *Credit Report*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Кредитный отчёт через *usfull.pro*",
            reply_markup=kb_usfull_cr(), parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "uf_cr":
        price = await user_price(uid, "credit_report_price")
        await q.edit_message_text(
            f"💳 *Credit Report*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"Данные:\n"
            f"`First Name: John`\n`Last Name: Smith`\n`Address: 123 Main St`\n`City: LA`\n`State: CA`\n`ZIP: 90210`\n`DOB: 01/15/1980`\n`SSN: 123-45-6789`",
            reply_markup=kb_back("sec_cr"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "uf_cr", "price_key": "credit_report_price"})
        return

    # SSN Batch
    if data == "sec_ssn_batch":
        price = await user_price(uid, "ssn_dob_price")
        await q.edit_message_text(
            f"📋 *SSN/DOB Batch*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"До 20 записей, формат:\n"
            f"`FirstName LastName State DOB`\n\n"
            f"Пример:\n"
            f"`John Smith NY 1985`\n"
            f"`Jane Doe TX 01/15/1985`",
            reply_markup=kb_back("sec_ssn"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "uf_ssn_batch", "price_key": "ssn_dob_price"})
        return

    # Email Batch
    if data == "em_batch":
        price = await user_price(uid, "emailrep_price")
        await q.edit_message_text(
            f"📋 *EmailRep Batch*\n\n"
            f"💰 Цена: *${price}*\n\n"
            f"До 20 email'ов, по одному на строке:",
            reply_markup=kb_back("sec_email"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.update({"state": "em_batch", "price_key": "emailrep_price"})
        return

    # Export
    if data.startswith("exp_"):
        parts = data.split("_", 2)
        fmt = parts[1]
        batch_key = parts[2] if len(parts) > 2 else ""
        results = context.bot_data.get("batch_results", {}).get(batch_key, [])
        if not results:
            await q.answer("Нет результатов", show_alert=True)
            return
        stype = results[0].get("type", "search") if results else "search"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if fmt == "csv":
            buf = export_csv(results, stype)
            fname = f"results_{stype}_{ts}.csv"
        elif fmt == "txt":
            buf = export_txt(results, stype)
            fname = f"results_{stype}_{ts}.txt"
        else:
            buf = export_json(results)
            fname = f"results_{stype}_{ts}.json"
        # Safe chat_id extraction
        export_chat_id = None
        if q.message and q.message.chat:
            export_chat_id = q.message.chat.id
        elif q.message and hasattr(q.message, "chat_id"):
            export_chat_id = q.message.chat_id
        if export_chat_id:
            await context.bot.send_document(
                chat_id=export_chat_id,
                document=InputFile(buf, filename=fname),
                caption=f"📁 {fname} — {len(results)} записей",
            )
        return

    # Admin
    if data.startswith("adm_") and await is_admin(uid):
        await handle_admin_callback(update, context, data)
        return

    # ── Chain ALL persons (parallel SSN) ──
    if data.startswith("chain_all:"):
        _, batch_key = data.split(":", 1)
        persons = context.bot_data.get("person_cache", {}).get(batch_key, [])
        if not persons:
            await q.answer("Нет персон для цепочки", show_alert=True)
            return
        await chain_all_persons(persons, batch_key, uid, q, context)
        return

    # ── Person selection ──
    if data.startswith("person:"):
        _, batch_key, idx_str = data.split(":", 2)
        idx = int(idx_str)
        persons = context.bot_data.get("person_cache", {}).get(batch_key, [])
        if idx < len(persons) and persons:
            p = persons[idx]
            card = _fmt_person_card(p)
            await q.edit_message_text(card[:4000],
                                      reply_markup=kb_chain_actions(idx, batch_key),
                                      parse_mode=ParseMode.MARKDOWN)
        else:
            await q.answer("Персона не найдена", show_alert=True)
        return

    # ── Person actions ──
    if data.startswith("chain_ssn:"):
        _, batch_key, idx_str = data.split(":", 2)
        idx = int(idx_str)
        persons = context.bot_data.get("person_cache", {}).get(batch_key, [])
        if idx < len(persons):
            p = persons[idx]
            name_parts = p.get("name", "").split()
            fn = p.get("first_name") or (name_parts[0] if name_parts else "")
            ln = name_parts[-1] if len(name_parts) > 1 else ""
            loc = p.get("location", "") or p.get("address", "")
            st = ""
            if loc:
                from validators import US_STATES_LIST
                for part in loc.split(","):
                    s = part.strip().upper()
                    if s in US_STATES_LIST:
                        st = s
                        break
            uf_key = await db.get_setting("usfull_api_key")
            if not uf_key:
                await q.edit_message_text(
                    "❌ API ключ Usfull не настроен",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")]]))
                return

            # Daily limit check
            price = await user_price(uid, "ssn_dob_price")
            allowed, _, _ = await check_daily_limit_or_block(uid, q.message.chat.id, price, context)
            if not allowed:
                return

            matched_addr = p.get("_matched_addr", {})
            st_addr = matched_addr.get("street", "")
            city    = matched_addr.get("city", "")
            zipcode = matched_addr.get("zip", "")
            st_state = matched_addr.get("state", "")
            if not st_state and loc:
                from validators import US_STATES_LIST
                for part in loc.split(","):
                    s = part.strip().upper()
                    if s in US_STATES_LIST:
                        st_state = s
                        break
            await q.edit_message_text(f"⏳ SSN/DOB поиск: {fn} {ln} {st_state}...")
            uf_engine.api_key = uf_key
            result = await uf_engine.search_ssn_dob(
                first_name=fn.strip(),
                last_name=ln.strip(),
                state=st_state,
                street_address=st_addr,
                city=city,
                zip_code=zipcode,
            )
            if result.get("ok") and result.get("results"):
                ded = await db.deduct_balance(uid, price, f"chain_ssn:{fn} {ln}")
                if ded:
                    await db.save_search(uid, "ssn_dob", f"{fn} {ln}", json.dumps(result), price, 0, source="usfull")
                    # Store for CR chain
                    context.bot_data.setdefault("chain_data", {})[f"ssn:{batch_key}:{idx}"] = result
                    text = fmt_usfull_ssn(result)
                    mk = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 Credit Report", callback_data=f"chain_cr:{batch_key}:{idx}")],
                        [InlineKeyboardButton("🪪 Driver License", callback_data=f"chain_dl:{batch_key}:{idx}")],
                        [InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")],
                    ])
                    await q.edit_message_text(text[:4000], reply_markup=mk, parse_mode=ParseMode.MARKDOWN)
                else:
                    await q.edit_message_text("❌ Недостаточно средств")
            else:
                await q.edit_message_text("❌ SSN/DOB не найден",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")]]))
        return

    # ── Chain: Credit Report ──
    if data.startswith("chain_cr:"):
        _, batch_key, idx_str = data.split(":", 2)
        idx = int(idx_str)
        persons = context.bot_data.get("person_cache", {}).get(batch_key, [])
        if idx >= len(persons):
            await q.answer("Персона не найдена", show_alert=True)
            return
        p = persons[idx]

        # Try SSN result from chain_data
        ssn_result = context.bot_data.get("chain_data", {}).get(f"ssn:{batch_key}:{idx}")

        uf_key = await db.get_setting("usfull_api_key")
        if not uf_key:
            await q.edit_message_text("❌ API ключ Usfull не настроен",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=f"person:{batch_key}:{idx}")]]),
                parse_mode=ParseMode.MARKDOWN)
            return

        # Daily limit check
        price = await user_price(uid, "credit_report_price")
        allowed, _, _ = await check_daily_limit_or_block(uid, q.message.chat.id, price, context)
        if not allowed:
            return

        await q.edit_message_text("⏳ Credit Report...")
        uf_engine.api_key = uf_key

        if ssn_result and ssn_result.get("results"):
            rec = ssn_result["results"][0]
            result = await uf_engine.search_credit_report(
                first_name=rec.get("firstname", "") or "",
                last_name=rec.get("lastname", "") or "",
                street_address=rec.get("address", "") or "",
                city=rec.get("city", "") or "",
                state=rec.get("st", "") or "",
                zip_code=rec.get("zip", "") or "",
                dob=rec.get("dob", "") or "",
                ssn=str(rec.get("ssn", "") or ""),
            )
        else:
            name_parts = p.get("name", "").split()
            loc = p.get("location", "") or p.get("address", "")
            loc_parts = loc.split(",") if loc else ["", "", ""]
            result = await uf_engine.search_credit_report(
                first_name=name_parts[0] if name_parts else "",
                last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                street_address=loc_parts[0].strip() if loc_parts else "",
                city=loc_parts[1].strip() if len(loc_parts) > 1 else "",
                state=loc_parts[-1].strip()[:2] if len(loc_parts) > 2 else "",
                zip_code="", dob="", ssn="",
            )

        if result.get("ok") and result.get("data"):
            price = await user_price(uid, "credit_report_price")
            ded = await db.deduct_balance(uid, price, f"chain_cr:{p.get('name','')}")
            if ded:
                await db.save_search(uid, "credit_report", p.get("name",""), json.dumps(result), price, 0, source="usfull")
                text = fmt_usfull_cr(result)
                mk = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🪪 Driver License", callback_data=f"chain_dl:{batch_key}:{idx}")],
                    [InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")],
                ])
                await q.edit_message_text(text[:4000], reply_markup=mk, parse_mode=ParseMode.MARKDOWN)
            else:
                await q.edit_message_text("❌ Недостаточно средств")
        else:
            await q.edit_message_text("❌ Credit Report не найден",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")]]))
        return

    # ── Chain: ALL persons SSN ──
    if data.startswith("chain_all:"):
        batch_key = data.split(":", 1)[1]
        persons = context.bot_data.get("person_cache", {}).get(batch_key, [])
        if not persons:
            await q.answer("Персоны не найдены", show_alert=True)
            return
        await chain_all_persons(persons, batch_key, uid, q, context)
        return

    # ── Chain: Driver License ──
    if data.startswith("chain_dl:"):
        _, batch_key, idx_str = data.split(":", 2)
        idx = int(idx_str)
        persons = context.bot_data.get("person_cache", {}).get(batch_key, [])
        if idx >= len(persons):
            await q.answer("Персона не найдена", show_alert=True)
            return
        p = persons[idx]
        name_parts = p.get("name", "").split()
        matched_addr = p.get("_matched_addr", {})
        st_addr = matched_addr.get("street", "")
        zipcode = matched_addr.get("zip", "")
        if not zipcode:
            loc = p.get("location", "") or p.get("address", "")
            loc_parts = (loc.split(",") if loc else ["", "", ""])
            zipcode = loc_parts[-1].strip()[:10] if len(loc_parts) > 2 else ""
        st_state = matched_addr.get("state", "")
        if not st_state and loc:
            from validators import US_STATES_LIST
            for part in (p.get("location", "") or p.get("address", "")).split(","):
                s = part.strip().upper()
                if s in US_STATES_LIST:
                    st_state = s
                    break

        uf_key = await db.get_setting("usfull_api_key")
        if not uf_key:
            await q.edit_message_text("❌ API ключ Usfull не настроен",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=f"person:{batch_key}:{idx}")]]),
                parse_mode=ParseMode.MARKDOWN)
            return

        # Daily limit check
        price = await user_price(uid, "driver_license_price")
        allowed, _, _ = await check_daily_limit_or_block(uid, q.message.chat.id, price, context)
        if not allowed:
            return

        await q.edit_message_text("⏳ Driver License...")
        uf_engine.api_key = uf_key
        result = await uf_engine.search_driver_license(
            first_name=name_parts[0] if name_parts else "",
            last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            address=st_addr,
            zipcode=zipcode,
            dob=p.get("date_of_birth", "") or "",
        )

        if result.get("ok") and result.get("data"):
            price = await user_price(uid, "driver_license_price")
            ded = await db.deduct_balance(uid, price, f"chain_dl:{p.get('name','')}")
            if ded:
                await db.save_search(uid, "driver_license", p.get("name",""), json.dumps(result), price, 0, source="usfull")
                text = fmt_usfull_dl(result)
                mk = InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")],
                ])
                await q.edit_message_text(text[:4000], reply_markup=mk, parse_mode=ParseMode.MARKDOWN)
            else:
                await q.edit_message_text("❌ Недостаточно средств")
        else:
            await q.edit_message_text("❌ Driver License не найден",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад к персоне", callback_data=f"person:{batch_key}:{idx}")]]))
        return


# ── Input parsers ───────────────────────────────────────────────────

def parse_phone(raw: str) -> dict:
    phone = re.sub(r"[^\d+]", "", raw)
    return {"phone": phone}


def parse_address(raw: str) -> dict:
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) >= 2:
        return {"first_name": parts[0], "last_name": parts[1] if len(parts) > 1 else ""}
    name_parts = raw.split()
    return {
        "first_name": name_parts[0] if len(name_parts) > 0 else "",
        "last_name": name_parts[1] if len(name_parts) > 1 else "",
    }


def parse_number_address(raw: str) -> dict:
    parts = raw.split()
    return {
        "first_name": parts[0] if parts else "",
        "last_name": parts[1] if len(parts) > 1 else "",
    }


def parse_name(raw: str) -> dict:
    parts = raw.split()
    state = ""
    for p in parts:
        if len(p) == 2 and p.isupper():
            state = p
    name_parts = [p for p in parts if p.upper() != state]
    return {
        "first_name": name_parts[0] if name_parts else "",
        "last_name":  " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        "state":      state,
    }


def parse_email(raw: str) -> dict:
    return {"email": raw.strip().lower()}


# ── Usfull search handler ───────────────────────────────────────────

def _parse_usfull_kv(lines: list) -> dict:
    result = {}
    for line in lines:
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip().lower().replace(" ", "_")] = v.strip()
    return result


async def handle_usfull_search(update, context, uid: int, search_type: str, items: list, batch_key: str):
    price_map = {
        "ssn_dob":        "ssn_dob_price",
        "ssn_direct":     "ssn_dob_price",
        "ssn_batch":      "ssn_dob_price",
        "driver_license": "driver_license_price",
        "credit_report":  "credit_report_price",
    }
    fmt_map = {
        "ssn_dob":        fmt_usfull_ssn,
        "ssn_direct":     fmt_usfull_ssn,
        "ssn_batch":      fmt_usfull_ssn,
        "driver_license": fmt_usfull_dl,
        "credit_report":  fmt_usfull_cr,
    }
    price_key = price_map.get(search_type, "ssn_dob_price")
    fmt_fn    = fmt_map.get(search_type, fmt_usfull_ssn)

    # Rate limit check (10 searches per 60 seconds)
    allowed = await db.check_rate_limit(uid, "search", max_count=10, window_seconds=60)
    if not allowed:
        rem, reset_in = await db.get_rate_limit_remaining(uid, "search", 10, 60)
        await update.message.reply_text(
            f"⏱ *Слишком много запросов*\n\n"
            f"Подождите *{reset_in} сек* и попробуйте снова.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    price     = await user_price(uid, price_key)
    user      = await db.get_user(uid)
    balance   = user.get("balance", 0)

    # Daily limit check — shared with batch_search
    allowed, _, _ = await check_daily_limit_or_block(uid, update.effective_chat.id, price, context)
    if not allowed:
        return

    if balance < price:
        await update.message.reply_text(
            f"❌ *Недостаточно средств*\n"
            f"💰 Баланс: ${balance:.2f} | Нужно: ${price:.2f}\n\n"
            f"💡 Пополните баланс: /balance",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uf_key = await db.get_setting("usfull_api_key")
    if not uf_key:
        await update.message.reply_text(
            "❌ *API ключ usfull.pro не настроен*\n\n"
            "Админ: `/setufkey API_KEY`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uf_engine.api_key = uf_key
    raw_input = "\n".join(items)
    await update.message.reply_text("⏳ Выполняю поиск...")

    try:
        if search_type in ("ssn_dob", "ssn_batch"):
            parsed = parse_name(raw_input)
            result = await uf_engine.search_ssn_dob(
                first_name=parsed.get("first_name", ""),
                last_name=parsed.get("last_name", ""),
                state=parsed.get("state", ""),
                dob=parsed.get("dob", ""),
            )
        elif search_type == "ssn_direct":
            ssn = re.sub(r"[^\d]", "", raw_input)
            result = await uf_engine.search_ssn_dob(ssn=ssn)
        elif search_type == "driver_license":
            kv = _parse_usfull_kv(items)
            result = await uf_engine.search_driver_license(
                first_name=kv.get("first_name", ""),
                last_name=kv.get("last_name", ""),
                address=kv.get("address", ""),
                zipcode=kv.get("zip", ""),
                dob=kv.get("dob", ""),
            )
        elif search_type == "credit_report":
            kv = _parse_usfull_kv(items)
            result = await uf_engine.search_credit_report(
                first_name=kv.get("first_name", ""),
                last_name=kv.get("last_name", ""),
                street_address=kv.get("address", ""),
                city=kv.get("city", ""),
                state=kv.get("state", ""),
                zip_code=kv.get("zip", ""),
                dob=kv.get("dob", ""),
                ssn=kv.get("ssn", ""),
            )
        else:
            result = {"ok": False, "error": "Unknown search type"}
    except Exception as e:
        result = {"ok": False, "error": str(e)}

    charged = False
    if result.get("ok") and (result.get("results") or result.get("data")):
        deducted = await db.deduct_balance(uid, price, f"{search_type}:{raw_input[:50]}")
        if deducted:
            await db.save_search(uid, search_type, raw_input[:100], json.dumps(result), price, 0, source="usfull")
            # Create guarantee for successful searches
            searches = await db.get_user_searches(uid, limit=1)
            if searches:
                try:
                    sid = searches[0].get("id", 0) or 0
                    await db.create_guarantee(uid, sid, search_type, raw_input[:100], price, days=8)
                except Exception:
                    pass
            # Balance alert if low
            new_user = await db.get_user(uid)
            new_balance = new_user.get("balance", 0) if new_user else 0
            min_deposit = float(await db.get_setting("min_deposit") or "5")
            if new_balance > 0 and new_balance < min_deposit:
                await db.create_user_alert(uid, "low_balance",
                    f"⚠️ Низкий баланс: ${new_balance:.2f}. Пополните для продолжения работы.")
            charged = True
        else:
            logger.warning(f"[Usfull] Failed to deduct balance for user {uid}")

    text = fmt_fn(result)
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.MARKDOWN)

    if charged:
        await update.message.reply_text(
            "💡 *Что дальше?*",
            reply_markup=kb_upsell(search_type), parse_mode=ParseMode.MARKDOWN
        )


# ── Smart Search handler ────────────────────────────────────────────

async def handle_smart_search(update, context, phone_raw: str, uid: int):
    user = await db.get_user(uid)
    balance = user.get("balance", 0)
    price_id  = await user_price(uid, "phone_verify_price")
    price_ssn = await user_price(uid, "ssn_dob_price")

    if balance < price_id:
        await update.message.reply_text(
            f"❌ Недостаточно средств (${balance:.2f})",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    msg = await update.message.reply_text(
        f"🔍 *Smart Search*\n⏳ Шаг 1/2: Phone Identify (Enformion)...",
        parse_mode=ParseMode.MARKDOWN
    )

    # Step 1: Phone Identify via Enformion
    phone_q = parse_phone(phone_raw)
    id_result = await enf_pool.search("phone_identify", phone_q)
    if id_result.ok and id_result.people:
        await db.deduct_balance(uid, price_id, f"smart:identify:{phone_raw}")
        await db.save_search(uid, "phone_identify", phone_raw, json.dumps(id_result.to_dict()), price_id, 0, source="enformion")
        id_text = fmt_phone_identify(id_result, phone_raw)
        await update.message.reply_text(id_text[:2000], parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.edit_text(
            f"🔍 *Smart Search*\n"
            f"❌ Phone Identify: {id_result.error}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Extract name
    name_from_id = ""
    state_from_id = ""
    if id_result.people:
        p = id_result.people[0]
        fn = p.get("first_name", p.get("name", ""))
        ln = p.get("last_name", "")
        if not fn and " " in p.get("name", ""):
            parts = p["name"].split()
            fn, ln = parts[0], " ".join(parts[1:])
        name_from_id = f"{fn} {ln}".strip()
        state_from_id = p.get("location", "")
    if not name_from_id:
        await msg.edit_text(
            f"🔍 *Smart Search*\n✅ Phone Identify: готово\n⚠️ Имя не найдено.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Step 2: SSN/DOB via Usfull
    uf_key = await db.get_setting("usfull_api_key")
    if not uf_key:
        await msg.edit_text(
            f"🔍 *Smart Search*\n✅ Phone Identify: готово\n⚠️ SSN: API ключ не настроен.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    uf_engine.api_key = uf_key
    await msg.edit_text(
        f"🔍 *Smart Search*\n"
        f"✅ Phone Identify: готово\n"
        f"⏳ Шаг 2/2: SSN/DOB по имени `{name_from_id}` (Usfull)...",
        parse_mode=ParseMode.MARKDOWN
    )

    name_parts = name_from_id.split()
    state_code = ""
    for part in state_from_id.split(","):
        p = part.strip().upper()
        if len(p) == 2 and p not in ("NY", "TX", "CA", "FL", "IL", "PA", "OH", "GA", "NC", "MI"):
            # Check if it looks like a state code
            from validators import US_STATES_LIST
            if p in US_STATES_LIST:
                state_code = p
                break
        elif p in ["NY", "TX", "CA", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]:
            state_code = p
            break

    ssn_result = await uf_engine.search_ssn_dob(
        first_name=name_parts[0] if name_parts else "",
        last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        state=state_code,
    )

    if ssn_result.get("ok") and (ssn_result.get("results") or ssn_result.get("count", 0) > 0):
        await db.deduct_balance(uid, price_ssn, f"smart:ssn:{name_from_id}")
        await db.save_search(uid, "ssn_dob", name_from_id, json.dumps(ssn_result), price_ssn, 0, source="usfull")
        ssn_text = fmt_usfull_ssn(ssn_result)
        await update.message.reply_text(ssn_text[:4000], parse_mode=ParseMode.MARKDOWN)
        await msg.edit_text(
            f"🔍 *Smart Search — Готово!*\n"
            f"✅ Phone Identify\n"
            f"✅ SSN/DOB Found",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await msg.edit_text(
            f"🔍 *Smart Search*\n"
            f"✅ Phone Identify: готово\n"
            f"❌ SSN/DOB: не найдено",
            parse_mode=ParseMode.MARKDOWN
        )

    await update.message.reply_text(
        "💡 *Что дальше?*",
        reply_markup=kb_upsell("ssn_dob"), parse_mode=ParseMode.MARKDOWN
    )


# ── Parallel chain: SSN for ALL persons ─────────────────────────────

async def chain_all_persons(persons: list, batch_key: str, uid: int, q, context) -> None:
    """
    Run SSN chain on top 5 persons in parallel using asyncio.gather.
    Shows summary with expandable cards.
    Stores all chain results in context.bot_data["chain_all"][batch_key].
    """
    if not persons:
        await q.edit_message_text("❌ Нет персон для цепочки.", parse_mode=ParseMode.MARKDOWN)
        return

    top_persons = persons[:5]
    chain_key = f"chain_all:{batch_key}"
    msg = await q.edit_message_text(
        f"⚡ *Chain ALL*\n⏳ Запускаю SSN для {len(top_persons)} персон...",
        parse_mode=ParseMode.MARKDOWN
    )

    uf_key = await db.get_setting("usfull_api_key")
    if not uf_key:
        await msg.edit_text("❌ API ключ Usfull не настроен.", parse_mode=ParseMode.MARKDOWN)
        return

    uf_engine.api_key = uf_key

    async def chain_single(p: dict, idx: int) -> dict:
        """Run SSN search for a single person."""
        name_parts = p.get("name", "").split()
        fn = p.get("first_name") or (name_parts[0] if name_parts else "")
        ln = name_parts[-1] if len(name_parts) > 1 else ""
        loc = p.get("location", "") or p.get("address", "")
        st = ""
        if loc:
            from validators import US_STATES_LIST
            for part in loc.split(","):
                s = part.strip().upper()
                if s in US_STATES_LIST:
                    st = s
                    break
        matched_addr = p.get("_matched_addr", {})
        st_addr = matched_addr.get("street", "")
        city = matched_addr.get("city", "")
        zipcode = matched_addr.get("zip", "")

        result = await uf_engine.search_ssn_dob(
            first_name=fn.strip(),
            last_name=ln.strip(),
            state=st,
            street_address=st_addr,
            city=city,
            zip_code=zipcode,
        )
        return {"idx": idx, "person": p, "result": result}

    # Run all chains in parallel
    tasks = [chain_single(p, i) for i, p in enumerate(top_persons)]
    chain_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    ok_count = 0
    found_count = 0
    lines = [f"⚡ *Chain ALL — Результаты*\n"]
    result_map = {}

    for cr in chain_results:
        if isinstance(cr, Exception):
            continue
        idx = cr["idx"]
        p = cr["person"]
        res = cr["result"]
        name = p.get("name", "Unknown")
        result_map[idx] = cr

        if res.get("ok") and res.get("results"):
            ok_count += 1
            found_count += len(res.get("results", []))
            score = p.get("_score", 0)
            conf = p.get("_confidence_icon", "")
            lines.append(f"*#{idx+1}* {conf} {name} [Score: {score}]")
            rec = res["results"][0]
            dob = rec.get("dob", "") or ""
            ssn_val = rec.get("ssn", "") or ""
            if ssn_val and len(str(ssn_val)) >= 9:
                ssn_fmt = f"{ssn_val[:3]}-{ssn_val[3:5]}-{ssn_val[5:]}"
                lines.append(f"  🆔 SSN: `{ssn_fmt}`")
            if dob:
                if len(dob) == 8:
                    dob = f"{dob[4:6]}/{dob[6:8]}/{dob[:4]}"
                lines.append(f"  🎂 DOB: {dob}")
            addr_parts = []
            for fld in ["address", "city", "st", "zip"]:
                v = rec.get(fld, "") or ""
                if v and str(v) != "NULL":
                    addr_parts.append(str(v))
            if addr_parts:
                lines.append(f"  🏠 {', '.join(addr_parts)}")
            lines.append("")
        else:
            score = p.get("_score", 0)
            conf = p.get("_confidence_icon", "")
            lines.append(f"*#{idx+1}* {conf} {name} [Score: {score}]")
            lines.append("  ❌ SSN не найден\n")

    lines.append(f"✅ Найдено: {found_count} записей ({ok_count}/{len(top_persons)} персон)")

    # Store chain results
    context.bot_data.setdefault("chain_all", {})[batch_key] = result_map

    await msg.edit_text(
        "\n".join(lines)[:4000],
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад к списку", callback_data=f"pback:{batch_key}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main")],
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_emailrep_batch(update, context, items, batch_key):
    uid = update.effective_user.id
    price = await user_price(uid, "emailrep_price")
    results = []

    prog = await update.message.reply_text(
        f"⏳ Проверяю *{len(items)}* email(ов)...", parse_mode=ParseMode.MARKDOWN
    )

    key = await db.get_setting("emailrep_key") or EMAILREP_KEY
    for i, email_item in enumerate(items):
        if not await check_balance(uid, price):
            break
        data = await enf_pool.emailrep_lookup(email_item.strip(), key)
        deducted = await db.deduct_balance(uid, price, f"emailrep:{email_item}")
        if deducted:
            await db.save_search(uid, "emailrep", email_item, json.dumps(data), price, 0, source="emailrep")
        else:
            logger.warning(f"[EmailRep] Failed to deduct for user {uid}")

        text = fmt_emailrep(data, email_item)
        await update.message.reply_text(text[:2000], parse_mode=ParseMode.MARKDOWN)

        if i % 5 == 0 and i > 0:
            try:
                await prog.edit_text(
                    f"⏳ {i+1}/{len(items)} готово...", parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    try:
        await prog.delete()
    except Exception:
        pass

    if len(results) > 1:
        flat = [
            {
                "ok": True, "type": "emailrep",
                "query": {"email": r["email"]},
                "parsed": r["data"], "people": [],
            }
            for r in results
        ]
        context.bot_data.setdefault("batch_results", {})[batch_key] = flat
        await update.message.reply_text(
            f"✅ EmailRep: {len(results)} проверено",
            reply_markup=kb_export(batch_key)
        )


# ── File upload handler ─────────────────────────────────────────────

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith((".txt", ".csv")):
        await update.message.reply_text("❌ Только `.txt` и `.csv`.", parse_mode=ParseMode.MARKDOWN)
        return

    msg = await update.message.reply_text("⏳ Читаю файл аккаунтов...")

    try:
        file = await context.bot.get_file(doc.file_id)
        buf = io.BytesIO()
        await file.download_to_memory(buf)
        content = buf.getvalue().decode("utf-8", errors="replace")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")
        return

    parsed = enf_pool.parse_accounts_file(content)
    if not parsed:
        await msg.edit_text("❌ Не найдено аккаунтов. Формат: `email:password:proxy`", parse_mode=ParseMode.MARKDOWN)
        return

    await msg.edit_text(f"⏳ Найдено {len(parsed)} аккаунтов. Добавляю...")

    added = 0
    for acc in parsed:
        await db.upsert_sb_account(acc["email"], acc["password"], acc.get("proxy", ""))
        added += 1

    accounts = await db.get_sb_accounts()
    enf_pool.load(accounts)

    await msg.edit_text(f"⏳ Добавлено {added} аккаунтов. Логин...")

    stats = await enf_pool.login_all()

    for acc in enf_pool.accounts:
        await db.update_sb_account_status(
            acc.email, acc.status, acc.balance, acc.init_balance
        )

    lines = [
        f"✅ *Файл загружен!*\n",
        f"📊 Всего: {stats['total']}",
        f"✅ Вошли: {stats['ok']}",
        f"❌ Ошибок: {stats['failed']}",
        "",
    ]
    STATUS_ICON = {
        "active": "✅", "low_balance": "⚠️",
        "no_balance": "❌", "blocked": "⛔", "failed": "🔴", "unknown": "❓"
    }
    for a in enf_pool.accounts[-len(parsed):]:
        icon = STATUS_ICON.get(a.status, "❓")
        bal = f"{a.balance:.0f}$T" if a.balance else "?"
        lines.append(f"{icon} `{a.email}` — {bal} — {a.proxy[:30] or 'нет прокси'}")

    await msg.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    context.user_data["admin_state"] = ""


# ── Message handler ─────────────────────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if user.get("is_banned"):
        return

    uid = update.effective_user.id

    # File upload for admin
    if update.message.document and await is_admin(uid):
        await handle_file_upload(update, context)
        return

    text = update.message.text.strip() if update.message.text else ""
    state = context.user_data.get("state", "")
    admin_state = context.user_data.get("admin_state", "")

    # Admin text states
    if admin_state and await is_admin(uid):
        await handle_admin_message(update, context, text, admin_state)
        return

    if not state or not text:
        await send_main(update, context)
        return

    items = [line.strip() for line in text.split("\n") if line.strip()]
    if not items:
        await update.message.reply_text("❌ Пустой ввод.")
        return

    price_key = context.user_data.get("price_key", "phone_price")
    price = await user_price(uid, price_key)
    balance = user.get("balance", 0)

    if balance < price:
        await update.message.reply_text(
            f"❌ *Недостаточно средств*\n\n💰 Баланс: ${balance:.2f}\n💸 Нужно: ${price:.2f}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    max_items = int(balance / price)
    if len(items) > max_items:
        await update.message.reply_text(
            f"⚠️ Баланса хватит на *{max_items}* запросов. Обрабатываю первые {max_items}.",
            parse_mode=ParseMode.MARKDOWN
        )
        items = items[:max_items]

    batch_key = f"{uid}_{state}_{int(datetime.now().timestamp())}"
    context.user_data["last_batch_key"] = batch_key

    # Route by state
    if state in ("ph_lookup", "ph_batch", "batch_phones"):
        results = await process_batch(
            items, "phone", parse_phone, "phone_price",
            uid, update.effective_chat.id, context, batch_key
        )
        fullz_raw = "\n".join(items)
        await send_results(update, context, results, "phone", batch_key, fmt_enformion_result, fullz_input=fullz_raw)
        if any(r.get("ok") for r in results):
            await update.message.reply_text(
                "💡 *Что дальше?*",
                reply_markup=kb_upsell("phone"), parse_mode=ParseMode.MARKDOWN
            )

    elif state == "ph_identify":
        results = await process_batch(
            items, "phone_identify", parse_phone, "phone_verify_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "phone_identify", batch_key, fmt_phone_identify)

    elif state == "ph_verify":
        results = await process_batch(
            items, "phone_verify", parse_phone, "phone_verify_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "phone_verify", batch_key, fmt_phone_verify)

    elif state in ("ad_lookup", "ad_batch"):
        results = await process_batch(
            items, "address", parse_address, "address_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "address", batch_key, fmt_enformion_result)

    elif state == "ad_numaddr":
        results = await process_batch(
            items, "number_address", parse_number_address, "number_address_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "number_address", batch_key, fmt_enformion_result)

    elif state == "ad_verify":
        results = await process_batch(
            items, "address_verify", parse_address, "address_verify_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "address_verify", batch_key, fmt_address_verify)

    elif state in ("bg_name", "bg_batch"):
        results = await process_batch(
            items, "background", parse_name, "background_price",
            uid, update.effective_chat.id, context, batch_key
        )
        # Pass fullz raw input to enable address matching + chain precision
        fullz_raw = "\n".join(items)
        await send_results(update, context, results, "background", batch_key, fmt_enformion_result, fullz_input=fullz_raw)
        if any(r.get("ok") for r in results):
            await update.message.reply_text(
                "💡 *Что дальше?*",
                reply_markup=kb_upsell("background"), parse_mode=ParseMode.MARKDOWN
            )

    elif state == "em_lookup":
        results = await process_batch(
            items, "email", parse_email, "phone_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "email", batch_key, fmt_enformion_result)
        if any(r.get("ok") for r in results):
            await update.message.reply_text(
                "💡 *Что дальше?*",
                reply_markup=kb_upsell("email"), parse_mode=ParseMode.MARKDOWN
            )

    elif state == "em_verify":
        results = await process_batch(
            items, "email_verify", parse_email, "email_verify_price",
            uid, update.effective_chat.id, context, batch_key
        )
        await send_results(update, context, results, "email_verify", batch_key, fmt_email_verify)

    elif state == "em_rep":
        await handle_emailrep_batch(update, context, items, batch_key)

    elif state == "smart_phone":
        await handle_smart_search(update, context, items[0], uid)

    elif state == "uf_ssn_name":
        await handle_usfull_search(update, context, uid, "ssn_dob", items, batch_key)

    elif state == "uf_ssn_direct":
        await handle_usfull_search(update, context, uid, "ssn_direct", items, batch_key)

    elif state == "uf_dl":
        await handle_usfull_search(update, context, uid, "driver_license", items, batch_key)

    elif state == "uf_cr":
        await handle_usfull_search(update, context, uid, "credit_report", items, batch_key)

    elif state == "uf_ssn_batch":
        await handle_usfull_search(update, context, uid, "ssn_batch", items, batch_key)

    elif state == "em_batch":
        await handle_emailrep_batch(update, context, items, batch_key)


    context.user_data["state"] = ""


# ── Admin callbacks ─────────────────────────────────────────────────

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    q = update.callback_query
    uid = q.from_user.id

    if data == "adm_users":
        users = await db.get_all_users()
        lines = [f"👥 *Пользователи* ({len(users)})\n"]
        for u in users[:25]:
            status = "🚫" if u.get("is_banned") else ("👑" if u.get("is_admin") else "👤")
            lines.append(
                f"{status} `{u['user_id']}` @{u.get('username','?')} "
                f"— ${u.get('balance',0):.2f} — {u.get('searches',0)} поисков"
            )
        if len(users) > 25:
            lines.append(f"_...ещё {len(users)-25}_")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "adm_balance":
        await q.edit_message_text(
            "💳 *Добавить баланс*\n\n`USER_ID СУММА [комментарий]`\n\nПример:\n`123456789 10.00`",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "add_balance"
        return

    if data == "adm_enf":
        accounts = await db.get_sb_accounts()
        STATUS_ICON = {
            "active": "✅", "low_balance": "⚠️",
            "no_balance": "❌", "blocked": "⛔", "failed": "🔴", "unknown": "❓"
        }
        lines = [f"🔧 *ENF Аккаунты* ({len(accounts)})\n"]
        for a in accounts:
            bal = a.get("balance_tok", 0)
            init = a.get("init_tok", 1) or 1
            pct = int(bal / init * 100) if init else 0
            icon = STATUS_ICON.get(a["status"], "❓")
            lines.append(
                f"{icon} `{a['email']}`\n"
                f"   💰 {bal:.0f}$T ({pct}%) | 🔍 {a['searches']} | 🔗 {(a.get('proxy') or '—')[:30]}"
            )
        if not accounts:
            lines.append("Нет аккаунтов.")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "adm_add_enf":
        await q.edit_message_text(
            "➕ *Добавить ENF аккаунт*\n\n`email password [proxy]`\n\nПример:\n`user@mail.com pass123 http://proxy:8080`",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "add_enf_account"
        return

    if data == "adm_markup":
        await q.edit_message_text(
            "💰 *Наценка*\n\n`USER_ID ПРОЦЕНТ`\n\nПример:\n`123456789 50`",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "set_markup"
        return

    if data == "adm_stats":
        stats = await db.get_stats()
        enf_accounts = await db.get_sb_accounts()
        active_enf = sum(1 for a in enf_accounts if a["status"] in ("active", "low_balance"))
        dead_enf = sum(1 for a in enf_accounts if a["status"] in ("no_balance", "blocked", "failed"))
        uf_accounts = await db.get_usfull_accounts()
        active_uf = sum(1 for a in uf_accounts if a.get("status") in ("active", "low_balance"))

        text = (
            f"📊 *Статистика*\n\n"
            f"👥 Всего: *{stats['users']}* юзеров\n"
            f"💰 Суммарный баланс: *${stats['total_balance']:.2f}*\n\n"
            f"📅 *Сегодня:*\n"
            f"   Поисков: *{stats['today_searches']}*\n"
            f"   Выручка: *${stats['today_revenue']:.2f}*\n"
            f"   Депозиты: *${stats['today_deposits']:.2f}*\n"
            f"   Активных: *{stats['active_users_today']}*\n\n"
            f"💸 *За всё время:*\n"
            f"   Выручка: *${stats['total_revenue']:.2f}*\n"
            f"   Депозиты: *${stats['total_deposits']:.2f}*\n"
            f"   Прибыль: *${stats['profit']:.2f}*\n"
            f"   Поисков: *{stats['searches']}*\n\n"
            f"📂 *По источникам:*\n"
            f"   🔧 ENF: *${stats['rev_enf']:.2f}*\n"
            f"   🌐 Usfull: *${stats['rev_uf']:.2f}*\n\n"
            f"🔧 ENF: {active_enf}/{len(enf_accounts)} ✅ | ❌ {dead_enf}\n"
            f"🌐 Usfull: {active_uf}/{len(uf_accounts)} ✅"
        )
        await q.edit_message_text(text, reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "adm_broadcast":
        await q.edit_message_text(
            "📢 *Рассылка*\n\nОтправьте сообщение:",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "broadcast"
        return

    if data == "adm_prices":
        settings = await db.get_all_settings()
        price_keys = [k for k in settings if "price" in k or k == "min_deposit"]
        lines = ["⚙️ *Цены*\n\n`set_price КЛЮЧ ЗНАЧЕНИЕ`\n"]
        for k in price_keys:
            lines.append(f"`{k}` = ${settings[k]}")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = "set_price"
        return

    # ── Daily limits settings ────────────────────────────────────────
    if data == "adm_limits":
        settings = await db.get_all_settings()
        lines = ["🔢 *Дневные лимиты*\n\n"]
        limit_keys = [k for k in settings if "limit" in k or k == "allow_pay_over_limit"]
        for k in limit_keys:
            val = settings.get(k, "—")
            desc = {
                "default_daily_limit": "Без подписки (запросов/день)",
                "daily_limit_basic": "Basic план",
                "daily_limit_pro": "Pro план",
                "daily_limit_enterprise": "Enterprise план",
                "allow_pay_over_limit": "Оплата сверх лимита (0=нет, 1=да)",
            }.get(k, k)
            lines.append(f"`{k}` = *{val}*  — {desc}")
        lines.append("\n\n_Изменить: `set_limit КЛЮЧ ЗНАЧЕНИЕ`_")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = "set_limit"
        return

    # ── Per-user daily limit ─────────────────────────────────────────
    if data == "adm_user_limit":
        await q.edit_message_text(
            "👤 *Лимит юзера*\n\n"
            "`USER_ID ЛИМИТ`\n\n"
            "Пример:\n`123456789 20`\n\n"
            "Лимит=0 — сбросить (наследовать из плана/умолч.)",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "set_user_limit"
        return

    # ── Revenue breakdown ───────────────────────────────────────────
    if data == "adm_revenue":
        stats = await db.get_stats()
        by_type = stats.get("by_type", [])

        # Revenue by period
        async with aiosqlite.connect(db.DB_PATH) as db:
            async with db.execute("""
                SELECT date(created_at) as day, COALESCE(SUM(cost_user),0), COUNT(*)
                FROM searches WHERE status='ok' AND date(created_at) >= date('now','-7 days')
                GROUP BY day ORDER BY day DESC
            """) as cur:
                week_rows = await cur.fetchall()

        lines = ["💰 *Доход — Подробно*\n"]
        lines.append(f"Общая выручка: *${stats['total_revenue']:.2f}*")
        lines.append(f"Депозиты:      *${stats['total_deposits']:.2f}*")
        lines.append(f"Чистая прибыль: *${stats['profit']:.2f}*\n")
        lines.append("📂 *По типу поиска:*")
        type_map = {
            "phone": "📱 Phone", "address": "🏠 Address", "background": "🔍 Background",
            "name": "👤 Name", "phone_identify": "📡 Phone ID", "phone_verify": "✔ Phone Verify",
            "number_address": "📍 Num→Addr", "email": "📧 Email",
            "ssn_dob": "🆔 SSN/DOB", "driver_license": "🪪 DL",
            "credit_report": "💳 CR", "credit_score": "📊 CS",
        }
        for t in sorted(by_type, key=lambda x: x["revenue"], reverse=True):
            icon = type_map.get(t["type"], t["type"])
            lines.append(f"  {icon}: *${t['revenue']:.2f}* ({t['count']} шт)")
        if not by_type:
            lines.append("  пока нет данных")

        lines.append("\n📅 *Последние 7 дней:*")
        for row in week_rows:
            day, rev, cnt = row
            lines.append(f"  {day}: *${rev:.2f}* ({cnt} шт)")

        # Cost breakdown by source
        lines.append(f"\n🔧 ENF: *${stats['rev_enf']:.2f}* | 🌐 Usfull: *${stats['rev_uf']:.2f}*")

        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    # ── Top users ──────────────────────────────────────────────────
    if data == "adm_top_users":
        async with aiosqlite.connect(db.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT u.user_id, u.username, u.balance,
                       COALESCE(SUM(s.cost_user),0) as spent,
                       COUNT(s.id) as searches
                FROM users u
                LEFT JOIN searches s ON s.user_id=u.user_id AND s.status='ok'
                GROUP BY u.user_id
                ORDER BY spent DESC
                LIMIT 20
            """) as cur:
                rows = await cur.fetchall()

        lines = ["🏆 *Топ 20 пользователей*\n"]
        lines.append(f"{'#':<3} {'Юзер':<14} {'Поисков':>7} {'Потрачено':>10}")
        lines.append("─" * 40)
        total_spent = sum(r["spent"] for r in rows)
        for i, r in enumerate(rows, 1):
            uid = str(r["user_id"])[:12]
            lines.append(
                f"{i:<3} `{uid}` {r['searches']:>7} ${r['spent']:>9.2f}"
            )
        lines.append("─" * 40)
        lines.append(f"💰 Итого: *${total_spent:.2f}*")
        await q.edit_message_text("\n".join(lines)[:4000], reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    # ── Access management ──────────────────────────────────────────
    if data == "adm_access":
        async with aiosqlite.connect(db.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT user_id, username, is_admin, is_banned FROM users ORDER BY created_at DESC") as cur:
                all_users = await cur.fetchall()
        admins = [u for u in all_users if u["is_admin"]]
        banned = [u for u in all_users if u["is_banned"]]
        regular = [u for u in all_users if not u["is_admin"] and not u["is_banned"]]

        lines = [
            "🔑 *Управление доступом*\n",
            f"👑 Админов: *{len(admins)}*",
            f"🚫 Забанены: *{len(banned)}*",
            f"👤 Юзеров: *{len(regular)}*\n",
            "_Команды:_",
            "`setadmin USER_ID` — назначить админом",
            "`removeadmin USER_ID` — снять админа",
            "`ban USER_ID причина` — забанить",
            "`unban USER_ID` — разбанить",
        ]
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = "access"
        return

    # ── Bot control ────────────────────────────────────────────────
    if data == "adm_control":
        lines = [
            "⚡ *Управление ботом*\n",
            "🔄 `reloadpool` — перезагрузить пул аккаунтов",
            "🔧 `reloadenf` — перелогинить ENF",
            "🌐 `reloaduf` — перелогинить Usfull",
            "📊 `stats` — свежая статистика",
            "💾 `gc` — очистить кэш пулов",
            "⏸ `pause` — пауза (все поиски)",
            "▶️ `resume` — возобновить",
        ]
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = "control"
        return

    # ── User search ─────────────────────────────────────────────────
    if data == "adm_user_search":
        await q.edit_message_text(
            "🔎 *Найти пользователя*\n\n"
            "Отправьте `USER_ID` или `username`:",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "user_search"
        return

    # ── Ban user ────────────────────────────────────────────────────
    if data == "adm_ban_user":
        await q.edit_message_text(
            "🛡 *Забанить пользователя*\n\n"
            "Отправьте: `USER_ID причина`\n\n"
            "Пример:\n`123456789 Спам`",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "ban_user"
        return

    # ── Usfull accounts ─────────────────────────────────────────────
    if data == "adm_uf":
        accounts = await db.get_usfull_accounts()
        STATUS_ICON = {
            "active": "✅", "low_balance": "⚠️",
            "no_balance": "❌", "blocked": "⛔", "failed": "🔴", "unknown": "❓"
        }
        lines = [f"🌐 *Usfull Аккаунты* ({len(accounts)})\n"]
        for a in accounts:
            init = a.get("initial_balance", 1) or 1
            pct = int(a.get("balance", 0) / init * 100) if init else 0
            icon = STATUS_ICON.get(a.get("status", "unknown"), "❓")
            lines.append(
                f"{icon} `{a['username']}`\n"
                f"   💰 ${a.get('balance', 0):.2f} ({pct}%) | 🔍 {a.get('searches', 0)}"
            )
        if not accounts:
            lines.append("Нет аккаунтов. Используйте `/setufkey API_KEY`.")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    # ── Add Usfull account ──────────────────────────────────────────
    if data == "adm_add_uf":
        await q.edit_message_text(
            "🔄 *Добавить Usfull аккаунт*\n\n"
            "`username password api_key [proxy]`\n\n"
            "Пример:\n`john_api pass123 sk_live_abc http://proxy:8080`",
            reply_markup=kb_back("adm_main"), parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = "add_uf_account"
        return

    # ── Admin logs ──────────────────────────────────────────────────
    if data == "adm_logs":
        logs = await db.get_admin_logs(limit=30)
        if not logs:
            await q.edit_message_text("📋 *Логи админа*\n\nНет записей.", reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
            return
        lines = ["📋 *Последние действия админов*\n"]
        for log in logs[:20]:
            dt = log.get("created_at", "")[:16]
            target = f" → `{log.get('target_id', '')}`" if log.get("target_id") else ""
            lines.append(
                f"`{dt}` {log.get('admin_id', '')}: {log.get('action', '')}{target}\n"
                f"   {log.get('details', '')[:60]}"
            )
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    # ── Webhook logs ────────────────────────────────────────────────
    if data == "adm_webhook_logs":
        logs = await db.get_webhook_logs(limit=30)
        if not logs:
            await q.edit_message_text("🔗 *Webhook логи*\n\nНет записей.", reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
            return
        lines = ["🔗 *Последние webhook'и*\n"]
        for log in logs[:20]:
            dt = log.get("created_at", "")[:16]
            ok_icon = "✅" if log.get("processed") else "🔴"
            status = log.get("status_code", 0)
            lines.append(
                f"{ok_icon} `{dt}` {log.get('provider', '')} | "
                f"HTTP {status} | invoice: `{log.get('invoice_id', '-')[:20]}`"
            )
            if log.get("error_msg"):
                lines.append(f"   ❌ {log.get('error_msg', '')[:60]}")
        await q.edit_message_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "adm_main":
        await q.edit_message_text(
            "🛠 *Панель администратора*",
            reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN
        )
        return


# ── Admin message handler ───────────────────────────────────────────

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: str):
    uid = update.effective_user.id

    if state == "awaiting_accounts_file":
        parsed = enf_pool.parse_accounts_file(text)
        if parsed:
            for acc in parsed:
                await db.upsert_sb_account(acc["email"], acc["password"], acc.get("proxy", ""))
            accounts = await db.get_sb_accounts()
            enf_pool.load(accounts)
            msg = await update.message.reply_text(f"⏳ Добавлено {len(parsed)}. Логин...")
            stats = await enf_pool.login_all()
            for acc in enf_pool.accounts:
                await db.update_sb_account_status(acc.email, acc.status, acc.balance, acc.init_balance)
            await msg.edit_text(
                f"✅ Загружено: {stats['ok']}/{stats['total']} вошли, {stats['failed']} ошибок.",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data["admin_state"] = ""
        else:
            await update.message.reply_text(
                "❌ Не удалось распознать аккаунты. Формат: `email:password:proxy`",
                parse_mode=ParseMode.MARKDOWN
            )
        return

    if state == "add_balance":
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            await update.message.reply_text("❌ `USER_ID СУММА [комментарий]`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[0]); amount = float(parts[1]); comment = parts[2] if len(parts) > 2 else "Admin top-up"
        except Exception:
            await update.message.reply_text("❌ Неверный формат."); return
        target = await db.get_user(target_id)
        if not target:
            await update.message.reply_text(f"❌ Пользователь {target_id} не найден."); return
        await db.add_balance(target_id, amount, comment, uid)
        await update.message.reply_text(
            f"✅ +*${amount:.2f}* для `{target_id}`\nБаланс: ${target.get('balance',0)+amount:.2f}",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await context.bot.send_message(target_id, f"💳 +${amount:.2f}\n{comment}", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        context.user_data["admin_state"] = ""
        return

    if state == "add_enf_account":
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            await update.message.reply_text("❌ `email password [proxy]`", parse_mode=ParseMode.MARKDOWN)
            return
        email, password = parts[0], parts[1]
        proxy = parts[2] if len(parts) > 2 else ""
        await _add_single_account(update, email, password, proxy)
        context.user_data["admin_state"] = ""
        return

    if state == "set_markup":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ `USER_ID ПРОЦЕНТ`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[0]); pct = float(parts[1])
        except Exception:
            await update.message.reply_text("❌ Неверный формат."); return
        await db.set_user_markup(target_id, pct)
        await update.message.reply_text(f"✅ Наценка для `{target_id}` = *{pct}%*", parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = ""
        return

    if state == "broadcast":
        users = await db.get_all_users()
        sent = 0
        for u in users:
            try:
                await context.bot.send_message(u["user_id"], f"📢 {text}")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        await update.message.reply_text(f"✅ Рассылка: {sent}/{len(users)}")
        context.user_data["admin_state"] = ""
        return

    if state == "set_price":
        if text.startswith("set_price "):
            parts = text.split()
            if len(parts) == 3:
                await db.set_setting(parts[1], parts[2])
                await update.message.reply_text(f"✅ `{parts[1]}` = `{parts[2]}`", parse_mode=ParseMode.MARKDOWN)
                context.user_data["admin_state"] = ""
                return
        await update.message.reply_text("Формат: `set_price КЛЮЧ ЗНАЧЕНИЕ`", parse_mode=ParseMode.MARKDOWN)
        return

    # ── Global daily limits ────────────────────────────────────────
    if state == "set_limit":
        if text.startswith("set_limit "):
            parts = text.split()
            if len(parts) == 3:
                await db.set_setting(parts[1], parts[2])
                await update.message.reply_text(f"✅ `{parts[1]}` = `{parts[2]}`", parse_mode=ParseMode.MARKDOWN)
                context.user_data["admin_state"] = ""
                return
        await update.message.reply_text("Формат: `set_limit КЛЮЧ ЗНАЧЕНИЕ`", parse_mode=ParseMode.MARKDOWN)
        return

    # ── Per-user daily limit ───────────────────────────────────────
    if state == "set_user_limit":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ `USER_ID ЛИМИТ`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[0]); limit_val = int(parts[1])
        except Exception:
            await update.message.reply_text("❌ Неверный формат."); return
        if limit_val == 0:
            await db.set_user_daily_limit(target_id, 0)
            await db.log_admin_action(uid, "set_user_limit", "user", str(target_id), "0 (inherit)")
            await update.message.reply_text(f"✅ Лимит для `{target_id}` сброшен (наследуется)", parse_mode=ParseMode.MARKDOWN)
        else:
            await db.set_user_daily_limit(target_id, limit_val)
            await db.log_admin_action(uid, "set_user_limit", "user", str(target_id), f"{limit_val}/day")
            await update.message.reply_text(f"✅ Лимит для `{target_id}` = *{limit_val}* запросов/день", parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = ""
        return

    # ── Set admin ────────────────────────────────────────────────
    if text.startswith("setadmin "):
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ `setadmin USER_ID`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[1])
        except Exception:
            await update.message.reply_text("❌ Неверный USER_ID."); return
        await db.set_admin(target_id, True)
        await db.log_admin_action(uid, "setadmin", "user", str(target_id), "")
        await update.message.reply_text(f"✅ `{target_id}` назначен админом", parse_mode=ParseMode.MARKDOWN)
        return

    # ── Remove admin ─────────────────────────────────────────────
    if text.startswith("removeadmin ") or text.startswith("rmadmin "):
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ `removeadmin USER_ID`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[1])
        except Exception:
            await update.message.reply_text("❌ Неверный USER_ID."); return
        await db.set_admin(target_id, False)
        await db.log_admin_action(uid, "removeadmin", "user", str(target_id), "")
        await update.message.reply_text(f"✅ С админа `{target_id}` сняты права", parse_mode=ParseMode.MARKDOWN)
        return

    # ── Bot control commands ──────────────────────────────────────
    if text.startswith("reloadpool"):
        await update.message.reply_text("⏳ Перезагрузка пула...")
        accounts = await db.get_sb_accounts()
        enf_pool.load(accounts)
        stats = await enf_pool.login_all()
        for acc in enf_pool.accounts:
            await db.update_sb_account_status(acc.email, acc.status, acc.balance, acc.init_balance)
        await update.message.reply_text(
            f"✅ ENF пул: {stats['ok']}/{stats['total']} OK\n"
            f"🌐 Usfull: {uf_engine.active_count()}/{len(uf_engine.accounts)} OK",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if text.startswith("reloadenf"):
        accounts = await db.get_sb_accounts()
        enf_pool.load(accounts)
        stats = await enf_pool.login_all()
        for acc in enf_pool.accounts:
            await db.update_sb_account_status(acc.email, acc.status, acc.balance, acc.init_balance)
        await update.message.reply_text(f"✅ ENF: {stats['ok']}/{stats['total']} OK", parse_mode=ParseMode.MARKDOWN)
        return

    if text.startswith("reloaduf"):
        uf_accounts = await db.get_usfull_accounts()
        if uf_accounts:
            uf_engine.load_accounts(uf_accounts)
        await update.message.reply_text(
            f"✅ Usfull: {uf_engine.active_count()}/{len(uf_engine.accounts)} OK",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if text.startswith("gc") or text.startswith("clearcache"):
        enf_pool.clear_cache()
        uf_engine.clear_cache()
        await update.message.reply_text("✅ Кэш очищен", parse_mode=ParseMode.MARKDOWN)
        return

    if text.startswith("pause"):
        enf_pool.pause()
        await update.message.reply_text("⏸ ENF пул приостановлен", parse_mode=ParseMode.MARKDOWN)
        return

    if text.startswith("resume"):
        enf_pool.resume()
        await update.message.reply_text("▶️ ENF пул возобновлён", parse_mode=ParseMode.MARKDOWN)
        return

    # ── User search ──────────────────────────────────────────────
    if context.user_data.get("admin_state") == "user_search":
        result = await db.find_user(text.strip())
        if not result:
            await update.message.reply_text("❌ Не найдено.", parse_mode=ParseMode.MARKDOWN)
        elif isinstance(result, list):
            lines = [f"🔎 *Найдено: {len(result)}*\n"]
            for u in result:
                status = "🚫" if u.get("is_banned") else ("👑" if u.get("is_admin") else "👤")
                lines.append(
                    f"{status} `{u['user_id']}` @{u.get('username','?')} "
                    f"— ${u.get('balance',0):.2f} — {u.get('searches',0)} поисков"
                )
            await update.message.reply_text("\n".join(lines), reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        else:
            u = result
            status = "🚫" if u.get("is_banned") else ("👑" if u.get("is_admin") else "👤")
            text_out = (
                f"{status} `{u['user_id']}` @{u.get('username','?')}\n"
                f"💰 Баланс: ${u.get('balance',0):.2f}\n"
                f"🔍 Поисков: {u.get('searches',0)}\n"
                f"🔢 Дневной лимит: {u.get('daily_limit', 0) or 'по умолчанию'}\n"
                f"💸 Потрачено: ${u.get('total_spent',0):.2f}\n"
                f"📊 Наценка: {u.get('markup_pct',0)}%\n"
                f"🗓 Создан: {u.get('created_at','')[:10]}\n"
                f"🕐 Последний: {u.get('last_seen','')[:16]}"
            )
            await update.message.reply_text(text_out, reply_markup=kb_admin(), parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = ""
        return

    # ── Ban user ─────────────────────────────────────────────────
    if context.user_data.get("admin_state") == "ban_user":
        parts = text.split(maxsplit=1)
        if not parts:
            await update.message.reply_text("❌ `USER_ID причина`")
            return
        try:
            target_id = int(parts[0])
        except Exception:
            await update.message.reply_text("❌ Неверный USER_ID")
            return
        reason = parts[1] if len(parts) > 1 else "No reason specified"
        await db.set_banned(target_id, True)
        await db.log_admin_action(uid, "ban", "user", str(target_id), reason)
        await update.message.reply_text(
            f"🚫 Пользователь `{target_id}` забанен.\nПричина: {reason}",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await context.bot.send_message(target_id, f"⛔ Ваш аккаунт заблокирован.\nПричина: {reason}")
        except Exception:
            pass
        context.user_data["admin_state"] = ""
        return

    # ── Add balance → also log ────────────────────────────────────
    if state == "add_balance":
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            await update.message.reply_text("❌ `USER_ID СУММА [комментарий]`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[0]); amount = float(parts[1]); comment = parts[2] if len(parts) > 2 else "Admin top-up"
        except Exception:
            await update.message.reply_text("❌ Неверный формат."); return
        target = await db.get_user(target_id)
        if not target:
            await update.message.reply_text(f"❌ Пользователь {target_id} не найден."); return
        await db.add_balance(target_id, amount, comment, uid)
        await db.log_admin_action(uid, "add_balance", "user", str(target_id), f"+${amount:.2f} — {comment}")
        await update.message.reply_text(
            f"✅ +*${amount:.2f}* для `{target_id}`\nБаланс: ${target.get('balance',0)+amount:.2f}",
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await context.bot.send_message(target_id, f"💳 +${amount:.2f}\n{comment}", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        context.user_data["admin_state"] = ""
        return

    # ── Add Usfull account ─────────────────────────────────────────
    if context.user_data.get("admin_state") == "add_uf_account":
        parts = text.split(maxsplit=3)
        if len(parts) < 3:
            await update.message.reply_text("❌ `username password api_key [proxy]`", parse_mode=ParseMode.MARKDOWN)
            return
        username, password, api_key = parts[0], parts[1], parts[2]
        proxy = parts[3] if len(parts) > 3 else ""
        await db.upsert_usfull_account(username, password, api_key, proxy)
        accounts = await db.get_usfull_accounts()
        uf_engine.load_accounts(accounts)
        await db.log_admin_action(uid, "add_usfull_account", "usfull", username, f"proxy={proxy[:30]}")
        await update.message.reply_text(
            f"✅ Usfull аккаунт `{username}` добавлен",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data["admin_state"] = ""
        return

    # ── Add ENF account → also log ──────────────────────────────
    if state == "add_enf_account":
        parts = text.split(maxsplit=2)
        if len(parts) < 2:
            await update.message.reply_text("❌ `email password [proxy]`", parse_mode=ParseMode.MARKDOWN)
            return
        email, password = parts[0], parts[1]
        proxy = parts[2] if len(parts) > 2 else ""
        await _add_single_account(update, email, password, proxy)
        await db.log_admin_action(uid, "add_enf_account", "enf", email)
        context.user_data["admin_state"] = ""
        return

    if state == "set_markup":
        parts = text.split()
        if len(parts) < 2:
            await update.message.reply_text("❌ `USER_ID ПРОЦЕНТ`", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            target_id = int(parts[0]); pct = float(parts[1])
        except Exception:
            await update.message.reply_text("❌ Неверный формат."); return
        await db.set_user_markup(target_id, pct)
        await db.log_admin_action(uid, "set_markup", "user", str(target_id), f"{pct}%")
        await update.message.reply_text(f"✅ Наценка для `{target_id}` = *{pct}%*", parse_mode=ParseMode.MARKDOWN)
        context.user_data["admin_state"] = ""
        return

    if state == "broadcast":
        users = await db.get_all_users()
        sent = 0
        for u in users:
            try:
                await context.bot.send_message(u["user_id"], f"📢 {text}")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        await db.log_admin_action(uid, "broadcast", "all_users", "", text[:100])
        await update.message.reply_text(f"✅ Рассылка: {sent}/{len(users)}")
        context.user_data["admin_state"] = ""
        return


# ── Background tasks ────────────────────────────────────────────────

async def balance_monitor(app: Application):
    """Monitor ENF account balance every 30 min (doesn't cost tokens — checks status only)."""
    while True:
        await asyncio.sleep(1800)  # every 30 min, not 5
        for acc in enf_pool.accounts:
            if acc.status in ("active", "low_balance"):
                # Use lightweight check — don't spend tokens
                try:
                    await enf_pool.refresh_balance(acc)
                    await db.update_sb_account_status(
                        acc.email, acc.status, acc.balance, acc.init_balance
                    )
                except Exception as e:
                    logger.error(f"[Monitor] Error refreshing {acc.email}: {e}")
        logger.info(f"[Monitor] Balance check. Active: {enf_pool.active_count()}/{len(enf_pool.accounts)}")


# ── API Key Management ─────────────────────────────────────────────────────

async def cmd_apikey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await db.get_user(uid):
        await update.message.reply_text("\u274c \u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u043d\u0430\u0447\u043d\u0438\u0442\u0435: /start")
        return
    args = context.args or []
    action = args[0] if args else "list"

    if action == "tiers":
        await update.message.reply_text(
            "\u2b50 *API Tiers*\n\n"
            "*Starter* \u2014 $29.99/\u043c\u0435\u0441\n"
            "\u2514 100 \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432/\u0434\u0435\u043d\u044c | 10/\u043c\u0438\u043d\n\n"
            "*Pro* \u2014 $99.99/\u043c\u0435\u0441\n"
            "\u2514 500 \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432/\u0434\u0435\u043d\u044c | 30/\u043c\u0438\u043d\n\n"
            "*Enterprise* \u2014 $299.99/\u043c\u0435\u0441\n"
            "\u2514 2,000 \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432/\u0434\u0435\u043d\u044c | 60/\u043c\u0438\u043d\n\n"
            "*Unlimited* \u2014 $999.99/\u043c\u0435\u0441\n"
            "\u2514 \u0411\u0435\u0437\u043b\u0438\u043c\u0438\u0442 | 300/\u043c\u0438\u043d\n\n"
            "_\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435: /apikey upgrade <tier>_",
            parse_mode=ParseMode.MARKDOWN)
        return

    if action == "create":
        label = args[1] if len(args) > 1 else "default"
        k = await db.create_api_key(uid, label)
        await update.message.reply_text(
            f"\u2705 *API Key \u0441\u043e\u0437\u0434\u0430\u043d*\n\n`{k['api_key']}`\n\n"
            f"*tier:* {k.get('tier','starter')} | *\u043b\u0438\u043c\u0438\u0442:* {k.get('daily_limit',100)}/\u0434\u0435\u043d\u044c | *rate:* {k.get('rate_limit',10)}/\u043c\u0438\u043d\n\n"
            f"\u26a0\ufe0f *\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u0435 \u043a\u043b\u044e\u0447!*",
            parse_mode=ParseMode.MARKDOWN)
        return

    if action == "revoke":
        if len(args) < 2:
            keys = await db.get_api_keys_for_user(uid)
            txt = "\u2b50 *\u0412\u0430\u0448\u0438 \u043a\u043b\u044e\u0447\u0438:*\n\n"
            txt += "\n".join(f"`{x['api_key'][:24]}...` \u2014 {x.get('label','default')} (id={x['id']})" for x in keys) if keys else "\u043d\u0435\u0442"
            txt += "\n\n_/apikey revoke <id>_"
            await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
            return
        try:
            ok = await db.revoke_api_key(int(args[1]), uid)
        except ValueError:
            ok = False
        await update.message.reply_text("\u2705 \u043a\u043b\u044e\u0447 \u043e\u0442\u043e\u0437\u0432\u0430\u043d" if ok else "\u274c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d")
        return

    if action == "upgrade":
        if len(args) < 2:
            await update.message.reply_text("\u274c /apikey upgrade <tier> (starter|pro|enterprise|unlimited)")
            return
        tier = args[1].lower()
        if tier not in ("starter", "pro", "enterprise", "unlimited"):
            await update.message.reply_text("\u274c starter, pro, enterprise, unlimited")
            return
        keys = await db.get_api_keys_for_user(uid)
        if not keys:
            await update.message.reply_text("\u274c \u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u043a\u043b\u044e\u0447: /apikey create")
            return
        await db.update_api_key_tier(keys[0]["id"], uid, tier)
        s = await db.get_api_tier_settings(tier)
        await update.message.reply_text(
            f"\u2705 Tier: *{tier.upper()}*\n\u0417\u0430\u043f\u0440\u043e\u0441\u043e\u0432: {int(s.get('daily',100))}/\u0434\u0435\u043d\u044c\n\u0426\u0435\u043d\u0430: ${s.get('cost',0):.2f}/\u043c\u0435\u0441",
            parse_mode=ParseMode.MARKDOWN)
        return

    # list
    keys = await db.get_api_keys_for_user(uid)
    if not keys:
        await update.message.reply_text(
            "\ud83d\udd11 *API Keys*\n\n\u043d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u043a\u043b\u044e\u0447\u0435\u0439.\n\n/apikey create",
            parse_mode=ParseMode.MARKDOWN)
        return
    lines = ["\ud83d\udd11 *API Keys*"]
    for k in keys:
        r = max(0, k.get("daily_limit",100) - k.get("searches_today",0))
        lines.append(f"`{k['api_key'][:20]}...`  tier:{k.get('tier')}  {k.get('searches_today',0)}/{k.get('daily_limit',100)} ({r} \u043e\u0441\u0442)  id={k['id']}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    keys = await db.get_api_keys_for_user(uid)
    if not keys:
        await update.message.reply_text("\u2b50 \u041d\u0435\u0442 API \u043a\u043b\u044e\u0447\u0430. /apikey create")
        return
    k = keys[0]
    s = await db.get_api_tier_settings(k.get("tier","starter"))
    await update.message.reply_text(
        f"\u2b50 *API Active*\n\n`{k['api_key'][:30]}...`\n\n"
        f"tier: *{k.get('tier','starter').upper()}*\n"
        f"\u0441\u0435\u0433\u043e\u0434\u043d\u044f: {k.get('searches_today',0)}/{k.get('daily_limit',100)}\n"
        f"\u0432\u0441\u0435\u0433\u043e: {k.get('total_requests',0)}\n\n"
        f"${s.get('cost',0):.2f}/\u043c\u0435\u0441",
        parse_mode=ParseMode.MARKDOWN)

# ── Startup ─────────────────────────────────────────────────────────

async def post_init(app: Application):
    global _app_ref
    _app_ref = app

    await db.init_db()

    enf_pool.set_alert_callback(_alert_admin)

    accounts = await db.get_sb_accounts()
    if accounts:
        enf_pool.load(accounts)
        logger.info(f"Loaded {len(accounts)} Enformion accounts")
        stats = await enf_pool.login_all()
        logger.info(f"ENF login: {stats['ok']}/{stats['total']} OK, {stats['failed']} failed")
        for acc in enf_pool.accounts:
            await db.update_sb_account_status(acc.email, acc.status, acc.balance, acc.init_balance)
    else:
        logger.warning("No ENF accounts in DB. Use /loadaccounts or /addaccount")

    await app.bot.set_my_commands([
        BotCommand("start",          "Главное меню"),
        BotCommand("balance",        "Ваш баланс"),
        BotCommand("health",         "Статус бота"),
        BotCommand("admin",          "Панель администратора"),
        BotCommand("enfstatus",      "Статус пула ENF аккаунтов"),
        BotCommand("loadaccounts",   "Загрузить файл аккаунтов"),
        BotCommand("addaccount",     "Добавить ENF аккаунт"),
        BotCommand("reloadpool",     "Перезагрузить пул"),
        BotCommand("setadmin",       "Назначить админа"),
        BotCommand("setadminchat",   "Чат для алертов"),
        BotCommand("ban",            "Забанить пользователя"),
        BotCommand("unban",          "Разбанить"),
        BotCommand("setufkey",       "API ключ usfull.pro"),
        BotCommand("setpayment",     "Настроить платежи"),
        BotCommand("shutdown",       "Остановить бота (admin)"),
        BotCommand(command="apikey", description="Управление API ключами"),
        BotCommand(command="api", description="Статус API"),
    ])

    # Load payment settings
    cb_token = await db.get_setting("cryptobot_token")
    if cb_token:
        payment_mgr.setup_cryptobot(cb_token)
    hk_key = await db.get_setting("heleket_api_key")
    hk_sec = await db.get_setting("heleket_secret")
    if hk_key and hk_sec:
        payment_mgr.setup_heleket(hk_key, hk_sec)
    bp_url = await db.get_setting("btcpay_base_url")
    bp_key = await db.get_setting("btcpay_api_key")
    bp_sid = await db.get_setting("btcpay_store_id")
    if bp_url and bp_key and bp_sid:
        payment_mgr.setup_btcpay(bp_url, bp_key, bp_sid)
        logger.info("BTCPayServer loaded from DB")

    # Load usfull API key
    uf_key = await db.get_setting("usfull_api_key")
    if uf_key:
        uf_engine.api_key = uf_key
        logger.info("Usfull API key loaded")

    # Load usfull accounts from DB
    uf_accounts = await db.get_usfull_accounts()
    if uf_accounts:
        uf_engine.load_accounts(uf_accounts)
        uf_engine.set_alert_callback(_alert_usfull)
        logger.info(f"Loaded {len(uf_accounts)} Usfull accounts")

    asyncio.create_task(balance_monitor(app))
    logger.info("Bot started!")


# ── Health check ────────────────────────────────────────────────────

async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = enf_pool.status_report()
    total = len(status)
    active = sum(1 for s in status if s["status"] in ("active", "low_balance"))
    errors = enf_pool._error_window
    error_rate = sum(errors) / len(errors) if errors else 0.0
    await update.message.reply_text(
        f"✅ *Бот работает*\n"
        f"🔧 Аккаунты: {active}/{total}\n"
        f"📊 Error rate: {error_rate:.0%} ({len(errors)} samples)\n"
        f"🔒 Pool ok: {'Да' if enf_pool._pool_ok else 'Нет'}",
        parse_mode=ParseMode.MARKDOWN
    )


# ── Graceful shutdown ──────────────────────────────────────────────

_shutdown_event: Optional[asyncio.Event] = None

async def cmd_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏳ Остановка бота...", parse_mode=ParseMode.MARKDOWN)
    if _shutdown_event:
        _shutdown_event.set()


def _init_shutdown_handler():
    global _shutdown_event
    _shutdown_event = asyncio.Event()
    import signal
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda s, f: (
                logger.info(f"Received {s}, requesting shutdown"),
                _shutdown_event.set() if _shutdown_event else None
            ))
        except (OSError, ValueError):
            pass  # Windows signal handling


# ── Main ────────────────────────────────────────────────────────────

def main():
    import socket
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

    # PID lock — предотвращение multiple instances
    import os, sys
    pidfile = Path("data/bot.pid")
    if pidfile.exists():
        old_pid = pidfile.read_text().strip()
        if old_pid and old_pid.isdigit():
            try:
                os.kill(int(old_pid), 0)
                logger.critical(f"Another instance already running (PID {old_pid}). Exiting.")
                sys.exit(1)
            except ProcessLookupError:
                logger.warning(f"Stale PID file (PID {old_pid} is dead). Removing.")
        pidfile.unlink()
    pidfile.write_text(str(os.getpid()))
    logger.info(f"PID lock acquired: {os.getpid()}")

    _init_shutdown_handler()

    # Force IPv4 to avoid httpx.ConnectTimeout on macOS with IPv6
    import socket
    original_getaddrinfo = socket.getaddrinfo
    def getaddrinfo_ipv4(*args):
        results = original_getaddrinfo(*args)
        return [r for r in results if r[0] == socket.AF_INET]
    socket.getaddrinfo = getaddrinfo_ipv4
    logger.info("Forced IPv4 for DNS resolution")

    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        connect_timeout=15,
        read_timeout=15,
        connection_pool_size=8,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("admin",         cmd_admin))
    app.add_handler(CommandHandler("balance",       cmd_balance))
    app.add_handler(CommandHandler("health",        cmd_health))
    app.add_handler(CommandHandler("enfstatus",     cmd_enfstatus))
    app.add_handler(CommandHandler("addaccount",    cmd_addaccount))
    app.add_handler(CommandHandler("loadaccounts",  cmd_loadaccounts))
    app.add_handler(CommandHandler("reloadpool",    cmd_reloadpool))
    app.add_handler(CommandHandler("setadmin",      cmd_setadmin))
    app.add_handler(CommandHandler("setadminchat",  cmd_setadminchat))
    app.add_handler(CommandHandler("ban",           cmd_ban))
    app.add_handler(CommandHandler("unban",          cmd_unban))
    app.add_handler(CommandHandler("setufkey",       cmd_setufkey))
    app.add_handler(CommandHandler("setpayment",     cmd_setpayment))
    app.add_handler(CommandHandler("shutdown", cmd_shutdown))
    app.add_handler(CommandHandler("apikey", cmd_apikey))
    app.add_handler(CommandHandler("api", cmd_api))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.Document.ALL) & ~filters.COMMAND,
        on_message
    ))

    logger.info("Starting polling...")
    import urllib.request
    import time
    for attempt in range(5):
        try:
            # Close any old pollers
            if attempt > 0:
                try:
                    urllib.request.urlopen(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/close",
                        timeout=15
                    )
                    logger.info(f"Closed old session (attempt {attempt+1})")
                except Exception as e:
                    logger.warning(f"Failed to close: {e}")
                time.sleep(8)

            app2 = (
                Application.builder()
                .token(BOT_TOKEN)
                .post_init(post_init)
                .build()
            )
            app2.add_handler(CommandHandler("start", cmd_start))
            app2.add_handler(CommandHandler("admin", cmd_admin))
            app2.add_handler(CommandHandler("balance", cmd_balance))
            app2.add_handler(CommandHandler("health", cmd_health))
            app2.add_handler(CommandHandler("enfstatus", cmd_enfstatus))
            app2.add_handler(CommandHandler("addaccount", cmd_addaccount))
            app2.add_handler(CommandHandler("loadaccounts", cmd_loadaccounts))
            app2.add_handler(CommandHandler("reloadpool", cmd_reloadpool))
            app2.add_handler(CommandHandler("setadmin", cmd_setadmin))
            app2.add_handler(CommandHandler("setadminchat", cmd_setadminchat))
            app2.add_handler(CommandHandler("ban", cmd_ban))
            app2.add_handler(CommandHandler("unban", cmd_unban))
            app2.add_handler(CommandHandler("setufkey", cmd_setufkey))
            app2.add_handler(CommandHandler("setpayment", cmd_setpayment))
            app2.add_handler(CommandHandler("shutdown", cmd_shutdown))
            app2.add_handler(CommandHandler("apikey", cmd_apikey))
            app2.add_handler(CommandHandler("api", cmd_api))
            app2.add_handler(CallbackQueryHandler(on_callback))
            app2.add_handler(MessageHandler(
                (filters.TEXT | filters.Document.ALL) & ~filters.COMMAND,
                on_message
            ))
            import asyncio
            asyncio.run(app2.bot.delete_webhook(drop_pending_updates=True))
            time.sleep(3)
            app2.run_polling(drop_pending_updates=True)
            return
        except TelegramError:
            logger.error(f"Polling failed (attempt {attempt+1}/5)")
            if attempt >= 4:
                logger.error("All retry attempts failed")
                raise


if __name__ == "__main__":
    main()
