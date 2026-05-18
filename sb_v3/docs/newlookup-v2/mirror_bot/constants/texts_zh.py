from __future__ import annotations

"""
中文文本 for Mirror Bot
"""

class BotTexts:
    
    # ========== 主要消息 ==========
    START_MESSAGE = """⚡ ONE PROJECT — 不仅仅是一个机器人，而是您进入 ONE 生态系统的门户。

🚀 功能：
🔹 24/7 工作 — 始终开启。始终连接。
🔹 即时访问 ONE HUB、ONE LOOKUP、ONE BANKS
🔹 在一个安全的仪表板中管理一切

🔐 安全。快速。智能。
🧩 一个系统 — 一个访问 — 一个控制。

💡 为新数字世界的创造者、操作者和建设者而构建。

🌍 选择您的语言继续 👇"""

    MAIN_MENU_TEXT = "🏠 主菜单"
    
    # ========== 个人资料 ==========
    PROFILE_TEXT = """👤 个人资料

🧩 您的 ID：{user_id}
💰 余额：{balance} USD
🕓 注册时间：{created_at}

🔗 推荐链接：{referral_link}
👥 推荐人数：{referrals_count}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
🌐 实际链接
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

    # ========== 支付 ==========
    TOPUP_STEP1 = """🪙 步骤 1 — 选择支付系统"""

    TOPUP_STEP2 = """💵 步骤 2 — 输入金额

💰 输入您希望充值的金额：
10 — 5000 USD

⚠️ 最低：$10 · 最高：$5000

发送付款后，系统将自动验证。"""

    TOPUP_STEP2_CRYPTOPAY = """💵 步骤 2 — 输入金额

💰 输入您希望充值的金额：
10 — 5000 USD

⚠️ 最低：$10 · 最高：$5000

🚨 注意！CryptoBot 是第三方支付服务！
在 CryptoBot 本身充值余额不会将资金存入我们这里。
在 CryptoBot 中充值后，您必须支付我们将创建的发票。

发送付款后，系统将自动验证。"""

    TOPUP_STEP3 = """🔗 步骤 3 — 支付链接

您的支付链接已生成。

点击下方完成交易："""

    TOPUP_STEP3_CRYPTOPAY = """🔗 步骤 3 — 支付链接

💰 金额: ${amount} USD

⚠️ 重要！CryptoBot 是第三方服务！
在 CryptoBot 中充值余额后，您必须使用下面的链接支付发票。
在您支付发票之前，资金不会到达您的余额！

ℹ️ 需支付处理费

📌 接受的加密货币:
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ 发票1小时后过期

点击下方完成交易："""

    TOPUP_SUCCESS = """✅ 余额成功充值 +{amount}$

💼 您的新余额已自动更新。

🔁 输入 /menu 返回主界面。

⚡ 感谢使用 ONE PROJECT — 您的智能自动化生态系统。"""

    TOPUP_SUCCESS_SHORT = "✅ 支付成功！${amount} 已添加到您的余额。"

    # 自动支付通知
    PAYMENT_AUTO_SUCCESS_TITLE = "✅ <b>支付成功收到！</b>\n\n"
    PAYMENT_AUTO_SUCCESS_AMOUNT = "💵 已入账：<b>${amount}</b>\n"
    PAYMENT_AUTO_SUCCESS_BALANCE = "💰 您的余额：<b>${balance}</b>\n\n"
    PAYMENT_AUTO_SUCCESS_THANKS = "感谢您的充值！🎉"
    
    PAYMENT_AUTO_EXPIRED_TITLE = "⏰ <b>支付时间已过期</b>\n\n"
    PAYMENT_AUTO_EXPIRED_AMOUNT = "<b>${amount}</b> 的支付已取消。\n"
    PAYMENT_AUTO_EXPIRED_CREATE_NEW = "如果您想充值余额，请创建新的支付。"

    TOPUP_EXPIRED = """❌ 您的支付会话已过期或失败。

请创建新的支付链接，或如果资金已发送但未到账，请联系客服。

🧠 客服 → 创建工单"""

    TOPUP_INVALID_AMOUNT = """❌ 无效金额

⚠️ 最低：$10 · 最高：$5000

请输入有效金额："""

    # ========== 支付消息 ==========
    PAYMENT_SYSTEM_NOT_CONFIGURED = "❌ 支付系统未配置"
    PAYMENT_ERROR_CREATING = "❌ 创建支付错误：{error}"
    PAYMENT_SYSTEM_NOT_CONFIGURED_ALERT = "❌ 支付系统未配置"
    PAYMENT_INVOICE_NOT_FOUND = "❌ 未找到发票"
    PAYMENT_CONFIRMED = "✅ 支付已确认！"
    PAYMENT_CONFIRMED_TEXT = """✅ **支付已确认！**

金额：**${amount} {asset}**
发票 ID：`{invoice_id}`
支付时间：{paid_at}"""
    PAYMENT_EXPIRED = "❌ 发票已过期"
    PAYMENT_WAITING = "⏳ 等待支付中..."
    PAYMENT_CHECK_ERROR = "❌ 检查支付错误"
    PAYMENT_CANCELLED_SUCCESS = "✅ 支付已取消"
    PAYMENT_CANCELLED_TEXT = "❌ **支付已取消**"
    PAYMENT_CANCEL_FAILED = "❌ 无法取消支付"
    PAYMENT_CANCEL_ERROR = "❌ 取消支付错误"
    
    CRYPTOPAY_PAYMENT_FORMAT = """🪙 **{description}**
**通过 CryptoBot 支付**

**余额金额：** ${balance_amount:.2f} USD
**平台手续费 ({fee_percent}%)：** +${fee_amount:.2f} USD
━━━━━━━━━━━━━━━━━━━━━━
**总支付金额：** ${total_amount:.2f} USD

ℹ️ *支付处理费：{fee_percent}%*

📌 **接受的加密货币：**
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ 发票 1 小时内有效
🆔 发票 ID：`{invoice_id}`"""

    CRYPTOMUS_PAYMENT_FORMAT = """💎 **{description}**
**通过 Cryptomus 支付**

**余额金额：** ${balance_amount:.2f} USD
**平台手续费 ({fee_percent}%)：** +${fee_amount:.2f} USD
━━━━━━━━━━━━━━━━━━━━━━
**总支付金额：** ${total_amount:.2f} USD

ℹ️ *支付处理费：{fee_percent}%*

📌 **接受的加密货币：**
   • USDT (TRC20/ERC20/BEP20)
   • BTC, ETH, TON
   • LTC, TRX, USDC
   • 等等...

⏱ 发票 1 小时内有效
🆔 订单 ID：`{order_id}`
🔖 支付 UUID：`{uuid}`"""

    # ========== 转账 ==========
    SEND_MONEY_TEXT = """💸 向其他用户转账

输入接收者用户 ID："""

    SEND_MONEY_AMOUNT = """💰 输入转账金额：

您的余额：{balance} USD"""
    
    SEND_MONEY_AMOUNT_SHORT = "💰 输入转账金额:\n\n您的余额: ${balance}"

    SEND_MONEY_SUCCESS = """✅ 成功向用户 {user_id} 发送 ${amount}

💰 您的新余额：${balance}"""
    
    SEND_MONEY_SUCCESS_SHORT = "✅ 转账成功!\n\n💸 已发送: ${amount}\n👤 用户 ID: {recipient_id}\n💰 您的余额: ${balance}"
    
    SEND_MONEY_CONFIRM = "📝 **确认转账**\n\n💸 金额: ${amount}\n👤 收款人ID: {recipient_id}\n\n💰 转账后余额: ${balance_after}\n\n确认转账?"

    SEND_MONEY_INSUFFICIENT = """❌ 余额不足

💰 您的余额：${balance}
💳 需要：${amount}"""
    
    SEND_MONEY_INSUFFICIENT_SHORT = "❌ 余额不足!\n\n您的余额: ${balance}\n请求: ${amount}"
    
    LANGUAGE_CHANGED = "✅ 语言已更改为 {language}"
    MAIN_MENU_WITH_CHECKMARK = "✅ {menu_text}"

    # ========== 推荐系统 ==========
    REFERRAL_SYSTEM = """🤝 推荐计划 — 最高 +25%

🔗 您的推荐链接：
{referral_link}

📊 4级系统：
1️⃣ 第1级 — 10%
2️⃣ 第2级 — 7%
3️⃣ 第3级 — 5%
4️⃣ 第4级 — 3%

👥 总推荐数：{count}
💵 总收入：${earned} USD

💰 您链中的每笔购买都会自动为您带来奖金！"""

    # ========== 订单 ==========
    ORDER_CONFIRMATION = """✅ 订单确认

服务：{service_name}
💰 价格：${price}

📝 您的数据已验证！

