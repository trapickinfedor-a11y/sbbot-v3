"""中文文本 Marketer Bot"""


class MarketerTexts:

    CHOOSE_LANGUAGE = "🌍 选择语言 / Choose language"

    # ── Welcome & Rules ──
    WELCOME_INTRO = (
        "👋 <b>欢迎使用 Marketer Bot！</b>\n\n"
        "您可以创建最多 <b>10 个克隆机器人</b>，"
        "吸引用户并从他们的每笔购买中赚取佣金。\n\n"
        "<b>📋 运作方式：</b>\n"
        "1. 通过 @BotFather 创建机器人\n"
        "2. 在「我的机器人」中添加令牌\n"
        "3. 吸引用户到您的机器人\n"
        "4. 从每笔购买中赚取佣金\n\n"
        "<b>💰 等级计划：</b>\n"
        "🥉 <b>入门</b> — 7%（0–499 用户）\n"
        "🥈 <b>进阶</b> — 9%（500–4,999 用户）\n"
        "🥇 <b>精英</b> — 12%（5,000+ 用户）\n\n"
        "您的佣金比例基于所有机器人的<b>总用户数</b>。"
        "吸引的用户越多，佣金越高！"
    )
    RULES_TEXT = (
        "📜 <b>合作伙伴计划规则：</b>\n\n"
        "1. 禁止垃圾信息和刷用户\n"
        "2. 禁止欺诈行为\n"
        "3. 不得将机器人伪装为官方服务\n"
        "4. 违规的机器人将被立即删除\n"
        "5. 管理层保留更改条款的权利\n"
        "6. 每位营销人员最多 10 个机器人\n"
        "7. 提现需联系管理员\n\n"
        "点击「我同意」即表示您同意以上规则。"
    )
    BTN_ACCEPT_RULES = "✅ 我同意规则"

    # ── Dashboard ──
    DASHBOARD_TITLE = "📊 <b>营销面板</b>"
    TIER_LEVEL = "等级"
    TIER_MAX = "最高等级！"
    TIER_NEXT = '距 <b>{name}</b> ({percent}%): 还需 <b>{left}</b> 用户'
    TOTAL_USERS = "👥 总用户数"
    BOTS_COUNT = "🤖 机器人"
    ORDERS_COUNT = "🛒 订单"
    TOTAL_EARNED = "💰 总收入"
    TODAY = "📅 今天"
    LAST_30D = "📊 近30天"
    REGISTRATIONS = "📝 注册"
    BUYERS = "👥 买家"
    SALES = "🛒 销售"
    EARNED = "💰 收入"
    REG_SHORT = "📝 注册"
    TIERS_LABEL = "等级"

    # ── Buttons ──
    BTN_MY_BOTS = "🤖 我的机器人"
    BTN_ANALYTICS = "📈 分析"
    BTN_REFERRAL_MENU = "🔗 推荐"
    BTN_LOGS = "📋 活动日志"
    BTN_REFRESH = "🔄 刷新"
    BTN_BACK = "◀️ 返回"
    BTN_BACK_MAIN = "◀️ 主页"
    BTN_BACK_BOTS = "◀️ 我的机器人"
    BTN_CREATE_BOT = "➕ 创建新机器人"
    BTN_EDIT_WELCOME = "✏️ 欢迎语"
    BTN_TOGGLE_OFF = "⏸ 禁用"
    BTN_TOGGLE_ON = "▶️ 启用"
    BTN_DELETE = "🗑 删除"
    BTN_CANCEL = "❌ 取消"
    BTN_BY_BOTS = "🤖 按机器人"
    BTN_TRENDS_7 = "📉 趋势 7天"
    BTN_TRENDS_14 = "📉 趋势 14天"
    BTN_TRENDS_30 = "📉 趋势 30天"
    BTN_LANGUAGE = "🌐 语言"

    # ── Periods ──
    PERIOD_DAY = "今天"
    PERIOD_WEEK = "本周"
    PERIOD_MONTH = "本月"
    PERIOD_ALL = "全部"

    # ── My Bots ──
    MY_BOTS_TITLE = "🤖 <b>我的机器人</b>"
    BOT_ACTIVE = "✅ 运行中"
    BOT_INACTIVE = "❌ 已禁用"
    BOT_USERS = "👥 用户"
    BOT_ORDERS = "🛒 订单"
    BOT_EARNED = "💰 收入"
    BOT_RATE = "📊 当前费率"
    BOT_WELCOME = "💬 欢迎消息"
    BOT_WELCOME_DEFAULT = "默认"
    USERS_SHORT = "用户"
    NO_BOTS_YET = "您还没有机器人。\n通过 @BotFather 创建并添加到这里！"
    TIER_UNTIL = "📈 距 {percent}%: 还需 <b>{left}</b> 用户"
    BOT_LIMIT = "机器人上限: {max}"
    BOT_CREATED = '🎉 <b>机器人 @{username} 已添加！</b>\n\n📊 当前等级: {icon} {tier} — {percent}%\n👥 总用户: {total}\n\n吸引用户到您的机器人并提升等级！'
    BOT_ACTIVATED = "已启用 ✅"
    BOT_DEACTIVATED = "已禁用 ❌"
    BOT_DELETED = "机器人已删除"
    WELCOME_UPDATED = "✅ 欢迎消息已更新！"
    NOT_FOUND = "未找到"

    # ── Create bot FSM ──
    CREATE_BOT_TITLE = "🤖 <b>创建新机器人</b>"
    CREATE_STEP1 = (
        "<b>步骤 1:</b> 在 @BotFather 创建机器人:\n"
        "1. 打开 @BotFather\n"
        "2. 发送 /newbot\n"
        "3. 设置名称和用户名\n"
        "4. 复制令牌并发送到这里\n\n"
        "<i>示例: 1234567890:AAxxxxxx...</i>"
    )
    CREATE_BAD_TOKEN = "❌ 令牌格式无效，请重试或点击取消。"
    CREATE_DUPLICATE = "❌ 此令牌已注册。"
    CREATE_INVALID = "❌ 令牌无效，请检查后重试。"
    CREATE_FOUND = (
        '✅ 机器人 <b>@{username}</b> 已找到并添加！\n\n'
        '⚠️ <b>别忘了：</b>在 @BotFather 中设置机器人头像 '
        '(/setuserpic)，添加描述 (/setdescription) '
        '和简介 (/setabouttext) — 这能提升用户信任度！'
    )
    ENTER_WELCOME = "✏️ 输入新的欢迎消息:"
    FIRST_START = "请先发送 /start"

    # ── Analytics ──
    ANALYTICS_TITLE = "📈 <b>分析 — {period}</b>"
    TREND_LABEL = "(趋势)"
    CHART_TITLE = "本周"
    TOPUP_AMOUNT = "💵 充值金额"
    EFFICIENCY = "效率指标"
    CONVERSION = "📊 转化率 (注册→买家)"
    AVG_CHECK = "🧾 平均消费"
    AVG_DAILY = "📅 日均"
    AVG_REG = "注册"
    BOTS_STATS_TITLE = "📊 <b>各机器人统计</b>"
    BOTS_TOTAL = "合计"
    LAST_ACTIVITY = "最后活动"
    TREND_TITLE = "📉 <b>趋势 ({days}天)</b>"
    TREND_HEADER = "<i>收入 | 注册 | 销售</i>"
    NO_DATA = "暂无数据。"

    # ── Logs ──
    LOGS_TITLE = "📋 <b>活动日志</b>"
    LOGS_TITLE_COUNT = "📋 <b>活动日志</b> (最近 {n})"
    LOGS_EMPTY = "暂无记录。"
    LOG_REGISTRATION = "🆕 注册"
    LOG_EARNING = "💰 收入"
    LOG_TIER_UPGRADE = "📈 等级提升"
    LOG_BOT_CREATED = "🤖 机器人创建"
    LOG_BOT_DELETED = "🗑 机器人删除"

    # ── Help ──
    HELP_TEXT = (
        "📖 <b>Marketer Bot 帮助</b>\n\n"
        "<b>命令:</b>\n"
        "/start — 控制面板\n"
        "/bots — 我的机器人\n"
        "/logs — 活动日志\n"
        "/help — 帮助\n\n"
        "<b>运作方式:</b>\n"
        "1. 在 @BotFather 创建机器人\n"
        "2. 通过「我的机器人」添加令牌\n"
        "3. 吸引用户到您的机器人\n"
        "4. 从每笔交易中赚取 %\n\n"
        "<b>等级计划:</b>\n"
        "🥉 入门 — 7% (500用户以下)\n"
        "🥈 进阶 — 9% (500用户起)\n"
        "🥇 精英 — 12% (5000用户起)\n\n"
        "<b>📈 分析:</b>\n"
        "• 按天/周/月/全部时间统计\n"
        "• 转化率、平均消费、日均数据\n"
        "• 7 / 14 / 30天趋势\n"
        "• 各机器人详细分析\n\n"
        "<b>📬 每日报告:</b>\n"
        "每天21:00 (MSK) 发送完整摘要。\n\n"
        "最多可创建10个机器人。"
    )

    # ── Withdrawal ──
    BTN_WITHDRAW = "💸 提现"
    WITHDRAW_TITLE = "💸 <b>提现</b>"
    WITHDRAW_BALANCE = "💰 您的余额: <b>${balance}</b>"
    WITHDRAW_MIN = "最低提现金额: <b>${min}</b>"
    WITHDRAW_NO_FUNDS = "❌ 余额不足，无法提现。"
    WITHDRAW_ENTER_AMOUNT = "请输入提现金额（美元）:"
    WITHDRAW_BAD_AMOUNT = "❌ 金额无效。请输入 ${min} 到 ${max} 之间的数字。"
    WITHDRAW_CHOOSE_WALLET = "💳 选择收款钱包类型:"
    BTN_WALLET_BTC = "₿ BTC"
    BTN_WALLET_USDT = "₮ USDT"
    WITHDRAW_ENTER_ADDRESS_BTC = "📤 请输入您的 <b>BTC</b> 钱包地址:"
    WITHDRAW_ENTER_ADDRESS_USDT = "📤 请输入您的 <b>USDT TRC-20</b> 钱包地址:"
    WITHDRAW_ENTER_REQUISITES = (
        "💳 请输入收款信息:\n"
        "<i>（USDT TRC-20 钱包、银行卡号等）</i>"
    )
    WITHDRAW_CONFIRM = (
        "📋 <b>确认您的请求:</b>\n\n"
        "💰 金额: <b>${amount}</b>\n"
        "💳 收款信息: <code>{requisites}</code>\n\n"
        "确认？"
    )
    BTN_CONFIRM_WITHDRAW = "✅ 确认"
    WITHDRAW_CREATED = (
        "✅ <b>提现申请已创建！</b>\n\n"
        "💰 金额: <b>${amount}</b>\n"
        "📋 状态: 等待审核\n\n"
        "管理员将尽快处理您的请求。"
    )
    WITHDRAW_HISTORY_TITLE = "📜 <b>提现记录</b>"
    WITHDRAW_HISTORY_EMPTY = "您还没有提现记录。"
    BTN_WITHDRAW_HISTORY = "📜 提现记录"
    WITHDRAW_STATUS_PENDING = "⏳ 等待中"
    WITHDRAW_STATUS_APPROVED = "✅ 已支付"
    WITHDRAW_STATUS_REJECTED = "❌ 已拒绝"

    # ── Daily Report ──
    DAILY_TITLE = "📬 <b>每日报告 — {date}</b>"
    DAILY_TODAY = "📅 今天"
    DAILY_WEEK = "📊 本周"
    DAILY_BOTS = "🤖 机器人"
    DAILY_TOTALS = "总计"

    # ── Referral ──
    REFERRAL_TITLE = "🔗 <b>推荐计划</b>"
    REFERRAL_YOUR_LINK = (
        "您的推荐链接：\n"
        "<code>{link}</code>\n\n"
        "邀请用户，从他们每次首次购买中获得奖励！\n\n"
        "📊 <b>比率：</b>\n"
        "• 第1级（直接）：<b>{l1}%</b>\n"
        "• 第2级：<b>{l2}%</b>\n"
        "• 第3级：<b>{l3}%</b>\n"
        "• 第4级：<b>{l4}%</b>"
    )
    BTN_COPY_LINK = "📋 复制链接"
    BTN_SHARE_LINK = "📤 分享链接"
    BTN_REFERRAL_STATS = "📊 我的统计"
    BTN_REFERRAL_HISTORY = "📜 收益记录"
    BTN_REFERRAL_WITHDRAW = "💸 提取奖励"
    BTN_REFERRAL_BACK = "◀️ 返回"

    REFERRAL_STATS_TITLE = "📊 <b>推荐统计</b>"
    REFERRAL_STATS_TEXT = (
        "👥 已邀请总数：<b>{invited}</b>\n"
        "✅ 已确认（首次购买）：<b>{confirmed}</b>\n"
        "💰 总收益（显示）：<b>${earned}</b>\n"
        "⏳ 审核中：<b>${pending}</b>"
    )

    REFERRAL_HISTORY_TITLE = "📜 <b>收益记录</b>"
    REFERRAL_HISTORY_EMPTY = "您暂无推荐收益记录。"
    REFERRAL_HISTORY_ROW = "• {date}  Lv.{level}  <b>+${amount}</b>  {status}"
    REFERRAL_STATUS_PENDING = "⏳ 审核中"
    REFERRAL_STATUS_APPROVED = "✅ 已批准"
    REFERRAL_STATUS_REJECTED = "❌ 已拒绝"
    REFERRAL_STATUS_PAID = "💸 已支付"

    REFERRAL_WITHDRAW_TITLE = "💸 <b>提取推荐奖励</b>"
    REFERRAL_WITHDRAW_BALANCE = "💰 可用余额：<b>${balance}</b>"
    REFERRAL_WITHDRAW_MIN = "最低金额：<b>${min}</b>"
    REFERRAL_WITHDRAW_NO_FUNDS = "❌ 余额不足。"
    REFERRAL_WITHDRAW_ENTER_AMOUNT = "请输入提取金额（美元）："
    REFERRAL_WITHDRAW_ENTER_REQUISITES = (
        "💳 请输入收款信息：\n"
        "<i>（BTC 地址、USDT TRC-20 等）</i>"
    )
    REFERRAL_WITHDRAW_BAD_AMOUNT = "❌ 无效金额（${min} 至 ${max}）。"
    REFERRAL_WITHDRAW_CONFIRM = (
        "📋 <b>确认提款：</b>\n\n"
        "💰 金额：<b>${amount}</b>\n"
        "💳 收款信息：<code>{requisites}</code>\n\n"
        "确认？"
    )
    BTN_CONFIRM_REFERRAL_WITHDRAW = "✅ 确认"
    REFERRAL_WITHDRAW_CREATED = (
        "✅ <b>申请已提交！</b>\n\n"
        "💰 金额：<b>${amount}</b>\n"
        "📋 状态：等待审核"
    )

    # ── Referral notifications ──
    NOTIF_NEW_REFERRAL = "🎉 <b>新推荐用户！</b>\n\n有用户通过您的链接注册了。"
    NOTIF_REFERRAL_PURCHASE = (
        "💰 <b>您的推荐用户完成了首次购买！</b>\n\n"
        "奖励 <b>${amount}</b>（第 {level} 级）已提交审核。"
    )
    NOTIF_REFERRAL_WITHDRAW_APPROVED = (
        "✅ <b>提款已批准！</b>\n\n"
        "💰 金额：<b>${amount}</b>\n"
        "资金将尽快转账。"
    )
    NOTIF_REFERRAL_WITHDRAW_REJECTED = (
        "❌ <b>提款已拒绝。</b>\n\n"
        "💰 金额：<b>${amount}</b>\n"
        "原因：{reason}"
    )
