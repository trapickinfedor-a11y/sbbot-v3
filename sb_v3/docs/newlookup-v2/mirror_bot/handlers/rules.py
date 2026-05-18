from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.media_library import resolve_bot_photo

router = Router()

RULES_PHOTO = resolve_bot_photo("rules", "правила", fallback_path="media/правила.jpg")
CALL_SERVICE_PHOTO = resolve_bot_photo("call_service", "поддержка", fallback_path="media/поддержка.png")
REFERRAL_PHOTO = resolve_bot_photo("referral", "реф", fallback_path="media/реф.jpg")


@router.message(F.text.in_(ButtonTexts.get_all_variants("SERVICE_RULES")))
async def rules_handler(message: Message, texts, buttons):
    """Legacy handler — kept for users who still have old keyboard"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        await message.answer_photo(photo=RULES_PHOTO)
        await message.answer(texts.RULES_TEXT, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending rules photo: {e}")
        await message.answer(texts.RULES_TEXT, parse_mode="Markdown")


@router.message(F.text.in_(ButtonTexts.get_all_variants("CALL_SERVICE")))
async def call_service_handler(message: Message, texts, buttons):
    import logging
    logger = logging.getLogger(__name__)
    try:
        await message.answer_photo(photo=CALL_SERVICE_PHOTO)
        await message.answer(texts.CALL_SERVICE_TEXT, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending call service photo: {e}")
        await message.answer(texts.CALL_SERVICE_TEXT, parse_mode="Markdown")


@router.message(F.text.in_(ButtonTexts.get_all_variants("REFERRALS")))
async def referrals_shortcut_handler(message: Message, session, mirror_bot_id: int, texts, buttons):
    from mirror_bot.services.user_service import UserService
    from mirror_bot.config import mirror_bot_config
    import json
    from sqlalchemy import select as _select, func as _func
    from shared.database.models import Referral, SystemSetting, User

    user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
    if not user:
        await message.answer(texts.USER_NOT_FOUND)
        return

    ref_stats = await UserService.get_referral_stats(session, message.from_user.id)

    # Load configured rates
    rates_row = await session.scalar(_select(SystemSetting).where(SystemSetting.key == "referral_rates"))
    try:
        rates = {**{"1": 5.0, "2": 3.0, "3": 2.0, "4": 1.0}, **(json.loads(rates_row.value) if rates_row else {})}
    except Exception:
        rates = {"1": 5.0, "2": 3.0, "3": 2.0, "4": 1.0}

    # Count chain levels
    total_in_chain = ref_stats["count"]
    ref_link = f"https://t.me/{mirror_bot_config.main_bot_username}?start={user.referral_link}"

    text = (
        f"🤝 *Referral Program — up to +12%*\n\n"
        f"Your referral link:\n`{ref_link}`\n\n"
        f"💰 Total earned: *${ref_stats['earned']:.2f}*\n"
        f"👥 Direct referrals: *{total_in_chain}*\n\n"
        f"📊 *4-level system:* every purchase in your chain earns you a bonus on your balance — automatically.\n\n"
        f"Share your link and earn from every order your referrals make!"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Copy Ref Link", url=ref_link)],
    ])

    try:
        await message.answer_photo(photo=REFERRAL_PHOTO, caption=text, reply_markup=kb)
    except Exception:
        await message.answer(text, reply_markup=kb)