确认订单？"""

    ORDER_CREATED = """✅ **订单创建成功！**

🎲 **{product}**
💵 **价格：** ${price:.2f}
⏱ **ETA：** {eta}
💳 **余额：** ${balance:.2f}

您的订单已发送至支持团队进行处理。"""
    
    ORDER_CREATED_DISCOUNT_SAVINGS = "\n💰 **批量折扣 (-{discount_percent}%)：** ${savings:.2f}"

    ORDER_COMPLETED = """✅ 订单 #{order_id} 已完成！

服务：{service_name}

{result_text}

💰 您的余额：${balance}

输入 /menu 返回主菜单。"""

    BULK_ORDER_RESULT = """✅ 批量订单 #{order_id} 已完成！

服务：{service_name}

{items_text}

💰 未找到项目的退款：+${refund}
💰 您的余额：${balance}

输入 /menu 返回主菜单。"""

    # ========== 验证 ==========
    INVALID_DATA = """❌ 数据格式无效

{error_message}

📝 示例：
{example}"""

    INSUFFICIENT_BALANCE = """❌ 余额不足

💰 您的余额：${balance}
💳 需要：${price}

请充值余额以继续。"""

    # ========== 其他 ==========
    RULES_TEXT = """📜 **用户政策 / 服务条款**

⚖️ **1. 总则**
• 机器人仅提供信息、分析和技术服务  
• 服务不是银行、金融机构、信用局或政府机构  
• 使用机器人即表示您确认您已年满18岁并遵守您所在国家/地区的法律  
• 在某些禁止此类服务的司法管辖区，服务可能不可用或受限  

🔐 **2. 数据与隐私**
• 您仅提交您有合法权利处理的数据（您自己的数据、经所有者同意提交的数据、根据合同、法律等）  
• 禁止违反隐私和数据保护法提交第三方的个人数据  
• 所有数据都是自动处理的，仅用于完成您的请求  
• 服务不承诺存储结果，处理后可能自动删除数据  
• 除法律要求外，我们不与第三方共享您的数据  

🚫 **3. 禁止使用**
严格禁止将服务用于：  
• 欺诈、欺骗、金融计划、洗钱或任何其他非法活动  
• 未经授权访问第三方的账户、设备、数据库或系统  
• 在没有法律依据的情况下收集、泄露、发布或出售个人数据（人肉搜索或类似活动）  
• 规避银行、支付系统、政府机构或监管机构的要求  
• 骚扰、勒索、敲诈、威胁、施压或歧视任何人  
• 任何违反您所在国家/地区法律或适用于您的法律的行为  

👤 **4. 用户责任**
• 您完全无条件地承担**如何以及出于何种目的**使用通过机器人获得的信息和结果的责任  
• 服务管理层实际上无法验证您的意图，也不控制您对法律的遵守  
• 与使用服务相关的所有风险（法律、财务、声誉等）由用户承担  
• 如果怀疑违反规则或法律，服务可能会限制、冻结或阻止访问，无需解释且不予补偿  

📎 **5. 责任限制**
• 所有信息和结果均按"原样"提供，仅用于信息/技术目的  
• 服务不提供法律、财务、税务或任何其他专业建议  
• 管理层对因使用或无法使用服务而产生的任何直接或间接损失不承担责任  
• 服务可能随时更改功能、规则和条件，无需事先通知用户  

🧾 **6. 本政策的变更**
• 本用户政策可能会不时更新和补充  
• 在进行更改后继续使用机器人，即表示您确认同意更新版本的政策  
• 当前版本的政策始终是使用时在机器人中显示的版本  

✅ **7. 接受政策**
• 启动并继续使用机器人，即表示您确认：
  – 已仔细阅读本政策和服务规则；  
  – 完全理解其内容；  
  – 自愿且有意识地同意它们；  
  – 承担使用服务的全部责任。  

• 如果您**不同意**本政策的任何部分，您必须立即停止使用机器人和服务。  

**服务不鼓励或支持任何非法活动。  
遵守法律的所有责任由用户承担。**"""

    CALL_SERVICE_TEXT = """📦 *延迟 / 订单问题*

*我们解决的任务示例：*
• 澄清卡在海关的包裹状态
• 下单后更改配送地址
• 解决与商店有关丢失或损坏物品的纠纷
• 移除被错误阻止的订单的"保留"

✅ *为了正确处理您的请求，我们需要：*
• Tracking Number: (追踪号码)
• Shop Name: (商店名称)
• Full Name, Shipping Address, and Phone Number: (全名、配送地址和电话号码)
📞 *联系支持：* @one1caller

💳 *PayPal*

*我们解决的任务示例：*
• 将新的银行账户或卡链接到您的账户
• 移除限制并完成账户验证
• 恢复对被阻止账户的访问

✅ *为了正确处理您的请求，请提供：*
• Personal Data: 姓名、地址、SSN、出生日期
• Email Access: 关联的电子邮件（您能接收电子邮件吗？）
• Phone Access: 伪装号码（您能接收短信吗？）
• Linked Accounts/Cards: 银行名称、账户/卡类型、后4位数字
• Background Report (BG): 链接账户可能需要
• Task Description: 详细说明需要做什么
📞 *联系支持：* @one1caller

📞 *电话订购*

*我们解决的任务示例：*
• 购买仅通过电话提供的限量商品
• 使用特定折扣或条件下订单

✅ *为了正确处理您的请求，我们需要以下信息：*
• Contact for Call: 商店号码（打给谁）和伪装号码
• Addresses: 姓名 + 账单地址，姓名 + 配送地址
• Order Details: 商品链接、数量、颜色、尺寸等
• Gift Cards: 对于 E-gift — 类型、金额、收件人姓名和电子邮件
• Payment Details: 完整的卡详细信息
📞 *联系支持：* @one1caller

🏦 *银行电话 / 贷款*

*我们解决的任务示例：*
• 在登录尝试失败后解除在线访问
• 验证大额转账（电汇）
• 重置信用卡数据（CC重置）

⚠️ *重要：每家银行都是独特的。您提供的信息越多，效果越好。*

✅ *为了正确处理您的请求，我们需要：*
• Situation Description: 详细描述发生了什么
• Contact for Call: 银行号码和伪装号码（您能接收短信吗？）
• Personal Data: 全名、SSN、出生日期、地址（带县）
• Access Details: 电子邮件（您能接收电子邮件吗？）、MMN、DL、EIN（商业用）
• Secret Data: 完整的账户/卡号、登录、口头密码、PIN、安全问答
• History: 最近3-5笔交易（截图或文本）
• Documents: BG（背景调查）、CR（信用报告）— 如果有
📞 *联系支持：* @one1caller

💼 *商户电话*

*我们解决的任务示例：*
• 设置商户账户和集成支付系统
• 讨论合同条款和支付操作

✅ *为了正确处理您的请求，我们需要：*
• Contact for Call: 商户号码和呼叫号码（可以接收短信吗？）
• Personal Information: 姓名、SSN、出生日期、地址、职位
• Email Access: 电子邮件地址（可以访问电子邮件吗？）
• Company Details: 名称、网站、EIN
• 业务描述和财务信息
• 账户注册详细信息和服务付款信息

