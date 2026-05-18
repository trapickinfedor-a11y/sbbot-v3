from __future__ import annotations
from decimal import Decimal


class SystemFees:
    """Системные комиссии и проценты"""
    
    # Комиссия платформы за пополнение
    PAYMENT_FEE_PERCENT = 3  # 3% (CryptoPay)
    CRYPTOMUS_FEE_PERCENT = 2  # 2% (Cryptomus)
    
    # Реферальный процент
    REFERRAL_PERCENT = 25  # sum of 4-level: 10+7+5+3


class BulkDiscounts:
    """Bulk-discount helpers.

    Static methods use hardcoded fallbacks.
    Async class-methods read from the DB (BulkDiscountTier) when a session is provided.
    """

    # Hardcoded fallback tiers (Banks / Accounts / Documents)
    BANKS_QTY_3 = 2
    BANKS_QTY_5 = 3
    BANKS_QTY_10 = 5

    # Hardcoded fallback tiers (eSIM / FULLZ)
    ESIM_QTY_3 = 5
    ESIM_QTY_5 = 10
    ESIM_QTY_10 = 15

    @staticmethod
    def get_bank_discount(quantity: int) -> int:
        if quantity >= 10:
            return BulkDiscounts.BANKS_QTY_10
        elif quantity >= 5:
            return BulkDiscounts.BANKS_QTY_5
        elif quantity >= 3:
            return BulkDiscounts.BANKS_QTY_3
        return 0

    @staticmethod
    def get_esim_discount(quantity: int) -> int:
        if quantity >= 10:
            return BulkDiscounts.ESIM_QTY_10
        elif quantity >= 5:
            return BulkDiscounts.ESIM_QTY_5
        elif quantity >= 3:
            return BulkDiscounts.ESIM_QTY_3
        return 0

    @staticmethod
    def get_bank_discount_decimal(quantity: int) -> Decimal:
        return Decimal(str(BulkDiscounts.get_bank_discount(quantity))) / Decimal("100")

    @staticmethod
    def get_esim_discount_decimal(quantity: int) -> Decimal:
        return Decimal(str(BulkDiscounts.get_esim_discount(quantity))) / Decimal("100")

    # ── DB-backed helpers (async) ──────────────────────────────────────────────

    @staticmethod
    async def get_discount_from_db(session, category: str, quantity: int) -> Decimal:
        """Return discount as Decimal fraction from DB, fallback to hardcoded."""
        try:
            from shared.services.bulk_discount_service import get_discount_decimal
            return await get_discount_decimal(session, category, quantity)
        except Exception:
            pass
        # Fallback
        cat_group = {
            "banks": "bank", "accounts": "bank", "docs": "bank",
            "esim": "esim", "fullz": "esim", "cc": "esim",
        }.get(category, "bank")
        if cat_group == "esim":
            return BulkDiscounts.get_esim_discount_decimal(quantity)
        return BulkDiscounts.get_bank_discount_decimal(quantity)


