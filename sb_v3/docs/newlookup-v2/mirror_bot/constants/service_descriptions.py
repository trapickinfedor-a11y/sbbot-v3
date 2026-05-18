"""
Детальные описания услуг на разных языках
"""

class ServiceDescriptions:
    """
    Детальные описания услуг для каждого языка
    """
    
    # ========== CREDIT REPORTS ==========
    # Описания взяты из шаблона "Шаблоны ботов EN-RU-CH Окт 26 2025.md"
    CREDIT_REPORTS = {
        "en": {
            "cr_transunion": "All credit cards (issuer, limit, balance, payment history), loans (mortgage, auto, student), public records (bankruptcies), inquiries, FICO/VantageScore credit score.",
            "cr_experian": "Complete credit profile including all credit accounts, payment history, credit utilization, public records, hard/soft inquiries, and detailed credit score analysis.",
            "cr_equifax": "Full credit report with all credit cards, loans, payment patterns, credit limits, balances, public records, and comprehensive credit score breakdown.",
            "cr_lexisnexis": "Detailed credit analysis including all financial accounts, credit history, payment behavior, public records, and advanced credit scoring models.",
            "cr_wallet": "Free credit score (updated weekly), simplified report, factor analysis, improvement recommendations, change monitoring."
        },
        "ru": {
            "cr_transunion": "Все кредитные карты (эмитент, лимит, баланс, история платежей), кредиты (ипотека, авто, студенческие), публичные записи (банкротства), запросы, кредитный рейтинг FICO/VantageScore.",
            "cr_experian": "Полный кредитный профиль включая все кредитные счета, историю платежей, использование кредита, публичные записи, жесткие/мягкие запросы и детальный анализ кредитного рейтинга.",
            "cr_equifax": "Полный кредитный отчет со всеми кредитными картами, кредитами, схемами платежей, кредитными лимитами, балансами, публичными записями и комплексной разбивкой кредитного рейтинга.",
            "cr_lexisnexis": "Детальный кредитный анализ включая все финансовые счета, кредитную историю, поведение платежей, публичные записи и продвинутые модели кредитного скоринга.",
            "cr_wallet": "Бесплатный кредитный рейтинг (обновляется еженедельно), упрощенный отчет, анализ факторов, рекомендации по улучшению, мониторинг изменений."
        },
        "zh": {
            "cr_transunion": "所有信用卡（发行商、额度、余额、付款历史）、贷款（抵押贷款、汽车贷款、学生贷款）、公共记录（破产）、查询、FICO/VantageScore信用评分。",
            "cr_experian": "完整的信用档案，包括所有信用账户、付款历史、信用利用率、公共记录、硬/软查询和详细的信用评分分析。",
            "cr_equifax": "完整的信用报告，包含所有信用卡、贷款、付款模式、信用额度、余额、公共记录和综合信用评分明细。",
            "cr_lexisnexis": "详细的信用分析，包括所有金融账户、信用历史、付款行为、公共记录和先进的信用评分模型。",
            "cr_wallet": "免费信用评分（每周更新）、简化报告、因素分析、改进建议、变化监控。"
        }
    }
    
    # ========== LOOKUP SERVICES ==========
    LOOKUP_SERVICES = {
        "en": {
            "lookup_ssn": "Complete personal information lookup including full name, current and previous addresses, date of birth, phone numbers, email addresses, and associated family members.",
            "lookup_dl": "Driver's license verification with full personal details, license status, restrictions, endorsements, and driving record summary.",
            "lookup_mvr": "Motor vehicle records including driving violations, accidents, license suspensions, DUI/DWI records, and complete driving history.",
            "lookup_fullmvr": "Comprehensive motor vehicle report with detailed accident history, traffic violations, license points, insurance claims, and vehicle registration history.",
            "lookup_credit": "Credit score lookup with current FICO/VantageScore, credit range classification, and recent credit activity summary.",
            "lookup_bg": "Background check including criminal records, court cases, liens, judgments, bankruptcies, and public records search.",
            "lookup_phone": "Phone number investigation with owner identification, carrier information, line type, and associated addresses.",
            "lookup_phone_ssn": "Phone and SSN match in credit bureaus, owner name, address, confidence score.",
            "lookup_mmn": "Mother's maiden name lookup through public records, genealogy databases, and family tree analysis.",
            "lookup_ein": "Employer Identification Number lookup with business details, registration status, and corporate structure information."
        },
        "ru": {
            "lookup_ssn": "Полный поиск личной информации включая полное имя, текущие и предыдущие адреса, дату рождения, номера телефонов, адреса электронной почты и связанных членов семьи.",
            "lookup_dl": "Проверка водительских прав с полными личными данными, статусом лицензии, ограничениями, одобрениями и сводкой водительского стажа.",
            "lookup_mvr": "Записи автотранспортных средств включая нарушения вождения, аварии, приостановки лицензий, записи DUI/DWI и полную историю вождения.",
            "lookup_fullmvr": "Комплексный отчет об автотранспортных средствах с детальной историей аварий, нарушениями правил дорожного движения, баллами лицензии, страховыми претензиями и историей регистрации транспортных средств.",
            "lookup_credit": "Поиск кредитного рейтинга с текущим FICO/VantageScore, классификацией кредитного диапазона и сводкой недавней кредитной активности.",
            "lookup_bg": "Проверка биографических данных включая уголовные записи, судебные дела, залоги, судебные решения, банкротства и поиск публичных записей.",
            "lookup_phone": "Расследование номера телефона с идентификацией владельца, информацией о перевозчике, типом линии и связанными адресами.",
            "lookup_phone_ssn": "Совпадение телефона и SSN в кредитных бюро, имя владельца, адрес, уровень уверенности (confidence score).",
            "lookup_mmn": "Поиск девичьей фамилии матери через публичные записи, генеалогические базы данных и анализ семейного древа.",
            "lookup_ein": "Поиск идентификационного номера работодателя с деталями бизнеса, статусом регистрации и информацией о корпоративной структуре."
        },
        "zh": {
            "lookup_ssn": "完整的个人信息查找，包括全名、当前和以前的地址、出生日期、电话号码、电子邮件地址和相关家庭成员。",
            "lookup_dl": "驾驶执照验证，包含完整的个人详细信息、执照状态、限制、背书和驾驶记录摘要。",
            "lookup_mvr": "机动车记录，包括驾驶违规、事故、执照暂停、DUI/DWI记录和完整的驾驶历史。",
            "lookup_fullmvr": "综合机动车报告，包含详细的事故历史、交通违规、执照积分、保险索赔和车辆登记历史。",
            "lookup_credit": "信用评分查找，包含当前FICO/VantageScore、信用范围分类和最近信用活动摘要。",
            "lookup_bg": "背景调查，包括犯罪记录、法庭案件、留置权、判决、破产和公共记录搜索。",
            "lookup_phone": "电话号码调查，包含所有者识别、运营商信息、线路类型和相关地址。",
            "lookup_phone_ssn": "电话和SSN在信用局的匹配，所有者姓名、地址、置信度评分。",
            "lookup_mmn": "通过公共记录、族谱数据库和家谱分析查找母亲的娘家姓。",
            "lookup_ein": "雇主识别号码查找，包含业务详细信息、注册状态和公司结构信息。"
        }
    }
    
    # ========== BANKS ==========
    BANK_SERVICES = {
        "en": {
            "vcc_chime": "Chime virtual card with instant spending notifications, fee-free overdraft up to $200, early direct deposit, and automatic savings features.",
            "vcc_paypal": "PayPal virtual card with cryptocurrency buying/selling, instant transfers, buyer protection, and international payment capabilities.",
            "vcc_current": "Current virtual card with real-time spending alerts, fee-free ATM network, instant money transfers, and budgeting tools.",
            "pers_chase": "Chase personal banking with premium checking, savings accounts, credit cards, mortgage services, and investment options.",
            "pers_wells": "Wells Fargo personal banking including checking, savings, credit cards, personal loans, and wealth management services.",
            "crypto_coinbase": "Coinbase cryptocurrency exchange account with trading capabilities, wallet services, staking rewards, and institutional features."
        },
        "ru": {
            "vcc_chime": "Виртуальная карта Chime с мгновенными уведомлениями о тратах, бесплатным овердрафтом до $200, ранним прямым депозитом и автоматическими функциями сбережений.",
            "vcc_paypal": "Виртуальная карта PayPal с покупкой/продажей криптовалют, мгновенными переводами, защитой покупателя и возможностями международных платежей.",
            "vcc_current": "Виртуальная карта Current с оповещениями о тратах в реальном времени, бесплатной сетью банкоматов, мгновенными денежными переводами и инструментами бюджетирования.",
            "pers_chase": "Личное банковское обслуживание Chase с премиальными чековыми, сберегательными счетами, кредитными картами, ипотечными услугами и инвестиционными опциями.",
            "pers_wells": "Личное банковское обслуживание Wells Fargo включая чековые, сберегательные счета, кредитные карты, личные кредиты и услуги управления богатством.",
            "crypto_coinbase": "Аккаунт криптовалютной биржи Coinbase с торговыми возможностями, услугами кошелька, наградами за стейкинг и институциональными функциями."
        },
        "zh": {
            "vcc_chime": "Chime虚拟卡，具有即时消费通知、高达200美元的免费透支、提前直接存款和自动储蓄功能。",
            "vcc_paypal": "PayPal虚拟卡，具有加密货币买卖、即时转账、买家保护和国际支付功能。",
            "vcc_current": "Current虚拟卡，具有实时消费警报、免费ATM网络、即时转账和预算工具。",
            "pers_chase": "Chase个人银行业务，包括高级支票、储蓄账户、信用卡、抵押贷款服务和投资选择。",
            "pers_wells": "Wells Fargo个人银行业务，包括支票、储蓄、信用卡、个人贷款和财富管理服务。",
            "crypto_coinbase": "Coinbase加密货币交易所账户，具有交易功能、钱包服务、质押奖励和机构功能。"
        }
    }
    
    @classmethod
    def get_service_description(cls, service_type: str, service_id: str, language: str = "en") -> str:
        """
        Получить детальное описание услуги
        
        Args:
            service_type: Тип услуги (credit_reports, lookup_services, bank_services)
            service_id: ID услуги (cr_transunion, lookup_ssn, vcc_chime, etc.)
            language: Язык (en, ru, zh)
        
        Returns:
            Детальное описание услуги или пустую строку если не найдено
        """
        service_map = {
            "credit_reports": cls.CREDIT_REPORTS,
            "lookup_services": cls.LOOKUP_SERVICES, 
            "bank_services": cls.BANK_SERVICES
        }
        
        if service_type in service_map:
            lang_data = service_map[service_type].get(language, {})
            return lang_data.get(service_id, "")
        
        return ""