📞 *联系支持：* @one1caller"""

    BACK_TO_MAIN = "⬅️ 返回主菜单"

    # ========== 错误消息 ==========
    ERROR_INVALID_DATA_FORMAT = "❌ 错误：数据格式无效"
    ORDER_CREATED_ALERT = "✅ 订单已创建！"
    ERROR_GENERAL = "❌ 错误"
    TRY_ANOTHER_STATE = "请尝试其他州或稍后再查看。"
    PLEASE_TOPUP_BALANCE = "请充值余额以继续。"
    PLEASE_CONTACT_SUPPORT = "请联系客服。"
    FILE_ERROR_TITLE = "文件错误"
    FILE_DELIVERY_FAILED = "无法交付文件"
    USER_NOT_FOUND = "❌ 用户未找到。请 /start"
    INVALID_PAYMENT_METHOD = "❌ 无效的支付方式。请重新从 /profile 开始"
    INVALID_USER_ID = "❌ 无效的用户 ID。请输入数字。"
    RECIPIENT_NOT_FOUND = "❌ 收款人未找到。ID为 {recipient_id} 的用户不存在于系统中。"
    USER_NOT_FOUND_CONTACT_SUPPORT = "❌ 用户未找到。请联系客服。"
    INVALID_AMOUNT_NUMBER = "❌ 无效金额。请输入数字。"
    ERROR_CREATING_PAYMENT = "❌ 创建支付时出错：{error}\n\n请重试或联系客服。"
    PAYMENT_SUCCESSFUL = "✅ 支付成功！"
    PAYMENT_NOT_RECEIVED = "⏳ 尚未收到付款..."
    ERROR_CHANGING_LANGUAGE = "❌ 更改语言时出错"
    PLEASE_START_AGAIN = "⚠️ 请重新开始流程"

    # ========== 验证错误 ==========
    MINIMUM_ENTRIES_REQUIRED = "❌ 至少需要 {min_items} 个条目"
    MAXIMUM_ENTRIES_ALLOWED = "❌ 最多允许 {max_items} 个条目"
    ENTRY_EMPTY_DATA = "❌ 条目 #{entry}：空数据"
    ERROR_PROCESSING_BULK = "❌ 处理批量条目时出错：\n{error}"
    ORDER_CANCELLED = "❌ 订单已取消"

    # ========== 文档 ==========
    DOCUMENTS_MAIN = "选择类别："
    DOCUMENT_EXAMPLE_FORMAT = "张;三\n北京市朝阳区;北京;{state};90210\n01/15/1990"
    DOCUMENT_INVALID_DATA = "❌ 数据格式无效\n\n{issues_text}\n\n📝 示例:\n{example}"
    DOCUMENT_VALIDATION_ERROR = "❌ 数据无效:\n\n{errors}\n\n📝 示例:\n{example}"
    DOCUMENT_UNKNOWN_TYPE = "未知文档类型"
    PHOTO_CATALOG_HEADER = "📸 照片目录\n\n选择文档类型："
    SELECT_STATE = "选择州："
    HIGH_QUALITY_DRAWING_COMING_SOON = "🧑‍🎨 高质量绘图\n\n🚧 即将推出...\n\n请联系客服进行定制订单。"
    ROBOT_DRAWING_COMING_SOON = "🤖 机器人绘图 — 即将推出！"
    
    # ========== 查询服务 ==========
    ESIM_MAIN = "📶 eSIM\n\n选择类型："
    ESIM_SMS_SELECT_OPERATOR = "🇺🇸 eSIM 短信\n\n选择运营商："
    ESIM_DATA_SELECT_OPERATOR = "📶 eSIM 数据\n\n选择运营商："
    ESIM_SMS_SELECT_PERIOD = "📶 {operator} — 短信\n\n选择期间："
    ESIM_DATA_SELECT_PLAN = "📶 {operator} — 数据\n\n选择数据套餐："
    ESIM_SMS_ORDER_DETAILS = """📶 eSIM 订单

🇺🇸 类型：短信
📶 运营商：{operator}
⏳ 期间：{period} 个月
💵 单价：${price}
🕒 交付：5-10 分钟（自动）

选择数量或购买 1 件："""
    ESIM_DATA_ORDER_DETAILS = """📶 eSIM 订单

📶 类型：数据
📶 运营商：{operator}
📦 数据：{gb} GB
💵 单价：${price}
🕒 交付：5-10 分钟（自动）

选择数量或购买 1 件："""
    ESIM_GV_SELECT = "📞 Google Voice\n\n选择产品："
    
    # ========== 账户 ==========
    ACCOUNTS_MAIN = "🧾 订阅 / 账户\n\n选择类别："
    
    # ========== 添加信息 ==========
    ADDINFO_MAIN = "✍️ 在 CR 中添加信息\n\n选择类别："
    
    # Add Info service formats
    ADDINFO_TU_FORMAT = "✍️ 在 TU 中添加信息 — ${price}\n⏱ ETA: 10-24 小时\n📖 说明: [添加信息 TU](https://t.me/ONE_TUTORIAL/78)\n\n📝 输入数据:\n\n{example}"
    ADDINFO_EX_FORMAT = "✍️ 在 EX 中添加信息 — ${price}\n⏱ ETA: 48-72 小时\n📖 说明: [添加信息 EX](https://t.me/ONE_TUTORIAL/79)\n\n📝 输入数据:\n\n{example}"
    ADDINFO_ALL_FORMAT = "✍️ 在所有中添加信息 — ${price}\n⏱ ETA: 4-48 小时\n📖 说明: [添加信息全部](https://t.me/ONE_TUTORIAL/80)\n\n📝 输入数据:\n\n{example}"
    ADDINFO_BG_FORMAT = "✍️ 在 BG 中添加信息 — ${price}\n⏱ ETA: 48-72 小时\n📖 说明: [添加信息 BG](https://t.me/ONE_TUTORIAL/81)\n\n📝 输入数据:\n\n{example}"
    UNFREEZE_TU_FORMAT = "🔓 解冻 TU — ${price}\n⏱ ETA: 10-24 小时\n📖 说明: [解冻 TU](https://t.me/ONE_TUTORIAL/82)\n\n📝 输入数据:\n\n{example}"
    UNFREEZE_EX_FORMAT = "🔓 解冻 EX — ${price}\n⏱ ETA: 48-72 小时\n📖 说明: [解冻 EX](https://t.me/ONE_TUTORIAL/83)\n\n📝 输入数据:\n\n{example}"
    ADD_EMPLOYER_FORMAT = "🏢 添加雇主 — ${price}\n⏱ ETA: 10-24 小时\n📖 说明: [添加雇主](https://t.me/ONE_TUTORIAL/84)\n\n📝 输入数据:\n\n{example}"
    
    # ========== FULLZ ==========
    FULLZ_MAIN = "🧰 PROS & FULLZ\n\n选择类型："
    FULLZ_PERSONAL_PROFILES = "👤 个人 FULLZ\n\n选择配置文件："
    FULLZ_BUSINESS_MAIN = "🏢 商业 FULLZ\n\n选择州："
    FULLZ_BUSINESS_SELECT_STATE = "🏢 商业 FULLZ\n\n选择州："
    FULLZ_PROFILE_SELECT_STATE = "📍 配置文件：{profile}\n\n选择州："
    FULLZ_SELECT_STATE = "📍 选择州："
    
    # Business FULLZ specific texts
    FULLZ_STATE_SELECT_COMPANY = "📍 州：{state}\n🏢 选择公司类型："
    FULLZ_COMPANY_SELECT_LOAN = "🏢 公司类型：{company_type}\n💰 选择贷款规模："
    FULLZ_CS_SELECT_REPORT = "💳 信用评分：{cs}\n📑 选择报告组："
    FULLZ_SELECT_AGE = "🎂 选择年龄组："
    FULLZ_LOAN_SELECT_CS = "💰 收入：{loan_size}\n💳 选择信用评分:"
    FULLZ_SELECT_GENDER = "👥 选择性别："
    FULLZ_SELECT_CARRIER_EXCLUSION = "📱 **排除运营商**\n\n排除特定运营商？需额外付费。"
    FULLZ_SELECT_BANK_EXCLUSION = "🏦 **排除银行**\n\n排除特定银行？需额外付费。"
    FULLZ_SELECT_REPORT_GROUP = "📑 选择报告组："
    FULLZ_COMPANY_SELECT_CEO_CS = "🏢 公司类型：{company_type}\n💳 选择CEO信用评分："
    FULLZ_CEO_CS_SELECT_LOAN = "💳 CEO信用评分：{ceo_cs}\n💰 选择贷款规模："
    FULLZ_REPORT_SELECT_QUANTITY = "📑 报告组：{report}\n🔢 选择数量："
    FULLZ_SELECT_QUANTITY = "🔢 选择数量："
    FULLZ_STATE_SELECT_CS = "📍 州：{state}\n\n选择信用评分："
    
    # FULLZ Order Summary
    FULLZ_BUSINESS_ORDER_TITLE = "🧾 **商业FULLZ订单**"
    FULLZ_PERSONAL_ORDER_TITLE = "📋 **个人FULLZ订单**"
    FULLZ_ORDER_QUANTITY = "📊 **数量：**"
    FULLZ_ORDER_STATE = "📍 **州：**"
    FULLZ_ORDER_COMPANY_TYPE = "🏢 **公司类型：**"
    FULLZ_ORDER_LOAN_SIZE = "💰 **贷款规模：**"
    FULLZ_ORDER_CREDIT_SCORE = "💳 **信用评分：**"
    FULLZ_ORDER_AGE = "🎂 **年龄：**"
    FULLZ_ORDER_GENDER = "👥 **性别：**"
    FULLZ_ORDER_REPORT_GROUP = "📑 **报告组：**"
    FULLZ_ORDER_TOTAL_COST = "💵 **总费用：**"
    FULLZ_ORDER_CURRENT_BALANCE = "💳 **当前余额：**"
    FULLZ_ORDER_NEW_BALANCE = "📊 **新余额：**"
    FULLZ_ORDER_DISCOUNT = "🎁 折扣："
    FULLZ_ORDER_DISCOUNT_SAVE = "节省"
    
    FULLZ_RANDOM_ORDER_CREATED = """✅ 订单创建成功！

