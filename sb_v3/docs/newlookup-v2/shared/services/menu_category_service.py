from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import MirrorMenuCategory


DEFAULT_MENU_CATEGORIES = [
    # Row 5 — Education (standalone)
    {
        "code": "education",
        "route_key": "education",
        "count_key": "education",
        "label_en": "📚 Education",
        "label_ru": "📚 Education",
        "label_zh": "📚 Education",
        "label_es": "📚 Education",
        "row_index": 5,
        "position": 10,
    },
    # Row 10 — Profile | Top-up
    {
        "code": "my_profile",
        "route_key": "my_profile",
        "count_key": None,
        "label_en": "👤 My profile",
        "label_ru": "👤 My profile",
        "label_zh": "👤 My profile",
        "label_es": "👤 My profile",
        "row_index": 10,
        "position": 10,
    },
    {
        "code": "topup_balance",
        "route_key": "topup_balance",
        "count_key": None,
        "label_en": "💳 Top-up balance",
        "label_ru": "💳 Top-up balance",
        "label_zh": "💳 Top-up balance",
        "label_es": "💳 Top-up balance",
        "row_index": 10,
        "position": 20,
    },
    # Row 20 — Search | Credit Reports
    {
        "code": "search",
        "route_key": "search",
        "count_key": None,
        "label_en": "🔎 Search",
        "label_ru": "🔎 Search",
        "label_zh": "🔎 Search",
        "label_es": "🔎 Search",
        "row_index": 20,
        "position": 10,
    },
    {
        "code": "credit_reports",
        "route_key": "credit_reports",
        "count_key": None,
        "label_en": "📈 CREDIT REPORTS",
        "label_ru": "📈 CREDIT REPORTS",
        "label_zh": "📈 CREDIT REPORTS",
        "label_es": "📈 CREDIT REPORTS",
        "row_index": 20,
        "position": 20,
    },
    # Row 30 — Banks | Accounts
    {
        "code": "banks",
        "route_key": "banks",
        "count_key": "banks",
        "label_en": "🏦 BANKS",
        "label_ru": "🏦 BANKS",
        "label_zh": "🏦 BANKS",
        "label_es": "🏦 BANKS",
        "row_index": 30,
        "position": 10,
    },
    {
        "code": "accounts",
        "route_key": "accounts",
        "count_key": "accounts",
        "label_en": "🧾 Subscriptions / Accounts",
        "label_ru": "🧾 Subscriptions / Accounts",
        "label_zh": "🧾 Subscriptions / Accounts",
        "label_es": "🧾 Subscriptions / Accounts",
        "row_index": 30,
        "position": 20,
    },
    # Row 40 — CC (standalone)
    {
        "code": "cc",
        "route_key": "cc",
        "count_key": "cc",
        "label_en": "💳 CC",
        "label_ru": "💳 CC",
        "label_zh": "💳 CC",
        "label_es": "💳 CC",
        "row_index": 40,
        "position": 10,
    },
    # Row 50 — Pros & Fullz | Documents
    {
        "code": "pros_fullz",
        "route_key": "pros_fullz",
        "count_key": "fullz",
        "label_en": "🧰 PROS & FULLZ",
        "label_ru": "🧰 PROS & FULLZ",
        "label_zh": "🧰 PROS & FULLZ",
        "label_es": "🧰 PROS & FULLZ",
        "row_index": 50,
        "position": 10,
    },
    {
        "code": "documents",
        "route_key": "documents",
        "count_key": "documents",
        "label_en": "📄 DOCUMENTS",
        "label_ru": "📄 DOCUMENTS",
        "label_zh": "📄 DOCUMENTS",
        "label_es": "📄 DOCUMENTS",
        "row_index": 50,
        "position": 20,
    },
    # Row 60 — Add info in CR | eSIM
    {
        "code": "add_info_cr",
        "route_key": "add_info_cr",
        "count_key": None,
        "label_en": "✍️ Add info in CR",
        "label_ru": "✍️ Add info in CR",
        "label_zh": "✍️ Add info in CR",
        "label_es": "✍️ Add info in CR",
        "row_index": 60,
        "position": 10,
    },
    {
        "code": "esim",
        "route_key": "esim",
        "count_key": None,
        "label_en": "📶 eSIM",
        "label_ru": "📶 eSIM",
        "label_zh": "📶 eSIM",
        "label_es": "📶 eSIM",
        "row_index": 60,
        "position": 20,
    },
    # Row 70 — Support | Referrals
    {
        "code": "support",
        "route_key": "support",
        "count_key": None,
        "label_en": "📞 Support",
        "label_ru": "📞 Support",
        "label_zh": "📞 Support",
        "label_es": "📞 Support",
        "row_index": 70,
        "position": 10,
    },
    {
        "code": "referrals",
        "route_key": "referrals",
        "count_key": None,
        "label_en": "🤝 Referrals +12%",
        "label_ru": "🤝 Referrals +12%",
        "label_zh": "🤝 Referrals +12%",
        "label_es": "🤝 Referrals +12%",
        "row_index": 70,
        "position": 20,
    },
    # Row 80 — Other Services (standalone)
    {
        "code": "another_services",
        "route_key": "another_services",
        "count_key": None,
        "label_en": "📞 Other Services",
        "label_ru": "📞 Other Services",
        "label_zh": "📞 Other Services",
        "label_es": "📞 Other Services",
        "row_index": 80,
        "position": 10,
    },
    # Row 90 — VIP Watchlist (standalone)
    {
        "code": "vip_watchlist",
        "route_key": "vip_watchlist",
        "count_key": None,
        "label_en": "🌟 VIP Watchlist — $500",
        "label_ru": "🌟 VIP Watchlist — $500",
        "label_zh": "🌟 VIP Watchlist — $500",
        "label_es": "🌟 VIP Watchlist — $500",
        "row_index": 90,
        "position": 10,
    },
]

