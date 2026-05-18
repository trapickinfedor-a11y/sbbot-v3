"""
Константы категорий и сервисов для веб-панели
"""

# Структура категорий и их сервисов
CATEGORIES_DATA = {
    "📶 eSIM": {
        "emoji": "📶",
        "name": "eSIM",
        "services": {
            "eSIM for receive SMS": [
                {"code": "sms_verizon", "name": "Verizon"},
                {"code": "sms_att", "name": "AT&T"}, 
                {"code": "sms_tmobile", "name": "T-Mobile"}
            ],
            "eSIM for Data": [
                {"code": "data_verizon", "name": "Verizon"},
                {"code": "data_att", "name": "AT&T"},
                {"code": "data_tmobile", "name": "T-Mobile"}
            ]
        }
    },
    "📄 DOCUMENTS": {
        "emoji": "📄",
        "name": "DOCUMENTS", 
        "services": {
            "Photo Documents": [
                {"code": "doc_dl", "name": "DL (Front & Back)"},
                {"code": "doc_dl_selfie", "name": "DL + Selfie"}, 
                {"code": "doc_passport", "name": "Passport"},
                {"code": "doc_business", "name": "Business Docs"}
            ]
            # Drawing Documents - Coming Soon
            # "Drawing Documents": [
            #     "High-Quality Drawing",
            #     "Robot Drawing"
            # ]
        }
    },
    "🧰 PROS & FULLZ": {
        "emoji": "🧰",
        "name": "PROS & FULLZ",
        "services": {
            "FULLZ Types": [
                {"code": "fullz_cs", "name": "CUSTOM WITH CS/CR"},
                {"code": "fullz_700plus", "name": "700+ CS"},
                {"code": "fullz_800plus", "name": "800+ CS"},
                {"code": "fullz_under18", "name": "UNDER 18 OLD"},
                {"code": "fullz_immigrant", "name": "IMMIGRANT"},
                {"code": "fullz_zero_bank", "name": "FULLZ 0 BANK"},
                {"code": "fullz_random", "name": "RANDOM"},
                {"code": "personal_random", "name": "RANDOM (Personal)"},
                {"code": "fullz_business", "name": "BUSINESS"}
            ]
        }
    },
    "🏦 BANKS": {
        "emoji": "🏦", 
        "name": "BANKS",
        "services": {
            "PERSONAL VCC": [
                {"code": "vcc_chime", "name": "Chime VCC"},
                {"code": "vcc_paypal", "name": "PayPal VCC"},
                {"code": "vcc_onepay", "name": "One Pay VCC"},
                {"code": "vcc_current", "name": "Current VCC"}, 
                {"code": "vcc_neteller", "name": "Neteller VCC"},
                {"code": "vcc_wise", "name": "Wise Personal VCC"},
                {"code": "vcc_netspend", "name": "Netspend VCC"},
                {"code": "vcc_greenfi", "name": "GreenFi VCC"},
                {"code": "vcc_quickbooks", "name": "QuickBooks VCC"},
                {"code": "vcc_go2bank", "name": "Go2Bank + VCC"},
                {"code": "vcc_venmo", "name": "Venmo"},
                {"code": "vcc_kikoff", "name": "Kikoff"},
                {"code": "vcc_shopify", "name": "Shopify"},
                {"code": "vcc_varo", "name": "Varo + VCC"}
            ],
            "PERSONAL BANKS": [
                {"code": "pers_citi", "name": "Citi Personal"},
                {"code": "pers_citi_gold", "name": "Citi Gold Bank"},
                {"code": "pers_usalliance", "name": "Usalliance"},
                {"code": "pers_usbank", "name": "US Bank"},
                {"code": "pers_ally", "name": "Ally Bank"}, 
                {"code": "pers_regions", "name": "Regions Bank"},
                {"code": "pers_chase", "name": "Chase"},
                {"code": "pers_wells", "name": "WellsFargo"},
                {"code": "pers_schwab", "name": "Charles Schwab"},
                {"code": "pers_citizens", "name": "Citizens Bank"},
                {"code": "pers_huntington", "name": "Huntington Bank"},
                {"code": "pers_td", "name": "TD bank"},
                {"code": "pers_boa", "name": "BankOFAmerica"},
                {"code": "pers_alliant", "name": "Alliant Cu"},
                {"code": "pers_pnc", "name": "Pnc Bank"}
            ],
            "BUSINESS BANKS": [
                {"code": "biz_quickbooks", "name": "QuickBooks (LLC/ CORP)"},
                {"code": "biz_bmo", "name": "Bmo Business"},
                {"code": "biz_boa", "name": "BankOFAmerica Business"},
                {"code": "biz_usbank", "name": "Us Business"},
                {"code": "biz_north_one", "name": "North One (LLC/Corp)"},
                {"code": "biz_lili", "name": "Lili Business Vcc"}, 
                {"code": "biz_pnc", "name": "Pnc Business"},
                {"code": "biz_capital_one", "name": "Capital One Business"},
                {"code": "biz_chase", "name": "Chase Business"},
                {"code": "biz_wells", "name": "Wells Fargo Business"}
            ],
            "CRYPTO BANKS": [
                {"code": "crypto_cashapp", "name": "Cash App + BTC"},
                {"code": "crypto_blockchain", "name": "Blockchain Gold"},
                {"code": "crypto_kraken", "name": "Kraken"},
                {"code": "crypto_coinbase", "name": "CoinBase"},
                {"code": "crypto_crypto_com", "name": "Crypto.com"},
                {"code": "crypto_binance", "name": "Binance"}
            ]
        }
    },
    "🧾 Subscriptions / Accounts": {
        "emoji": "🧾",
        "name": "Subscriptions / Accounts",
        "services": {
            "Background Accounts": [
                {"code": "bg_beenverified", "name": "BeenVerified"},
                {"code": "bg_truthfinder", "name": "TruthFinder"},
                {"code": "bg_instantcheck", "name": "InstantCheckmate"},
                {"code": "bg_intelius", "name": "Intelius"},
                {"code": "bg_whitepages", "name": "WhitePages"},
                {"code": "bg_mylife", "name": "MyLife"},
                {"code": "bg_intelius_30", "name": "Intelius - 30 days"},
                {"code": "bg_truthfinder_30", "name": "Truthfinder - 30 days"},
                {"code": "bg_instantcheck_30", "name": "InstantCheckmate - 30 days"},
                {"code": "bg_whitepages_30", "name": "Whitepages - 30 days"}
            ],
            "Financial Apps": [
                {"code": "lookup_monarch", "name": "Monarch Money"},
                {"code": "lookup_yodlee", "name": "Yodlee"}, 
                {"code": "lookup_empower", "name": "Empower"},
                {"code": "lookup_pocketguard", "name": "PocketGuard"},
                {"code": "lookup_everydollar", "name": "EveryDollar"}
            ]
        }
    },
    "✍️ Add info in CR": {
        "emoji": "✍️",
        "name": "Add info in CR",
        "services": {
            "Add Info in Credit Report": [
                {"code": "addcr_all", "name": "Add phone + address + employer (all CR)"},
                {"code": "addcr_phone_addr", "name": "Add phone + address (all CR)"},
                {"code": "addcr_phone_all", "name": "Add phone (all CR)"},
                {"code": "addcr_addr_all", "name": "Add address (all CR)"},
                {"code": "addcr_phone_ex", "name": "Add phone (EX)"},
                {"code": "addcr_addr_ex", "name": "Add address (EX)"},
                {"code": "addcr_phone_tu", "name": "Add phone (TU)"},
                {"code": "addcr_addr_tu", "name": "Add address (TU)"}
            ],
            "Add Info in BG": [
                {"code": "addbg_phone_addr", "name": "Add phone + address (BG)"},
                {"code": "addbg_phone", "name": "Add phone (BG)"},
                {"code": "addbg_addr", "name": "Add address (BG)"}
            ],
            "Add Employer to CR": [
                {"code": "addemp_tu", "name": "Add employer (TU)"},
                {"code": "addemp_update", "name": "Update current employer"},
                {"code": "addemp_remove", "name": "Remove outdated employer"}
            ],
            "Unfreeze CR": [
                {"code": "unfreeze_tu", "name": "Permanent Unfreeze (TU)"},
                {"code": "unfreeze_ex", "name": "Permanent Unfreeze (EX)"}
            ]
        }
    },
    "🔎 Search": {
        "emoji": "🔎",
        "name": "Search",
        "services": {
            "Lookup Services": [
                {"code": "ssn_dob", "name": "SSN & DOB"},
                {"code": "credit", "name": "Credit Score"},
                {"code": "dl", "name": "DL (Driver License)"},
                {"code": "mvr", "name": "MVR"},
                {"code": "fullmvr", "name": "Full MVR"},
                {"code": "phone_name", "name": "Phone to Name & Address"},
                {"code": "phone_ssn", "name": "Phone to SSN"},
                {"code": "phone_full", "name": "Phone Full Info"},
                {"code": "bg", "name": "BG (Background)"},
                {"code": "mmn", "name": "MMN (Mother's Maiden Name)"},
                {"code": "ein", "name": "EIN (Business Info)"}
            ],
            "Bank Lookup": [
                {"code": "lookup_ba_an_rn", "name": "Check AN+RN"},
                {"code": "lookup_ba_transactions", "name": "Check Transactions [15 days]"},
                {"code": "lookup_ba_balance", "name": "Check Balance"},
                {"code": "lookup_ba_name", "name": "Check NAME"},
                {"code": "lookup_ba_an_rn_name", "name": "Check AN+RN+NAME"}
            ]
        }
    },
    "📈 CREDIT REPORTS": {
        "emoji": "📈",
        "name": "CREDIT REPORTS",
        "services": {
            "Credit Bureaus": [
                {"code": "cr_transunion", "name": "TransUnion"},
                {"code": "cr_experian", "name": "Experian"}, 
                {"code": "cr_equifax", "name": "Equifax"},
                {"code": "cr_lexisnexis", "name": "LexisNexis"},
                {"code": "cr_wallet", "name": "WalletHub / Credit Karma"}
            ]
        }
    }
}