🎲 **随机个人 FULLZ**
💰 **价格：** ${price}
⏱ **ETA：** {eta}
💳 **余额：** ${balance}

您的订单已发送给支持团队处理。"""

    # FULLZ Support info
    FULLZ_SUPPORT_INFO = """📞 **FULLZ 支持**

在这里您可以订购需要个别处理的专业fullz：

🎖️ **军事 Fullz** — 军事人员数据
✈️ **Work & Travel** — 工作签证资料
🧒 **年轻 Fullz** — 25岁以下资料

如需这些及其他定制请求，请直接联系我们的卖家：

👤 **联系方式：** @fullz_support_seller

⏱ **处理时间：** 12-48小时
💬 在聊天中描述您的需求，卖家将提供报价。"""

    ORDER_CREATION_ERROR = "❌ 创建订单时出错。请重试。"
    
    # ========== 支付按钮 ==========
    OPEN_PAYMENT_LINK = "💳 打开支付链接"
    REFRESH_STATUS = "♻️ 刷新状态"
    CHECK_STATUS = "♻️ 检查状态"
    PAY_INVOICE = "💳 支付发票"
    PAY_WITH_CRYPTO = "💳 使用加密货币支付"
    
    # ========== 语言按钮 ==========
    LANG_RUSSIAN = "🇷🇺 俄语"
    LANG_ENGLISH = "🇬🇧 英语"
    LANG_CHINESE = "🇨🇳 中文"
    
    # ========== 系统消息 ==========
    LANGUAGE_SAVED = "✅ 语言已保存！"
    USER_NOT_FOUND_ALERT = "❌ 用户未找到"
    
    # ========== 错误消息 ==========
    ITEM_NOT_FOUND = "❌ 项目未找到"
    INSUFFICIENT_BALANCE_ALERT = "❌ 余额不足"
    INSUFFICIENT_BALANCE_DETAILED = "❌ 余额不足\n需要：${required}\n您的余额：${balance}"
    INVALID_QUANTITY = "❌ 无效数量。请输入 1-100。"
    INVALID_FORMAT_NUMBER = "❌ 格式无效。请输入数字 (1-100)。"
    PLEASE_ENTER_DATA = "❌ 请输入数据\n\n📝 示例：\n{example}"
    INVALID_DATA_FORMAT = "❌ 数据格式无效\n\n{issues_text}\n\n📝 示例：\n{example}"
    VALIDATION_ERROR = "❌ 验证错误\n\n{errors}\n\n📝 示例：\n{example}"
    MIN_ENTRIES_REQUIRED = "❌ 至少需要 {min_items} 个条目"
    MAX_ENTRIES_ALLOWED = "❌ 最多允许 {max_items} 个条目"
    EMPTY_DATA_ENTRY = "❌ 条目 #{entry_num}：空数据"
    ENTRY_ISSUES = "❌ 条目 #{entry_num}：\n{issues_text}"
    ENTRY_VALIDATION_ERROR = "❌ 条目 #{entry_num}：{error_msg}"
    BULK_PROCESSING_ERROR = "❌ 批量处理条目时出错：\n{error}"
    
    # ========== EXAMPLE FORMAT TEXTS ==========
    EXAMPLE_FORMATS_LABEL = "📝 格式示例："
    REQUIRED_LABEL = "💡 必填："
    OPTIONAL_LABEL = "💡 可选："
    ANY_FORMAT_WORKS = "✅ 任何格式都可以"
    DOB_OPTIONAL = "💡 出生日期可选"
    NO_VALIDATION = "无验证"
    BUSINESS_NAME_REQUIRED = "💡 需要公司名称"
    BULK_ENTRY_SEPARATOR = "📦 输入2-20条记录 — 记录之间留空行："
    LEAVE_EMPTY_LINE = "📦 每条记录之间留**一个空行**。"
    CAN_SEND_ENTRIES = "➡️ 您可以在一条消息中发送2到20条记录。"
    NAME_ADDRESS_DOB_REQUIRED = "姓名、地址、出生日期"
    
    # ========== 成功消息 ==========
    ORDER_CREATED_SUCCESS = "✅ 订单已创建！"
    ENTRIES_VALIDATED = "✅ {count} 个条目已验证！\n\n"
    
    # ========== 确认消息 ==========
    BULK_TOTAL_CONFIRM = "💰 总计：${price}\n\n确认？"
    ENTER_DATA_MMN = "📝 输入数据：\n\n{example}"
    ENTER_DATA_EIN = "📝 输入数据：\n\n{example}"
    
    # ========== 通用服务消息 ==========
    SERVICE_BULK_ORDER_HEADER = "📝 {service_name} — 批量订单"
    SERVICE_PRICE_PER_ENTRY = "💰 每条价格: ${price}"
    YOUR_DATA_LABEL = "📄 **您的数据:**"
    DATA_RECEIVED_LABEL = "📄 数据已接收:"
    PLEASE_ENTER_YOUR_DATA = "📝 请输入您的数据:"
    NO_VALIDATION_NOTE = "⚠️ 无验证 - 以任何格式发送"
    EXAMPLE_LABEL = "💡 示例:"
    PRICE_LABEL = "💵 价格:"
    PROCESSING_LABEL = "🕒 处理:"
    MANUAL_PROCESSING = "手动（支持团队）"
    NOTE_LABEL = "📝 注意:"
    REQUIRED_FIELDS_NOTE = "需要：姓名、地址、SSN、DOB（无验证）"
    STATUS_AVAILABLE = "✅ 状态: 可用"
    PAYMENT_CONFIRMATION_NOTE = "付款确认后，我们的团队将处理您的请求。"
    PRESS_BUY_NOW = "按立即购买继续:"
    SELECT_A_SERVICE = "选择服务:"
    SELECT_A_PRODUCT_NOTE = "选择产品查看详情并购买"
    CLICK_BUY_NOW_NOTE = "点击'立即购买'购买此产品"
    TAP_TOPUP_TO_ADD_FUNDS = "点击 /topup 充值"
    CHOOSE_YOUR_LANGUAGE = "🌍 Choose your language / Выберите язык / 选择语言 / Elige idioma:"
    
    # ========== 产品 ==========
    AVAILABLE_PRODUCTS = "🛍️ **可用产品**"
    CATEGORY_LABEL = "📂 **类别:**"
    STATE_LABEL = "🏛️ **州:**"
    TOTAL_LABEL = "📦 **总计:**"
    PRODUCTS_COUNT = "{total} 个产品"
    PRODUCT_LABEL = "📦 **产品:**"
    PAID_LABEL = "💰 **已支付:**"
    NEW_BALANCE_LABEL = "💳 **新余额:**"
    FILE_WILL_BE_DELETED = "⚠️ *文件将在1小时后删除以确保安全*"
    PURCHASE_SUCCESSFUL = "✅ **购买成功!**"
    PURCHASE_COMPLETED = "✅ **购买完成!**"
    FILE_HAS_BEEN_SENT = "📁 **文件已发送给您!**"
    PURCHASE_SUCCESSFUL_SHORT = "购买成功! ✅"
    INSUFFICIENT_BALANCE_CAPS = "❌ **余额不足**"
    REQUIRED_LABEL_CAPS = "💰 **需要:**"
    YOUR_BALANCE_LABEL = "💳 **您的余额:**"
    NEED_LABEL = "💸 **需要:**"
    PURCHASE_FAILED = "❌ **购买失败**"
    FILE_DELIVERY_FAILED_SHORT = "❌ **文件传送失败:**"
    FILE_NOT_FOUND_SERVER = "服务器上未找到文件"
    
    # ========== 产品按钮 ==========
    BUY_NOW_BUTTON = "💰 立即购买"
    BACK_TO_LIST_BUTTON = "🔙 返回列表"
    BACK_TO_STATES_BUTTON = "🔙 返回州列表"
    FILE_TYPE_LABEL = "**文件类型:**"
    DESCRIPTION_LABEL = "📝 **描述:**"
    YOUR_ORDER_READY = "✅ **您的订单{order_text}已准备好!**"
    YOUR_FILE_ATTACHED_BELOW = "📎 您的文件已附在下方:"
    VALIDATION_ERROR_SHORT = "❌ 验证错误:"
    TOTAL_WITH_CONFIRM = "💰 总计: ${total}\n\n确认?"
    CONFIRM_PURCHASE_QUESTION = "确认购买?"
    NO_PRODUCTS_AVAILABLE = "❌ **没有可用产品**"
    INVALID_DATA_FORMAT_SHORT = "❌ 数据格式无效"
    ERROR_LOADING_PRODUCTS = "❌ 加载产品时出错"
    ERROR_LOADING_PAGE = "❌ 加载页面时出错"
    ERROR_LOADING_PRODUCT = "❌ 加载产品时出错"
    ERROR_PROCESSING_PURCHASE = "❌ 处理购买时出错"
    ERROR_LOADING_STATES = "加载州列表时出错"
    PRODUCT_NOT_FOUND = "❌ 未找到产品"
    PURCHASE_FAILED_SHORT = "❌ 购买失败"
    PURCHASE_PINNED = "📌 订单 #{order_id} 数据已固定在聊天中。"
    PURCHASE_ARCHIVED = "📢 数据也已发送到你的归档频道。"
    PURCHASE_HISTORY_TITLE = "📦 我的购买"
    PURCHASE_HISTORY_EMPTY = "你还没有任何购买记录。"
    PURCHASE_HISTORY_FILTER_CATEGORY = "🗂 按类别"
    PURCHASE_HISTORY_FILTER_SELLER = "👨‍💼 按卖家"
    PURCHASE_HISTORY_DETAILS = "详情"
    PURCHASE_HISTORY_SELECT_CATEGORY = "选择类别过滤："
    PURCHASE_HISTORY_SELECT_SELLER = "选择卖家过滤："
    HISTORY_FILTER_ALL = "📋 所有类别"
    ARCHIVE_SETUP_INSTRUCTIONS = "📁 归档设置\n\n1. 创建一个私有频道。\n2. 将此机器人添加为管理员。\n3. 将该频道中的任意消息转发到这里。"
    ARCHIVE_SETUP_SUCCESS = "✅ 归档频道连接成功。"
    ARCHIVE_SETUP_INVALID = "❌ 请转发一条来自频道的消息，以便我保存频道 ID。"
    ARCHIVE_SETUP_BOT_NOT_ADMIN = "❌ 请先把此机器人设为频道管理员，然后再试。"
    PHONE_EXAMPLE_FORMAT = "示例: +1 (320) 932-0202 或 3209320202"
    INVALID_DATA_FORMAT_WITH_EXAMPLE = "❌ 数据格式无效\n\n{issues_text}\n\n📝 示例:\n{example}"
    
    # ========== FALLBACK ==========
    PLEASE_START_PROCESS_AGAIN = "⚠️ 请重新开始流程"
    UNHANDLED_ACTION = "⚠️"
    VIOLATION_OF_SERVICE_RULES = "违反服务规则"

    RULES_ACCEPT_PROMPT = "📜 使用服务前请阅读并接受规则："
    RULES_ACCEPTED_SUCCESS = "✅ 规则已接受！欢迎使用服务。"
    RULES_DECLINED_MESSAGE = "❌ 您必须接受规则才能使用服务。发送 /start 重试。"
    
    # DL 示例
    DL_SINGLE_EXAMPLE = """📝 示例格式:
