"""
Ссылки на инструкции для всех сервисов
"""

class TutorialLinks:
    """Централизованные ссылки на инструкции"""
    
    # LOOKUP SERVICES
    LOOKUP_SSN = "https://t.me/ONE_TUTORIAL/85"
    LOOKUP_SSN_BULK = "https://t.me/ONE_TUTORIAL/86"
    LOOKUP_DL = "https://t.me/ONE_TUTORIAL/87"
    LOOKUP_DL_BULK = "https://t.me/ONE_TUTORIAL/88"
    LOOKUP_CS = "https://t.me/ONE_TUTORIAL/89"
    LOOKUP_CS_BULK = "https://t.me/ONE_TUTORIAL/90"
    LOOKUP_MVR = "https://t.me/ONE_TUTORIAL/91"
    LOOKUP_MVR_BULK = "https://t.me/ONE_TUTORIAL/2"
    LOOKUP_FULL_MVR = "https://t.me/ONE_TUTORIAL/3"
    LOOKUP_PHONE = "https://t.me/ONE_TUTORIAL/5"
    LOOKUP_PHONE_SSN = "https://t.me/ONE_TUTORIAL/6"
    LOOKUP_PHONE_SSN_CS = "https://t.me/ONE_TUTORIAL/7"
    LOOKUP_BG = "https://t.me/ONE_TUTORIAL/8"
    LOOKUP_BG_BULK = "https://t.me/ONE_TUTORIAL/9"
    LOOKUP_MMN = "https://t.me/ONE_TUTORIAL/10"
    LOOKUP_MMN_BULK = "https://t.me/ONE_TUTORIAL/11"
    LOOKUP_EIN = "https://t.me/ONE_TUTORIAL/12"
    LOOKUP_EIN_BULK = "https://t.me/ONE_TUTORIAL/13"
    
    # CREDIT REPORTS
    CR_TRANSUNION = "https://t.me/ONE_TUTORIAL/14"
    CR_EXPERIAN = "https://t.me/ONE_TUTORIAL/15"
    CR_EQUIFAX = "https://t.me/ONE_TUTORIAL/16"
    CR_LEXISNEXIS = "https://t.me/ONE_TUTORIAL/17"
    CR_WALLETHUB = "https://t.me/ONE_TUTORIAL/18"
    
    # VCC BANKS
    VCC_CHIME = "https://t.me/ONE_TUTORIAL/28"
    VCC_PAYPAL = "https://t.me/ONE_TUTORIAL/29"
    VCC_CURRENT = "https://t.me/ONE_TUTORIAL/30"
    VCC_WISE = "https://t.me/ONE_TUTORIAL/31"
    VCC_ONE = "https://t.me/ONE_TUTORIAL/32"
    VCC_GO2BANK = "https://t.me/ONE_TUTORIAL/33"
    VCC_VARO = "https://t.me/ONE_TUTORIAL/34"
    VCC_VENMO = "https://t.me/ONE_TUTORIAL/35"
    VCC_KIKOFF = "https://t.me/ONE_TUTORIAL/36"
    VCC_SHOPIFY = "https://t.me/ONE_TUTORIAL/37"
    
    # PERSONAL BANKS
    PERS_CITI = "https://t.me/ONE_TUTORIAL/38"
    PERS_USBANK = "https://t.me/ONE_TUTORIAL/39"
    PERS_CHASE = "https://t.me/ONE_TUTORIAL/40"
    PERS_WELLS = "https://t.me/ONE_TUTORIAL/41"
    PERS_TD = "https://t.me/ONE_TUTORIAL/42"
    PERS_HUNTINGTON = "https://t.me/ONE_TUTORIAL/43"
    PERS_CITI_GOLD = "https://t.me/ONE_TUTORIAL/44"
    PERS_CITIZENS = "https://t.me/ONE_TUTORIAL/45"
    PERS_USALLIANCE = "https://t.me/ONE_TUTORIAL/46"
    PERS_BOA = "https://t.me/ONE_TUTORIAL/47"
    PERS_ALLY = "https://t.me/ONE_TUTORIAL/48"
    PERS_ALLIANT = "https://t.me/ONE_TUTORIAL/49"
    PERS_PNC = "https://t.me/ONE_TUTORIAL/50"
    
    # BUSINESS BANKS
    BIZ_QUICKBOOKS = "https://t.me/ONE_TUTORIAL/51"
    BIZ_BMO = "https://t.me/ONE_TUTORIAL/52"
    BIZ_BOA = "https://t.me/ONE_TUTORIAL/53"
    BIZ_CHASE = "https://t.me/ONE_TUTORIAL/54"
    BIZ_USBANK = "https://t.me/ONE_TUTORIAL/55"
    BIZ_NORTH_ONE = "https://t.me/ONE_TUTORIAL/56"
    BIZ_LILI = "https://t.me/ONE_TUTORIAL/58"
    BIZ_PNC = "https://t.me/ONE_TUTORIAL/59"
    
    # CRYPTO BANKS
    CRYPTO_CASHAPP = "https://t.me/ONE_TUTORIAL/60"
    CRYPTO_BLOCKCHAIN = "https://t.me/ONE_TUTORIAL/61"
    CRYPTO_KRAKEN = "https://t.me/ONE_TUTORIAL/62"
    CRYPTO_COINBASE = "https://t.me/ONE_TUTORIAL/63"
    CRYPTO_CRYPTO_COM = "https://t.me/ONE_TUTORIAL/64"
    CRYPTO_BINANCE = "https://t.me/ONE_TUTORIAL/65"
    
    # ACCOUNTS
    ACC_MONARCH = "https://t.me/ONE_TUTORIAL/66"
    ACC_YODLEE = "https://t.me/ONE_TUTORIAL/67"
    ACC_EMPOWER = "https://t.me/ONE_TUTORIAL/68"
    ACC_POCKETGUARD = "https://t.me/ONE_TUTORIAL/69"
    ACC_EVERYDOLLAR = "https://t.me/ONE_TUTORIAL/70"
    ACC_BEENVERIFIED = "https://t.me/ONE_TUTORIAL/71"
    ACC_TRUTHFINDER = "https://t.me/ONE_TUTORIAL/72"
    ACC_INSTANTCHECK = "https://t.me/ONE_TUTORIAL/73"
    ACC_INTELIUS = "https://t.me/ONE_TUTORIAL/74"
    ACC_WHITEPAGES = "https://t.me/ONE_TUTORIAL/75"
    ACC_INTELIUS_30 = "https://t.me/ONE_TUTORIAL/76"
    ACC_TRUTHFINDER_30 = "https://t.me/ONE_TUTORIAL/77"
    ACC_INSTANTCHECK_30 = "https://t.me/ONE_TUTORIAL/78"
    ACC_WHITEPAGES_30 = "https://t.me/ONE_TUTORIAL/79"
    
    # ADD INFO SERVICES
    ADDINFO_TU = "https://t.me/ONE_TUTORIAL/78"
    ADDINFO_EX = "https://t.me/ONE_TUTORIAL/79"
    ADDINFO_ALL = "https://t.me/ONE_TUTORIAL/80"
    ADDINFO_BG = "https://t.me/ONE_TUTORIAL/81"
    UNFREEZE_TU = "https://t.me/ONE_TUTORIAL/82"
    UNFREEZE_EX = "https://t.me/ONE_TUTORIAL/83"
    ADD_EMPLOYER = "https://t.me/ONE_TUTORIAL/84"
    
    @classmethod
    def get_lookup_link(cls, service_type: str, is_bulk: bool = False) -> str:
        """Получить ссылку для lookup сервиса"""
        service_links = {
            "lookup_ssn": cls.LOOKUP_SSN_BULK if is_bulk else cls.LOOKUP_SSN,
            "lookup_dl": cls.LOOKUP_DL_BULK if is_bulk else cls.LOOKUP_DL,
            "lookup_credit": cls.LOOKUP_CS_BULK if is_bulk else cls.LOOKUP_CS,
            "lookup_mvr": cls.LOOKUP_MVR_BULK if is_bulk else cls.LOOKUP_MVR,
            "lookup_fullmvr": cls.LOOKUP_FULL_MVR,
            "lookup_bg": cls.LOOKUP_BG_BULK if is_bulk else cls.LOOKUP_BG,
            "lookup_mmn": cls.LOOKUP_MMN_BULK if is_bulk else cls.LOOKUP_MMN,
            "lookup_ein": cls.LOOKUP_EIN_BULK if is_bulk else cls.LOOKUP_EIN,
        }
        return service_links.get(service_type, "")
    
    @classmethod
    def get_credit_report_link(cls, service_type: str) -> str:
        """Получить ссылку для credit report сервиса"""
        service_links = {
            "cr_transunion": cls.CR_TRANSUNION,
            "cr_experian": cls.CR_EXPERIAN,
            "cr_equifax": cls.CR_EQUIFAX,
            "cr_lexisnexis": cls.CR_LEXISNEXIS,
            "cr_wallet": cls.CR_WALLETHUB,
        }
        return service_links.get(service_type, "")
