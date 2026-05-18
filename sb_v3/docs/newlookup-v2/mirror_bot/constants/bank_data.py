from typing import Dict, List, Optional
from mirror_bot.constants.prices import ServicePrices
from shared.utils.seller_product_meta import bank_item_badge


class BankData:
    
    VCC_BANKS = [
        {"id": "vcc_chime", "name": "🤩 Chime VCC", "price": ServicePrices.BANK_VCC_CHIME, "desc": "Virtual card"},
        {"id": "vcc_paypal", "name": "🏦 PayPal VCC", "price": ServicePrices.BANK_VCC_PAYPAL, "desc": "Virtual card"},
        {"id": "vcc_onepay", "name": "🤩 One Pay VCC", "price": ServicePrices.BANK_VCC_ONEPAY, "desc": "Virtual card"},
        {"id": "vcc_current", "name": "🤩 Current VCC", "price": ServicePrices.BANK_VCC_CURRENT, "desc": "Virtual card"},
        {"id": "vcc_neteller", "name": "🏦 Neteller VCC", "price": ServicePrices.BANK_VCC_NETELLER, "desc": "Virtual card"},
        {"id": "vcc_wise", "name": "🎰 Wise Personal VCC", "price": ServicePrices.BANK_VCC_WISE, "desc": "Virtual card"},
        {"id": "vcc_netspend", "name": "🤩 Netspend VCC", "price": ServicePrices.BANK_VCC_NETSPEND, "desc": "Virtual card"},
        {"id": "vcc_greenfi", "name": "🤩 GreenFi VCC", "price": ServicePrices.BANK_VCC_GREENFI, "desc": "Virtual card"},
        {"id": "vcc_quickbooks", "name": "🏦 QuickBooks VCC", "price": ServicePrices.BANK_VCC_QUICKBOOKS, "desc": "Virtual card"},
        {"id": "vcc_go2bank", "name": "🏛️ Go2Bank + VCC", "price": ServicePrices.BANK_VCC_GO2BANK, "desc": "Virtual card"},
        {"id": "vcc_venmo", "name": "🏛️ Venmo", "price": ServicePrices.BANK_VCC_VENMO, "desc": "Virtual card"},
        {"id": "vcc_kikoff", "name": "🏛️ Kikoff", "price": ServicePrices.BANK_VCC_KIKOFF, "desc": "Virtual card"},
        {"id": "vcc_shopify", "name": "🏛️ Shopify", "price": ServicePrices.BANK_VCC_SHOPIFY, "desc": "Virtual card"},
        {"id": "vcc_varo", "name": "🏛️ Varo + VCC", "price": ServicePrices.BANK_VCC_VARO, "desc": "Virtual card"},
    ]
    
    PERSONAL_BANKS = [
        {"id": "pers_citi", "name": "🏦 Citi Personal", "price": ServicePrices.BANK_PERS_CITI, "desc": "Personal account"},
        {"id": "pers_citi_gold", "name": "🏦 Citi Gold Bank", "price": ServicePrices.BANK_PERS_CITI_GOLD, "desc": "Gold account"},
        {"id": "pers_usalliance", "name": "🏦 Usalliance", "price": ServicePrices.BANK_PERS_USALLIANCE, "desc": "Personal account"},
        {"id": "pers_usbank", "name": "🏦 US Bank", "price": ServicePrices.BANK_PERS_USBANK, "desc": "Personal account"},
        {"id": "pers_ally", "name": "🏦 Ally Bank", "price": ServicePrices.BANK_PERS_ALLY, "desc": "Personal account"},
        {"id": "pers_regions", "name": "🏦 Regions Bank", "price": ServicePrices.BANK_PERS_REGIONS, "desc": "Personal account"},
        {"id": "pers_chase", "name": "🏦 Chase", "price": ServicePrices.BANK_PERS_CHASE, "desc": "Personal account"},
        {"id": "pers_wells", "name": "🏦 WellsFargo", "price": ServicePrices.BANK_PERS_WELLS, "desc": "Personal account"},
        {"id": "pers_schwab", "name": "🏦 Charles Schwab", "price": ServicePrices.BANK_PERS_SCHWAB, "desc": "Personal account"},
        {"id": "pers_citizens", "name": "🏦 Citizens Bank", "price": ServicePrices.BANK_PERS_CITIZENS, "desc": "Personal account"},
        {"id": "pers_huntington", "name": "🏦 Huntington Bank", "price": ServicePrices.BANK_PERS_HUNTINGTON, "desc": "Personal account"},
        {"id": "pers_td", "name": "🏦 TD bank", "price": ServicePrices.BANK_PERS_TD, "desc": "Personal account"},
        {"id": "pers_boa", "name": "🏦 BankOFAmerica", "price": ServicePrices.BANK_PERS_BOA, "desc": "Personal account"},
        {"id": "pers_alliant", "name": "🏦 Alliant Cu", "price": ServicePrices.BANK_PERS_ALLIANT, "desc": "Personal account"},
        {"id": "pers_pnc", "name": "🏦 Pnc Bank", "price": ServicePrices.BANK_PERS_PNC, "desc": "Personal account"},
    ]
    
    BUSINESS_BANKS = [
        {"id": "biz_quickbooks", "name": "🏢 QuickBooks (LLC/ CORP)", "price": ServicePrices.BANK_BIZ_QUICKBOOKS, "desc": "Business account"},
        {"id": "biz_bmo", "name": "🏢 Bmo Buisness", "price": ServicePrices.BANK_BIZ_BMO, "desc": "Business account"},
        {"id": "biz_boa", "name": "🏢 BankOFAmerica", "price": ServicePrices.BANK_BIZ_BOA, "desc": "Business account"},
        {"id": "biz_usbank", "name": "🏢 Us Buisness", "price": ServicePrices.BANK_BIZ_USBANK, "desc": "Business account"},
        {"id": "biz_north_one", "name": "🏢 North One (LLC/Corp)", "price": ServicePrices.BANK_BIZ_NORTH_ONE, "desc": "Business account"},
        {"id": "biz_lili", "name": "🏢 Lili Business Vcc", "price": ServicePrices.BANK_BIZ_LILI, "desc": "Business account"},
        {"id": "biz_pnc", "name": "🏢 Pnc Business", "price": ServicePrices.BANK_BIZ_PNC, "desc": "Business account"},
        {"id": "biz_capital_one", "name": "🏢 Capital One Business", "price": ServicePrices.BANK_BIZ_CAPITAL_ONE, "desc": "Business account"},
        {"id": "biz_chase", "name": "🏢 Chase Business", "price": ServicePrices.BANK_BIZ_CHASE, "desc": "Business account"},
        {"id": "biz_wells", "name": "🏢 Wells Fargo Business", "price": ServicePrices.BANK_BIZ_WELLS, "desc": "Business account"},
    ]
    
    CRYPTO_BANKS = [
        {"id": "crypto_cashapp", "name": "💸 Cash App + BTC", "price": ServicePrices.BANK_CRYPTO_CASHAPP, "desc": "Crypto wallet"},
        {"id": "crypto_blockchain", "name": "💸 Blockchain Gold", "price": ServicePrices.BANK_CRYPTO_BLOCKCHAIN, "desc": "Exchange account"},
        {"id": "crypto_kraken", "name": "💸 Kraken", "price": ServicePrices.BANK_CRYPTO_KRAKEN, "desc": "Exchange account"},
        {"id": "crypto_coinbase", "name": "💸 CoinBase", "price": ServicePrices.BANK_CRYPTO_COINBASE, "desc": "Exchange account"},
        {"id": "crypto_crypto_com", "name": "💸 Crypto.com", "price": ServicePrices.BANK_CRYPTO_CRYPTO_COM, "desc": "Exchange account"},
        {"id": "crypto_binance", "name": "💸 Binance", "price": ServicePrices.BANK_CRYPTO_BINANCE, "desc": "Exchange account"},
    ]
    
    MERCHANT_BANKS = [
        {"id": "mrch_mercury",      "name": "🔷 Mercury LLC",               "price": ServicePrices.BANK_MERCHANT_MERCURY,      "desc": "LLC merchant account"},
        {"id": "mrch_rho",          "name": "🔷 Rho LLC",                   "price": ServicePrices.BANK_MERCHANT_RHO,          "desc": "LLC merchant account"},
        {"id": "mrch_relay",        "name": "🔷 Relay LLC Europe/USA Owner","price": ServicePrices.BANK_MERCHANT_RELAY,        "desc": "LLC merchant account"},
        {"id": "mrch_revolut_biz",  "name": "🔷 Revolut Business LLC",      "price": ServicePrices.BANK_MERCHANT_REVOLUT_BIZ,  "desc": "LLC merchant account"},
        {"id": "mrch_bluevine",     "name": "🔷 Blue Vine LLC",             "price": ServicePrices.BANK_MERCHANT_BLUEVINE,     "desc": "LLC merchant account"},
        {"id": "mrch_novobank",     "name": "🔷 Novobank LLC",              "price": ServicePrices.BANK_MERCHANT_NOVOBANK,     "desc": "LLC merchant account"},
        {"id": "mrch_wise_biz",     "name": "🔷 Wise Business LLC",         "price": ServicePrices.BANK_MERCHANT_WISE_BIZ,     "desc": "LLC merchant account"},
        {"id": "mrch_payoneer",     "name": "🔷 Payoneer LLC",              "price": ServicePrices.BANK_MERCHANT_PAYONEER,     "desc": "LLC merchant account"},
        {"id": "mrch_revolut_pers", "name": "🔷 Revolut Personal on EMU",   "price": ServicePrices.BANK_MERCHANT_REVOLUT_PERS, "desc": "Personal EMU account"},
    ]

    LOGS_BANKS = [
        {"id": "log_chime", "name": "📋 Chime Log", "price": ServicePrices.BANK_LOG_CHIME, "desc": "Bank log"},
        {"id": "log_cashapp", "name": "📋 Cash App Log", "price": ServicePrices.BANK_LOG_CASHAPP, "desc": "Bank log"},
        {"id": "log_paypal", "name": "📋 PayPal Log", "price": ServicePrices.BANK_LOG_PAYPAL, "desc": "Bank log"},
        {"id": "log_zelle", "name": "📋 Zelle Log", "price": ServicePrices.BANK_LOG_ZELLE, "desc": "Bank log"},
        {"id": "log_venmo", "name": "📋 Venmo Log", "price": ServicePrices.BANK_LOG_VENMO, "desc": "Bank log"},
        {"id": "log_coinbase", "name": "📋 Coinbase Log", "price": ServicePrices.BANK_LOG_COINBASE, "desc": "Bank log"},
        {"id": "log_chase", "name": "📋 Chase Log", "price": ServicePrices.BANK_LOG_CHASE, "desc": "Bank log"},
        {"id": "log_boa", "name": "📋 BankOfAmerica Log", "price": ServicePrices.BANK_LOG_BOA, "desc": "Bank log"},
        {"id": "log_wells", "name": "📋 WellsFargo Log", "price": ServicePrices.BANK_LOG_WELLS, "desc": "Bank log"},
        {"id": "log_td", "name": "📋 TD Bank Log", "price": ServicePrices.BANK_LOG_TD, "desc": "Bank log"},
    ]

    CATEGORIES = {
        "vcc": {"name": "💳 PERSONAL VCC", "items": VCC_BANKS},
        "personal": {"name": "🏦 PERSONAL BANKS", "items": PERSONAL_BANKS},
        "business": {"name": "🏢 BUSINESS BANKS", "items": BUSINESS_BANKS},
        "crypto": {"name": "🪙 CRYPTO BANKS", "items": CRYPTO_BANKS},
        "merchant": {"name": "🏪 MERCHANT ACCOUNTS", "items": MERCHANT_BANKS},
        "logs": {"name": "📋 LOGS", "items": LOGS_BANKS},
    }
    
    @classmethod
    def get_bank_by_id(cls, bank_id: str) -> Dict:
        for category_data in cls.CATEGORIES.values():
            for bank in category_data["items"]:
                if bank["id"] == bank_id:
                    return bank
        return None

    @classmethod
    def get_category_items(cls, category: str) -> List[Dict]:
        return cls.CATEGORIES.get(category, {}).get("items", [])

    @classmethod
    async def get_category_items_ordered(cls, session, category: str) -> List[Dict]:
        """Получить товары категории из БД (BankItem), с fallback на хардкод"""
        try:
            from sqlalchemy import select
            from shared.database.models import BankItem

            result = await session.execute(
                select(BankItem).where(
                    BankItem.category == category,
                    BankItem.is_active == True
                ).order_by(BankItem.position, BankItem.id)
            )
            db_items = result.scalars().all()
            if db_items:
                return [
                    {"id": b.bank_code, "name": b.name, "price": b.price, "desc": b.description or "", "section": b.section}
                    for b in db_items
                ]
        except Exception:
            pass
        items = cls.get_category_items(category)
        try:
            from sqlalchemy import select
            from shared.database.models import BankPosition

            result = await session.execute(
                select(BankPosition).where(BankPosition.category == category).order_by(BankPosition.position)
            )
            positions = result.scalars().all()
            if positions:
                pos_map = {p.bank_id: p.position for p in positions}
                return sorted(items, key=lambda x: pos_map.get(x["id"], 999))
        except Exception:
            pass
        return items

    @classmethod
    def get_bank_category(cls, bank_id: str) -> str:
        """Возвращает категорию банка по его ID"""
        for category_key, category_data in cls.CATEGORIES.items():
            for bank in category_data["items"]:
                if bank["id"] == bank_id:
                    return category_key
        return None

    @classmethod
    async def get_section_counts(cls, session, category: str) -> Dict[str, int]:
        from sqlalchemy import func, select, case
        from shared.database.models import BankItem, Seller, SellerBank

        free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)
        available_stock_expr = case((free_stock_expr > 0, free_stock_expr), else_=0)

        available_result = await session.execute(
            select(func.coalesce(func.sum(available_stock_expr), 0)).join(Seller).where(
                SellerBank.category == category,
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
                free_stock_expr > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            )
        )
        per_order_result = await session.execute(
            select(func.count(BankItem.id)).where(
                BankItem.category == category,
                BankItem.section == "order",
                BankItem.is_active == True,
            )
        )
        per_order_count = int(per_order_result.scalar() or 0)
        if per_order_count == 0:
            per_order_count = len(cls.get_category_items(category))
        return {
            "available": int(available_result.scalar() or 0),
            "per_order": per_order_count,
        }

    @classmethod
    async def get_available_items_by_category(cls, session, category: str) -> List[Dict]:
        from sqlalchemy import func, select, case
        from shared.database.models import Seller, SellerBank

        free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)
        available_stock_expr = case((free_stock_expr > 0, free_stock_expr), else_=0)

        result = await session.execute(
            select(
                SellerBank.bank_code,
                func.max(SellerBank.bank_name).label("bank_name"),
                func.max(SellerBank.category).label("category"),
                func.max(SellerBank.product_type).label("product_type"),
                func.max(SellerBank.product_subtype).label("product_subtype"),
                func.max(SellerBank.description).label("description"),
                func.min(SellerBank.buyer_price).label("price"),
                func.coalesce(func.sum(available_stock_expr), 0).label("available_count"),
            ).join(Seller).where(
                SellerBank.category == category,
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
                free_stock_expr > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            ).group_by(SellerBank.bank_code).order_by(func.max(SellerBank.bank_name))
        )
        return [
            {
                "id": row.bank_code,
                "name": f"{row.bank_name} [{bank_item_badge(row.product_type, row.product_subtype)}]",
                "category": row.category,
                "product_type": row.product_type,
                "product_subtype": row.product_subtype,
                "desc": row.description or "",
                "price": row.price,
                "available_count": int(row.available_count or 0),
                "section": "available",
            }
            for row in result.all()
            if int(row.available_count or 0) > 0
        ]

    @classmethod
    async def get_available_bank_names(cls, session, category: str) -> List[dict]:
        """Distinct seller bank_name values with total available stock (for subcategory step)."""
        from sqlalchemy import func, select, case
        from shared.database.models import Seller, SellerBank

        free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)
        available_stock_expr = case((free_stock_expr > 0, free_stock_expr), else_=0)

        result = await session.execute(
            select(
                SellerBank.bank_name,
                func.coalesce(func.sum(available_stock_expr), 0).label("available_count"),
            ).join(Seller).where(
                SellerBank.category == category,
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
                free_stock_expr > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            ).group_by(SellerBank.bank_name).order_by(SellerBank.bank_name)
        )
        rows = []
        for row in result.all():
            cnt = int(row.available_count or 0)
            if cnt <= 0:
                continue
            rows.append({"bank_name": row.bank_name, "available_count": cnt})
        return rows

    @classmethod
    async def get_available_items_by_bank_name(
        cls, session, category: str, bank_name: str
    ) -> List[Dict]:
        """Available listings filtered by bank_name (still one row per bank_code offer)."""
        from sqlalchemy import func, select, case
        from shared.database.models import Seller, SellerBank

        free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)
        available_stock_expr = case((free_stock_expr > 0, free_stock_expr), else_=0)

        result = await session.execute(
            select(
                SellerBank.bank_code,
                func.max(SellerBank.bank_name).label("bank_name"),
                func.max(SellerBank.category).label("category"),
                func.max(SellerBank.product_type).label("product_type"),
                func.max(SellerBank.product_subtype).label("product_subtype"),
                func.max(SellerBank.description).label("description"),
                func.min(SellerBank.buyer_price).label("price"),
                func.coalesce(func.sum(available_stock_expr), 0).label("available_count"),
            ).join(Seller).where(
                SellerBank.category == category,
                SellerBank.bank_name == bank_name,
                SellerBank.is_in_stock == True,
                SellerBank.is_active == True,
                SellerBank.moderation_status == "approved",
                free_stock_expr > 0,
                Seller.is_approved == True,
                Seller.is_active == True,
                Seller.is_on_vacation == False,
            ).group_by(SellerBank.bank_code).order_by(func.min(SellerBank.buyer_price))
        )
        return [
            {
                "id": row.bank_code,
                "name": f"{row.bank_name} [{bank_item_badge(row.product_type, row.product_subtype)}]",
                "category": row.category,
                "product_type": row.product_type,
                "product_subtype": row.product_subtype,
                "desc": row.description or "",
                "price": row.price,
                "available_count": int(row.available_count or 0),
                "section": "available",
            }
            for row in result.all()
            if int(row.available_count or 0) > 0
        ]

    @classmethod
    async def get_per_order_items_by_category(cls, session, category: str) -> List[Dict]:
        try:
            from sqlalchemy import select
            from shared.database.models import BankItem

            result = await session.execute(
                select(BankItem).where(
                    BankItem.category == category,
                    BankItem.section == "order",
                    BankItem.is_active == True,
                ).order_by(BankItem.position, BankItem.id)
            )
            db_items = result.scalars().all()
            if db_items:
                return [
                    {
                        "id": b.bank_code,
                        "name": b.name,
                        "price": b.price,
                        "desc": b.description or "",
                        "section": "order",
                    }
                    for b in db_items
                ]
        except Exception:
            pass
        return cls.get_category_items(category)

    @classmethod
    async def get_bank_by_id_async(cls, session, bank_id: str, section: str = "order") -> Optional[Dict]:
        if section == "available":
            category = cls.get_bank_category(bank_id)
            if category:
                for item in await cls.get_available_items_by_category(session, category):
                    if item["id"] == bank_id:
                        return item
            try:
                from shared.database.models import SellerBank, Seller
                from sqlalchemy import select, and_, func

                free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)
                result = await session.execute(
                    select(SellerBank).join(Seller).where(
                        and_(
                            SellerBank.bank_code == bank_id,
                            SellerBank.is_in_stock == True,
                            SellerBank.is_active == True,
                            SellerBank.moderation_status == "approved",
                            free_stock_expr > 0,
                            Seller.is_approved == True,
                            Seller.is_active == True,
                            Seller.is_on_vacation == False,
                        )
                    ).order_by(SellerBank.buyer_price.asc(), SellerBank.id.asc()).limit(1)
                )
                bank = result.scalar_one_or_none()
                if bank:
                    return {
                        "id": bank.bank_code,
                        "name": f"{bank.bank_name} [{bank_item_badge(getattr(bank, 'product_type', 'bank'), getattr(bank, 'product_subtype', 'log'))}]",
                        "category": bank.category,
                        "product_type": getattr(bank, "product_type", "bank"),
                        "product_subtype": getattr(bank, "product_subtype", "log"),
                        "desc": bank.description or "",
                        "price": bank.buyer_price,
                        "available_count": max(0, int(bank.stock_count or 0) - int(getattr(bank, "reserved_count", 0) or 0)),
                        "section": "available",
                    }
            except Exception:
                pass
            return None
        try:
            from sqlalchemy import select
            from shared.database.models import BankItem

            result = await session.execute(
                select(BankItem).where(
                    BankItem.bank_code == bank_id,
                    BankItem.section == "order",
                    BankItem.is_active == True,
                )
            )
            bank_item = result.scalar_one_or_none()
            if bank_item:
                return {
                    "id": bank_item.bank_code,
                    "name": bank_item.name,
                    "price": bank_item.price,
                    "desc": bank_item.description or "",
                    "section": "order",
                }
        except Exception:
            pass
        bank = cls.get_bank_by_id(bank_id)
        if bank:
            bank = {**bank, "section": "order"}
        return bank

    @staticmethod
    async def get_seller_bank_for_purchase(session, bank_id: str, quantity: int = 1):
        """Find a seller bank entry for a given bank_id with enough stock."""
        from sqlalchemy import select, and_, func
        from shared.database.models import SellerBank, Seller

        free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)

        result = await session.execute(
            select(SellerBank).join(Seller).where(
                and_(
                    SellerBank.bank_code == bank_id,
                    SellerBank.is_in_stock == True,
                    SellerBank.is_active == True,
                    SellerBank.moderation_status == "approved",
                    free_stock_expr >= quantity,
                    Seller.is_approved == True,
                    Seller.is_active == True,
                    Seller.is_on_vacation == False,
                )
            ).order_by(SellerBank.buyer_price.asc(), free_stock_expr.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def reserve_seller_bank_for_purchase(session, bank_id: str, quantity: int = 1):
        from sqlalchemy import select, and_, func, update
        from shared.database.models import SellerBank, Seller

        free_stock_expr = SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)
        candidates = await session.execute(
            select(SellerBank.id).join(Seller).where(
                and_(
                    SellerBank.bank_code == bank_id,
                    SellerBank.is_in_stock == True,
                    SellerBank.is_active == True,
                    SellerBank.moderation_status == "approved",
                    free_stock_expr >= quantity,
                    Seller.is_approved == True,
                    Seller.is_active == True,
                    Seller.is_on_vacation == False,
                )
            ).order_by(SellerBank.buyer_price.asc(), free_stock_expr.desc(), SellerBank.id.asc())
        )

        for seller_bank_id in candidates.scalars().all():
            reserve_stmt = (
                update(SellerBank)
                .where(
                    SellerBank.id == seller_bank_id,
                    (SellerBank.stock_count - func.coalesce(SellerBank.reserved_count, 0)) >= quantity,
                )
                .values(
                    reserved_count=func.coalesce(SellerBank.reserved_count, 0) + quantity,
                    is_in_stock=(SellerBank.stock_count - (func.coalesce(SellerBank.reserved_count, 0) + quantity)) > 0,
                )
            )
            reserve_result = await session.execute(reserve_stmt)
            if reserve_result.rowcount:
                refreshed = await session.execute(select(SellerBank).where(SellerBank.id == seller_bank_id))
                return refreshed.scalar_one_or_none()
        return None