张三\n北京市朝阳区街道123号, 北京, 北京市, 90210\n 01/15/1990

💡 必需: 姓名、地址、出生日期 | ✅ 任何格式都可以"""

    DL_BULK_EXAMPLE = """📦 输入2-20条记录 — 记录之间留空行:

张三
北京市朝阳区街道123号 北京 北京市 90210  
01/15/1990

李四
上海市浦东新区街道456号
上海 上海市 90001
01/15/1990

王五  
广州市天河区街道789号 广州 广东省 60601  
01/15/1990

💡 必需: 姓名、地址、出生日期 | ✅ 任何格式都可以
📦 每条记录之间留**一个空行**。
➡️ 您可以在一条消息中发送2到20条记录。"""

    # Background 示例
    BG_SINGLE_EXAMPLE = """📝 示例格式:
张三\n北京市朝阳区街道123号, 北京, 北京市, 90210

💡 DOB可选 | ✅ 任何格式都可以"""

    BG_BULK_EXAMPLE = """📦 输入2-20条记录 — 记录之间留空行:

示例 1:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001  

示例 2:
北京市朝阳区街道123号, 
北京, 
北京市 
90001

示例 3:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001
04/05/1995 apr 5,1995 04-05-1996

📦 **每条记录之间留一个空行**。
➡️ DOB（出生日期）可选。  
➡️ 您可以在一条消息中发送2到20条记录。"""

    # MMN 示例
    MMN_SINGLE_EXAMPLE = """📝 示例格式:
张三\n北京市朝阳区街道123号, 北京, 北京市, 90210

💡 DOB可选 | ✅ 任何格式都可以"""

    MMN_BULK_EXAMPLE = """📦 输入2-20条记录 — 记录之间留空行:

示例 1:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001  

示例 2:
北京市朝阳区街道123号, 
北京, 
北京市 
90001

示例 3:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001
04/05/1995 apr 5,1995 04-05-1996

📦 每条记录之间留**一个空行**。
➡️ DOB（出生日期）可选。  
➡️ 您可以在一条消息中发送2到20条记录。"""

    # EIN 示例
    EIN_SINGLE_EXAMPLE = """(Kellington Protection Service, LLC)\n公司名称/ DBA名称\n北京市朝阳区街道123号, 北京, 北京市 90001

📝 以任何格式发送任何数据
💡 所有信息将按原样接受"""

    EIN_BULK_EXAMPLE = """(Kellington Protection Service, LLC)\n公司名称/ DBA名称\n北京市朝阳区街道123号, 北京, 北京市 90001

📦 输入2-20条记录 — 记录之间留空行

📝 以任何格式发送任何数据
💡 所有信息将按原样接受

📦 每条记录之间留**一个空行**。
➡️ 您可以在一条消息中发送2到20条记录。"""

    # MVR 示例
    MVR_SINGLE_EXAMPLE = """张三\n北京市朝阳区街道123号, 北京, 北京市 90001\n04-05-1995 000-00-0000\n驾照号码; 签发州\n✅ 无需验证

📝 以任何格式发送任何数据
💡 所有信息将按原样接受"""

    MVR_BULK_EXAMPLE = """
示例 1:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001  
04-05-1995
000-00-0000
驾照号码; 签发州 

示例 2:
北京市朝阳区街道123号, 
北京, 
北京市 
90001
apr 5,1995
000000000
驾照号码; 签发州 

示例 3:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001
04/05/1995
000-00-0000
驾照号码; 签发州 \n✅ 无需验证

📦 输入2-20条记录 — 记录之间留空行

📝 以任何格式发送任何数据
💡 所有信息将按原样接受

📦 每条记录之间留**一个空行**。
➡️ 您可以在一条消息中发送2到20条记录。"""

    # CS 示例
    CS_SINGLE_EXAMPLE = """📝 示例格式:
张三\n北京市朝阳区街道123号, 北京, 北京市, 90210\n12/03/1998(如果有)

💡 DOB可选 | ✅ 任何格式都可以"""

    CS_BULK_EXAMPLE = """📦 输入2-20条记录 — 记录之间留空行:

示例 1:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001  

示例 2:
北京市朝阳区街道123号, 
北京, 
北京市 
90001

示例 3:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001
04/05/1995 apr 5,1995 04-05-1996

