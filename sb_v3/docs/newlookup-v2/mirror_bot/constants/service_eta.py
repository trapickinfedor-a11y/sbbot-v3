"""
Service ETA (Estimated Time of Arrival) constants
Централизованное хранение времени обработки для каждого сервиса
"""

class ServiceETA:
    """ETA времена для всех сервисов"""
    
    # ========== LOOKUP SERVICES ==========
    SSN_DOB = "10-90 minutes"
    PHONE_NAME = "10-90 minutes"
    PHONE_SSN = "10-90 minutes"
    PHONE_FULL = "10-90 minutes"
    PHONE_SEARCH = "10-90 minutes"
    
    # Driver License & Motor Vehicles
    DL_LOOKUP = "10-90 minutes"
    MVR_LOOKUP = "10-90 minutes"
    FULL_MVR_LOOKUP = "10-90 minutes"
    
    # Credit & Background
    CREDIT_SCORE = "10-90 minutes"
    BACKGROUND_CHECK = "10-90 minutes"
    
    # Other Lookups
    MMN_LOOKUP = "10-90 minutes"
    EIN_LOOKUP = "10-90 minutes"
    
    # ========== CREDIT REPORTS ==========
    CREDIT_REPORT_EXPERIAN = "4-30 minutes"
    CREDIT_REPORT_EQUIFAX = "4-30 minutes"
    CREDIT_REPORT_TRANSUNION = "4-30 minutes"
    CREDIT_REPORT_LEXISNEXIS = "4-30 minutes"
    
    # ========== FULLZ ==========
    FULLZ_PERSONAL = "4-24 hours"
    FULLZ_PERSONAL_CS = "4-24 hours"
    FULLZ_BUSINESS = "4-24 hours"
    FULLZ_INSTANT = "Instant ⚡"
    
    # ========== DOCUMENTS ==========
    DOCUMENT_DL = "4-24 hours"
    DOCUMENT_PASSPORT = "4-24 hours"
    DOCUMENT_SSN = "4-24 hours"
    DOCUMENT_BIZ = "4-24 hours"
    
    # ========== BANKS ==========
    BANK_ACCOUNT = "4-24 hours"
    
    # ========== ACCOUNTS ==========
    SOCIAL_ACCOUNT = "4-24 hours"
    
    # ========== ESIM ==========
    ESIM = "1-6 hours"
    
    # ========== ADDITIONAL INFO ==========
    ADDITIONAL_INFO = "4-24 hours"
    
    @classmethod
    def get_eta(cls, service_type: str) -> str:
        """
        Получить ETA для сервиса
        
        Args:
            service_type: Тип сервиса (например, "ssn_dob", "mvr", "credit_experian")
        
        Returns:
            ETA строка (например, "10-90 minutes")
        """
        # Маппинг service_type -> атрибут класса
        eta_mapping = {
            # Lookups
            "ssn_dob": cls.SSN_DOB,
            "phone_name": cls.PHONE_NAME,
            "phone_ssn": cls.PHONE_SSN,
            "phone_full": cls.PHONE_FULL,
            "phone_search": cls.PHONE_SEARCH,
            "lookup_dl": cls.DL_LOOKUP,
            "dl": cls.DL_LOOKUP,
            "lookup_credit": cls.CREDIT_SCORE,
            "credit": cls.CREDIT_SCORE,
            "lookup_bg": cls.BACKGROUND_CHECK,
            "bg": cls.BACKGROUND_CHECK,
            "lookup_mvr": cls.MVR_LOOKUP,
            "mvr": cls.MVR_LOOKUP,
            "lookup_fullmvr": cls.FULL_MVR_LOOKUP,
            "fullmvr": cls.FULL_MVR_LOOKUP,
            "lookup_mmn": cls.MMN_LOOKUP,
            "mmn": cls.MMN_LOOKUP,
            "lookup_ein": cls.EIN_LOOKUP,
            "ein": cls.EIN_LOOKUP,
            
            # Credit Reports
            "cr_experian": cls.CREDIT_REPORT_EXPERIAN,
            "experian": cls.CREDIT_REPORT_EXPERIAN,
            "cr_equifax": cls.CREDIT_REPORT_EQUIFAX,
            "equifax": cls.CREDIT_REPORT_EQUIFAX,
            "cr_transunion": cls.CREDIT_REPORT_TRANSUNION,
            "transunion": cls.CREDIT_REPORT_TRANSUNION,
            "cr_lexisnexis": cls.CREDIT_REPORT_LEXISNEXIS,
            "lexisnexis": cls.CREDIT_REPORT_LEXISNEXIS,
            
            # FULLZ
            "fullz_personal": cls.FULLZ_PERSONAL,
            "fullz_personal_cs": cls.FULLZ_PERSONAL_CS,
            "fullz_cs": cls.FULLZ_PERSONAL_CS,
            "fullz_business": cls.FULLZ_BUSINESS,
            "fullz_700plus": cls.FULLZ_PERSONAL,
            "fullz_800plus": cls.FULLZ_PERSONAL,
            "fullz_under18": cls.FULLZ_PERSONAL,
            "fullz_immigrant": cls.FULLZ_PERSONAL,
            "fullz_zero_bank": cls.FULLZ_PERSONAL,
            "personal_random": cls.FULLZ_PERSONAL,
            
            # Documents
            "dl_doc": cls.DOCUMENT_DL,
            "dl_front_back_doc": cls.DOCUMENT_DL,
            "dl_selfie_doc": cls.DOCUMENT_DL,
            "dl_kyc_doc": cls.DOCUMENT_DL,
            "passport_doc": cls.DOCUMENT_PASSPORT,
            "ssn_doc": cls.DOCUMENT_SSN,
            "biz_doc": cls.DOCUMENT_BIZ,
            "business_docs_doc": cls.DOCUMENT_BIZ,
            
            # Banks
            "bank": cls.BANK_ACCOUNT,
            
            # Accounts
            "account": cls.SOCIAL_ACCOUNT,
            
            # eSIM
            "esim": cls.ESIM,
            
            # Additional Info
            "addinfo": cls.ADDITIONAL_INFO,
        }
        
        # Возвращаем ETA или дефолтное значение
        return eta_mapping.get(service_type, "4-24 hours")

