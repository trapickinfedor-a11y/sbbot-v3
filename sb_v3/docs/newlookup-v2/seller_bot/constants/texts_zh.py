from seller_bot.constants.texts_en import BotTexts as EnglishBotTexts


class BotTexts(EnglishBotTexts):
    WELCOME_BACK = "👋 欢迎回来，<b>{name}</b>！\n\n🏦 卖家面板已准备就绪。\n📦 订单总数: {total_orders}\n💰 总收益: ${total_earned:.2f}"
    PENDING_APPROVAL = "⏳ <b>您的申请正在审核中。</b>\n\n请等待管理员审核。\n账号通过后您会收到通知。"
    START_NEW = "🏦 <b>Seller Bot</b>\n\n欢迎！该机器人可让您出售银行账户。\n\n发送 /register 提交卖家申请。\n管理员会审核您的申请。"
    ALREADY_REGISTERED = "✅ 您已经注册为卖家！"
    ALREADY_PENDING = "⏳ 您的申请已在审核中。"
    APPLICATION_SUBMITTED = "✅ <b>申请已提交！</b>\n\n您的卖家申请已发送给管理员。\n通过后您会收到通知。"
    MENU_TEXT = "🏦 <b>卖家面板</b>\n\n👤 {name}\n📦 订单: {total_orders}\n💰 收益: ${total_earned:.2f}"
    NO_SELLER_ACCESS = "❌ 您没有卖家权限。"
    NOT_AUTHORIZED = "❌ 未授权"
    WITHDRAW_INSUFFICIENT = "余额不足"
