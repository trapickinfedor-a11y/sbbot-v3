"""
Полные названия сервисов для support bot
"""

# Маппинг коротких названий сервисов на полные названия
SERVICE_NAMES_MAPPING = {
    # SSN & DOB Lookup
    "ssn_dob": "SSN & Date of Birth Lookup",
    "lookup_ssn": "SSN & Date of Birth Lookup",  # Алиас с префиксом

    # Driver License Lookup
    "dl": "Driver License Lookup",  # Алиас без префикса для обратной совместимости
    "lookup_dl": "Driver License Lookup",

    # Credit Score Lookup
    "credit": "Credit Score Lookup",  # Алиас без префикса
    "lookup_credit": "Credit Score Lookup",

    # Motor Vehicle Records
    "mvr": "Motor Vehicle Record (MVR)",  # Алиас без префикса
    "lookup_mvr": "Motor Vehicle Record (MVR)",
    "fullmvr": "Full Motor Vehicle Record (MVR)",  # Алиас без префикса
    "lookup_fullmvr": "Full Motor Vehicle Record (MVR)",

    # Background Check
    "bg": "Background Check",  # Алиас без префикса
    "lookup_bg": "Background Check",

    # Mother's Maiden Name
    "mmn": "Mother's Maiden Name (MMN) Lookup",  # Алиас без префикса
    "lookup_mmn": "Mother's Maiden Name (MMN) Lookup",

    # EIN Lookup
    "ein": "Employer Identification Number (EIN) Lookup",  # Алиас без префикса
    "lookup_ein": "Employer Identification Number (EIN) Lookup",
    
    # Bank Lookup (BA)
    "lookup_ba_an_rn": "Check AN+RN (Account + Routing)",
    "lookup_ba_transactions": "Check Transactions [15 days]",
    "lookup_ba_balance": "Check Balance",
    "lookup_ba_name": "Check NAME (by AN+RN)",
    "lookup_ba_an_rn_name": "Check AN+RN+NAME",
    
    # Phone Search Services
    "phone_name": "Phone to Name & Address Lookup",
    "phone_ssn": "Phone to SSN Lookup",
    "phone_full": "Phone to Full Information Lookup",
    
    # Credit Reports
    "cr_transunion": "TransUnion Credit Report",
    "cr_experian": "Experian Credit Report",
    "cr_equifax": "Equifax Credit Report",
    "cr_lexisnexis": "LexisNexis Credit Report",
    "cr_wallet": "WalletHub/Credit Karma Report",
    
    # Documents
    "doc_dl": "Driver License Document (Front & Back)",
    "doc_dl_selfie": "Driver License + Selfie Document",
    "doc_passport": "Passport Document",
    "doc_biz": "Business Documents",
    "doc_business": "Business Documents",
    
    # FULLZ Services
    "fullz_personal": "Personal FULLZ Package",
    "fullz_cs": "Personal FULLZ with Credit Score/Report",
    "fullz_personal_cs": "Personal FULLZ with Credit Score/Report",  # Алиас для обратной совместимости
    "fullz_military": "Military FULLZ Package",
    "fullz_work": "Work & Travel FULLZ Package",
    "fullz_young": "Young Person FULLZ Package",
    "fullz_random": "Random FULLZ Package",
    "personal_random": "Random FULLZ Package",  # Алиас
    "fullz_biz": "Business FULLZ Package",
    "fullz_business": "Business FULLZ Package",
    
    # VCC Banks
    "vcc_chime": "Chime Virtual Credit Card",
    "vcc_paypal": "PayPal Virtual Credit Card",
    "vcc_onepay": "OnePay Virtual Credit Card",
    "vcc_current": "Current Virtual Credit Card",
    "vcc_neteller": "Neteller Virtual Credit Card",
    "vcc_wise": "Wise Personal Virtual Credit Card",
    "vcc_netspend": "Netspend Virtual Credit Card",
    "vcc_greenfi": "GreenFi Virtual Credit Card",
    "vcc_quickbooks": "QuickBooks Virtual Credit Card",
    "vcc_go2bank": "Go2Bank Virtual Credit Card",
    "vcc_venmo": "Venmo Virtual Credit Card",
    "vcc_kikoff": "Kikoff Virtual Credit Card",
    "vcc_shopify": "Shopify Virtual Credit Card",
    "vcc_varo": "Varo Virtual Credit Card",
    "vcc_blockchain": "Blockchain.com Virtual Credit Card",
    
    # Personal Banks
    "pers_citi": "Citi Personal Checking Account",
    "pers_citi_gold": "Citi Gold Personal Account",
    "pers_usbank": "US Bank Personal Account",
    "pers_ally": "Ally Bank Personal Account",
    "pers_regions": "Regions Bank Personal Account",
    "pers_chase": "Chase Personal Account",
    "pers_wells": "Wells Fargo Personal Account",
    "pers_schwab": "Charles Schwab Personal Account",
    "pers_citizens": "Citizens Bank Personal Account",
    "pers_huntington": "Huntington Bank Personal Account",
    "pers_td": "TD Bank Personal Account",
    "pers_usalliance": "US Alliance Personal Account",
    "pers_boa": "Bank of America Personal Account",
    "pers_alliant": "Alliant Credit Union Personal Account",
    "pers_pnc": "PNC Bank Personal Account",
    
    # Business Banks
    "biz_bmo": "BMO Business Account",
    "biz_boa": "Bank of America Business Account",
    "biz_capital_one": "Capital One Business Account",
    "biz_chase": "Chase Business Account",
    "biz_lili": "Lili Business Account",
    "biz_north_one": "North One Business Account",
    "biz_pnc": "PNC Business Account",
    "biz_usbank": "US Bank Business Account",
    "biz_wells": "Wells Fargo Business Account",
    "biz_quickbooks": "QuickBooks Business Account",
    
    # Crypto Banks
    "crypto_cashapp": "CashApp Bitcoin Account",
    "crypto_kraken": "Kraken Crypto Account",
    "crypto_coinbase": "Coinbase Crypto Account",
    "crypto_crypto_com": "Crypto.com Account",
    "crypto_binance": "Binance US Account",
    "crypto_blockchain": "Blockchain.com Account",
    
    # Background Accounts
    "bg_beenverified": "BeenVerified Background Account",
    "bg_truthfinder": "TruthFinder Background Account",
    "bg_instantcheck": "InstantCheckmate Background Account",
    "bg_intelius": "Intelius Background Account",
    "bg_intelius_30": "Intelius Background Account (30 days)",
    "bg_truthfinder_30": "TruthFinder Background Account (30 days)",
    "bg_instantcheck_30": "InstantCheckmate Background Account (30 days)",
    "bg_whitepages": "WhitePages Background Account",
    "bg_whitepages_30": "WhitePages Background Account (30 days)",
    "bg_mylife": "MyLife Background Account",
    
    # Financial Apps
    "lookup_monarch": "Monarch Money Financial App",
    "lookup_yodlee": "Yodlee Financial App",
    "lookup_empower": "Empower Financial App",
    "lookup_pocketguard": "PocketGuard Financial App",
    "lookup_everydollar": "EveryDollar Financial App",
    
    # Add Info Services
    "addcr_all": "Add Phone + Address + Employer (All Credit Reports)",
    "addcr_phone_addr": "Add Phone + Address (All Credit Reports)",
    "addcr_phone_all": "Add Phone Number (All Credit Reports)",
    "addcr_addr_all": "Add Address (All Credit Reports)",
    "addcr_phone_ex": "Add Phone Number (Experian Only)",
    "addcr_addr_ex": "Add Address (Experian Only)",
    "addcr_phone_tu": "Add Phone Number (TransUnion Only)",
    "addcr_addr_tu": "Add Address (TransUnion Only)",
    
    # Add Info - Background
    "addbg_phone_addr": "Add Phone + Address (Background Reports)",
    "addbg_phone": "Add Phone Number (Background Reports)",
    "addbg_addr": "Add Address (Background Reports)",
    
    # Add Info - Employer
    "addemp_tu": "Add Employer (TransUnion)",
    "addemp_update": "Update Current Employer",
    "addemp_remove": "Remove Outdated Employer",
    
    # Add Info - Unfreeze
    "unfreeze_tu": "Permanent Unfreeze (TransUnion)",
    "unfreeze_ex": "Permanent Unfreeze (Experian)",
}

