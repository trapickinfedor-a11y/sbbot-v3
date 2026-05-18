"""
中文按钮文本 for Mirror Bot
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
        return f"🤝 推荐 +{SystemFees.REFERRAL_PERCENT}%"
    
    # ========== LANGUAGE SELECTION ==========
    LANG_RUSSIAN = "🇷🇺 俄语"
    LANG_ENGLISH = "🇬🇧 英语"
    LANG_CHINESE = "🇨🇳 中文"
    LANG_SPANISH = "🇪🇸 西班牙语"
    
    # ========== PROFILE ==========
    SEND_MONEY = "💸 向其他用户转账"
    REFERRAL_SYSTEM = "🤝 推荐系统"
    MY_BANK_ORDERS = "📦 我的银行订单"
    MY_PURCHASES = "📦 我的购买"
    SETUP_ARCHIVE = "📁 设置归档"
    CHOOSE_LANGUAGE = "🌍 选择语言"
    BACK = "⬅️ 返回"
    
    # ========== PAYMENT ==========
    PAY_CRYPTOBOT = "🪙 通过 CryptoBot 支付 "
    PAY_CRYPTOMUS = "💎 通过 Cryptomus 支付 🔥"
    PAY_VIA_CRYPTOBOT = "🪙 通过 CryptoBot 支付"
    PAY_VIA_CRYPTOMUS = "💎 通过 Cryptomus 支付"
    OPEN_PAYMENT_LINK = "💳 打开支付链接"
    REFRESH_STATUS = "♻️ 刷新状态"
    PAY_INVOICE = "💳 支付发票"
    CHECK_STATUS = "♻️ 检查状态"
    CANCEL = "❌ 取消"
    PAY_WITH_CRYPTO = "💳 用加密货币支付"
    BACK_TO_MENU = "⬅️ 返回菜单"
    
    # ========== ORDERS ==========
    CONFIRM = "✅ 确认"
    CANCEL_ORDER = "❌ 取消"
    SINGLE_ORDER = "1️⃣ 单个订单"
    BULK_ORDER = "💼 批量订单 (2-20)"
    CONFIRM_ALL = "✅ 确认全部"
    BULK_CANCEL = "❌ 取消"
    
    # ========== CONFIRMATION ==========
    EDIT = "✏️ 编辑"
    CONTINUE = "✅ 继续"
    CONFIRM_PAY = "✅ 确认并付款"
    CONFIRM_BUSINESS = "✅ 确认"
    
    # ========== LOOKUP SERVICES ==========
    SSN_DOB_LOOKUP = "🧾 SSN & DOB — $2.8-$3"
    CREDIT_SCORE_LOOKUP = "📉 信用评分 — $1.6-$2"
    DL_LOOKUP = "🪪 驾照 — $6.50-$7"
    MVR_LOOKUP = "🚗 MVR — $10-$11"
    FULL_MVR_LOOKUP = "📋 完整 MVR — $20-$22"
    PHONE_SEARCH = "📞 电话搜索"
    BG_LOOKUP = "👤 背景调查 — $1.5-$2"
    MMN_LOOKUP = "👩‍👦 MMN — $9"
    EIN_LOOKUP = "🏢 EIN — $11"
    LOOKUP_SSN_DOB = "🧾 SSN & DOB — $2.8-$3"
    LOOKUP_CREDIT_SCORE = "📉 信用评分 — $1.6-$2"
    LOOKUP_DL = "🪪 驾照 — $6.50-$7"
    LOOKUP_MVR = "🚗 MVR — $10-$11"
    LOOKUP_FULL_MVR = "📋 完整 MVR — $20-$22"
    LOOKUP_PHONE_SEARCH = "📞 电话搜索"
    LOOKUP_BACKGROUND = "👤 背景调查 — $1.5-$2"
    LOOKUP_MMN = "👩‍👦 MMN — $9"
    LOOKUP_EIN = "🏢 EIN — $11"
    LOOKUP_SUPPORT = "💬 查询支持"
    LOOKUP_BUTTON = "📖 Lookup"
    BRUTE_BANK_SOON = "🔓 Brute BANK"
    LOOKUP_BANK_ACCOUNTS = "🏦 银行账户查询"
    ORDER_BY_NAME = "📝 按姓名下单"
    MY_CC_ORDERS = "💳 我的CC订单"
    BRUTE_BANK = "🔓 Brute BANK"
    BRUTE_BUY = "⚡ 立即购买"
    BRUTE_BACK = "⬅️ 返回Brute"
    EDU_SUBSCRIPTIONS = "📅 订阅"
    EDU_MANUALS = "📖 手册"
    EDU_BUY_SUBSCRIPTION = "✅ 购买订阅"
    EDU_BUY_MANUAL = "📥 购买手册"
    EDU_BACK = "⬅️ 返回教育"
    LOOKUP_BA_SUPPORT = "📖 LOOKUP BA 支持"
    
    # ========== PHONE LOOKUP ==========
    PHONE_NAME_LOOKUP = "📛 姓名查找 — $1.5"
    PHONE_SSN_LOOKUP = "🆔 姓名 DOB SSN — $4"
    PHONE_NAME_DOB_SSN = "🆔 姓名 DOB SSN — $4"
    PHONE_FULL_LOOKUP = "📊 完整查找 — $5"
    
    # ========== CREDIT REPORTS ==========
    CR_TRANSUNION = "🟢 TransUnion — $4.99"
    CR_EXPERIAN = "🔵 Experian — $5.99"
    CR_EQUIFAX = "🟡 EQUIFAX — $5.99"
    CR_LEXISNEXIS = "🟣 LexisNexis — $9.99"
    CR_WALLETHUB = "⚪ WalletHub / Credit Karma — $7.99"
    
    # ========== BANKS ==========
    BANKS_PERSONAL_VCC = "💳 个人 VCC"
    BANKS_PERSONAL = "🏦 个人银行"
    BANKS_BUSINESS = "🏢 商业银行"
    BANKS_CRYPTO = "🪙 加密银行"
    BANKS_MERCHANT = "🏪 Merchant"
    BANKS_LOGS = "📋 Logs BA"
    BANKS_PREV = "⬅️ 上一页"
    BANKS_NEXT = "下一页 ➡️"
    BANKS_BACK_TO_CATEGORIES = "🏠 返回类别"

    # ========== CC ==========
    CC_ENROLL = "🏦 Enroll"
    CC_OTP = "🔑 OTP"
    CC_NFC = "📱 NFC"
    CC_SELFREG_CC = "🏧 Selfreg CC"
    CC_CHECKS = "📄 Checks"
    CC_BUY = "🛒 购买"
    CC_LIKE = "👍 点赞"
    CC_DISLIKE = "👎 踩"
    CC_REPORT_ISSUE = "⚠️ 报告问题"
    CC_BACK_TO_CC = "⬅️ 返回CC"
    CC_OPEN_CHAT = "💬 打开卖家聊天"
    CC_NO_ITEMS = "📭 暂无商品"

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
    CUSTOM_QUANTITY = "📝 自定义数量"
    BANK_CUSTOM_QTY = "📝 自定义数量"
    BUY_1_ITEM = "✅ 购买 1 个"
    BACK_TO_LIST = "⬅️ 返回列表"
    
    # ========== ESIM ==========
    ESIM_SMS = "🇺🇸 eSIM 短信"
    ESIM_DATA = "📶 eSIM 数据"
    ESIM_GV = "📞 Google Voice"
    ESIM_VERIZON_SMS = "📶 Verizon — $20/月"
    ESIM_ATT_SMS = "📶 AT&T — $35/月"
    ESIM_TMOBILE_SMS = "📶 T-Mobile — $35/月"
    ESIM_VERIZON_DATA = "📶 Verizon (5-15 GB)"
    ESIM_ATT_DATA = "📶 AT&T (10-30 GB)"
    ESIM_TMOBILE_DATA = "📶 T-Mobile (10-30 GB)"
    
    # ========== ESIM PERIODS ==========
    ESIM_1_MONTH = "⏳ 1 个月"
    ESIM_3_MONTHS = "⏳ 3 个月"
    ESIM_6_MONTHS = "⏳ 6 个月"
    
    # ========== ESIM DATA PLANS ==========
    ESIM_5GB = "📦 5 GB — $10"
    ESIM_10GB = "📦 10 GB — $20"
    ESIM_15GB = "📦 15 GB — $30"
    
    # ========== SUPPORT ==========
    SUPPORT_PAYMENT = "💰 充值"
    SUPPORT_PRODUCT = "📦 产品"
    SUPPORT_GENERAL = "💬 一般"
    SUPPORT_PARTNERSHIP = "🤝 合作"
    MY_TICKETS = "📋 我的工单"
    SUPPORT_BACK = "⬅️ 返回"
    
    # ========== TICKET ACTIONS ==========
    TICKET_REPLY = "✍️ 回复"
    TICKET_ATTACH_FILES = "📎 附加文件"
    TICKET_BACK_TO_TICKETS = "⬅️ 返回我的工单"
    TICKET_BACK_TO_SUPPORT = "⬅️ 返回客服"
    
    # ========== MAIN KEYBOARD ==========
    EDUCATION = "📚 教育"
    MY_PROFILE = "👤 我的资料"
    TOP_UP_BALANCE = "💳 充值余额"
    SEARCH = "🔎 搜索"
    CREDIT_REPORTS = "📈 信用报告"
    DOCUMENTS = "📄 文档"
    PROS_FULLZ = "🧰 专业和完整"
    BANKS = "🏦 银行"
    CC = "💳 CC"
    NFC = "📱 NFC"
    ENROLL = "🏦 Enroll"
    SELFREG_BA = "🏧 Selfreg BA"
    LOGS = "📋 Logs"
    OTP_CARD = "📲 OTP Card"
    SELFREG_CC = "💳 Selfreg CC"
    CHECKS = "📄 Checks"
    ESIM = "📶 eSIM"
    SUBSCRIPTIONS_ACCOUNTS = "🧾 订阅/账户"
    ADD_INFO_CR = "✍️ 在 CR 中添加信息"
    SERVICE_RULES = "📜 服务规则"
    CALL_SERVICE = "📞 联系服务"
    ANOTHER_SERVICES = "📞 其他服务"
    REFERRALS = "🤝 推荐 +25%"
    SUPPORT = "📞 客服"
    ACCEPT_RULES = "✅ 我接受规则"
    DECLINE_RULES = "❌ 我拒绝"
    VIEW_RULES = "📜 规则"
    
    # ========== PAGINATION ==========
    PAGE_INFO = "📄 {page}/{total_pages}"
    PREV = "⬅️ 上一页"
    NEXT = "下一页 ➡️"
    PREV_PAGE = "⬅️ 上一页"
    NEXT_PAGE = "下一页 ➡️"
    BACK_SUPPORT = "⬅️ 返回"
    BACK_TO_SUPPORT = "⬅️ 返回客服"
    BACK_TO_CATEGORIES = "🏠 返回类别"
    BACK_FULLZ = "⬅️ 返回"
    BACK_FULLZ_SHORT = "🔙 返回"
    EDIT_FULLZ = "✏️ 编辑"
    BUY_ANY = "🎯 购买任意"
    CUSTOMISE = "⚙️ 自定义"
    TEXT_ORDER = "📝 文本"
    
    # ========== DOCUMENTS ==========
    HIGH_QUALITY_DRAWING_COMING_SOON = "🧑‍🎨 高质量绘图"
    ROBOT_DRAWING_COMING_SOON = "🤖 机器人绘图（即将推出）"
    PHOTO = "🔥📸 照片🔥"
    DL_FRONT_BACK = "🪪 驾照（正反面）"
    DL_SELFIE = "🤳 驾照 + 自拍"
    DL_KYC = "🤳 驾照 + KYC 视频"
    PASSPORT = "🛂 护照"
    BUSINESS_DOCS = "🧾 商业文件"
    
    # ========== ADD INFO ==========
    ADDINFO_CR = "📈 在信用报告中添加信息"
    ADDINFO_BG = "🧾 在 BG 中添加信息"
    ADDINFO_EMPLOYER = "🏢 在 CR 中添加雇主"
    ADDINFO_UNFREEZE = "❄️ 解冻 CR"
    
    # ========== FULLZ ==========
    FULLZ_PERSONAL = "👤 个人"
    FULLZ_BUSINESS = "🏢 商业"
    FULLZ_WITH_CS_CR = "🔥 CUSTOM 带 CS/CR"
    FULLZ_700_PLUS = "💳 700+ CS"
    FULLZ_800_PLUS = "⭐ 800+ CS"
    FULLZ_UNDER_18 = "🧒 未满18岁"
    FULLZ_IMMIGRANT = "🌍 移民"
    FULLZ_ZERO_BANK = "🏦 FULLZ 0 BANK"
    FULLZ_SUPPORT = "📞 FULLZ 支持"
    FULLZ_RANDOM = "🎲 随机"
    
    # ========== MISC ==========
    BULK_ORDER_BUTTON = "📦 批量订单 (2-20)"
    REORDER = "🔄 再次下单"
