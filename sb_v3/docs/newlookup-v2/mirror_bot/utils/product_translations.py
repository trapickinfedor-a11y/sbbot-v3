"""
Утилита для получения мультиязычных названий продуктов, сервисов и категорий
"""

from typing import Dict, Optional


class ProductTranslations:
    """Класс для управления переводами названий продуктов"""
    
    # Переводы категорий
    CATEGORIES = {
        "en": {
            "vcc": "Virtual Cards",
            "personal": "Personal Banks",
            "business": "Business Banks",
            "crypto": "Crypto Accounts",
            "lookup": "Lookup Services",
            "credit_reports": "Credit Reports",
            "documents": "Documents",
            "fullz": "FULLZ",
            "banks": "Banks",
            "accounts": "Accounts",
            "addinfo": "Add Info to CR",
            "esim": "eSIM",
            "acc_bg": "Background Accounts",
            "acc_lookup": "Lookup Accounts"
        },
        "ru": {
            "vcc": "Виртуальные карты",
            "personal": "Личные банки",
            "business": "Бизнес банки",
            "crypto": "Крипто аккаунты",
            "lookup": "Поиск данных",
            "credit_reports": "Кредитные отчеты",
            "documents": "Документы",
            "fullz": "FULLZ",
            "banks": "Банки",
            "accounts": "Аккаунты",
            "addinfo": "Добавить инфо в КО",
            "esim": "eSIM",
            "acc_bg": "Аккаунты проверки",
            "acc_lookup": "Аккаунты поиска"
        },
        "zh": {
            "vcc": "虚拟卡",
            "personal": "个人银行",
            "business": "商业银行",
            "crypto": "加密账户",
            "lookup": "查找服务",
            "credit_reports": "信用报告",
            "documents": "文档",
            "fullz": "FULLZ",
            "banks": "银行",
            "accounts": "账户",
            "addinfo": "添加信息到信用报告",
            "esim": "eSIM",
            "acc_bg": "背景账户",
            "acc_lookup": "查找账户"
        }
    }
    
    # Переводы названий банков и сервисов
    SERVICES = {
        "en": {
            # VCC
            "vcc_chime": "Chime VCC",
            "vcc_paypal": "PayPal VCC",
            "vcc_onepay": "One Pay VCC",
            "vcc_current": "Current VCC",
            "vcc_neteller": "Neteller VCC",
            "vcc_wise": "Wise Personal VCC",
            "vcc_netspend": "Netspend VCC",
            "vcc_greenfi": "GreenFi VCC",
            "vcc_quickbooks": "QuickBooks VCC",
            "vcc_go2bank": "Go2Bank + VCC",
            "vcc_venmo": "Venmo",
            "vcc_kikoff": "Kikoff",
            "vcc_shopify": "Shopify",
            "vcc_varo": "Varo + VCC",
            
            # Personal Banks
            "pers_citi": "Citi Personal",
            "pers_citi_gold": "Citi Gold Bank",
            "pers_usalliance": "Usalliance",
            "pers_usbank": "US Bank",
            "pers_ally": "Ally Bank",
            "pers_regions": "Regions Bank",
            "pers_chase": "Chase",
            "pers_wells": "Wells Fargo",
            "pers_schwab": "Charles Schwab",
            "pers_citizens": "Citizens Bank",
            "pers_huntington": "Huntington Bank",
            "pers_td": "TD Bank",
            "pers_boa": "Bank of America",
            "pers_alliant": "Alliant CU",
            "pers_pnc": "PNC Bank",
            
            # Business Banks
            "biz_quickbooks": "QuickBooks (LLC/CORP)",
            "biz_bmo": "BMO Business",
            "biz_boa": "Bank of America Business",
            "biz_usbank": "US Bank Business",
            "biz_north_one": "North One (LLC/Corp)",
            "biz_lili": "Lili Business VCC",
            "biz_pnc": "PNC Business",
            "biz_capital_one": "Capital One Business",
            "biz_wells": "Wells Fargo Business",
            "biz_chase": "Chase Business",
            
            # Crypto
            "crypto_cashapp": "CashApp BTC",
            "crypto_kraken": "Kraken",
            "crypto_coinbase": "Coinbase",
            "crypto_crypto_com": "Crypto.com",
            "crypto_binance": "Binance US",
            "crypto_brute": "BRUTE",
            
            # Credit Reports
            "cr_transunion": "TransUnion Credit Report",
            "cr_experian": "Experian Credit Report",
            "cr_equifax": "Equifax Credit Report",
            "cr_lexisnexis": "LexisNexis Report",
            "cr_wallet": "Credit Wallet Report",
            
            # Lookup Services
            "ssn_dob": "SSN & DOB Lookup",
            "phone_name": "Phone Name Lookup",
            "phone_ssn": "Phone + SSN Lookup",
            "phone_full": "Phone Full Lookup",
            "phone_search": "Phone Search",
            "lookup_dl": "Driver License Lookup",
            "lookup_credit": "Credit Score Lookup",
            "lookup_bg": "Background Lookup",
            "lookup_mvr": "MVR Lookup",
            "lookup_fullmvr": "Full MVR Lookup",
            "lookup_mmn": "MMN Lookup",
            "lookup_ein": "EIN Lookup",
            "dl": "Driver License Lookup",
            "credit": "Credit Score Lookup",
            "bg": "Background Lookup",
            "mvr": "MVR Lookup",
            "fullmvr": "Full MVR Lookup",
            "mmn": "MMN Lookup",
            "ein": "EIN Lookup",
            
            # eSIM
            "esim_verizon_sms": "Verizon eSIM SMS",
            "esim_att_sms": "AT&T eSIM SMS",
            "esim_tmobile_sms": "T-Mobile eSIM SMS",
            "esim_verizon_data": "Verizon eSIM Data",
            "esim_att_data": "AT&T eSIM Data",
            "esim_tmobile_data": "T-Mobile eSIM Data",
            
            # Accounts
            "acc_background": "Background Account",
            "acc_beenverified": "BeenVerified",
            "acc_truthfinder": "TruthFinder",
            "acc_instantcheck": "InstantCheckmate",
            "acc_intelius": "Intelius",
            "acc_whitepages": "WhitePages",
            "acc_mylife": "MyLife",
            "acc_lookup_ba": "Lookup BA",
            
            # Add Info
            "addinfo_all": "Add phone + address + employer (all CR)",
            "addinfo_phone_address": "Add phone + address (all CR)",
            "addinfo_phone_all": "Add phone (all CR)",
            "addinfo_address_all": "Add address (all CR)",
            "addinfo_employer_all": "Add employer (all CR)",
            
            # FULLZ
            "fullz_personal": "Personal FULLZ",
            "fullz_personal_cs": "Personal FULLZ with CS/CR",
            "fullz_cs": "Personal FULLZ with CS/CR",
            "fullz_business": "Business FULLZ",
            "personal_random": "Random Personal FULLZ",
            "fullz_random": "Random Personal FULLZ",
            
            # Documents
            "dl_doc": "Driver License Document",
            "passport_doc": "Passport Document",
            "ssn_doc": "SSN Card Document"
        },
        "ru": {
            # VCC
            "vcc_chime": "Chime VCC",
            "vcc_paypal": "PayPal VCC",
            "vcc_onepay": "One Pay VCC",
            "vcc_current": "Current VCC",
            "vcc_neteller": "Neteller VCC",
            "vcc_wise": "Wise Personal VCC",
            "vcc_netspend": "Netspend VCC",
            "vcc_greenfi": "GreenFi VCC",
            "vcc_quickbooks": "QuickBooks VCC",
            "vcc_go2bank": "Go2Bank + VCC",
            "vcc_venmo": "Venmo",
            "vcc_kikoff": "Kikoff",
            "vcc_shopify": "Shopify",
            "vcc_varo": "Varo + VCC",
            
            # Personal Banks
            "pers_citi": "Citi Персональный",
            "pers_citi_gold": "Citi Gold Банк",
            "pers_usalliance": "Usalliance",
            "pers_usbank": "US Bank",
            "pers_ally": "Ally Bank",
            "pers_regions": "Regions Bank",
            "pers_chase": "Chase",
            "pers_wells": "Wells Fargo",
            "pers_schwab": "Charles Schwab",
            "pers_citizens": "Citizens Bank",
            "pers_huntington": "Huntington Bank",
            "pers_td": "TD Bank",
            "pers_boa": "Bank of America",
            "pers_alliant": "Alliant CU",
            "pers_pnc": "PNC Bank",
            
            # Business Banks
            "biz_quickbooks": "QuickBooks (ООО/Корп)",
            "biz_bmo": "BMO Бизнес",
            "biz_boa": "Bank of America Бизнес",
            "biz_usbank": "US Bank Бизнес",
            "biz_north_one": "North One (ООО/Корп)",
            "biz_lili": "Lili Бизнес VCC",
            "biz_pnc": "PNC Бизнес",
            "biz_capital_one": "Capital One Бизнес",
            "biz_wells": "Wells Fargo Бизнес",
            "biz_chase": "Chase Бизнес",
            
            # Crypto
            "crypto_cashapp": "CashApp BTC",
            "crypto_kraken": "Kraken",
            "crypto_coinbase": "Coinbase",
            "crypto_crypto_com": "Crypto.com",
            "crypto_binance": "Binance US",
            "crypto_brute": "BRUTE",
            
            # Credit Reports
            "cr_transunion": "TransUnion Кредитный отчет",
            "cr_experian": "Experian Кредитный отчет",
            "cr_equifax": "Equifax Кредитный отчет",
            "cr_lexisnexis": "LexisNexis Отчет",
            "cr_wallet": "Credit Wallet Отчет",
            
            # Lookup Services
            "ssn_dob": "Поиск SSN и даты рождения",
            "phone_name": "Поиск имени по телефону",
            "phone_ssn": "Поиск телефон + SSN",
            "phone_full": "Полный поиск по телефону",
            "phone_search": "Поиск по телефону",
            "lookup_dl": "Поиск водительских прав",
            "lookup_credit": "Поиск кредитного рейтинга",
            "lookup_bg": "Проверка данных",
            "lookup_mvr": "Поиск MVR",
            "lookup_fullmvr": "Полный поиск MVR",
            "lookup_mmn": "Поиск MMN",
            "lookup_ein": "Поиск EIN",
            "dl": "Поиск водительских прав",
            "credit": "Поиск кредитного рейтинга",
            "bg": "Проверка данных",
            "mvr": "Поиск MVR",
            "fullmvr": "Полный поиск MVR",
            "mmn": "Поиск MMN",
            "ein": "Поиск EIN",
            
            # eSIM
            "esim_verizon_sms": "Verizon eSIM SMS",
            "esim_att_sms": "AT&T eSIM SMS",
            "esim_tmobile_sms": "T-Mobile eSIM SMS",
            "esim_verizon_data": "Verizon eSIM Data",
            "esim_att_data": "AT&T eSIM Data",
            "esim_tmobile_data": "T-Mobile eSIM Data",
            
            # Accounts
            "acc_background": "Аккаунт проверки",
            "acc_beenverified": "BeenVerified",
            "acc_truthfinder": "TruthFinder",
            "acc_instantcheck": "InstantCheckmate",
            "acc_intelius": "Intelius",
            "acc_whitepages": "WhitePages",
            "acc_mylife": "MyLife",
            "acc_lookup_ba": "Lookup BA",
            
            # Add Info
            "addinfo_all": "Добавить телефон + адрес + работодателя (все КО)",
            "addinfo_phone_address": "Добавить телефон + адрес (все КО)",
            "addinfo_phone_all": "Добавить телефон (все КО)",
            "addinfo_address_all": "Добавить адрес (все КО)",
            "addinfo_employer_all": "Добавить работодателя (все КО)",
            
            # FULLZ
            "fullz_personal": "Личный FULLZ",
            "fullz_personal_cs": "Личный FULLZ с CS/CR",
            "fullz_cs": "Личный FULLZ с CS/CR",
            "fullz_business": "Бизнес FULLZ",
            "personal_random": "Случайный личный FULLZ",
            "fullz_random": "Случайный личный FULLZ",
            
            # Documents
            "dl_doc": "Документ водительских прав",
            "passport_doc": "Документ паспорта",
            "ssn_doc": "Документ карты SSN"
        },
        "zh": {
            # VCC
            "vcc_chime": "Chime 虚拟卡",
            "vcc_paypal": "PayPal 虚拟卡",
            "vcc_onepay": "One Pay 虚拟卡",
            "vcc_current": "Current 虚拟卡",
            "vcc_neteller": "Neteller 虚拟卡",
            "vcc_wise": "Wise 个人虚拟卡",
            "vcc_netspend": "Netspend 虚拟卡",
            "vcc_greenfi": "GreenFi 虚拟卡",
            "vcc_quickbooks": "QuickBooks 虚拟卡",
            "vcc_go2bank": "Go2Bank + 虚拟卡",
            "vcc_venmo": "Venmo",
            "vcc_kikoff": "Kikoff",
            "vcc_shopify": "Shopify",
            "vcc_varo": "Varo + 虚拟卡",
            
            # Personal Banks
            "pers_citi": "花旗个人",
            "pers_citi_gold": "花旗金卡银行",
            "pers_usalliance": "Usalliance",
            "pers_usbank": "美国银行",
            "pers_ally": "Ally 银行",
            "pers_regions": "Regions 银行",
            "pers_chase": "大通银行",
            "pers_wells": "富国银行",
            "pers_schwab": "嘉信理财",
            "pers_citizens": "Citizens 银行",
            "pers_huntington": "Huntington 银行",
            "pers_td": "TD 银行",
            "pers_boa": "美国银行",
            "pers_alliant": "Alliant CU",
            "pers_pnc": "PNC 银行",
            
            # Business Banks
            "biz_quickbooks": "QuickBooks (有限责任公司/公司)",
            "biz_bmo": "BMO 商业",
            "biz_boa": "美国银行商业",
            "biz_usbank": "美国银行商业",
            "biz_north_one": "North One (有限责任公司/公司)",
            "biz_lili": "Lili 商业虚拟卡",
            "biz_pnc": "PNC 商业",
            "biz_capital_one": "Capital One 商业",
            "biz_wells": "富国银行商业",
            "biz_chase": "大通银行商业",
            
            # Crypto
            "crypto_cashapp": "CashApp BTC",
            "crypto_kraken": "Kraken",
            "crypto_coinbase": "Coinbase",
            "crypto_crypto_com": "Crypto.com",
            "crypto_binance": "币安美国",
            "crypto_brute": "BRUTE",
            
            # Credit Reports
            "cr_transunion": "TransUnion 信用报告",
            "cr_experian": "Experian 信用报告",
            "cr_equifax": "Equifax 信用报告",
            "cr_lexisnexis": "LexisNexis 报告",
            "cr_wallet": "Credit Wallet 报告",
            
            # Lookup Services
            "ssn_dob": "SSN与生日查询",
            "phone_name": "电话姓名查询",
            "phone_ssn": "电话 + SSN 查询",
            "phone_full": "电话完整查询",
            "phone_search": "电话搜索",
            "lookup_dl": "驾照查询",
            "lookup_credit": "信用评分查询",
            "lookup_bg": "背景查询",
            "lookup_mvr": "MVR 查询",
            "lookup_fullmvr": "完整 MVR 查询",
            "lookup_mmn": "MMN 查询",
            "lookup_ein": "EIN 查询",
            "dl": "驾照查询",
            "credit": "信用评分查询",
            "bg": "背景查询",
            "mvr": "MVR 查询",
            "fullmvr": "完整 MVR 查询",
            "mmn": "MMN 查询",
            "ein": "EIN 查询",
            
            # eSIM
            "esim_verizon_sms": "Verizon eSIM 短信",
            "esim_att_sms": "AT&T eSIM 短信",
            "esim_tmobile_sms": "T-Mobile eSIM 短信",
            "esim_verizon_data": "Verizon eSIM 数据",
            "esim_att_data": "AT&T eSIM 数据",
            "esim_tmobile_data": "T-Mobile eSIM 数据",
            
            # Accounts
            "acc_background": "背景账户",
            "acc_beenverified": "BeenVerified",
            "acc_truthfinder": "TruthFinder",
            "acc_instantcheck": "InstantCheckmate",
            "acc_intelius": "Intelius",
            "acc_whitepages": "WhitePages",
            "acc_mylife": "MyLife",
            "acc_lookup_ba": "Lookup BA",
            
            # Add Info
            "addinfo_all": "添加电话 + 地址 + 雇主（所有信用报告）",
            "addinfo_phone_address": "添加电话 + 地址（所有信用报告）",
            "addinfo_phone_all": "添加电话（所有信用报告）",
            "addinfo_address_all": "添加地址（所有信用报告）",
            "addinfo_employer_all": "添加雇主（所有信用报告）",
            
            # FULLZ
            "fullz_personal": "个人FULLZ",
            "fullz_personal_cs": "带有CS/CR的个人FULLZ",
            "fullz_cs": "带有CS/CR的个人FULLZ",
            "fullz_business": "商业FULLZ",
            "personal_random": "随机个人FULLZ",
            "fullz_random": "随机个人FULLZ",
            
            # Documents
            "dl_doc": "驾照文件",
            "passport_doc": "护照文件",
            "ssn_doc": "SSN卡文件"
        }
    }
    
    @classmethod
    def get_category_name(cls, category_id: str, language: str = "en") -> str:
        """Получить название категории на нужном языке"""
        if language not in cls.CATEGORIES:
            language = "en"
        return cls.CATEGORIES[language].get(category_id, category_id)
    
    @classmethod
    def get_service_name(cls, service_id: str, language: str = "en") -> str:
        """Получить название сервиса на нужном языке"""
        if language not in cls.SERVICES:
            language = "en"
        return cls.SERVICES[language].get(service_id, service_id)
    
    @classmethod
    def get_product_name(cls, product_id: str, language: str = "en") -> str:
        """Получить название продукта на нужном языке
        Это alias для get_service_name для совместимости
        """
        return cls.get_service_name(product_id, language)