# Плоский список всех категорий
ALL_CATEGORIES = list(CATEGORIES_DATA.keys())

# Плоский список всех сервисов (коды)
ALL_SERVICES = []
for category_data in CATEGORIES_DATA.values():
    for service_group in category_data["services"].values():
        for service in service_group:
            if isinstance(service, dict):
                ALL_SERVICES.append(service["code"])
            else:
                ALL_SERVICES.append(service)

# Маппинг сервисов из ботов на категории веб-панели
SERVICE_TO_CATEGORY_MAPPING = {
    # Lookup services
    "ssn_dob": "🔎 Search",
    "dl": "🔎 Search",
    "credit": "🔎 Search", 
    "bg": "🔎 Search",
    "mmn": "🔎 Search",
    "ein": "🔎 Search",
    "mvr": "🔎 Search",
    "fullmvr": "🔎 Search",
    "phone_name": "🔎 Search",
    "phone_ssn": "🔎 Search", 
    "phone_full": "🔎 Search",
    # Bank Lookup (BA)
    "lookup_ba_an_rn": "🔎 Search",
    "lookup_ba_transactions": "🔎 Search",
    "lookup_ba_balance": "🔎 Search",
    "lookup_ba_name": "🔎 Search",
    "lookup_ba_an_rn_name": "🔎 Search",
    
    # Credit Reports
    "cr_transunion": "📈 CREDIT REPORTS",
    "cr_experian": "📈 CREDIT REPORTS",
    "cr_equifax": "📈 CREDIT REPORTS",
    "cr_lexisnexis": "📈 CREDIT REPORTS",
    "cr_wallet": "📈 CREDIT REPORTS",
    
    # Documents (Photo Documents only - Drawing is Coming Soon)
    "doc_dl": "📄 DOCUMENTS",
    "doc_dl_selfie": "📄 DOCUMENTS",
    "doc_passport": "📄 DOCUMENTS",
    "doc_biz": "📄 DOCUMENTS",
    "doc_business": "📄 DOCUMENTS",
    
    # Coming Soon (not implemented yet)
    # "doc_drawing": "📄 DOCUMENTS",
    # "doc_robot": "📄 DOCUMENTS",
    
    # FULLZ - все типы
    "fullz_cs": "🧰 PROS & FULLZ",
    "fullz_700plus": "🧰 PROS & FULLZ",
    "fullz_800plus": "🧰 PROS & FULLZ",
    "fullz_under18": "🧰 PROS & FULLZ",
    "fullz_immigrant": "🧰 PROS & FULLZ",
    "fullz_zero_bank": "🧰 PROS & FULLZ",
    "fullz_random": "🧰 PROS & FULLZ",
    "personal_random": "🧰 PROS & FULLZ",
    "fullz_business": "🧰 PROS & FULLZ",
    "fullz_personal": "🧰 PROS & FULLZ",
    
    # Banks - VCC
    "vcc_chime": "🏦 BANKS",
    "vcc_paypal": "🏦 BANKS",
    "vcc_onepay": "🏦 BANKS",
    "vcc_current": "🏦 BANKS",
    "vcc_neteller": "🏦 BANKS",
    "vcc_wise": "🏦 BANKS",
    "vcc_netspend": "🏦 BANKS",
    "vcc_greenfi": "🏦 BANKS",
    "vcc_quickbooks": "🏦 BANKS",
    "vcc_go2bank": "🏦 BANKS",
    "vcc_venmo": "🏦 BANKS",
    "vcc_kikoff": "🏦 BANKS",
    "vcc_shopify": "🏦 BANKS",
    "vcc_varo": "🏦 BANKS",
    
    # Banks - Personal
    "pers_citi": "🏦 BANKS",
    "pers_citi_gold": "🏦 BANKS",
    "pers_usalliance": "🏦 BANKS",
    "pers_usbank": "🏦 BANKS",
    "pers_ally": "🏦 BANKS",
    "pers_regions": "🏦 BANKS",
    "pers_chase": "🏦 BANKS",
    "pers_wells": "🏦 BANKS",
    "pers_schwab": "🏦 BANKS",
    "pers_citizens": "🏦 BANKS",
    "pers_huntington": "🏦 BANKS",
    "pers_td": "🏦 BANKS",
    "pers_boa": "🏦 BANKS",
    "pers_alliant": "🏦 BANKS",
    "pers_pnc": "🏦 BANKS",
    
    # Banks - Business
    "biz_quickbooks": "🏦 BANKS",
    "biz_bmo": "🏦 BANKS",
    "biz_boa": "🏦 BANKS",
    "biz_capital_one": "🏦 BANKS",
    "biz_chase": "🏦 BANKS",
    "biz_lili": "🏦 BANKS",
    "biz_north_one": "🏦 BANKS",
    "biz_pnc": "🏦 BANKS",
    "biz_usbank": "🏦 BANKS",
    "biz_wells": "🏦 BANKS",
    
    # Banks - Crypto
    "crypto_cashapp": "🏦 BANKS",
    "crypto_blockchain": "🏦 BANKS",
    "crypto_kraken": "🏦 BANKS",
    "crypto_coinbase": "🏦 BANKS",
    "crypto_crypto_com": "🏦 BANKS",
    "crypto_binance": "🏦 BANKS",
    
    # Accounts - Background
    "bg_beenverified": "🧾 Subscriptions / Accounts",
    "bg_truthfinder": "🧾 Subscriptions / Accounts",
    "bg_instantcheck": "🧾 Subscriptions / Accounts",
    "bg_intelius": "🧾 Subscriptions / Accounts",
    "bg_whitepages": "🧾 Subscriptions / Accounts",
    "bg_mylife": "🧾 Subscriptions / Accounts",
    "bg_intelius_30": "🧾 Subscriptions / Accounts",
    "bg_truthfinder_30": "🧾 Subscriptions / Accounts",
    "bg_instantcheck_30": "🧾 Subscriptions / Accounts",
    "bg_whitepages_30": "🧾 Subscriptions / Accounts",
    
    # Accounts - Financial
    "lookup_monarch": "🧾 Subscriptions / Accounts",
    "lookup_yodlee": "🧾 Subscriptions / Accounts",
    "lookup_empower": "🧾 Subscriptions / Accounts",
    "lookup_pocketguard": "🧾 Subscriptions / Accounts",
    "lookup_everydollar": "🧾 Subscriptions / Accounts",
    
    # Add Info - Credit Report
    "addcr_all": "✍️ Add info in CR",
    "addcr_phone_addr": "✍️ Add info in CR",
    "addcr_phone_all": "✍️ Add info in CR",
    "addcr_addr_all": "✍️ Add info in CR",
    "addcr_phone_ex": "✍️ Add info in CR",
    "addcr_addr_ex": "✍️ Add info in CR",
    "addcr_phone_tu": "✍️ Add info in CR",
    "addcr_addr_tu": "✍️ Add info in CR",
    
    # Add Info - Background
    "addbg_phone_addr": "✍️ Add info in CR",
    "addbg_phone": "✍️ Add info in CR",
    "addbg_addr": "✍️ Add info in CR",
    
    # Add Info - Employer
    "addemp_tu": "✍️ Add info in CR",
    "addemp_update": "✍️ Add info in CR",
    "addemp_remove": "✍️ Add info in CR",
    
    # Add Info - Unfreeze
    "unfreeze_tu": "✍️ Add info in CR",
    "unfreeze_ex": "✍️ Add info in CR",
}