📦 每条记录之间留**一个空行**。
➡️ 您可以在一条消息中发送2到20条记录。"""
    
    # ========== 查找服务 ==========
    LOOKUP_MAIN = "🔎 查找服务\n\n选择服务："
    PHONE_SEARCH_HEADER = "📞 电话搜索\n\n选择搜索类型:"
    
    PHONE_LOOKUP_FORMAT = "📞 电话搜索 — {service_name} — ${price}\n⏱ ETA: 4-15 分钟\n📖 说明: {tutorial_link}\n\n输入电话号码：\n格式：+1 (320) 932-0202 或 3209320202"
    
    # 查找服务格式
    SSN_LOOKUP_FORMAT = "🧾 SSN & DOB 查找 — ${price}\n⏱ ETA: 4-10 分钟\n📖 说明: [SSN](https://t.me/ONE_TUTORIAL/85)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    SSN_BULK_FORMAT = "🧾 批量订单 SSN — ${price} 每条\n⏱ ETA: 5-30 分钟\n📖 说明: [SSN Bulk](https://t.me/ONE_TUTORIAL/86)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    DL_LOOKUP_FORMAT = "🪪 驾照查找 — ${price}\n⏱ ETA: 4-30 分钟\n📖 说明: [DL](https://t.me/ONE_TUTORIAL/87)\n\n📝 输入数据：\n姓名, 地址, 出生日期\n\n{example}"
    DL_BULK_FORMAT = "🪪 批量订单 DL — ${price} 每条\n⏱ ETA: 15-60 分钟\n📖 说明: [DL Bulk](https://t.me/ONE_TUTORIAL/88)\n\n📝 输入数据：\n姓名, 地址, 出生日期\n\n{example}"
    MVR_LOOKUP_FORMAT = "🚗 MVR 查找 — ${price}\n⏱ ETA: 10-90 分钟\n📖 说明: [MVR](https://t.me/ONE_TUTORIAL/91)\n\n📝 输入数据：\n姓名, 地址, SSN, 出生日期, 驾照\n\n{example}"
    MVR_BULK_FORMAT = "🚗 批量订单 MVR — ${price} 每条\n⏱ ETA: 15-120 分钟\n📖 说明: [MVR Bulk](https://t.me/ONE_TUTORIAL/2)\n\n📝 输入数据：\n姓名, 地址, SSN, 出生日期, 驾照\n\n{example}"
    FULL_MVR_LOOKUP_FORMAT = "📋 完整 MVR 查找 — ${price}\n⏱ ETA: 10-150 分钟\n📖 说明: [Full MVR](https://t.me/ONE_TUTORIAL/3)\n\n📝 输入数据：\n姓名, 地址, SSN, 出生日期, 驾照\n\n{example}"
    CREDIT_SCORE_LOOKUP_FORMAT = "💳 信用评分查找 — ${price}\n⏱ ETA: 4-15 分钟\n📖 说明: [CS](https://t.me/ONE_TUTORIAL/89)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    CS_BULK_FORMAT = "💳 批量订单 CS — ${price} 每条\n⏱ ETA: 10-30 分钟\n📖 说明: [CS Bulk](https://t.me/ONE_TUTORIAL/90)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    BACKGROUND_LOOKUP_FORMAT = "🔍 背景调查 — ${price}\n⏱ ETA: 4-15 分钟\n📖 说明: [BG](https://t.me/ONE_TUTORIAL/8)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    BG_BULK_FORMAT = "🔍 批量订单 BG — ${price} 每条\n⏱ ETA: 10-30 分钟\n📖 说明: [BG Bulk](https://t.me/ONE_TUTORIAL/9)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    MMN_LOOKUP_FORMAT = "👩‍👦 MMN 查找 — ${price}\n⏱ ETA: 4-15 分钟\n📖 说明: [MMN](https://t.me/ONE_TUTORIAL/10)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    MMN_BULK_FORMAT = "👩‍👦 批量订单 MMN — ${price} 每条\n⏱ ETA: 10-30 分钟\n📖 说明: [MMN Bulk](https://t.me/ONE_TUTORIAL/11)\n\n📝 输入数据：\n姓名, 地址, 出生日期(如果有)\n\n{example}"
    EIN_LOOKUP_FORMAT = "🏢 EIN 查找 — ${price}\n⏱ ETA: 4-20 分钟\n📖 说明: [EIN](https://t.me/ONE_TUTORIAL/12)\n\n📝 输入数据：\n\n{example}"
    
    # ========== BANKS ==========
    BANKS_MAIN = "🏦 银行\n\n选择类别："
    BANKS_MAIN_TEXT = BANKS_MAIN
    BANKS_SELECT_ITEM = "{category_name}\n\n选择商品:"
    BANKS_INSUFFICIENT_BALANCE_MSG = "❌ 余额不足\n{detailed_msg}\n\n💡 点击 /topup 充值"
    BANKS_ITEM_PRICE = "💵 价格: ${price} 每件"
    BANKS_BULK_DISCOUNT = "💡 批量折扣: 3+ (-{d3}%), 5+ (-{d5}%), 10+ (-{d10}%)"
    BANKS_ENTER_QTY = "{item_name}\n\n{price_text}\n{discount_text}\n\n{enter_quantity}"

    # ========== 信用报告 ==========
    NO_OPEN_TICKETS = "🟢 **没有开放的工单**"
    CLOSED_TICKETS_HEADER = "⚪️ **已关闭（最近10个）：**"
    TICKET_NUMBER_PREFIX = "工单 #"
    CATEGORY_PREFIX = "类别："
    STATUS_PREFIX = "状态："
    CREATED_PREFIX = "创建："
    TICKET_HEADER = "🎫 **工单 #{ticket_id}**"
    SENDER_YOU = "👤 您"
    SENDER_SUPPORT = "👨‍💼 客服"
    FILES_COUNT = "📎 文件：{count}"
    YOUR_TICKET_CREATED = "✅ **您的咨询 #{ticket_id} 已创建！**"
    OUR_SPECIALISTS_WILL_REPLY = "我们的专家将很快回复您。"
    YOU_WILL_BE_NOTIFIED = "收到回复时您将收到通知。"
    WANT_TO_ATTACH_FILES = "您想附加文件或截图吗？"
    YOUR_MESSAGE_SENT = "✅ 您的消息已发送！"
    DESCRIBE_YOUR_PROBLEM = "📝 详细描述您的问题或疑问。\n\n发送消息后，您还可以附加照片或文件。"
    WRITE_YOUR_MESSAGE = "✍️ 写您的消息：\n\n（您也可以发送照片或文件）"
    SEND_FILES_INSTRUCTION = "📎 发送文件、照片或文档。\n\n完成后，按 /done"
    
    # ========== 客服系统 ==========
    EIN_BULK_FORMAT = """🛡️ **批量订单 EIN**