# eSIM Services (динамические названия)
def get_esim_service_name(service_name: str, quantity: int = 1) -> str:
    """Получить полное название для eSIM сервиса"""
    qty_str = f" x{quantity}" if quantity > 1 else ""
    
    if service_name.startswith("sms_"):
        parts = service_name.split("_")
        if len(parts) >= 3:
            operator = parts[1].upper()
            period = parts[2]
            return f"eSIM SMS ({operator}) - {period} month(s){qty_str}"
    
    elif service_name.startswith("data_"):
        parts = service_name.split("_")
        if len(parts) >= 3:
            operator = parts[1].upper()
            gb = parts[2]
            return f"eSIM Data ({operator}) - {gb}GB{qty_str}"
    
    return f"eSIM Service ({service_name}){qty_str}"

def get_full_service_name(service_name: str, input_data: dict = None) -> str:
    """
    Получить полное название сервиса
    
    Args:
        service_name: Короткое название сервиса
        input_data: Дополнительные данные заказа (например, quantity для eSIM)
        
    Returns:
        str: Полное название сервиса
    """
    # Проверяем прямой маппинг
    if service_name in SERVICE_NAMES_MAPPING:
        return SERVICE_NAMES_MAPPING[service_name]
    
    # Проверяем eSIM сервисы
    if service_name.startswith(("sms_", "data_")):
        quantity = 1
        if input_data and isinstance(input_data, dict):
            quantity = input_data.get("quantity", 1)
        return get_esim_service_name(service_name, quantity)
    
    # Если не найдено, возвращаем оригинальное название с заглавной буквы
    return service_name.replace("_", " ").title()