class ServicePrices:
    
    LOOKUP_SSN_DOB = Decimal("2.80")
    LOOKUP_SSN_DOB_BULK = Decimal("2.50")
    LOOKUP_CREDIT_SCORE = Decimal("2.00")
    LOOKUP_CREDIT_SCORE_BULK = Decimal("1.60")
    LOOKUP_DL = Decimal("7.00")
    LOOKUP_DL_BULK = Decimal("6.50")
    LOOKUP_MVR = Decimal("11.00")
    LOOKUP_MVR_BULK = Decimal("10.00")
    LOOKUP_FULL_MVR = Decimal("22.00")
    LOOKUP_FULL_MVR_BULK = Decimal("20.00")
    LOOKUP_PHONE_NAME = Decimal("1.50")
    LOOKUP_PHONE_SSN = Decimal("4.00")
    LOOKUP_PHONE_FULL = Decimal("5.00")
    LOOKUP_BG = Decimal("2.00")
    LOOKUP_BG_BULK = Decimal("1.60")
    LOOKUP_MMN = Decimal("9.00")
    LOOKUP_EIN = Decimal("11.00")
    
    CR_TRANSUNION = Decimal("4.99")
    CR_TRANSUNION_BULK = Decimal("4.49")
    CR_EXPERIAN = Decimal("5.99")
    CR_EXPERIAN_BULK = Decimal("5.49")
    CR_EQUIFAX = Decimal("6.00")
    CR_LEXISNEXIS = Decimal("9.00")
    CR_LEXISNEXIS_BULK = Decimal("8.50")
    CR_WALLETHUB = Decimal("8.00")
    CR_WALLETHUB_BULK = Decimal("7.00")
    
    # Coming Soon (not implemented yet)
    # DOC_HIGH_QUALITY = Decimal("50.00")
    # DOC_ROBOT = Decimal("20.00")
    
    FULLZ_BASE = Decimal("9.00")

    # Fixed-price personal fullz profiles (order+catalog)
    FULLZ_700_PLUS = Decimal("5.00")
    FULLZ_800_PLUS_PROFILE = Decimal("7.00")
    FULLZ_UNDER_18 = Decimal("25.00")
    FULLZ_IMMIGRANT = Decimal("100.00")
    FULLZ_ZERO_BANK = Decimal("150.00")

    FULLZ_STATE_SURCHARGE = Decimal("2.00")

    FULLZ_REPORT_BASIC = Decimal("0.00")
    FULLZ_REPORT_CR = Decimal("2.00")  # Personal FULLZ
    FULLZ_REPORT_CR_DL = Decimal("10.00")
    FULLZ_REPORT_CR_DL_MVR = Decimal("22.00")
    FULLZ_REPORT_CR_DL_FULLMVR = Decimal("32.00")
    
    # Business FULLZ specific (только отличающиеся цены)
    FULLZ_BIZ_REPORT_CR = Decimal("4.00") 
    
    FULLZ_CS_500_PLUS = Decimal("-1.00")
    FULLZ_CS_700_PLUS = Decimal("2.00")
    FULLZ_CS_800_PLUS = Decimal("3.00")
    
    FULLZ_AGE_18_25 = Decimal("1.00")
    FULLZ_AGE_26_35 = Decimal("1.00")
    FULLZ_AGE_36_PLUS = Decimal("1.00")
    
    FULLZ_GENDER_MALE = Decimal("2.00")
    FULLZ_GENDER_FEMALE = Decimal("2.00")

    FULLZ_NO_CARRIER = Decimal("10.00")
    FULLZ_NO_BANK_SINGLE = Decimal("10.00")
    FULLZ_NO_BANK_ANY = Decimal("15.00")
    
    FULLZ_BIZ_LLC = Decimal("5.00")
    FULLZ_BIZ_CORP = Decimal("5.00")
    
    FULLZ_BIZ_LOAN_25_200 = Decimal("5.00")
    FULLZ_BIZ_LOAN_200_500 = Decimal("5.00")
    FULLZ_BIZ_LOAN_500_PLUS = Decimal("7.00")
    
    # Business FULLZ base price
    FULLZ_BIZ_BASE = Decimal("15.00")
    
    ADD_INFO_PHONE_ADDRESS_EMPLOYER_ALL = Decimal("90.00")
    ADD_INFO_PHONE_ADDRESS_ALL = Decimal("80.00")
    ADD_INFO_PHONE_ALL = Decimal("40.00")
    ADD_INFO_ADDRESS_ALL = Decimal("45.00")
    ADD_INFO_PHONE_EX = Decimal("20.00")
    ADD_INFO_ADDRESS_EX = Decimal("20.00")
    ADD_INFO_PHONE_TU = Decimal("20.00")
    ADD_INFO_ADDRESS_TU = Decimal("40.00")
    
    ADD_INFO_BG_PHONE_ADDRESS = Decimal("60.00")
    ADD_INFO_BG_PHONE = Decimal("40.00")
    ADD_INFO_BG_ADDRESS = Decimal("40.00")
    
    ADD_EMPLOYER_TU = Decimal("15.00")
    UPDATE_EMPLOYER = Decimal("15.00")
    REMOVE_EMPLOYER = Decimal("15.00")
    
    UNFREEZE_TU = Decimal("20.00")
    UNFREEZE_EX = Decimal("25.00")
    
    # ОБНОВЛЕННЫЕ ЦЕНЫ VCC БАНКОВ
    BANK_VCC_CHIME = Decimal("85.00")  # было 70.00
    BANK_VCC_PAYPAL = Decimal("89.00")  # было 70.00
    BANK_VCC_ONEPAY = Decimal("99.00")  # было 60.00
    BANK_VCC_CURRENT = Decimal("70.00")  # обновлено согласно шаблону
    BANK_VCC_NETELLER = Decimal("65.00")  # без изменений
    BANK_VCC_WISE = Decimal("60.00")  # обновлено согласно шаблону
    BANK_VCC_NETSPEND = Decimal("55.00")  # без изменений
    BANK_VCC_GREENFI = Decimal("50.00")  # без изменений
    BANK_VCC_QUICKBOOKS = Decimal("99.00")  # без изменений
    
    # НОВЫЕ VCC БАНКИ
    BANK_VCC_GO2BANK = Decimal("69.00")
    BANK_VCC_VENMO = Decimal("99.00")
    BANK_VCC_KIKOFF = Decimal("74.00")
    BANK_VCC_SHOPIFY = Decimal("74.00")
    BANK_VCC_VARO = Decimal("120.00")
    BANK_VCC_BLOCKCHAIN = Decimal("170.00")
    
    # ОБНОВЛЕННЫЕ ЦЕНЫ ПЕРСОНАЛЬНЫХ БАНКОВ
    BANK_PERS_CITI = Decimal("89.00")  # без изменений
    BANK_PERS_CITI_GOLD = Decimal("110.00")  # новый
    BANK_PERS_USALLIANCE = Decimal("65.00")  # обновлено согласно шаблону
    BANK_PERS_USBANK = Decimal("99.00")  # было 79.00
    BANK_PERS_ALLY = Decimal("65.00")  # обновлено согласно шаблону
    BANK_PERS_REGIONS = Decimal("70.00")  # без изменений
    BANK_PERS_CHASE = Decimal("99.00")  # было 89.00
    BANK_PERS_WELLS = Decimal("259.00")  # было 90.00
    BANK_PERS_SCHWAB = Decimal("100.00")  # без изменений
    BANK_PERS_CITIZENS = Decimal("70.00")  # обновлено согласно шаблону
    BANK_PERS_HUNTINGTON = Decimal("89.00")  # было 70.00
    BANK_PERS_TD = Decimal("89.00")  # было 85.00
    BANK_PERS_BOA = Decimal("100.00")  # новый
    BANK_PERS_ALLIANT = Decimal("100.00")  # новый
    BANK_PERS_PNC = Decimal("140.00")  # новый
    
    # ОБНОВЛЕННЫЕ ЦЕНЫ БИЗНЕС БАНКОВ (согласно шаблону)
    BANK_BIZ_QUICKBOOKS = Decimal("99.00")  # согласно шаблону
    BANK_BIZ_BMO = Decimal("130.00")  # согласно шаблону
    BANK_BIZ_BOA = Decimal("120.00")  # согласно шаблону
    BANK_BIZ_USBANK = Decimal("140.00")  # согласно шаблону
    BANK_BIZ_NORTH_ONE = Decimal("130.00")  # согласно шаблону
    BANK_BIZ_LILI = Decimal("140.00")  # согласно шаблону
    BANK_BIZ_PNC = Decimal("250.00")  # согласно шаблону
    BANK_BIZ_CAPITAL_ONE = Decimal("250.00")  # без изменений
    BANK_BIZ_CHASE = Decimal("199.00")  # без изменений
    BANK_BIZ_WELLS = Decimal("395.00")  # без изменений
    
    # ОБНОВЛЕННЫЕ ЦЕНЫ КРИПТО БАНКОВ (согласно шаблону)
    BANK_CRYPTO_CASHAPP = Decimal("160.00")  # согласно шаблону
    BANK_CRYPTO_BLOCKCHAIN = Decimal("170.00")  # согласно шаблону
    BANK_CRYPTO_KRAKEN = Decimal("100.00")  # согласно шаблону
    BANK_CRYPTO_COINBASE = Decimal("140.00")  # согласно шаблону
    BANK_CRYPTO_CRYPTO_COM = Decimal("200.00")  # согласно шаблону
    BANK_CRYPTO_BINANCE = Decimal("199.00")  # согласно шаблону

    # MERCHANT ACCOUNTS (LLC / EMU)
    BANK_MERCHANT_MERCURY      = Decimal("1000.00")
    BANK_MERCHANT_RHO          = Decimal("4000.00")
    BANK_MERCHANT_RELAY        = Decimal("1000.00")
    BANK_MERCHANT_REVOLUT_BIZ  = Decimal("1000.00")
    BANK_MERCHANT_BLUEVINE     = Decimal("900.00")
    BANK_MERCHANT_NOVOBANK     = Decimal("900.00")
    BANK_MERCHANT_WISE_BIZ     = Decimal("350.00")
    BANK_MERCHANT_PAYONEER     = Decimal("300.00")
    BANK_MERCHANT_REVOLUT_PERS = Decimal("600.00")

    # LOGS — bank account logs (seller products)
    BANK_LOG_CHIME = Decimal("45.00")
    BANK_LOG_CASHAPP = Decimal("55.00")
    BANK_LOG_PAYPAL = Decimal("50.00")
    BANK_LOG_ZELLE = Decimal("60.00")
    BANK_LOG_VENMO = Decimal("50.00")
    BANK_LOG_COINBASE = Decimal("80.00")
    BANK_LOG_CHASE = Decimal("120.00")
    BANK_LOG_BOA = Decimal("110.00")
    BANK_LOG_WELLS = Decimal("130.00")
    BANK_LOG_TD = Decimal("90.00")
    
    # ИСПРАВЛЕННЫЕ ЦЕНЫ eSIM SMS (1 month, 3 months, 6 months)
    ESIM_VERIZON = Decimal("20.00")
    ESIM_VERIZON_3 = Decimal("50.00")  # было 55.00, исправлено согласно файлу
    ESIM_VERIZON_6 = Decimal("70.00")  # было 100.00, исправлено согласно файлу

    ESIM_ATT = Decimal("35.00")
    ESIM_ATT_3 = Decimal("50.00")  # было 95.00, исправлено согласно файлу
    ESIM_ATT_6 = Decimal("70.00")  # было 180.00, исправлено согласно файлу

    ESIM_TMOBILE = Decimal("35.00")
    ESIM_TMOBILE_3 = Decimal("50.00")  # было 95.00, исправлено согласно файлу
    ESIM_TMOBILE_6 = Decimal("70.00")  # было 180.00, исправлено согласно файлу

    # Google Voice
    ESIM_GV_ANY_STATE = Decimal("14.00")
    ESIM_GV_STATE_SURCHARGE = Decimal("2.00")

    # eSIM Configurator (with CS/CR) — surcharges on top of base eSIM price
    ESIM_CFG_CS_800_PLUS = Decimal("3.00")
    ESIM_CFG_CS_700_PLUS = Decimal("2.00")
    ESIM_CFG_REPORT_BASIC = Decimal("0.00")
    ESIM_CFG_REPORT_CR = Decimal("2.00")
    ESIM_CFG_REPORT_CR_DL = Decimal("10.00")
    ESIM_CFG_REPORT_CR_DL_MVR = Decimal("22.00")
    ESIM_CFG_REPORT_CR_DL_FULLMVR = Decimal("32.00")
    ESIM_CFG_STATE_SURCHARGE = Decimal("2.00")

    # eSIM Data (старые константы для совместимости)
    ESIM_DATA_5GB = Decimal("25.00")
    ESIM_DATA_10GB = Decimal("40.00")
    ESIM_DATA_15GB = Decimal("50.00")

    # ИСПРАВЛЕННЫЕ eSIM Data по операторам (исправлены опечатки)
    ESIM_DATA_VERIZON_5GB = Decimal("25.00")  # было VERIZION
    ESIM_DATA_VERIZON_10GB = Decimal("40.00")  # было VERIZION
    ESIM_DATA_VERIZON_15GB = Decimal("50.00")  # было VERIZION

    ESIM_DATA_ATT_5GB = Decimal("25.00")
    ESIM_DATA_ATT_10GB = Decimal("40.00")
    ESIM_DATA_ATT_15GB = Decimal("50.00")

    ESIM_DATA_TMOBILE_5GB = Decimal("25.00")
    ESIM_DATA_TMOBILE_10GB = Decimal("40.00")
    ESIM_DATA_TMOBILE_15GB = Decimal("50.00")
    
    # ОБНОВЛЕННЫЕ ЦЕНЫ АККАУНТОВ (согласно шаблону все $70)
    ACC_BG_BEENVERIFIED = Decimal("13.00")  # обновлено согласно шаблону
    ACC_BG_TRUTHFINDER = Decimal("10.00")  # обновлено согласно шаблону
    ACC_BG_INSTANTCHECK = Decimal("10.00")  # обновлено согласно шаблону
    ACC_BG_INTELIUS = Decimal("12.00")  # обновлено согласно шаблону
    ACC_BG_WHITEPAGES = Decimal("13.00")  # обновлено согласно шаблону
    ACC_BG_MYLIFE = Decimal("10.00")  # обновлено согласно шаблону
    
    ACC_LOOKUP_MONARCH = Decimal("15.00")  # обновлено согласно шаблону
    ACC_LOOKUP_YODLEE = Decimal("15.00")  # обновлено согласно шаблону
    ACC_LOOKUP_EMPOWER = Decimal("12.00")  # обновлено согласно шаблону
    ACC_LOOKUP_POCKETGUARD = Decimal("12.00")  # обновлено согласно шаблону
    ACC_LOOKUP_EVERYDOLLAR = Decimal("12.00")  # обновлено согласно шаблону
    
    # НОВЫЕ АККАУНТЫ 30 ДНЕЙ
    ACC_BG_INTELIUS_30 = Decimal("39.00")
    ACC_BG_TRUTHFINDER_30 = Decimal("39.00")
    ACC_BG_INSTANTCHECK_30 = Decimal("35.00")
    ACC_BG_WHITEPAGES_30 = Decimal("45.00")

    # EMAIL ACCOUNTS
    ACC_EMAIL_GMAIL = Decimal("5.00")
    ACC_EMAIL_OUTLOOK = Decimal("5.00")
    ACC_EMAIL_YAHOO = Decimal("4.00")
    ACC_EMAIL_ICLOUD = Decimal("8.00")
    ACC_EMAIL_PROTONMAIL = Decimal("6.00")
    ACC_EMAIL_AOL = Decimal("4.00")

    # AI ACCOUNTS
    ACC_AI_CHATGPT = Decimal("12.00")
    ACC_AI_MIDJOURNEY = Decimal("15.00")
    ACC_AI_CLAUDE = Decimal("14.00")
    ACC_AI_COPILOT = Decimal("10.00")
    ACC_AI_GEMINI = Decimal("10.00")

    # PROXY / VPN ACCOUNTS
    ACC_PROXY_NORDVPN = Decimal("8.00")
    ACC_PROXY_EXPRESSVPN = Decimal("10.00")
    ACC_PROXY_SURFSHARK = Decimal("6.00")
    ACC_PROXY_IPVANISH = Decimal("7.00")
    ACC_PROXY_911S5 = Decimal("15.00")
    
    @classmethod
    def calculate_fullz_price(cls, config: dict) -> Decimal:
        price = cls.FULLZ_BASE
        
        if config.get("credit_score"):
            price += {
                "500+": cls.FULLZ_CS_500_PLUS,
                "700+": cls.FULLZ_CS_700_PLUS,
                "800+": cls.FULLZ_CS_800_PLUS,
            }.get(config["credit_score"], Decimal("0.00"))
        
        if config.get("age"):
            price += {
                "18-25": cls.FULLZ_AGE_18_25,
                "26-35": cls.FULLZ_AGE_26_35,
                "36+": cls.FULLZ_AGE_36_PLUS,
            }.get(config["age"], Decimal("0.00"))
        
        if config.get("gender"):
            price += {
                "male": cls.FULLZ_GENDER_MALE,
                "female": cls.FULLZ_GENDER_FEMALE,
            }.get(config["gender"], Decimal("0.00"))
        
        if config.get("carrier_exclusion") and config["carrier_exclusion"] != "any":
            price += cls.FULLZ_NO_CARRIER

        if config.get("bank_exclusion") and config["bank_exclusion"] != "any":
            if config["bank_exclusion"] == "any_bank":
                price += cls.FULLZ_NO_BANK_ANY
            else:
                price += cls.FULLZ_NO_BANK_SINGLE

        if config.get("report_group"):
            price += {
                "basic": cls.FULLZ_REPORT_BASIC,
                "cr": cls.FULLZ_REPORT_CR,
                "cr_dl": cls.FULLZ_REPORT_CR_DL,
                "cr_dl_mvr": cls.FULLZ_REPORT_CR_DL_MVR,
                "cr_dl_fullmvr": cls.FULLZ_REPORT_CR_DL_FULLMVR,
            }.get(config["report_group"], Decimal("0.00"))

        if config.get("state") and config["state"] != "ANY":
            price += cls.FULLZ_STATE_SURCHARGE

        if config.get("company_type"):
            price += {
                "llc": cls.FULLZ_BIZ_LLC,
                "corp": cls.FULLZ_BIZ_CORP,
            }.get(config["company_type"], Decimal("0.00"))
        
        if config.get("loan_size"):
            price += {
                "25-200": cls.FULLZ_BIZ_LOAN_25_200,
                "200-500": cls.FULLZ_BIZ_LOAN_200_500,
                "500+": cls.FULLZ_BIZ_LOAN_500_PLUS,
            }.get(config["loan_size"], Decimal("0.00"))
        
        quantity = config.get("quantity", 1)
        discount = cls.get_bulk_discount(quantity)
        
        total = price * quantity
        total = total * (1 - discount)
        
        return total.quantize(Decimal("0.01"))
    
    @classmethod
    def calculate_business_fullz_price(cls, config: dict) -> Decimal:
        """Calculate Business FULLZ price using constants from prices.py"""
        price = cls.FULLZ_BIZ_BASE
        
        # Company Type
        if config.get("company_type"):
            price += {
                "llc": cls.FULLZ_BIZ_LLC,
                "corp": cls.FULLZ_BIZ_CORP,
            }.get(config["company_type"], Decimal("0.00"))
        
        # Loan Size
        if config.get("loan_size"):
            price += {
                "25k-200k": cls.FULLZ_BIZ_LOAN_25_200,
                "200k-500k": cls.FULLZ_BIZ_LOAN_200_500,
                "500k+": cls.FULLZ_BIZ_LOAN_500_PLUS,
            }.get(config["loan_size"], Decimal("0.00"))
        
        # Credit Score (используем существующие константы)
        if config.get("credit_score"):
            price += {
                "500+": cls.FULLZ_CS_500_PLUS,
                "700+": cls.FULLZ_CS_700_PLUS,
                "800+": cls.FULLZ_CS_800_PLUS,
            }.get(config["credit_score"], Decimal("0.00"))
        
        # Report Group (используем существующие константы)
        if config.get("report_group"):
            price += {
                "basic": cls.FULLZ_REPORT_BASIC,
                "cr": cls.FULLZ_BIZ_REPORT_CR,  # Business: +$4
                "cr_dl": cls.FULLZ_REPORT_CR_DL,
                "cr_dl_mvr": cls.FULLZ_REPORT_CR_DL_MVR,
                "cr_dl_fullmvr": cls.FULLZ_REPORT_CR_DL_FULLMVR,
            }.get(config["report_group"], Decimal("0.00"))

        if config.get("state") and config["state"] != "ANY":
            price += cls.FULLZ_STATE_SURCHARGE

        quantity = config.get("quantity", 1)
        discount = cls.get_bulk_discount(quantity)
        
        total = price * quantity
        total = total * (1 - discount)
        
        return total.quantize(Decimal("0.01"))
    
    @staticmethod
    def get_bulk_discount(quantity: int) -> Decimal:
        """Универсальный метод (использует eSIM/FULLZ скидки для обратной совместимости)"""
        return BulkDiscounts.get_esim_discount_decimal(quantity)
    
    @classmethod
    def get_service_price(cls, service_name: str, is_bulk: bool = False) -> Decimal:
        """Get price for a service — reads from DB first, then falls back to hardcoded"""
        price_map = {
            "lookup_ssn": (cls.LOOKUP_SSN_DOB, cls.LOOKUP_SSN_DOB_BULK),
            "lookup_credit": (cls.LOOKUP_CREDIT_SCORE, cls.LOOKUP_CREDIT_SCORE_BULK),
            "lookup_credit_score": (cls.LOOKUP_CREDIT_SCORE, cls.LOOKUP_CREDIT_SCORE_BULK),
            "lookup_dl": (cls.LOOKUP_DL, cls.LOOKUP_DL_BULK),
            "lookup_mvr": (cls.LOOKUP_MVR, cls.LOOKUP_MVR_BULK),
            "lookup_fullmvr": (cls.LOOKUP_FULL_MVR, cls.LOOKUP_FULL_MVR_BULK),
            "lookup_full_mvr": (cls.LOOKUP_FULL_MVR, cls.LOOKUP_FULL_MVR_BULK),
            "lookup_bg": (cls.LOOKUP_BG, cls.LOOKUP_BG_BULK),
            "lookup_mmn": (cls.LOOKUP_MMN, cls.LOOKUP_MMN),
            "lookup_ein": (cls.LOOKUP_EIN, cls.LOOKUP_EIN),
            "cr_transunion": (cls.CR_TRANSUNION, cls.CR_TRANSUNION_BULK),
            "cr_experian": (cls.CR_EXPERIAN, cls.CR_EXPERIAN_BULK),
            "cr_lexisnexis": (cls.CR_LEXISNEXIS, cls.CR_LEXISNEXIS_BULK),
            "cr_wallethub": (cls.CR_WALLETHUB, cls.CR_WALLETHUB_BULK),
        }

        single_price, bulk_price = price_map.get(service_name, (Decimal("0.00"), Decimal("0.00")))
        return bulk_price if is_bulk else single_price

    @classmethod
    async def get_dynamic_price(cls, session, key: str) -> "Decimal | None":
        """Read price from ServicePrice DB table"""
        try:
            from sqlalchemy import select
            from shared.database.models import ServicePrice
            result = await session.execute(
                select(ServicePrice).where(ServicePrice.key == key, ServicePrice.is_active == True)
            )
            item = result.scalar_one_or_none()
            if item:
                return item.price
        except Exception:
            pass
        return None

    @classmethod
    async def get_dynamic_price_pair(cls, session, key: str) -> "tuple":
        """Read (price, bulk_price) from ServicePrice DB table"""
        try:
            from sqlalchemy import select
            from shared.database.models import ServicePrice
            result = await session.execute(
                select(ServicePrice).where(ServicePrice.key == key, ServicePrice.is_active == True)
            )
            item = result.scalar_one_or_none()
            if item:
                return (item.price, item.bulk_price or item.price)
        except Exception:
            pass
        return None