—
💵 **价格：** ${price}
⏱ **ETA：** 10-40 分钟
📖 **完整说明：** [EIN Bulk](https://t.me/ONE_TUTORIAL/13)
—
✅ **准备订购？** 发送数据进行即时处理。


📘 输入指南：
{example}

➡️ 发送后，机器人会验证并准备数据进行下一步。"""

    # ========== CREDIT REPORTS ==========
    CREDIT_REPORTS_HEADER = "📈 {provider}\n\n选择提供商："
    CREDIT_REPORT_FORMAT = """🛡️ **CR {service_name}**
**详情：** 所有信用卡（发行人、限额、余额、付款历史）、贷款（抵押、汽车、学生）、公共记录（破产）、查询、FICO/VantageScore 信用评分。
—
💵 **价格：** ${single_price}
⏱ **ETA：** 4-30 分钟
📖 **完整说明：** {tutorial_link}
—
✅ **准备订购？** 发送数据进行即时处理。


📘 输入指南：
{example_text}

➡️ 发送后，机器人会验证并准备数据进行下一步。"""
    
    # ========== DOCUMENTS ==========
    DOCUMENTS_PHOTO_BUTTON = "📸 照片"
    
    # ========== ACCOUNTS ==========
    ACCOUNTS_BACK_BUTTON = "⬅️ 返回"
    
    # ========== ADDINFO ==========
    ADDINFO_BACK_BUTTON = "⬅️ 返回"
    
    # ========== QUANTITY INPUT ==========
    ENTER_QUANTITY = "📝 输入数量 (1-100)："
    ENTER_CUSTOM_QUANTITY = "📝 输入自定义数量 (1-100)："
    
    # ========== SUPPORT TICKETS ==========
    MY_TICKETS_HEADER = "📋 **我的请求**\n\n"
    OPEN_TICKETS_HEADER = "🟢 **开放：**\n"
    
    # ========== SUPPORT SYSTEM ==========
    SUPPORT_MAIN = """📞 支持

选择您的咨询类别：

💰 付款 - 关于付款和余额的问题
📦 产品 - 关于订单和服务的问题
💬 一般 - 一般问题
🤝 合作 - 合作提案"""

    SUPPORT_CHOOSE_CATEGORY = """📝 详细描述您的问题或疑问。

您也可以在发送消息后附加照片或文件。"""

    SUPPORT_MESSAGE_TOO_SHORT = "❌ 消息太短。请更详细地描述问题（至少10个字符）。"

    SUPPORT_TICKET_CREATED = """✅ 您的咨询 #{ticket_id} 已创建！

类别：{category}
状态：开放

我们的专家将很快回复您。
当回复到达时您将收到通知。

您想附加文件或截图吗？"""

    SUPPORT_TICKET_NOT_FOUND = "❌ 工单未找到"
    SUPPORT_ACCESS_DENIED = "❌ 访问被拒绝"
    SUPPORT_TICKET_CLOSED = "❌ 此工单已关闭。创建新的咨询。"
    SUPPORT_MESSAGE_EMPTY = "❌ 消息不能为空。"
    SUPPORT_MESSAGE_SENT = """✅ 您的消息已发送！

工单 #{ticket_id}
当回复到达时您将收到通知。"""

    SUPPORT_ATTACH_FILES = """📎 发送文件、照片或文档。

完成后，按 /done"""
    SUPPORT_FILES_ATTACHED = "✅ 文件已附加！"
    SUPPORT_FILE_ATTACHED = "✅ 文件已附加！发送更多或按 /done"

    # ========== MY TICKETS ==========
    MY_TICKETS_MAIN = "📋 我的工单"
    MY_TICKETS_OPEN = "🟢 开放："
    MY_TICKETS_NO_OPEN = "🟢 没有开放的工单"
    MY_TICKETS_CLOSED = "⚪️ 已关闭（最近10个）："
    
    # ========== TICKET DETAILS ==========
    TICKET_DETAIL_HEADER = """🎫 工单 #{ticket_id}

类别：{category}
状态：{status}
创建：{created_at}

━━━━━━━━━━━━━━━━━"""

    TICKET_SENDER_YOU = "👤 您"
    TICKET_SENDER_SUPPORT = "👨‍💼 支持"
    TICKET_FILES_COUNT = "📎 文件：{count}"

    # ========== TICKET REPLIES ==========
    TICKET_WRITE_REPLY = """✍️ 写您的消息：

（您也可以发送照片或文件）"""

    # ========== ADMIN NOTIFICATIONS ==========
    ADMIN_MESSAGE_FROM = "📢 管理员消息："
    ADMIN_BROADCAST_FROM = "📢 管理部门广播："
    SUPPORT_NEW_REPLY = "💬 工单 #{ticket_id} 中的新回复"
    SUPPORT_REPLY_CATEGORY = "类别：{category}"
    SUPPORT_REPLY_SUBJECT = "主题：{subject}"
    SUPPORT_REPLY_FROM_SUPPORT = "支持回复："
    SUPPORT_STATUS_CHANGED = "📊 工单状态已更改 #{ticket_id}"
    SUPPORT_NEW_STATUS = "新状态：{status}"

    # ========== DATA EXAMPLES ==========
    SSN_SINGLE_EXAMPLE = """📝 示例格式：
张三\n北京市朝阳区街道123号, 北京, 北京市, 90210\n01/15/1990(如果有)

💡 DOB 可选 | ✅ 任何格式都有效"""

    SSN_BULK_EXAMPLE = """📦 输入 2-20 个条目 — 条目之间空行：

JOHN SMITH
123 MAIN ST
NEW YORK NY 10001
123-45-6789 | 01/15/1990

JANE DOE
456 OAK AVE
LOS ANGELES CA 90001
234-56-7890 | 02/20/1985

MIKE WILSON
789 ELM RD
CHICAGO IL 60601
345-67-8901 | 03/10/1992

💡 必需：姓名、地址、城市、州、邮编、SSN、DOB
✅ 任何格式都有效"""

    CR_SINGLE_EXAMPLE = """📝 示例格式：
示例 1:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001  
04-05-1995
000-00-0000

示例 2:
北京市朝阳区街道123号, 
北京, 
北京市 
90001
apr 5,1995
000000000

示例 3:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001
04/05/1995
000-00-0000

✅ 任何格式都有效"""

    CR_BULK_EXAMPLE = """📦 输入 2-20 个条目 — 条目之间空行：

示例 1:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001  
04-05-1995
000-00-0000

示例 2:
北京市朝阳区街道123号, 
北京, 
北京市 
90001
apr 5,1995
000000000

示例 3:
张三  
北京市朝阳区街道123号, 北京, 北京市 90001
04/05/1995
000-00-0000

💡 必需：姓名、地址、城市、州、邮编、SSN、DOB
✅ 任何格式都有效"""

    # ========== BULK ORDER CONFIRMATIONS ==========
    BULK_ENTRIES_VALIDATED = "✅ {count} 个条目已验证！"
    BULK_ENTRY_NUMBER = "📋 **条目 #{number}：**"
    BULK_PRICE_PER_ITEM = "💰 单价：${price}"
    BULK_TOTAL_PRICE = "💰 总计：${total}"
    BULK_CONFIRM_QUESTION = "确认？"

    # ========== CATEGORIES ==========
    CATEGORY_PAYMENT = "💰 付款"
    CATEGORY_PRODUCT = "📦 产品"  
    CATEGORY_GENERAL = "💬 一般"
    CATEGORY_PARTNERSHIP = "🤝 合作"

    # ========== STATUS ==========
    STATUS_OPEN = "开放"
    STATUS_IN_PROGRESS = "进行中"
    STATUS_WAITING_USER = "等待回复"
    STATUS_CLOSED = "已关闭"

    # ========== SUPPORT BOT MESSAGES ==========
    ACCESS_DENIED = "❌ 访问被拒绝"
    ORDER_NOT_FOUND = "订单未找到"
    ORDER_TAKEN = "✅ 订单已接受！"
    ORDER_ALREADY_TAKEN = "❌ 订单已被其他工作人员接受"
    WRONG_CATEGORY = "❌ 您不能接受此订单（错误类别）"
    ORDER_MARKED_DONE = "✅ 订单标记为完成！"
    ORDER_MARKED_NF = "订单标记为未找到，余额已退还"
    INFO_WILL_BE_ADDED = "✅ 信息将在约 {hours} 小时内添加"
    ERROR_ORDER_INFO_NOT_FOUND = "❌ 错误：未找到订单信息"

    # ========== WEB PANEL BROADCASTS ==========
    WEB_ADMIN_MESSAGE_PREFIX = "📢 **管理员消息：**\n\n"
    WEB_ADMIN_BROADCAST_PREFIX = "📢 **管理部门广播：**\n\n"

    # ========== SUPPORT NOTIFICATIONS (HARDCODED) ==========
    SUPPORT_NEW_REPLY_TITLE = "💬 **工单 #{ticket_id} 中的新回复**\n\n"
    SUPPORT_REPLY_CATEGORY_LABEL = "类别：{category}\n"
    SUPPORT_REPLY_SUBJECT_LABEL = "主题：{subject}\n\n"
    SUPPORT_REPLY_FROM_SUPPORT_LABEL = "**支持回复：**\n"
    SUPPORT_STATUS_CHANGE_TITLE = "📊 **工单状态已更改 #{ticket_id}**\n\n"
    SUPPORT_STATUS_SUBJECT_LABEL = "主题：{subject}\n"
    SUPPORT_STATUS_NEW_STATUS_LABEL = "新状态：{status}"

    # ========== HANDLER ERROR MESSAGES ==========
    INVALID_FORMAT_TRY_AGAIN = "❌ 格式无效。请重试。"
    ERROR_IN_ENTRY = "❌ 条目 #{entry} 中的错误：\n{issues}\n\n{example}"
    MINIMUM_ENTRIES_FOR_BULK = "❌ 批量订单至少需要 {min_items} 个条目"
    MAXIMUM_ENTRIES_FOR_BULK = "❌ 最多允许 {max_items} 个条目"
    
    # ========== 产品描述模板 ==========
    PRODUCT_DESCRIPTION_TEMPLATE = """🏛️ {product_name}
📦 类别: {category}
💵 价格: ${price}
🕒 交付: {delivery}
📝 描述: [{description}]({tutorial_link})

✅ 状态: 可用
付款确认后，商品将自动交付。

选择数量或购买1件:"""
    
    # ========== 产品数据 ==========
    PRODUCT_DATA = {
        # VCC 银行
        "vcc_chime": {"category": "VCC", "delivery": "20-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/28", "description": "具有现金功能的虚拟卡"},
        "vcc_paypal": {"category": "VCC", "delivery": "20-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/29", "description": "PayPal + VCC + 加密货币功能"},
        "vcc_current": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/30", "description": "Current bank 虚拟卡"},
        "vcc_wise": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/31", "description": "Wise 个人虚拟卡"},
        "vcc_onepay": {"category": "VCC", "delivery": "20-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/32", "description": "One Pay 虚拟卡"},
        "vcc_go2bank": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/33", "description": "Go2Bank 虚拟卡"},
        "vcc_venmo": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/35", "description": "Venmo 虚拟卡"},
        "vcc_kikoff": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/36", "description": "Kikoff 虚拟卡"},
        "vcc_shopify": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/37", "description": "Shopify 虚拟卡"},
        "vcc_varo": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/38", "description": "Varo 虚拟卡"},
        "vcc_blockchain": {"category": "VCC", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/39", "description": "Blockchain 虚拟卡"},
        
        # 个人银行
        "pers_ally": {"category": "PERSONAL", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/40", "description": "Ally 个人账户"},
        "pers_citi_gold": {"category": "PERSONAL", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/41", "description": "Citi Gold 高级账户"},
        "pers_usalliance": {"category": "PERSONAL", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/42", "description": "US Alliance 个人账户"},
        "pers_boa": {"category": "PERSONAL", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/43", "description": "美国银行个人账户"},
        "pers_alliant": {"category": "PERSONAL", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/44", "description": "Alliant 信用合作社账户"},
        "pers_pnc": {"category": "PERSONAL", "delivery": "40-180 分钟", "tutorial": "https://t.me/ONE_TUTORIAL/45", "description": "PNC Bank 个人账户"},
        
        # 账户
        "bg_intelius_30": {"category": "AGGREGATORS", "delivery": "1-5 小时", "tutorial": "https://t.me/ONE_TUTORIAL/76", "description": "Intelius 30天高级访问"},
        "bg_truthfinder_30": {"category": "AGGREGATORS", "delivery": "1-5 小时", "tutorial": "https://t.me/ONE_TUTORIAL/77", "description": "TruthFinder 30天高级访问"},
        "bg_instantcheck_30": {"category": "AGGREGATORS", "delivery": "1-5 小时", "tutorial": "https://t.me/ONE_TUTORIAL/78", "description": "InstantCheckmate 30天高级访问"},
        "bg_whitepages_30": {"category": "AGGREGATORS", "delivery": "1-5 小时", "tutorial": "https://t.me/ONE_TUTORIAL/79", "description": "Whitepages 30天高级访问"}
    }

# ========== NOTIFICATION TEXTS ==========
    ORDER_COMPLETED_BULK_ITEM = "✅ 您的批量订单项目已完成！"
    ORDER_COMPLETED_SINGLE = "✅ 您的订单已完成！"
    ORDER_NOT_FOUND_BULK_ITEM = "❌ 您的批量订单项目 - 未找到"
    ORDER_NOT_FOUND_SINGLE = "❌ 您的订单 - 未找到"
    BULK_ORDER_COMPLETED = "🎯 您的批量订单已完成！"
    DATA_NOT_FOUND_MESSAGE = "很抱歉，我们找不到所请求的信息。\n您的余额已自动退还。"
    REFUND_AMOUNT = "退款金额"
    ORDER_UPDATE = "订单更新"
    ORDER_NUMBER = "订单"
    SERVICE = "服务"
    CUSTOMER_DATA = "客户数据"
    RESULT = "结果"
    DETAILS = "详情"
    THANK_YOU_FOR_ORDER = "感谢您的订单！🙏"

    ORDER_DETAILS = "📋 订单详情："
    SERVICE_TEXT = "服务："
    STATUS_TEXT = "状态："
    ITEM_TEXT = "项目："
    FILES_TEXT = "文件："
    BALANCE_TEXT = "余额："
    REFUND_TEXT = "退款："
    RESULT_READY = "您的结果已准备好！🎉"
    ORDER_COMPLETE_THANKS = "您的订单已完成！感谢使用我们的服务！🎉"
    NOT_FOUND_MESSAGE = "很抱歉，我们无法找到此项目的信息。\n您的款项已自动退还。💸"
    REFUND_PROCESSED = "很抱歉，我们无法找到所请求的信息。\n您的款项已自动退还。💸"

    FINAL_RESULTS = "📊 最终结果："
    ITEMS_FOUND_DELIVERED = "找到并交付："
    ITEMS_NOT_FOUND_REFUNDED = "未找到（已退款）："
    SUMMARY_TEXT = "💰 总结："
    ITEMS_FOUND = "找到的项目："
    ITEMS_REFUNDED = "退款的项目："
    CHECK_CHAT_HISTORY = "所有单独的结果已在上方发送。请查看聊天记录以获取每个项目的详细信息和文件。"
    CURRENT_BALANCE = "您的当前余额："
    THANK_YOU = "感谢您的订单！🙏"

        # ========== 封禁消息 ==========
    ACCOUNT_BLOCKED_MESSAGE = """🚫 账户已被封禁

    您的账户已被封禁。
    原因: {reason}

    如果您认为这是错误，请联系客服。"""

        # 机器人停用消息
    BOT_DEACTIVATED_MESSAGE = """🚫 机器人已停用

    此机器人已被管理员临时停用。

    请联系客服获取更多信息。"""

        # 管理员消息前缀
    ADMIN_MESSAGE_PREFIX = "📢 管理员消息:\n\n"
        
        # 管理员群发消息前缀
    ADMIN_BROADCAST_PREFIX = "📢 管理部门群发消息:\n\n"

    # ========== ADD INFO NOTIFICATIONS ==========
    ADD_INFO_PROCESSING_TITLE = "您的添加信息订单正在处理中！"
    ADD_INFO_STATUS_IN_PROGRESS = "🔄 处理中"
    ADD_INFO_PROCESSING_MESSAGE = "您的请求正在处理中。请等待大约 **{hours} 小时** 获取结果。"
    ADD_INFO_NOTIFY_READY = "准备好后我们会立即通知您！"
    ADD_INFO_COMPLETED_TITLE = "添加信息订单已完成！"
    ADD_INFO_COMPLETED_MESSAGE = "✅ 信息已成功添加到您的信用报告中！"

    # ========== BALANCE NOTIFICATIONS ==========
    BALANCE_UPDATED = "余额更新"
    BALANCE_ADDED = "已添加"
    BALANCE_DEDUCTED = "已扣除"
    REASON = "原因"
    CONTACT_SUPPORT_IF_QUESTIONS = "如有任何问题，请联系支持。"

    # ========== ORDER CANCELLATION NOTIFICATIONS ==========
    ORDER_CANCELLED_TITLE = "⚠️ 订单已取消"
    ORDER_CANCELLED_MESSAGE = "您的订单 #{order_id} 已被取消。"
    ORDER_CANCELLED_SERVICE = "服务: {service}"
    ORDER_CANCELLED_REFUND = "💰 退款: ${amount:.2f} 已退回您的余额。"
    ORDER_CANCELLED_BALANCE = "您当前的余额: ${balance:.2f}"
    ORDER_CANCELLED_SUPPORT = "如有任何问题，请联系客服。"
    ORDER_CANCELLED_INVALID_DATA = "❌ 提供的数据无效"
    ORDER_CANCELLED_NO_STOCK = "❌ 产品不可用"

    # ========== ADMIN MESSAGES ==========
    ADMIN_MESSAGE_TITLE = "管理员消息"
    USER_BANNED_TITLE = "账户状态更新"
    USER_BANNED_MESSAGE = "您的账户已被暂时停用。"
    USER_UNBANNED_MESSAGE = "您的账户已重新激活。"
    BAN_REASON = "原因"

    # ========== PRODUCT DISPLAY ==========
    CATEGORY = "类别"
    PRICE = "价格"
    DELIVERY = "交付"
    DESCRIPTION = "描述"
    STATUS = "状态"
    AVAILABLE = "可用"
    PREMIUM_SERVICE = "高级服务"
    PAYMENT_CONFIRMATION_TEXT = "确认付款后，商品将自动交付"
    SELECT_QUANTITY_TEXT = "选择数量或购买1件"
    HOURS = "小时"

    # ========== 批量购买确认 ==========
    BULK_PURCHASE_TITLE = "⚠️ **购买确认**"
    BULK_PURCHASE_WARNING = "请确认您的批量购买："
    BULK_PURCHASE_PRODUCT = "📦 **产品：** {product_name}"
    BULK_PURCHASE_QUANTITY = "🔢 **数量：** {quantity} 件"
    BULK_PURCHASE_UNIT_PRICE = "💵 **单价：** ${unit_price:.2f}"
    BULK_PURCHASE_DISCOUNT = "💸 **折扣：** {discount_percent}%"
    BULK_PURCHASE_TOTAL = "💰 **总价：** ${total_price:.2f}"
    BULK_PURCHASE_BALANCE = "💳 **您的余额：** ${balance:.2f}"
    BULK_PURCHASE_NEW_BALANCE = "📊 **购买后余额：** ${new_balance:.2f}"
    BULK_PURCHASE_CONFIRM_TEXT = "您确定要购买 {quantity} 件商品，总价 ${total_price:.2f} 吗？"
    CONFIRM_PURCHASE = "✅ 确认购买"
    CANCEL_PURCHASE = "❌ 取消"
    PURCHASE_CANCELLED = "❌ 购买已取消"

    # ========== 查询支持 ==========
    LOOKUP_SUPPORT_TEXT = """💬 **查询支持**

📋 **可用服务：**

• **SSN & DOB** ($2.8-$3) - 社会保障号码和出生日期查询
• **信用评分** ($1.6-$2) - 信用评分信息
• **驾照** ($6.50-$7) - 驾驶执照查询
• **MVR** ($10-$11) - 机动车报告
• **完整 MVR** ($20-$22) - 完整的机动车报告
• **电话搜索** - 各种电话查询服务
• **背景调查** ($1.5-$2) - 背景检查
• **MMN** ($9) - 母亲婚前姓氏查询
• **EIN** ($11) - 雇主识别号查询

📞 **需要帮助？**
联系我们的支持团队获取任何查询服务的帮助."""
    
    LOOKUP_SUPPORT_BANKS = """🔐 *银行暴力破解集成*

    *可用服务：*

    🏦 [银行登录暴力破解](your_link)
    • 自动登录尝试
    • 支持多家银行
    • 自定义字典集成

    💳 [卡片暴力破解](your_link)
    • 信用卡号生成
    • 基于BIN生成
    • 有效性检查

    (即将推出)"""

    LOOKUP_SUPPORT_ACCOUNTS = """即将推出"""