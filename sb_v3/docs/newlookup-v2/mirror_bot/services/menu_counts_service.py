from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select

from shared.database.models import (
    AccountCategory,
    AccountItem,
    BankItem,
    BruteBankItem,
    CCCategory,
    CCItem,
    EducationCategory,
    EducationManual,
    EducationSubscription,
    Product,
    Seller,
    SellerBank,
    SellerBankItem,
    SellerCCItem,
    SellerCheckItem,
    SellerEnrollItem,
    SellerLogsItem,
    SellerNFCItem,
    SellerOTPItem,
    SellerSelfregCCItem,
)
from shared.services.menu_count_cache_service import MenuCountCacheService


def _free_bank_stock_expr():
    return SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)


def _free_cc_stock_expr():
    return SellerCCItem.stock_count


class MenuCountService:
    @staticmethod
    def _unknown_map() -> defaultdict[str, str]:
        return defaultdict(lambda: "?")

    @staticmethod
    async def build_documents_counts(session) -> dict:
        result = await session.execute(
            select(Product.service, func.count(Product.id))
            .where(
                Product.category == "docs",
                Product.is_available == True,
                Product.moderation_status == "approved",
            )
            .group_by(Product.service)
        )
        service_counts = {service: int(total or 0) for service, total in result.all()}
        checks_count = int((await session.scalar(
            select(func.count(SellerCheckItem.id))
            .join(Seller)
            .where(
                SellerCheckItem.is_active == True,
                SellerCheckItem.is_in_stock == True,
                SellerCheckItem.moderation_status == "approved",
                Seller.is_approved == True,
                Seller.is_active == True,
            )
        )) or 0)
        return {
            "total": sum(service_counts.values()) + checks_count,
            "by_service": service_counts,
            "checks": checks_count,
        }

    @staticmethod
    async def build_documents_state_counts(session, service_code: str) -> dict[str, int]:
        result = await session.execute(
            select(Product.state, func.count(Product.id))
            .where(
                Product.category == "docs",
                Product.service == service_code,
                Product.is_available == True,
                Product.moderation_status == "approved",
            )
            .group_by(Product.state)
        )
        return {state: int(cnt) for state, cnt in result.all()}

    @staticmethod
    async def get_documents_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("documents")
        if cached is not None:
            cached["by_service"] = defaultdict(lambda: "?", cached.get("by_service") or {})
            return cached
        return {
            "total": "?",
            "by_service": MenuCountService._unknown_map(),
        }

    @staticmethod
    async def build_fullz_counts(session) -> dict:
        result = await session.execute(
            select(Product.service, func.count(Product.id))
            .where(
                Product.category == "pros_fullz",
                Product.is_available == True,
                Product.moderation_status == "approved",
            )
            .group_by(Product.service)
        )
        service_counts = {service: int(total or 0) for service, total in result.all()}
        return {
            "total": sum(service_counts.values()),
            "personal_total": sum(service_counts.values()),
            "business_total": 0,
            "by_service": service_counts,
        }

    @staticmethod
    async def get_fullz_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("fullz")
        if cached is not None:
            cached["by_service"] = defaultdict(lambda: "?", cached.get("by_service") or {})
            return cached
        return {
            "total": "?",
            "personal_total": "?",
            "business_total": "?",
            "by_service": MenuCountService._unknown_map(),
        }

    @staticmethod
    async def build_banks_counts(session) -> dict:
        free_stock_expr = _free_bank_stock_expr()
        category_result = await session.execute(
            select(SellerBank.category, func.coalesce(func.sum(free_stock_expr), 0))
            .join(Seller)
            .where(
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
                free_stock_expr > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            )
            .group_by(SellerBank.category)
        )
        category_counts = {category: int(total or 0) for category, total in category_result.all()}
        section_result = await session.execute(
            select(
                SellerBank.category,
                func.coalesce(func.sum(free_stock_expr), 0).label("available"),
            )
            .join(Seller)
            .where(
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
                free_stock_expr > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            )
            .group_by(SellerBank.category)
        )
        per_order_result = await session.execute(
            select(BankItem.category, func.count(BankItem.id))
            .where(BankItem.section == "order", BankItem.is_active == True)
            .group_by(BankItem.category)
        )
        from mirror_bot.constants.bank_data import BankData

        section_counts: dict[str, dict[str, int]] = defaultdict(dict)
        for category, total in section_result.all():
            section_counts[category]["available"] = int(total or 0)
        for category, total in per_order_result.all():
            section_counts[category]["per_order"] = int(total or 0)
        # Fallback: when BankItem table is empty for a category, use the
        # hardcoded item count so the section keyboard shows a real number.
        # Merchant is seller-only (no per_order), so skip it.
        for cat_key, cat_data in BankData.CATEGORIES.items():
            if cat_key in ("logs", "merchant"):
                continue
            if section_counts.get(cat_key, {}).get("per_order", 0) == 0:
                fallback = len(cat_data["items"])
                if fallback:
                    section_counts[cat_key]["per_order"] = fallback
        brute_result = await session.execute(
            select(func.count(BruteBankItem.id)).where(
                BruteBankItem.is_active == True,
                BruteBankItem.status == "available",
                BruteBankItem.moderation_status == "approved",
            )
        )
        brute_count = int(brute_result.scalar() or 0)
        async def _count_specials(model):
            r = await session.execute(
                select(func.count(model.id))
                .join(Seller)
                .where(
                    model.is_active == True,
                    model.is_in_stock == True,
                    model.moderation_status == "approved",
                    Seller.is_approved == True,
                    Seller.is_active == True,
                )
            )
            return int(r.scalar() or 0)

        logs_count = await _count_specials(SellerLogsItem)
        merchant_count = section_counts.get("merchant", {}).get("available", 0)

        return {
            "total": sum(category_counts.values()) + brute_count + logs_count + merchant_count,
            "by_category": {
                **category_counts,
                "merchant": merchant_count,
                "logs": logs_count,
            },
            "by_section": {
                category: {
                    "available": values.get("available", 0),
                    "per_order": values.get("per_order", 0),
                }
                for category, values in section_counts.items()
            },
            "brute": brute_count,
            "logs": logs_count,
        }

    @staticmethod
    async def get_banks_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("banks")
        if cached is not None:
            cached["by_category"] = defaultdict(lambda: "?", cached.get("by_category") or {})
            cached["by_section"] = defaultdict(
                lambda: {"available": "?", "per_order": "?"},
                cached.get("by_section") or {},
            )
            return cached
        return {
            "total": "?",
            "by_category": MenuCountService._unknown_map(),
            "by_section": defaultdict(lambda: {"available": "?", "per_order": "?"}),
            "brute": "?",
        }

    @staticmethod
    async def get_bank_section_counts(session, category: str) -> dict:
        banks = await MenuCountService.get_banks_counts(session)
        if isinstance(banks.get("by_section"), defaultdict):
            return banks["by_section"][category]
        return banks.get("by_section", {}).get(category, {"available": "?", "per_order": "?"})

    @staticmethod
    async def build_cc_counts(session) -> dict:
        categories_result = await session.execute(
            select(CCCategory.code).where(CCCategory.is_active == True)
        )
        category_codes = [code for code in categories_result.scalars().all()]
        counts: dict[str, int] = defaultdict(int)

        admin_result = await session.execute(
            select(CCItem.category_code, func.count(CCItem.id))
            .where(CCItem.is_active == True)
            .group_by(CCItem.category_code)
        )
        for category_code, total in admin_result.all():
            counts[category_code] += int(total or 0)

        seller_result = await session.execute(
            select(SellerCCItem.category_code, func.coalesce(func.sum(_free_cc_stock_expr()), 0))
            .join(Seller)
            .where(
                SellerCCItem.is_active == True,
                SellerCCItem.moderation_status == "approved",
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            )
            .group_by(SellerCCItem.category_code)
        )
        for category_code, total in seller_result.all():
            counts[category_code] += int(total or 0)

        for code in category_codes:
            counts.setdefault(code, 0)

        # Add Selfreg CC, Enroll, OTP, NFC counts (moved from Banks)
        def _base_specials_query(model):
            return (
                select(func.count(model.id))
                .join(Seller)
                .where(
                    model.is_active == True,
                    model.is_in_stock == True,
                    model.moderation_status == "approved",
                    Seller.is_approved == True,
                    Seller.is_active == True,
                )
            )
        selfreg_cc_count = int((await session.scalar(_base_specials_query(SellerSelfregCCItem))) or 0)
        enroll_count = int((await session.scalar(_base_specials_query(SellerEnrollItem))) or 0)
        otp_count = int((await session.scalar(_base_specials_query(SellerOTPItem))) or 0)
        nfc_count = int((await session.scalar(_base_specials_query(SellerNFCItem))) or 0)
        counts["selfreg_cc"] = selfreg_cc_count
        counts["enroll"] = enroll_count
        counts["otp"] = otp_count
        counts["nfc"] = nfc_count

        return {
            "total": sum(counts.values()),
            "by_category": dict(counts),
        }

    @staticmethod
    async def get_cc_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("cc")
        if cached is not None:
            cached["by_category"] = defaultdict(lambda: "?", cached.get("by_category") or {})
            return cached
        return {
            "total": "?",
            "by_category": MenuCountService._unknown_map(),
        }

    @staticmethod
    async def build_accounts_counts(session) -> dict:
        db_result = await session.execute(
            select(AccountItem.category_code, func.count(AccountItem.id))
            .where(AccountItem.is_active == True)
            .group_by(AccountItem.category_code)
        )
        counts = {category_code: int(total or 0) for category_code, total in db_result.all()}
        extra_categories_result = await session.execute(
            select(AccountCategory.code)
            .where(AccountCategory.is_active == True)
        )
        for code in extra_categories_result.scalars().all():
            counts.setdefault(code, 0)
        return {
            "total": sum(counts.values()),
            "by_category": counts,
        }

    @staticmethod
    async def get_accounts_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("accounts")
        if cached is not None:
            cached["by_category"] = defaultdict(lambda: "?", cached.get("by_category") or {})
            return cached
        return {
            "total": "?",
            "by_category": MenuCountService._unknown_map(),
        }

    @staticmethod
    async def build_education_counts(session) -> dict:
        subscription_result = await session.execute(
            select(EducationSubscription.category_code, func.count(EducationSubscription.id))
            .where(EducationSubscription.is_active == True)
            .group_by(EducationSubscription.category_code)
        )
        manual_result = await session.execute(
            select(EducationManual.category_code, func.count(EducationManual.id))
            .where(EducationManual.is_available == True)
            .group_by(EducationManual.category_code)
        )
        categories_result = await session.execute(
            select(EducationCategory.code, EducationCategory.item_type)
            .where(EducationCategory.is_active == True)
        )
        subscriptions_by_category = {code: int(total or 0) for code, total in subscription_result.all()}
        manuals_by_category = {code: int(total or 0) for code, total in manual_result.all()}
        for code, item_type in categories_result.all():
            if item_type == "subscription":
                subscriptions_by_category.setdefault(code, 0)
            elif item_type == "manual":
                manuals_by_category.setdefault(code, 0)
        return {
            "total": sum(subscriptions_by_category.values()) + sum(manuals_by_category.values()),
            "subscriptions_total": sum(subscriptions_by_category.values()),
            "manuals_total": sum(manuals_by_category.values()),
            "subscriptions_by_category": subscriptions_by_category,
            "manuals_by_category": manuals_by_category,
        }

    @staticmethod
    async def get_education_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("education")
        if cached is not None:
            cached["subscriptions_by_category"] = defaultdict(
                lambda: "?",
                cached.get("subscriptions_by_category") or {},
            )
            cached["manuals_by_category"] = defaultdict(
                lambda: "?",
                cached.get("manuals_by_category") or {},
            )
            return cached
        return {
            "total": "?",
            "subscriptions_total": "?",
            "manuals_total": "?",
            "subscriptions_by_category": MenuCountService._unknown_map(),
            "manuals_by_category": MenuCountService._unknown_map(),
        }

    @staticmethod
    async def build_seller_specials_counts(session) -> dict:
        def _base_query(model):
            return (
                select(func.count(model.id))
                .join(Seller, Seller.id == model.seller_id)
                .where(
                    model.is_active == True,
                    model.is_in_stock == True,
                    model.moderation_status == "approved",
                    Seller.is_approved == True,
                    Seller.is_active == True,
                    Seller.is_on_vacation == False,
                )
            )

        otp_count = int((await session.scalar(_base_query(SellerOTPItem))) or 0)
        counts = {
            "nfc": int((await session.scalar(_base_query(SellerNFCItem))) or 0),
            "enroll": int((await session.scalar(_base_query(SellerEnrollItem))) or 0),
            # Note: selfreg_ba merged with bank items
            "logs": int((await session.scalar(_base_query(SellerLogsItem))) or 0),
            "otp": otp_count,
            "otp_card": otp_count,
            "selfreg_cc": int((await session.scalar(_base_query(SellerSelfregCCItem))) or 0),
            "checks": int((await session.scalar(_base_query(SellerCheckItem))) or 0),
        }
        return {
            "total": (
                counts["nfc"]
                + counts["enroll"]
                + counts["logs"]
                + counts["otp"]
                + counts["selfreg_cc"]
                + counts["checks"]
            ),
            "by_kind": counts,
        }

    @staticmethod
    async def get_seller_specials_counts(session) -> dict:
        cached = await MenuCountCacheService.get_counts("seller_specials")
        if cached is not None:
            cached["by_kind"] = defaultdict(lambda: "?", cached.get("by_kind") or {})
            return cached
        live_counts = await MenuCountService.build_seller_specials_counts(session)
        await MenuCountCacheService.set_counts("seller_specials", live_counts)
        live_counts["by_kind"] = defaultdict(lambda: "?", live_counts.get("by_kind") or {})
        return live_counts

    @staticmethod
    async def get_main_menu_counts(session) -> dict:
        documents = await MenuCountService.get_documents_counts(session)
        fullz = await MenuCountService.get_fullz_counts(session)
        banks = await MenuCountService.get_banks_counts(session)
        cc = await MenuCountService.get_cc_counts(session)
        accounts = await MenuCountService.get_accounts_counts(session)
        education = await MenuCountService.get_education_counts(session)
        return {
            "documents": documents["total"],
            "fullz": fullz["total"],
            "banks": banks["total"],
            "cc": cc["total"],
            "accounts": accounts["total"],
            "education": education["total"],
        }