# Специальная функция для eSIM (динамические service_name)
def get_esim_category(service_name: str) -> str:
    """Получить категорию для eSIM сервисов"""
    if service_name.startswith(
        ("sms_", "data_", "esim_cfg_", "esim_gv_", "gv_", "esim_sms_", "esim_data_")
    ):
        return "📶 eSIM"
    return None

# Маппинг product catalog category_key → order-категория веб-панели
# Только для категорий, которые имеют И заказы И каталог (order + catalog)
PRODUCT_CATEGORY_MAPPING = {
    "pros_fullz": "🧰 PROS & FULLZ",
}

# Категории, которые загружают только sellers (не воркеры)
SELLER_ONLY_CATALOG_CATEGORIES = {"docs"}

# Обратный маппинг: order-category → product catalog category_key
ORDER_CATEGORY_TO_PRODUCT_KEY = {v: k for k, v in PRODUCT_CATEGORY_MAPPING.items()}

# Маппинг order-категории → AccountCategory codes для загрузки credentials
# Воркер с этими order-категориями может загружать AccountInventory
ORDER_CATEGORY_TO_ACCOUNT_CODES = {
    "🧾 Subscriptions / Accounts": ["background", "lookup_ba", "email", "ai", "proxy"],
    "📶 eSIM": ["esim_sms", "esim_data", "gv"],
}