# Codes that were previously in the main menu but should no longer be shown there.
# They are now accessible as sub-sections within BANKS / CC.
_DEPRECATED_MAIN_MENU_CODES = {
    "nfc", "enroll", "selfreg_ba", "logs", "otp_card",
    "selfreg_cc", "checks", "call_service", "lookup",
}


class MenuCategoryService:
    @staticmethod
    async def ensure_defaults(session: AsyncSession) -> None:
        existing = (await session.execute(select(MirrorMenuCategory))).scalars().all()
        existing_map = {cat.code: cat for cat in existing}

        changed = False

        # Deactivate deprecated codes
        for code in _DEPRECATED_MAIN_MENU_CODES:
            if code in existing_map and existing_map[code].is_active:
                existing_map[code].is_active = False
                changed = True

        # Add or update default categories
        default_codes = {item["code"] for item in DEFAULT_MENU_CATEGORIES}
        for item in DEFAULT_MENU_CATEGORIES:
            if item["code"] not in existing_map:
                session.add(MirrorMenuCategory(**item))
                changed = True
            else:
                cat = existing_map[item["code"]]
                # Restore if was deactivated, and sync row/position
                updated = False
                if not cat.is_active:
                    cat.is_active = True
                    updated = True
                if cat.row_index != item["row_index"] or cat.position != item["position"]:
                    cat.row_index = item["row_index"]
                    cat.position = item["position"]
                    updated = True
                if updated:
                    changed = True

        if changed:
            await session.commit()

    @staticmethod
    def get_label(category: MirrorMenuCategory, language: str) -> str:
        language = (language or "en").lower()
        if language == "ru" and category.label_ru:
            return category.label_ru
        if language == "zh" and category.label_zh:
            return category.label_zh
        if language == "es" and category.label_es:
            return category.label_es
        return category.label_en

    @staticmethod
    async def list_categories(
        session: AsyncSession,
        *,
        active_only: bool = False,
    ) -> list[MirrorMenuCategory]:
        await MenuCategoryService.ensure_defaults(session)
        query = select(MirrorMenuCategory)
        if active_only:
            query = query.where(MirrorMenuCategory.is_active == True)
        query = query.order_by(
            MirrorMenuCategory.row_index,
            MirrorMenuCategory.position,
            MirrorMenuCategory.id,
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_keyboard_payload(
        session: AsyncSession,
        *,
        language: str,
        active_only: bool = True,
    ) -> list[dict]:
        categories = await MenuCategoryService.list_categories(
            session,
            active_only=active_only,
        )
        return [
            {
                "code": category.code,
                "route_key": category.route_key,
                "count_key": category.count_key,
                "row_index": category.row_index,
                "position": category.position,
                "display_text": MenuCategoryService.get_label(category, language),
            }
            for category in categories
        ]

    @staticmethod
    def _iter_labels(category: MirrorMenuCategory) -> Iterable[str]:
        for value in (
            category.label_en,
            category.label_ru,
            category.label_zh,
            category.label_es,
        ):
            if value:
                yield value

    @staticmethod
    async def resolve_route_by_text(
        session: AsyncSession,
        text: str | None,
    ) -> str | None:
        from mirror_bot.constants.buttons_en import ButtonTexts

        normalized = ButtonTexts.strip_count_suffix(text)
        if not normalized:
            return None

        categories = await MenuCategoryService.list_categories(session, active_only=True)
        for category in categories:
            labels = {
                ButtonTexts.strip_count_suffix(label)
                for label in MenuCategoryService._iter_labels(category)
            }
            if normalized in labels:
                return category.route_key
        return None
