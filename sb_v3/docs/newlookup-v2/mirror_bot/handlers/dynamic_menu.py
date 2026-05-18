from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.menu_category_service import MenuCategoryService

logger = logging.getLogger(__name__)
router = Router(name="dynamic_menu")

SPECIALS_ROUTE_TO_KIND = {
    "nfc": "nfc",
    "enroll": "enroll",
    "selfreg_ba": "selfreg_ba",
    "logs": "logs",
    "otp_card": "otp_card",
    "selfreg_cc": "selfreg_cc",
    "checks": "checks",
}


class DynamicMenuRouteFilter(Filter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool | dict:
        route_key = await MenuCategoryService.resolve_route_by_text(session, message.text)
        if not route_key:
            return False
        return {"route_key": route_key}


@router.message(DynamicMenuRouteFilter())
async def dynamic_menu_dispatcher(
    message: Message,
    route_key: str,
    session: AsyncSession,
    state: FSMContext,
    mirror_bot_id: int,
    texts,
    buttons,
):
    if route_key == "education":
        from mirror_bot.handlers.education import education_main_handler

        await education_main_handler(message, session, texts, buttons)
        return
    if route_key == "my_profile":
        from mirror_bot.handlers.profile import profile_handler

        await profile_handler(message, session, mirror_bot_id, texts, buttons)
        return
    if route_key == "topup_balance":
        from mirror_bot.handlers.profile import topup_balance_handler

        await topup_balance_handler(message, texts, buttons)
        return
    if route_key in ("search", "lookup"):
        from mirror_bot.handlers.lookup.main import lookup_main_handler

        await lookup_main_handler(message, texts, buttons)
        return
    if route_key == "credit_reports":
        from mirror_bot.handlers.credit_reports import credit_reports_main

        await credit_reports_main(message, texts, buttons)
        return
    if route_key == "documents":
        from mirror_bot.handlers.documents import documents_main_handler

        await documents_main_handler(message, session, texts, buttons)
        return
    if route_key == "pros_fullz":
        from mirror_bot.handlers.fullz import fullz_main_handler

        await fullz_main_handler(message, state, session, texts, buttons)
        return
    if route_key == "banks":
        from mirror_bot.handlers.banks import banks_main_handler

        await banks_main_handler(message, session, texts, buttons)
        return
    if route_key == "accounts":
        from mirror_bot.handlers.accounts import accounts_main_handler

        await accounts_main_handler(message, session, texts, buttons)
        return
    if route_key == "cc":
        from mirror_bot.handlers.cc import cc_main_handler

        await cc_main_handler(message, session, texts, buttons)
        return
    if route_key == "esim":
        from mirror_bot.handlers.esim import esim_main_handler

        await esim_main_handler(message, texts, buttons)
        return
    if route_key == "add_info_cr":
        from mirror_bot.handlers.addinfo import addinfo_main_handler

        await addinfo_main_handler(message, texts, buttons)
        return
    if route_key == "support":
        from mirror_bot.handlers.support import support_button_handler

        await support_button_handler(message, state, texts, buttons)
        return
    if route_key == "referrals":
        from mirror_bot.handlers.rules import referrals_shortcut_handler

        await referrals_shortcut_handler(message, session, mirror_bot_id, texts, buttons)
        return
    if route_key == "another_services":
        from mirror_bot.handlers.another_services import another_services_handler

        await another_services_handler(message, session, texts, buttons)
        return
    if route_key == "vip_watchlist":
        from mirror_bot.handlers.vip_watchlist import vip_watchlist_main_handler
        await vip_watchlist_main_handler(message, session, mirror_bot_id, texts, buttons)
        return
    if route_key in SPECIALS_ROUTE_TO_KIND:
        from mirror_bot.handlers.seller_specials import open_specials_catalog_message

        await open_specials_catalog_message(message, session, SPECIALS_ROUTE_TO_KIND[route_key])
        return

    logger.warning("Unhandled dynamic menu route: %s", route_key)
