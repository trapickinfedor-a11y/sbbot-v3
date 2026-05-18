from __future__ import annotations

"""
English button texts for Mirror Bot
"""

import re

class ButtonTexts:
    COUNT_SUFFIX_RE = re.compile(r"\s*\[(?:\d+|\?)\]\s*$")
    
    @staticmethod
    def get_qty_button(qty: int, discount: int) -> str:
        """Генерирует текст кнопки количества с скидкой"""
        from mirror_bot.constants.prices import BulkDiscounts
        
        qty_emoji = {
            2: "2️⃣",
            3: "3️⃣",
            5: "5️⃣",
            6: "6️⃣",
            10: "1️⃣0️⃣"
        }
        
        emoji = qty_emoji.get(qty, str(qty))
        if discount > 0:
            return f"{emoji} (-{discount}%)"
        return emoji
    
    @staticmethod
    def get_referrals_button():
        """Генерирует текст кнопки рефералов с процентом из prices.py"""
        from mirror_bot.constants.prices import SystemFees
        from mirror_bot.constants.prices import SystemFees
        return f"🤝 Referrals +{SystemFees.REFERRAL_PERCENT}%"
    
    @staticmethod
    def get_all_variants(button_name: str) -> list:
        """Возвращает все языковые варианты кнопки"""
        from mirror_bot.constants.language_loader import get_buttons
        en = get_buttons('en')
        ru = get_buttons('ru')
        zh = get_buttons('zh')
        es = get_buttons('es')
        
        variants_map = {
            'MY_PROFILE': [en.MY_PROFILE, ru.MY_PROFILE, zh.MY_PROFILE, es.MY_PROFILE],
            'TOP_UP_BALANCE': [en.TOP_UP_BALANCE, ru.TOP_UP_BALANCE, zh.TOP_UP_BALANCE, es.TOP_UP_BALANCE],
            'SEARCH': [en.SEARCH, ru.SEARCH, zh.SEARCH, es.SEARCH],
            'CREDIT_REPORTS': [en.CREDIT_REPORTS, ru.CREDIT_REPORTS, zh.CREDIT_REPORTS, es.CREDIT_REPORTS],
            'DOCUMENTS': [en.DOCUMENTS, ru.DOCUMENTS, zh.DOCUMENTS, es.DOCUMENTS],
            'PROS_FULLZ': [en.PROS_FULLZ, ru.PROS_FULLZ, zh.PROS_FULLZ, es.PROS_FULLZ],
            'BANKS': [en.BANKS, ru.BANKS, zh.BANKS, es.BANKS],
            'EDUCATION': [en.EDUCATION, ru.EDUCATION, zh.EDUCATION, es.EDUCATION],
            'CC': [en.CC, ru.CC, zh.CC, es.CC],
            'ANOTHER_SERVICES': [en.ANOTHER_SERVICES, ru.ANOTHER_SERVICES, zh.ANOTHER_SERVICES, es.ANOTHER_SERVICES],
            'ESIM': [en.ESIM, ru.ESIM, zh.ESIM, es.ESIM],
            'SUBSCRIPTIONS_ACCOUNTS': [en.SUBSCRIPTIONS_ACCOUNTS, ru.SUBSCRIPTIONS_ACCOUNTS, zh.SUBSCRIPTIONS_ACCOUNTS, es.SUBSCRIPTIONS_ACCOUNTS],
            'ADD_INFO_CR': [en.ADD_INFO_CR, ru.ADD_INFO_CR, zh.ADD_INFO_CR, es.ADD_INFO_CR],
            'SERVICE_RULES': [en.SERVICE_RULES, ru.SERVICE_RULES, zh.SERVICE_RULES, es.SERVICE_RULES],
            'CALL_SERVICE': [en.CALL_SERVICE, ru.CALL_SERVICE, zh.CALL_SERVICE, es.CALL_SERVICE],
            'SUPPORT': [en.SUPPORT, ru.SUPPORT, zh.SUPPORT, es.SUPPORT],
            'REFERRALS': [en.REFERRALS, ru.REFERRALS, zh.REFERRALS, es.REFERRALS],
            'NFC': [en.NFC, ru.NFC, zh.NFC, es.NFC],
            'ENROLL': [en.ENROLL, ru.ENROLL, zh.ENROLL, es.ENROLL],
            'SELFREG_BA': [en.SELFREG_BA, ru.SELFREG_BA, zh.SELFREG_BA, es.SELFREG_BA],
            'LOGS': [en.LOGS, ru.LOGS, zh.LOGS, es.LOGS],
            'OTP_CARD': [en.OTP_CARD, ru.OTP_CARD, zh.OTP_CARD, es.OTP_CARD],
            'SELFREG_CC': [en.SELFREG_CC, ru.SELFREG_CC, zh.SELFREG_CC, es.SELFREG_CC],
            'CHECKS': [en.CHECKS, ru.CHECKS, zh.CHECKS, es.CHECKS],
            'MY_PURCHASES': [
                getattr(en, 'MY_PURCHASES', '📦 My Purchases'),
                getattr(ru, 'MY_PURCHASES', '📦 Мои покупки'),
                getattr(zh, 'MY_PURCHASES', '📦 我的购买'),
                getattr(es, 'MY_PURCHASES', '📦 Mis compras'),
            ],
            'SETUP_ARCHIVE': [
                getattr(en, 'SETUP_ARCHIVE', '📁 Setup Archive'),
                getattr(ru, 'SETUP_ARCHIVE', '📁 Настроить архив'),
                getattr(zh, 'SETUP_ARCHIVE', '📁 设置归档'),
                getattr(es, 'SETUP_ARCHIVE', '📁 Configurar archivo'),
            ],
            'VIP_WATCHLIST': [en.VIP_WATCHLIST, en.VIP_WATCHLIST, en.VIP_WATCHLIST, en.VIP_WATCHLIST],
        }
        
        return variants_map.get(button_name, [])

    @classmethod
    def strip_count_suffix(cls, text: str | None) -> str:
        return cls.COUNT_SUFFIX_RE.sub("", text or "").strip()

    @classmethod
    def with_count(cls, text: str, count: int | None) -> str:
        if count == "?":
            return f"{text} [?]"
        if count is None:
            return text
        return f"{text} [{max(0, int(count))}]"

    @classmethod
    def matches(cls, button_name: str, text: str | None) -> bool:
        normalized = cls.strip_count_suffix(text)
        return normalized in [cls.strip_count_suffix(item) for item in cls.get_all_variants(button_name)]
    
    # ========== LANGUAGE SELECTION ==========
    LANG_RUSSIAN = "🇷🇺 Russian"
    LANG_ENGLISH = "🇬🇧 English"
    LANG_CHINESE = "🇨🇳 Chinese"
    LANG_SPANISH = "🇪🇸 Spanish"
    
    # ========== PROFILE ==========
    SEND_MONEY = "💸 Send money to another user"
    REFERRAL_SYSTEM = "🤝 Referral system"
    MY_BANK_ORDERS = "📦 My Bank Orders"
    MY_PURCHASES = "📦 My Purchases"
    SETUP_ARCHIVE = "📁 Setup Archive"
    CHOOSE_LANGUAGE = "🌍 Choose language"
    BACK = "⬅️ Back"
    
    # ========== PAYMENT ==========
    PAY_CRYPTOBOT = "🪙 Pay via CryptoBot "
    PAY_CRYPTOMUS = "💎 Pay via Cryptomus 🔥"
    PAY_VIA_CRYPTOBOT = "🪙 Pay via CryptoBot"
    PAY_VIA_CRYPTOMUS = "💎 Pay via Cryptomus"
    OPEN_PAYMENT_LINK = "💳 Open Payment Link"
    REFRESH_STATUS = "♻️ Refresh Status"
    PAY_INVOICE = "💳 Pay Invoice"
    CHECK_STATUS = "♻️ Check Status"
    CANCEL = "❌ Cancel"
    PAY_WITH_CRYPTO = "💳 Pay with Crypto"
    BACK_TO_MENU = "⬅️ Back to Menu"
    
    # ========== ORDERS ==========
    CONFIRM = "✅ Confirm"
    CANCEL_ORDER = "❌ Cancel"
    SINGLE_ORDER = "1️⃣ Single Order"
    BULK_ORDER = "💼 Bulk Order (2-20)"
    CONFIRM_ALL = "✅ Confirm All"
    BULK_CANCEL = "❌ Cancel"
    
    # ========== CONFIRMATION ==========
    EDIT = "✏️ Edit"
    CONTINUE = "✅ Continue"
    CONFIRM_PAY = "✅ Confirm & Pay"
    CONFIRM_BUSINESS = "✅ CONFIRM"
    
    # ========== LOOKUP SERVICES ==========
    SSN_DOB_LOOKUP = "🧾 SSN & DOB — $2.8-$3"
    CREDIT_SCORE_LOOKUP = "📉 Credit Score — $1.6-$2"
    DL_LOOKUP = "🪪 DL — $6.50-$7"
    MVR_LOOKUP = "🚗 MVR — $10-$11"
    FULL_MVR_LOOKUP = "📋 Full MVR — $20-$22"
    PHONE_SEARCH = "📞 Phone Search"
    BG_LOOKUP = "👤 BG — $1.5-$2"
    MMN_LOOKUP = "👩‍👦 MMN — $9"
    EIN_LOOKUP = "🏢 EIN — $11"
    LOOKUP_SSN_DOB = "🧾 SSN & DOB — $2.8-$3"
    LOOKUP_CREDIT_SCORE = "📉 Credit Score — $1.6-$2"
    LOOKUP_DL = "🪪 DL — $6.50-$7"
    LOOKUP_MVR = "🚗 MVR — $10-$11"
    LOOKUP_FULL_MVR = "📋 Full MVR — $20-$22"
    LOOKUP_PHONE_SEARCH = "📞 Phone Search"
    LOOKUP_BACKGROUND = "👤 BG — $1.5-$2"
    LOOKUP_MMN = "👩‍👦 MMN — $9"
    LOOKUP_EIN = "🏢 EIN — $11"
    LOOKUP_SUPPORT = "💬 Lookup Support"
    LOOKUP_BUTTON = "📖 Lookup"
    BRUTE_BANK_SOON = "🔓 Brute BANK"
    LOOKUP_BA_SUPPORT = "📖 LOOKUP BA SUPPORT"
    LOOKUP_BANK_ACCOUNTS = "🏦 Bank Account Lookup"

    # ========== BANKS ON-NAME ==========
    ORDER_BY_NAME = "📝 Order by Name"

    # ========== PROFILE EXTRAS ==========
    MY_CC_ORDERS = "💳 My CC Orders"

    # ========== BRUTE BANK ==========
    BRUTE_BANK = "🔓 Brute BANK"
    BRUTE_BUY = "⚡ Buy Now"
    BRUTE_BACK = "⬅️ Back to Brute"

    # ========== EDUCATION ==========
    EDU_SUBSCRIPTIONS = "📅 Subscriptions"
    EDU_MANUALS = "📖 Manuals"
    EDU_BUY_SUBSCRIPTION = "✅ Buy Subscription"
    EDU_BUY_MANUAL = "📥 Buy Manual"
    EDU_BACK = "⬅️ Back to Education"
    
    # ========== PHONE LOOKUP ==========
    PHONE_NAME_LOOKUP = "📛 NAME LOOKUP — $1.5"
    PHONE_SSN_LOOKUP = "🆔 NAME DOB SSN — $4"
    PHONE_NAME_DOB_SSN = "🆔 NAME DOB SSN — $4"
    PHONE_FULL_LOOKUP = "📊 FULL LOOKUP — $5"
    
    # ========== CREDIT REPORTS ==========
    CR_TRANSUNION = "🟢 TransUnion — $4.99"
    CR_EXPERIAN = "🔵 Experian — $5.99"
    CR_EQUIFAX = "🟡 EQUIFAX — $5.99"
    CR_LEXISNEXIS = "🟣 LexisNexis — $9.99"
    CR_WALLETHUB = "⚪ WalletHub / Credit Karma — $7.99"
    
    # ========== BANKS ==========
    BANKS_PERSONAL_VCC = "💳 PERSONAL VCC"
    BANKS_PERSONAL = "🏦 PERSONAL BANKS"
    BANKS_BUSINESS = "🏢 BUSINESS BANKS"
    BANKS_CRYPTO = "🪙 CRYPTO BANKS"
    BANKS_MERCHANT = "🏪 Merchant"
    BANKS_LOGS = "📋 Logs BA"

    # ========== CC ==========
    CC_ENROLL = "🏦 Enroll"
    CC_OTP = "🔑 OTP"
    CC_NFC = "📱 NFC"
    CC_SELFREG_CC = "🏧 Selfreg CC"
    CC_CHECKS = "📄 Checks"
    CC_BUY = "🛒 Buy"
    CC_LIKE = "👍 Like"
    CC_DISLIKE = "👎 Dislike"
    CC_REPORT_ISSUE = "⚠️ Report Issue"
    CC_BACK_TO_CC = "⬅️ Back to CC"
    CC_OPEN_CHAT = "💬 Open Seller Chat"
    CC_NO_ITEMS = "📭 No items available"

    # ========== DOCUMENTS ==========
    DOCS_CHECKS = "📄 Checks"

    # ========== VIP ==========
    VIP_WATCHLIST = "🌟 VIP Watchlist — $500"
    BANKS_PREV = "⬅️ Prev"
    BANKS_NEXT = "Next ➡️"
    BANKS_BACK_TO_CATEGORIES = "🏠 Back to Categories"
    
    # ========== BANK QUANTITIES ==========
    QTY_2 = "2️⃣"
    QTY_3_DISCOUNT = "3️⃣ (-2%)"
    QTY_5_DISCOUNT = "5️⃣ (-3%)"
    QTY_10_DISCOUNT = "1️⃣0️⃣ (-5%)"
    BANK_QTY_3 = "3️⃣ (-2%)"
    BANK_QTY_5 = "5️⃣ (-3%)"
    BANK_QTY_10 = "1️⃣0️⃣ (-5%)"
    CUSTOM_QUANTITY = "📝 Custom Quantity"
    BANK_CUSTOM_QTY = "📝 Custom Quantity"
    BUY_1_ITEM = "✅ Buy 1 item"
    BACK_TO_LIST = "⬅️ Back to List"
    
    # ========== ESIM ==========
    ESIM_SMS = "🇺🇸 eSIM for SMS"
    ESIM_DATA = "📶 eSIM for Data"
    ESIM_GV = "📞 Google Voice"
    ESIM_VERIZON_SMS = "📶 Verizon — $20/month"
    ESIM_ATT_SMS = "📶 AT&T — $35/month"
    ESIM_TMOBILE_SMS = "📶 T-Mobile — $35/month"
    ESIM_VERIZON_DATA = "📶 Verizon (5-15 GB)"
    ESIM_ATT_DATA = "📶 AT&T (10-30 GB)"
    ESIM_TMOBILE_DATA = "📶 T-Mobile (10-30 GB)"
    
    # ========== ESIM PERIODS ==========
    ESIM_1_MONTH = "⏳ 1 month"
    ESIM_3_MONTHS = "⏳ 3 months"
    ESIM_6_MONTHS = "⏳ 6 months"
    
    # ========== ESIM DATA PLANS ==========
    ESIM_5GB = "📦 5 GB — $10"
    ESIM_10GB = "📦 10 GB — $20"
    ESIM_15GB = "📦 15 GB — $30"
    
    # ========== SUPPORT ==========
    SUPPORT_PAYMENT = "💰 Payment"
    SUPPORT_PRODUCT = "📦 Product"
    SUPPORT_GENERAL = "💬 General"
    SUPPORT_PARTNERSHIP = "🤝 Partnership"
    MY_TICKETS = "📋 My tickets"
    SUPPORT_BACK = "⬅️ Back"
    
    # ========== TICKET ACTIONS ==========
    TICKET_REPLY = "✍️ Reply"
    TICKET_ATTACH_FILES = "📎 Attach files"
    TICKET_BACK_TO_TICKETS = "⬅️ Back to my tickets"
    TICKET_BACK_TO_SUPPORT = "⬅️ Back to support"
    
    # ========== MAIN KEYBOARD ==========
    EDUCATION = "📚 Education"
    MY_PROFILE = "👤 My profile"
    TOP_UP_BALANCE = "💳 Top-up balance"
    SEARCH = "🔎 Search"
    CREDIT_REPORTS = "📈 CREDIT REPORTS"
    DOCUMENTS = "📄 DOCUMENTS"
    PROS_FULLZ = "🧰 PROS & FULLZ"
    BANKS = "🏦 BANKS"
    CC = "💳 CC"
    NFC = "📱 NFC"
    ENROLL = "🏦 Enroll"
    SELFREG_BA = "🏧 Selfreg BA"
    LOGS = "📋 Logs"
    OTP_CARD = "📲 OTP Card"
    SELFREG_CC = "💳 Selfreg CC"
    CHECKS = "📄 Checks"
    ESIM = "📶 eSIM"
    SUBSCRIPTIONS_ACCOUNTS = "🧾 Subscriptions / Accounts"
    ADD_INFO_CR = "✍️ Add info in CR"
    SERVICE_RULES = "📜 Service rules"
    CALL_SERVICE = "📞 CALL SERVICE"
    ANOTHER_SERVICES = "📞 Other Services"
    REFERRALS = "🤝 Referrals +25%"
    SUPPORT = "📞 Support"
    ACCEPT_RULES = "✅ I accept the rules"
    DECLINE_RULES = "❌ I decline"
    VIEW_RULES = "📜 Rules"
    
    # ========== PAGINATION ==========
    PAGE_INFO = "📄 {page}/{total_pages}"
    PREV = "⬅️ Prev"
    NEXT = "Next ➡️"
    PREV_PAGE = "⬅️ Prev"
    NEXT_PAGE = "Next ➡️"
    BACK_SUPPORT = "⬅️ Back"
    BACK_TO_SUPPORT = "⬅️ Back to support"
    BACK_TO_CATEGORIES = "🏠 Back to Categories"
    BACK_FULLZ = "⬅️ Back"
    BACK_FULLZ_SHORT = "🔙 Back"
    EDIT_FULLZ = "✏️ Edit"
    BUY_ANY = "🎯 BUY ANY"
    CUSTOMISE = "⚙️ CUSTOMISE"
    TEXT_ORDER = "📝 TEXT"
    
    # ========== DOCUMENTS ==========
    HIGH_QUALITY_DRAWING_COMING_SOON = "🧑‍🎨 High-Quality Drawing"
    ROBOT_DRAWING_COMING_SOON = "🤖 Robot Drawing (Soon)"
    PHOTO = "🔥📸 Photo🔥"
    DL_FRONT_BACK = "🪪 DL (Front & Back)"
    DL_SELFIE = "🤳 DL + Selfie"
    DL_KYC = "🤳 DL + KYC video"
    PASSPORT = "🛂 Passport"
    BUSINESS_DOCS = "🧾 Business Docs"
    
    # ========== ADD INFO ==========
    ADDINFO_CR = "📈 Add Info in Credit Report"
    ADDINFO_BG = "🧾 Add Info in BG"
    ADDINFO_EMPLOYER = "🏢 Add Employer to CR"
    ADDINFO_UNFREEZE = "❄️ Unfreeze CR"
    
    # ========== FULLZ ==========
    FULLZ_PERSONAL = "👤 PERSONAL"
    FULLZ_BUSINESS = "🏢 BUSINESS"
    FULLZ_WITH_CS_CR = "🔥 CUSTOM WITH CS/CR"
    FULLZ_700_PLUS = "💳 700+ CS"
    FULLZ_800_PLUS = "⭐ 800+ CS"
    FULLZ_UNDER_18 = "🧒 UNDER 18 OLD"
    FULLZ_IMMIGRANT = "🌍 IMMIGRANT"
    FULLZ_ZERO_BANK = "🏦 FULLZ 0 BANK"
    FULLZ_SUPPORT = "📞 FULLZ SUPPORT"
    FULLZ_RANDOM = "🎲 RANDOM"
    
    # ========== MISC ==========
    BULK_ORDER_BUTTON = "📦 Bulk Order (2-20)"
    REORDER = "🔄 Order again"
