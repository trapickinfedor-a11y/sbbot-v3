"""English texts for Marketer Bot"""


class MarketerTexts:

    CHOOSE_LANGUAGE = "🌍 Choose language / Выберите язык"

    # ── Welcome & Rules ──
    WELCOME_INTRO = (
        "👋 <b>Welcome to Marketer Bot!</b>\n\n"
        "Here you can create up to <b>10 clone bots</b>, "
        "attract users and earn a percentage from every purchase they make.\n\n"
        "<b>📋 How it works:</b>\n"
        "1. Create a bot via @BotFather\n"
        "2. Add its token in \"My Bots\"\n"
        "3. Attract users to your bots\n"
        "4. Earn commission from every purchase\n\n"
        "<b>💰 Tier Program:</b>\n"
        "🥉 <b>Start</b> — 7% (0–499 users)\n"
        "🥈 <b>Advanced</b> — 9% (500–4,999 users)\n"
        "🥇 <b>Elite</b> — 12% (5,000+ users)\n\n"
        "Your percentage is based on the <b>total users</b> "
        "across all your bots. The more you attract — the higher your rate!"
    )
    RULES_TEXT = (
        "📜 <b>Affiliate Program Rules:</b>\n\n"
        "1. Spam and fake users are prohibited\n"
        "2. Fraudulent schemes are prohibited\n"
        "3. Do not present the bot as an official service\n"
        "4. Bots with violations will be removed without warning\n"
        "5. Administration reserves the right to change the terms\n"
        "6. Maximum 10 bots per marketer\n"
        "7. Withdrawals — by request to the administrator\n\n"
        "By clicking \"I Accept\", you confirm that you agree to the rules."
    )
    BTN_ACCEPT_RULES = "✅ I Accept the Rules"

    # ── Dashboard ──
    DASHBOARD_TITLE = "📊 <b>Marketer Dashboard</b>"
    TIER_LEVEL = "Level"
    TIER_MAX = "Maximum level!"
    TIER_NEXT = 'To <b>{name}</b> ({percent}%): <b>{left}</b> more users'
    TOTAL_USERS = "👥 Total users"
    BOTS_COUNT = "🤖 Bots"
    ORDERS_COUNT = "🛒 Orders"
    TOTAL_EARNED = "💰 Total earned"
    TODAY = "📅 Today"
    LAST_30D = "📊 Last 30 days"
    REGISTRATIONS = "📝 Registrations"
    BUYERS = "👥 Buyers"
    SALES = "🛒 Sales"
    EARNED = "💰 Earned"
    REG_SHORT = "📝 Reg"
    TIERS_LABEL = "Tiers"

    # ── Buttons ──
    BTN_MY_BOTS = "🤖 My Bots"
    BTN_ANALYTICS = "📈 Analytics"
    BTN_REFERRAL_MENU = "🔗 Referrals"
    BTN_LOGS = "📋 Activity Log"
    BTN_REFRESH = "🔄 Refresh"
    BTN_BACK = "◀️ Back"
    BTN_BACK_MAIN = "◀️ Main"
    BTN_BACK_BOTS = "◀️ My Bots"
    BTN_CREATE_BOT = "➕ Create new bot"
    BTN_EDIT_WELCOME = "✏️ Welcome msg"
    BTN_TOGGLE_OFF = "⏸ Disable"
    BTN_TOGGLE_ON = "▶️ Enable"
    BTN_DELETE = "🗑 Delete"
    BTN_CANCEL = "❌ Cancel"
    BTN_BY_BOTS = "🤖 By bots"
    BTN_TRENDS_7 = "📉 Trends 7d"
    BTN_TRENDS_14 = "📉 Trends 14d"
    BTN_TRENDS_30 = "📉 Trends 30d"
    BTN_LANGUAGE = "🌐 Language"

    # ── Periods ──
    PERIOD_DAY = "Today"
    PERIOD_WEEK = "Week"
    PERIOD_MONTH = "Month"
    PERIOD_ALL = "All time"

    # ── My Bots ──
    MY_BOTS_TITLE = "🤖 <b>My Bots</b>"
    BOT_ACTIVE = "✅ Active"
    BOT_INACTIVE = "❌ Disabled"
    BOT_USERS = "👥 Users"
    BOT_ORDERS = "🛒 Orders"
    BOT_EARNED = "💰 Earned"
    BOT_RATE = "📊 Current rate"
    BOT_WELCOME = "💬 Welcome message"
    BOT_WELCOME_DEFAULT = "default"
    USERS_SHORT = "users"
    NO_BOTS_YET = "You have no bots yet.\nCreate a bot via @BotFather and add it here!"
    TIER_UNTIL = "📈 To {percent}%: <b>{left}</b> more users"
    BOT_LIMIT = "Bot limit: {max}"
    BOT_CREATED = '🎉 <b>Bot @{username} added!</b>\n\n📊 Current level: {icon} {tier} — {percent}%\n👥 Total users: {total}\n\nAttract users to your bots and level up!'
    BOT_ACTIVATED = "activated ✅"
    BOT_DEACTIVATED = "disabled ❌"
    BOT_DELETED = "Bot deleted"
    WELCOME_UPDATED = "✅ Welcome message updated!"
    NOT_FOUND = "Not found"

    # ── Create bot FSM ──
    CREATE_BOT_TITLE = "🤖 <b>Create new bot</b>"
    CREATE_STEP1 = (
        "<b>Step 1:</b> Create a bot in @BotFather:\n"
        "1. Open @BotFather\n"
        "2. Send /newbot\n"
        "3. Set name and username\n"
        "4. Copy the token and send it here\n\n"
        "<i>Example: 1234567890:AAxxxxxx...</i>"
    )
    CREATE_BAD_TOKEN = "❌ Invalid token format. Try again or press Cancel."
    CREATE_DUPLICATE = "❌ This token is already registered."
    CREATE_INVALID = "❌ Token is invalid. Check and try again."
    CREATE_FOUND = (
        '✅ Bot <b>@{username}</b> found and added!\n\n'
        '⚠️ <b>Don\'t forget:</b> set a bot avatar in @BotFather '
        '(/setuserpic), add a description (/setdescription) '
        'and about text (/setabouttext) — this builds user trust!'
    )
    ENTER_WELCOME = "✏️ Enter a new welcome message:"
    FIRST_START = "Please send /start first"

    # ── Analytics ──
    ANALYTICS_TITLE = "📈 <b>Analytics — {period}</b>"
    TREND_LABEL = "(trend)"
    CHART_TITLE = "This week"
    TOPUP_AMOUNT = "💵 Topup amount"
    EFFICIENCY = "Efficiency metrics"
    CONVERSION = "📊 Conversion (reg→buyer)"
    AVG_CHECK = "🧾 Avg check"
    AVG_DAILY = "📅 Avg/day"
    AVG_REG = "reg."
    BOTS_STATS_TITLE = "📊 <b>Stats by bot</b>"
    BOTS_TOTAL = "Total"
    LAST_ACTIVITY = "Last act"
    TREND_TITLE = "📉 <b>Trends ({days}d)</b>"
    TREND_HEADER = "<i>Earned | Reg | Sales</i>"
    NO_DATA = "No data."

    # ── Logs ──
    LOGS_TITLE = "📋 <b>Activity Log</b>"
    LOGS_TITLE_COUNT = "📋 <b>Activity Log</b> (last {n})"
    LOGS_EMPTY = "No entries yet."
    LOG_REGISTRATION = "🆕 Registration"
    LOG_EARNING = "💰 Earning"
    LOG_TIER_UPGRADE = "📈 Tier upgrade"
    LOG_BOT_CREATED = "🤖 Bot created"
    LOG_BOT_DELETED = "🗑 Bot deleted"

    # ── Help ──
    HELP_TEXT = (
        "📖 <b>Marketer Bot Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start — Dashboard\n"
        "/bots — My bots\n"
        "/logs — Activity log\n"
        "/help — This help\n\n"
        "<b>How it works:</b>\n"
        "1. Create a bot in @BotFather\n"
        "2. Add its token via \"My Bots\"\n"
        "3. Attract users to your bots\n"
        "4. Earn % from every purchase\n\n"
        "<b>Tier program:</b>\n"
        "🥉 Start — 7% (up to 500 users)\n"
        "🥈 Advanced — 9% (from 500 users)\n"
        "🥇 Elite — 12% (from 5,000 users)\n\n"
        "<b>📈 Analytics:</b>\n"
        "• Stats for day / week / month / all time\n"
        "• Conversion, avg check, daily averages\n"
        "• Trends for 7 / 14 / 30 days\n"
        "• Detailed breakdown by bot\n\n"
        "<b>📬 Daily report:</b>\n"
        "Every day at 21:00 (MSK) the bot sends a full summary.\n\n"
        "You can create up to 10 bots."
    )

    # ── Withdrawal ──
    BTN_WITHDRAW = "💸 Withdraw"
    WITHDRAW_TITLE = "💸 <b>Withdrawal</b>"
    WITHDRAW_BALANCE = "💰 Your balance: <b>${balance}</b>"
    WITHDRAW_MIN = "Minimum withdrawal: <b>${min}</b>"
    WITHDRAW_NO_FUNDS = "❌ Insufficient funds for withdrawal."
    WITHDRAW_ENTER_AMOUNT = "Enter withdrawal amount (in $):"
    WITHDRAW_BAD_AMOUNT = "❌ Invalid amount. Enter a number from ${min} to ${max}."
    WITHDRAW_CHOOSE_WALLET = "💳 Choose wallet type for receiving:"
    BTN_WALLET_BTC = "₿ BTC"
    BTN_WALLET_USDT = "₮ USDT"
    WITHDRAW_ENTER_ADDRESS_BTC = "📤 Enter your <b>BTC</b> wallet address:"
    WITHDRAW_ENTER_ADDRESS_USDT = "📤 Enter your <b>USDT TRC-20</b> wallet address:"
    WITHDRAW_ENTER_REQUISITES = (
        "💳 Enter payment details:\n"
        "<i>(USDT TRC-20 wallet, card number, etc.)</i>"
    )
    WITHDRAW_CONFIRM = (
        "📋 <b>Confirm your request:</b>\n\n"
        "💰 Amount: <b>${amount}</b>\n"
        "💳 Details: <code>{requisites}</code>\n\n"
        "Confirm?"
    )
    BTN_CONFIRM_WITHDRAW = "✅ Confirm"
    WITHDRAW_CREATED = (
        "✅ <b>Withdrawal request created!</b>\n\n"
        "💰 Amount: <b>${amount}</b>\n"
        "📋 Status: pending review\n\n"
        "The administrator will process your request shortly."
    )
    WITHDRAW_HISTORY_TITLE = "📜 <b>Withdrawal History</b>"
    WITHDRAW_HISTORY_EMPTY = "You have no withdrawal requests yet."
    BTN_WITHDRAW_HISTORY = "📜 Withdrawal History"
    WITHDRAW_STATUS_PENDING = "⏳ Pending"
    WITHDRAW_STATUS_APPROVED = "✅ Paid"
    WITHDRAW_STATUS_REJECTED = "❌ Rejected"

    # ── Daily Report ──
    DAILY_TITLE = "📬 <b>Daily report — {date}</b>"
    DAILY_TODAY = "📅 Today"
    DAILY_WEEK = "📊 This week"
    DAILY_BOTS = "🤖 Bots"
    DAILY_TOTALS = "Totals"

    # ── Referral ──
    REFERRAL_TITLE = "🔗 <b>Referral Program</b>"
    REFERRAL_YOUR_LINK = (
        "Your referral link:\n"
        "<code>{link}</code>\n\n"
        "Invite users and earn a bonus from each of their first purchases!\n\n"
        "📊 <b>Rates:</b>\n"
        "• Level 1 (direct): <b>{l1}%</b>\n"
        "• Level 2: <b>{l2}%</b>\n"
        "• Level 3: <b>{l3}%</b>\n"
        "• Level 4: <b>{l4}%</b>"
    )
    BTN_COPY_LINK = "📋 Copy link"
    BTN_SHARE_LINK = "📤 Share link"
    BTN_REFERRAL_STATS = "📊 My stats"
    BTN_REFERRAL_HISTORY = "📜 Earning history"
    BTN_REFERRAL_WITHDRAW = "💸 Withdraw bonus"
    BTN_REFERRAL_BACK = "◀️ Back"

    REFERRAL_STATS_TITLE = "📊 <b>Referral Statistics</b>"
    REFERRAL_STATS_TEXT = (
        "👥 Total invited: <b>{invited}</b>\n"
        "✅ Confirmed (first purchase): <b>{confirmed}</b>\n"
        "💰 Total earned (displayed): <b>${earned}</b>\n"
        "⏳ Pending moderation: <b>${pending}</b>"
    )

    REFERRAL_HISTORY_TITLE = "📜 <b>Earning History</b>"
    REFERRAL_HISTORY_EMPTY = "You have no referral earnings yet."
    REFERRAL_HISTORY_ROW = "• {date}  Lv.{level}  <b>+${amount}</b>  {status}"
    REFERRAL_STATUS_PENDING = "⏳ pending"
    REFERRAL_STATUS_APPROVED = "✅ approved"
    REFERRAL_STATUS_REJECTED = "❌ rejected"
    REFERRAL_STATUS_PAID = "💸 paid"

    REFERRAL_WITHDRAW_TITLE = "💸 <b>Withdraw Referral Bonus</b>"
    REFERRAL_WITHDRAW_BALANCE = "💰 Available balance: <b>${balance}</b>"
    REFERRAL_WITHDRAW_MIN = "Minimum amount: <b>${min}</b>"
    REFERRAL_WITHDRAW_NO_FUNDS = "❌ Insufficient funds."
    REFERRAL_WITHDRAW_ENTER_AMOUNT = "Enter the withdrawal amount (in USD):"
    REFERRAL_WITHDRAW_ENTER_REQUISITES = (
        "💳 Enter payment details:\n"
        "<i>(BTC address, USDT TRC-20, etc.)</i>"
    )
    REFERRAL_WITHDRAW_BAD_AMOUNT = "❌ Invalid amount (from ${min} to ${max})."
    REFERRAL_WITHDRAW_CONFIRM = (
        "📋 <b>Confirm withdrawal:</b>\n\n"
        "💰 Amount: <b>${amount}</b>\n"
        "💳 Details: <code>{requisites}</code>\n\n"
        "Confirm?"
    )
    BTN_CONFIRM_REFERRAL_WITHDRAW = "✅ Confirm"
    REFERRAL_WITHDRAW_CREATED = (
        "✅ <b>Request submitted!</b>\n\n"
        "💰 Amount: <b>${amount}</b>\n"
        "📋 Status: awaiting moderation"
    )

    # ── Referral notifications ──
    NOTIF_NEW_REFERRAL = "🎉 <b>New referral!</b>\n\nA user registered via your link."
    NOTIF_REFERRAL_PURCHASE = (
        "💰 <b>Your referral made their first purchase!</b>\n\n"
        "Bonus <b>${amount}</b> (level {level}) has been sent for moderation."
    )
    NOTIF_REFERRAL_WITHDRAW_APPROVED = (
        "✅ <b>Withdrawal approved!</b>\n\n"
        "💰 Amount: <b>${amount}</b>\n"
        "Funds will be transferred shortly."
    )
    NOTIF_REFERRAL_WITHDRAW_REJECTED = (
        "❌ <b>Withdrawal rejected.</b>\n\n"
        "💰 Amount: <b>${amount}</b>\n"
        "Reason: {reason}"
    )