# Все account category_codes, которые воркер может загружать (union)
ALL_WORKER_ACCOUNT_CODES = set()
for _codes in ORDER_CATEGORY_TO_ACCOUNT_CODES.values():
    ALL_WORKER_ACCOUNT_CODES.update(_codes)

# Маппинг категорий из ботов на категории веб-панели
CATEGORY_MAPPING = {
    "lookup": "🔎 Search",
    "lookup_ba": "🔎 Search",
    "credit": "📈 CREDIT REPORTS",
    "credit_reports": "📈 CREDIT REPORTS",  # Добавляем альтернативное название
    "documents": "📄 DOCUMENTS",
    "fullz": "🧰 PROS & FULLZ",
    "banks": "🏦 BANKS",
    "accounts": "🧾 Subscriptions / Accounts",
    "addinfo": "✍️ Add info in CR",
    "esim": "📶 eSIM",
}

# Функция для получения категории по сервису
def get_category_by_service(service_name: str) -> str:
    """Получить категорию по названию сервиса"""
    # Сначала проверяем прямой маппинг
    if service_name in SERVICE_TO_CATEGORY_MAPPING:
        return SERVICE_TO_CATEGORY_MAPPING[service_name]
    
    # Проверяем eSIM (динамические service_name)
    esim_category = get_esim_category(service_name)
    if esim_category:
        return esim_category

    # Dynamic Accounts service names (acc_db_* or db_*)
    if service_name.startswith(("acc_db_", "db_")):
        return "🧾 Subscriptions / Accounts"

    # Затем ищем в структуре категорий
    for category, data in CATEGORIES_DATA.items():
        for service_group in data["services"].values():
            if service_name in service_group:
                return category
    return "Неизвестно"

# Функция для получения категории по категории из бота
def get_category_by_bot_category(bot_category: str) -> str:
    """Получить категорию веб-панели по категории из бота"""
    return CATEGORY_MAPPING.get(bot_category, bot_category)

# Функция для получения всех сервисов категории
def get_services_by_category(category: str) -> list:
    """Получить все сервисы категории"""
    if category not in CATEGORIES_DATA:
        return []
    
    services = []
    for service_group in CATEGORIES_DATA[category]["services"].values():
        for service in service_group:
            if isinstance(service, dict):
                services.append(service["code"])
            else:
                services.append(service)
    return services

# Функция для получения названия сервиса по коду
def get_service_name_by_code(code: str) -> str:
    """Получить название сервиса по его коду"""
    for category_data in CATEGORIES_DATA.values():
        for service_group in category_data["services"].values():
            for service in service_group:
                if isinstance(service, dict):
                    if service["code"] == code:
                        return service["name"]
    return code  # Если не найден, возвращаем сам код
