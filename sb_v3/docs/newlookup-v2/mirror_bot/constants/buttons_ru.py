"""
Русские тексты кнопок для Mirror Bot
"""

class ButtonTexts:
    
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
        return f"🤝 Рефералы +{SystemFees.REFERRAL_PERCENT}%"
    
    # ========== LANGUAGE SELECTION ==========
    LANG_RUSSIAN = "🇷🇺 Русский"
    LANG_ENGLISH = "🇬🇧 Английский"
    LANG_CHINESE = "🇨🇳 Китайский"
    LANG_SPANISH = "🇪🇸 Испанский"
    
    # ========== PROFILE ==========
    SEND_MONEY = "💸 Отправить деньги другому пользователю"
    REFERRAL_SYSTEM = "🤝 Реферальная система"
    MY_BANK_ORDERS = "📦 Мои заказы банков"
    MY_PURCHASES = "📦 Мои покупки"
    SETUP_ARCHIVE = "📁 Настроить архив"
    CHOOSE_LANGUAGE = "🌍 Выбрать язык"
    BACK = "⬅️ Назад"
    
    # ========== PAYMENT ==========
    PAY_CRYPTOBOT = "🪙 Оплатить через CryptoBot "
    PAY_CRYPTOMUS = "💎 Оплатить через Cryptomus 🔥"
    PAY_VIA_CRYPTOBOT = "🪙 Оплата через CryptoBot"
    PAY_VIA_CRYPTOMUS = "💎 Оплата через Cryptomus"
    OPEN_PAYMENT_LINK = "💳 Открыть ссылку оплаты"
    REFRESH_STATUS = "♻️ Обновить статус"
    PAY_INVOICE = "💳 Оплатить счет"
    CHECK_STATUS = "♻️ Проверить статус"
    CANCEL = "❌ Отмена"
    PAY_WITH_CRYPTO = "💳 Оплатить криптой"
    BACK_TO_MENU = "⬅️ Назад в меню"
    
    # ========== ORDERS ==========
    CONFIRM = "✅ Подтвердить"
    CANCEL_ORDER = "❌ Отмена"
    SINGLE_ORDER = "1️⃣ Одиночный заказ"
    BULK_ORDER = "💼 Массовый заказ (2-20)"
    CONFIRM_ALL = "✅ Подтвердить все"
    BULK_CANCEL = "❌ Отмена"
    
    # ========== CONFIRMATION ==========
    EDIT = "✏️ Редактировать"
    CONTINUE = "✅ Продолжить"
    CONFIRM_PAY = "✅ Подтвердить и оплатить"
    CONFIRM_BUSINESS = "✅ ПОДТВЕРДИТЬ"
    
    # ========== LOOKUP SERVICES ==========
    SSN_DOB_LOOKUP = "🧾 SSN & DOB — $2.8-$3"
    CREDIT_SCORE_LOOKUP = "📉 Кредитный рейтинг — $1.6-$2"
    DL_LOOKUP = "🪪 Водительские права — $6.50-$7"
    MVR_LOOKUP = "🚗 MVR — $10-$11"
    FULL_MVR_LOOKUP = "📋 Полный MVR — $20-$22"
    PHONE_SEARCH = "📞 Поиск по телефону"
    BG_LOOKUP = "👤 Проверка данных — $1.5-$2"
    MMN_LOOKUP = "👩‍👦 MMN — $9"
    EIN_LOOKUP = "🏢 EIN — $11"
    LOOKUP_SSN_DOB = "🧾 SSN & DOB — $2.8-$3"
    LOOKUP_CREDIT_SCORE = "📉 Кредитный рейтинг — $1.6-$2"
    LOOKUP_DL = "🪪 Права — $6.50-$7"
    LOOKUP_MVR = "🚗 MVR — $10-$11"
    LOOKUP_FULL_MVR = "📋 Полный MVR — $20-$22"
    LOOKUP_PHONE_SEARCH = "📞 Поиск телефона"
    LOOKUP_BACKGROUND = "👤 Проверка — $1.5-$2"
    LOOKUP_MMN = "👩‍👦 MMN — $9"
    LOOKUP_EIN = "🏢 EIN — $11"
    LOOKUP_SUPPORT = "💬 Поддержка Lookup"
    LOOKUP_BUTTON = "📖 Lookup"
    BRUTE_BANK_SOON = "🔓 Brute BANK"
    LOOKUP_BANK_ACCOUNTS = "🏦 Проверка банк. аккаунта"
    ORDER_BY_NAME = "📝 Заказ по имени"
    MY_CC_ORDERS = "💳 Мои CC заказы"
    BRUTE_BANK = "🔓 Brute BANK"
    BRUTE_BUY = "⚡ Купить сейчас"
    BRUTE_BACK = "⬅️ Назад к Brute"
    EDU_SUBSCRIPTIONS = "📅 Подписки"
    EDU_MANUALS = "📖 Мануалы"
    EDU_BUY_SUBSCRIPTION = "✅ Купить подписку"
    EDU_BUY_MANUAL = "📥 Купить мануал"
    EDU_BACK = "⬅️ Назад к Education"
    LOOKUP_BA_SUPPORT = "📖 LOOKUP BA ПОДДЕРЖКА"
    
    # ========== PHONE LOOKUP ==========
    PHONE_NAME_LOOKUP = "📛 ПОИСК ИМЕНИ — $1.5"
    PHONE_SSN_LOOKUP = "🆔 ИМЯ DOB SSN — $4"
    PHONE_NAME_DOB_SSN = "🆔 ИМЯ DOB SSN — $4"
    PHONE_FULL_LOOKUP = "📊 ПОЛНЫЙ ПОИСК — $5"
    
    # ========== CREDIT REPORTS ==========
    CR_TRANSUNION = "🟢 TransUnion — $4.99"
    CR_EXPERIAN = "🔵 Experian — $5.99"
    CR_EQUIFAX = "🟡 EQUIFAX — $5.99"
    CR_LEXISNEXIS = "🟣 LexisNexis — $9.99"
    CR_WALLETHUB = "⚪ WalletHub / Credit Karma — $7.99"
    
    # ========== BANKS ==========
    BANKS_PERSONAL_VCC = "💳 ЛИЧНЫЕ VCC"
    BANKS_PERSONAL = "🏦 ЛИЧНЫЕ БАНКИ"
    BANKS_BUSINESS = "🏢 БИЗНЕС БАНКИ"
    BANKS_CRYPTO = "🪙 КРИПТО БАНКИ"
    BANKS_MERCHANT = "🏪 Merchant"
    BANKS_LOGS = "📋 Logs BA"
    BANKS_PREV = "⬅️ Пред"
    BANKS_NEXT = "След ➡️"
    BANKS_BACK_TO_CATEGORIES = "🏠 Назад к категориям"

    # ========== CC ==========
    CC_ENROLL = "🏦 Enroll"
    CC_OTP = "🔑 OTP"
    CC_NFC = "📱 NFC"
    CC_SELFREG_CC = "🏧 Selfreg CC"
    CC_CHECKS = "📄 Checks"
    CC_BUY = "🛒 Купить"
    CC_LIKE = "👍 Нравится"
    CC_DISLIKE = "👎 Не нравится"
    CC_REPORT_ISSUE = "⚠️ Сообщить о проблеме"
    CC_BACK_TO_CC = "⬅️ Назад к CC"
    CC_OPEN_CHAT = "💬 Открыть чат с продавцом"
    CC_NO_ITEMS = "📭 Нет товаров"

    # ========== DOCUMENTS ==========
    DOCS_CHECKS = "📄 Checks"

    # ========== VIP ==========
    VIP_WATCHLIST = "🌟 VIP Watchlist — $500"
    
    # ========== BANK QUANTITIES ==========
    QTY_2 = "2️⃣"
    QTY_3_DISCOUNT = "3️⃣ (-2%)"
    QTY_5_DISCOUNT = "5️⃣ (-3%)"
    QTY_10_DISCOUNT = "1️⃣0️⃣ (-5%)"
    BANK_QTY_3 = "3️⃣ (-2%)"
    BANK_QTY_5 = "5️⃣ (-3%)"
    BANK_QTY_10 = "1️⃣0️⃣ (-5%)"
    CUSTOM_QUANTITY = "📝 Свое количество"
    BANK_CUSTOM_QTY = "📝 Свое количество"
    BUY_1_ITEM = "✅ Купить 1 шт"
    BACK_TO_LIST = "⬅️ Назад к списку"
    
    # ========== ESIM ==========
    ESIM_SMS = "🇺🇸 eSIM для SMS"
    ESIM_DATA = "📶 eSIM для данных"
    ESIM_GV = "📞 Google Voice"
    ESIM_VERIZON_SMS = "📶 Verizon — $20/месяц"
    ESIM_ATT_SMS = "📶 AT&T — $35/месяц"
    ESIM_TMOBILE_SMS = "📶 T-Mobile — $35/месяц"
    ESIM_VERIZON_DATA = "📶 Verizon (5-15 ГБ)"
    ESIM_ATT_DATA = "📶 AT&T (10-30 ГБ)"
    ESIM_TMOBILE_DATA = "📶 T-Mobile (10-30 ГБ)"
    
    # ========== ESIM PERIODS ==========
    ESIM_1_MONTH = "⏳ 1 месяц"
    ESIM_3_MONTHS = "⏳ 3 месяца"
    ESIM_6_MONTHS = "⏳ 6 месяцев"
    
    # ========== ESIM DATA PLANS ==========
    ESIM_5GB = "📦 5 ГБ — $10"
    ESIM_10GB = "📦 10 ГБ — $20"
    ESIM_15GB = "📦 15 ГБ — $30"
    
    # ========== SUPPORT ==========
    SUPPORT_PAYMENT = "💰 Пополнение"
    SUPPORT_PRODUCT = "📦 Товар"
    SUPPORT_GENERAL = "💬 Обращение"
    SUPPORT_PARTNERSHIP = "🤝 Сотрудничество"
    MY_TICKETS = "📋 Мои запросы"
    SUPPORT_BACK = "⬅️ Назад"
    
    # ========== TICKET ACTIONS ==========
    TICKET_REPLY = "✍️ Ответить"
    TICKET_ATTACH_FILES = "📎 Прикрепить файлы"
    TICKET_BACK_TO_TICKETS = "⬅️ К моим запросам"
    TICKET_BACK_TO_SUPPORT = "⬅️ Назад к поддержке"
    
    # ========== MAIN KEYBOARD ==========
    EDUCATION = "📚 Обучение"
    MY_PROFILE = "👤 Мой профиль"
    TOP_UP_BALANCE = "💳 Пополнить баланс"
    SEARCH = "🔎 Поиск"
    CREDIT_REPORTS = "📈 КРЕДИТНЫЕ ОТЧЕТЫ"
    DOCUMENTS = "📄 ДОКУМЕНТЫ"
    PROS_FULLZ = "🧰 ПРОФИ И ФУЛЛЗ"
    BANKS = "🏦 БАНКИ"
    CC = "💳 CC"
    NFC = "📱 NFC"
    ENROLL = "🏦 Enroll"
    SELFREG_BA = "🏧 Selfreg BA"
    LOGS = "📋 Logs"
    OTP_CARD = "📲 OTP Card"
    SELFREG_CC = "💳 Selfreg CC"
    CHECKS = "📄 Checks"
    ESIM = "📶 eSIM"
    SUBSCRIPTIONS_ACCOUNTS = "🧾 Подписки / Аккаунты"
    ADD_INFO_CR = "✍️ Добавить инфо в CR"
    SERVICE_RULES = "📜 Правила сервиса"
    CALL_SERVICE = "📞 СВЯЗЬ С СЕРВИСОМ"
    ANOTHER_SERVICES = "📞 Другие услуги"
    REFERRALS = "🤝 Рефералы +25%"
    SUPPORT = "📞 Поддержка"
    ACCEPT_RULES = "✅ Я принимаю правила"
    DECLINE_RULES = "❌ Отказываюсь"
    VIEW_RULES = "📜 Правила"
    
    # ========== PAGINATION ==========
    PAGE_INFO = "📄 {page}/{total_pages}"
    PREV = "⬅️ Пред"
    NEXT = "След ➡️"
    PREV_PAGE = "⬅️ Пред"
    NEXT_PAGE = "След ➡️"
    BACK_SUPPORT = "⬅️ Назад"
    BACK_TO_SUPPORT = "⬅️ Назад к поддержке"
    BACK_TO_CATEGORIES = "🏠 Назад к категориям"
    BACK_FULLZ = "⬅️ Назад"
    BACK_FULLZ_SHORT = "🔙 Назад"
    EDIT_FULLZ = "✏️ Редактировать"
    BUY_ANY = "🎯 КУПИТЬ ЛЮБОЙ"
    CUSTOMISE = "⚙️ НАСТРОИТЬ"
    TEXT_ORDER = "📝 ТЕКСТ"
    
    # ========== DOCUMENTS ==========
    HIGH_QUALITY_DRAWING_COMING_SOON = "🧑‍🎨 Высококачественная отрисовка"
    ROBOT_DRAWING_COMING_SOON = "🤖 Роботизированная отрисовка (Скоро)"
    PHOTO = "🔥📸 Фото🔥"
    DL_FRONT_BACK = "🪪 Права (Перед и Зад)"
    DL_SELFIE = "🤳 Права + Селфи"
    DL_KYC = "🤳 Права + KYC видео"
    PASSPORT = "🛂 Паспорт"
    BUSINESS_DOCS = "🧾 Бизнес Документы"
    
    # ========== ADD INFO ==========
    ADDINFO_CR = "📈 Добавить инфо в кредитный отчет"
    ADDINFO_BG = "🧾 Добавить инфо в BG"
    ADDINFO_EMPLOYER = "🏢 Добавить работодателя в CR"
    ADDINFO_UNFREEZE = "❄️ Разморозить CR"
    
    # ========== FULLZ ==========
    FULLZ_PERSONAL = "👤 ЛИЧНЫЕ"
    FULLZ_BUSINESS = "🏢 БИЗНЕС"
    FULLZ_WITH_CS_CR = "🔥 CUSTOM С CS/CR"
    FULLZ_700_PLUS = "💳 700+ CS"
    FULLZ_800_PLUS = "⭐ 800+ CS"
    FULLZ_UNDER_18 = "🧒 ДО 18 ЛЕТ"
    FULLZ_IMMIGRANT = "🌍 ИММИГРАНТ"
    FULLZ_ZERO_BANK = "🏦 FULLZ 0 BANK"
    FULLZ_SUPPORT = "📞 FULLZ ПОДДЕРЖКА"
    FULLZ_RANDOM = "🎲 СЛУЧАЙНЫЕ"
    
    # ========== MISC ==========
    BULK_ORDER_BUTTON = "📦 Массовый заказ (2-20)"
    REORDER = "🔄 Заказать ещё"
