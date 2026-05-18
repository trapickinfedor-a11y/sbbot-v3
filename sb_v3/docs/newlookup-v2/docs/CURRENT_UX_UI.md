# Mirror Bot — Полное текущее UX/UI оформление

> Все тексты, кнопки и клавиатуры **как сейчас в коде**. Напиши что поменять / добавить / убрать.

---

## 1. WELCOME / START FLOW

### 1.1 Приветствие (START_MESSAGE EN)
```
⚡ ONE PROJECT — not just a bot, but your gateway to the ONE Ecosystem.

🚀 Capabilities:
🔹 24/7 WORK — Always ON. Always Connected.
🔹 Instant access to ONE HUB, ONE LOOKUP, ONE BANKS
🔹 Manage everything in one secure dashboard

🔐 Safe. Fast. Smart.
🧩 ONE SYSTEM — ONE ACCESS — ONE CONTROL.

💡 Built for creators, operators, and builders of the new digital world.

🌍 Choose your language to continue 👇
```

### 1.2 Приветствие (START_MESSAGE RU)
```
⚡ ONE PROJECT — не просто бот, а ваш шлюз в экосистему ONE.

🚀 Возможности:
🔹 24/7 РАБОТА — Всегда ВКЛ. Всегда на связи.
🔹 Мгновенный доступ к ONE HUB, ONE LOOKUP, ONE BANKS
🔹 Управляйте всем в одной безопасной панели

🔐 Безопасно. Быстро. Умно.
🧩 ОДНА СИСТЕМА — ОДИН ДОСТУП — ОДИН КОНТРОЛЬ.

💡 Создано для творцов, операторов и строителей нового цифрового мира.

🌍 Выберите язык для продолжения 👇
```

### 1.3 Выбор языка (inline keyboard)
```
[🇷🇺 Russian]  [🇬🇧 English]
[🇨🇳 Chinese]  [🇪🇸 Spanish]
```

### 1.4 Правила — промпт
```
📜 Please read and accept the rules before using the service:
```

### 1.5 Кнопки принятия правил
```
[✅ I accept the rules]
[❌ I decline]
```

### 1.6 Welcome Bonus (после принятия правил, hardcoded)
```
✅ Rules accepted! Welcome to the service.

🎁 Welcome Bonus!
✅ +$0.50 added to your balance as a welcome gift!
Use it toward your first purchase. 🛍️

🎟 Your coupon code: WELCOME10
Use it for 10% off your first purchase! (valid 30 days)

👋 New here? Take a quick 3-step tour to learn how everything works!
[🚀 Start Tour]  [⏭ Skip]
```

---

## 2. MAIN MENU

### 2.1 Текст сообщения
```
EN: 🏠 Main Menu
RU: 🏠 Главное меню
```
+ Фото: `media/main.jpg`

### 2.2 Reply Keyboard (строится из БД, типичный набор EN)
```
[🔎 Search]              [📈 CREDIT REPORTS]
[📄 DOCUMENTS]           [🧰 PROS & FULLZ]
[🏦 BANKS]               [💳 CC]
[📶 eSIM]                [🧾 Subscriptions / Accounts]
[✍️ Add info in CR]      [📚 Education]
[👤 My profile]          [💳 Top-up balance]
[📞 Support]             [🤝 Referrals +4%]
```

### 2.3 Reply Keyboard RU
```
[🔎 Поиск]               [📈 КРЕДИТНЫЕ ОТЧЕТЫ]
[📄 ДОКУМЕНТЫ]            [🧰 ПРОФИ И ФУЛЛЗ]
[🏦 БАНКИ]                [💳 CC]
[📶 eSIM]                 [🧾 Подписки / Аккаунты]
[✍️ Добавить инфо в CR]   [📚 Обучение]
[👤 Мой профиль]          [💳 Пополнить баланс]
[📞 Поддержка]            [🤝 Рефералы +4%]
```

---

## 3. PROFILE

### 3.1 Текст профиля EN
```
👤 Profile

🧩 Your ID: {user_id}
💰 Balance: {balance} USD
🕓 Registered: {created_at}

🔗 Referral link: {referral_link}
👥 Number of referrals: {referrals_count}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
🌐 ACTUAL LINK
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
```
+ Фото: `media/профиль.png`

### 3.2 Текст профиля RU
```
👤 Профиль

🧩 Ваш ID: {user_id}
💰 Баланс: {balance} USD
🕓 Регистрация: {created_at}

🔗 Реферальная ссылка: {referral_link}
👥 Количество рефералов: {referrals_count}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
🌐 АКТУАЛЬНАЯ ССЫЛКА
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
```

### 3.3 Inline Keyboard профиля (12 кнопок в 1 колонку)
```
[📦 My Bank Orders]
[📦 My Purchases]
[💳 My CC Orders]
[🛍 Seller Specials]
[💸 Send money to another user]
[🎟 Apply Coupon]
[🤝 Referral system]
[📁 Setup Archive]
[🔔 Notification Settings]
[📜 Rules]
[🌍 Choose language]
[⬅️ Back]
```

### 3.4 Реферальная система EN
```
🤝 Referral System

🔗 Your referral link:
{referral_link}

📊 Statistics:
👥 Total referrals: {count}
💵 Total earned: ${earned} USD

🎁 The more referrals, the more you earn!
```
+ Фото: `media/реф.jpg`

---

## 4. PAYMENT / TOP UP

### 4.1 Step 1 — Выбор метода
```
EN: 🪙 Step 1 — Choose Payment System
RU: 🪙 Шаг 1 — Выберите платежную систему
```
+ Фото: `media/top up.jpg`

Inline keyboard:
```
[🪙 Pay via CryptoBot]
[💎 Pay via Cryptomus]
[⬅️ Back to Menu]
```

### 4.2 Step 2 — Ввод суммы (Cryptomus)
```
💵 Step 2 — Enter the Amount

💰 Enter the amount you wish to top-up:
10 — 5000 USD

⚠️ Minimum: $10 · Maximum: $5000

After you send the payment, the system will verify it automatically.
```

### 4.3 Step 2 — Ввод суммы (CryptoBot)
```
💵 Step 2 — Enter the Amount

💰 Enter the amount you wish to top-up:
10 — 5000 USD

⚠️ Minimum: $10 · Maximum: $5000

🚨 ATTENTION! CryptoBot is a third-party payment service!
Topping up your balance in CryptoBot itself does NOT credit money to us.
After topping up in CryptoBot, you MUST pay the invoice that we will create.

After you send the payment, the system will verify it automatically.
```

### 4.4 Step 3 — Ссылка для оплаты
```
🔗 Step 3 — Payment Link

Your payment link has been generated.

Tap below to complete your transaction:
```

Inline keyboard:
```
[💳 Open Payment Link]
[♻️ Refresh Status]
[⬅️ Back to Menu]
```

### 4.5 CryptoPay Invoice Format
```
🪙 **Top-up Balance**
**Payment via CryptoBot**

**Amount to balance:** $50.00 USD
**Platform fee (3%):** +$1.50 USD
━━━━━━━━━━━━━━━━━━━━━━
**Total to pay:** $51.50 USD

ℹ️ *Payment processing fee: 3%*

📌 **Accepted cryptocurrencies:**
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ Invoice expires in 1 hour
🆔 Invoice ID: `abc123`
```

Inline keyboard:
```
[💳 Pay Invoice]
[♻️ Check Status]
[❌ Cancel]
```

### 4.6 Cryptomus Invoice Format
```
💎 **Top-up Balance**
**Payment via Cryptomus**

**Amount to balance:** $50.00 USD
**Platform fee (2%):** +$1.00 USD
━━━━━━━━━━━━━━━━━━━━━━
**Total to pay:** $51.00 USD

ℹ️ *Payment processing fee: 2%*

📌 **Accepted cryptocurrencies:**
   • USDT (TRC20/ERC20/BEP20)
   • BTC, ETH, TON
   • LTC, TRX, USDC
   • And more...

⏱ Invoice expires in 1 hour
🆔 Order ID: `xyz789`
🔖 Payment UUID: `uuid-123`
```

### 4.7 Уведомления об оплате
```
✅ Payment successful! $50 has been added to your balance.

✅ <b>Payment successfully received!</b>
💵 Credited: <b>$50</b>
💰 Your balance: <b>$192.50</b>
Thank you for your top-up! 🎉

⏰ <b>Payment time expired</b>
Payment for <b>$50</b> was cancelled.
Create a new payment if you want to top up your balance.
```

### 4.8 Send Money
```
💸 Send money to another user
Enter recipient User ID:

💰 Enter amount to send:
Your balance: $142.50

📝 **Confirm transfer**
💸 Amount: $25
👤 To User ID: 987654321
💰 Your balance after: $117.50
Confirm transfer?
```

---

## 5. LOOKUP SERVICES

### 5.1 Lookup Main
```
EN: 🔎 Lookup Services — Choose a service to continue:
RU: 🔎 Услуги поиска — Выберите услугу для продолжения:
```

### 5.2 Lookup Inline Keyboard (layout: 2+3+1+3+1+1)
```
[🧾 SSN & DOB — $2.8-$3]  [📉 Credit Score — $1.6-$2]
[🪪 DL — $6.50-$7]  [🚗 MVR — $10-$11]  [📋 Full MVR — $20-$22]
[📞 Phone Search]
[👤 BG — $1.5-$2]  [👩‍👦 MMN — $9]  [🏢 EIN — $11]
[🏦 Bank Account Lookup]
[⬅️ Back]
```

### 5.3 Phone Search Keyboard
```
[📛 NAME LOOKUP — $1.5]
[🆔 NAME DOB SSN — $4]
[📊 FULL LOOKUP — $5]
[⬅️ Back]
```

### 5.4 Order Type Selection
```
[1️⃣ Single Order]
[📦 Bulk Order (2-20)]
[⬅️ Back]
```

### 5.5 Confirm / Bulk Confirm
```
[✅ Confirm]        [✅ Confirm All]
[🎟 Apply Coupon]   [🎟 Apply Coupon]
[❌ Cancel]         [✏️ Edit]
                    [❌ Cancel]
```

### 5.6 Пример lookup format (SSN)
```
🧾 SSN & DOB Lookup — $2.80
⏱ ETA: 4-10 minutes
📖 Instructions: SSN

📝 Enter data:
NAME, ADRESS, DOB(if have)

📝 Example formats:
John Doe
123 Main St, Los Angeles, CA, 90210
01/15/1990(if have)

💡 DOB optional | ✅ Any format works
```

---

## 6. CREDIT REPORTS

### 6.1 Credit Reports Keyboard
```
[🟢 TransUnion — $4.99]
[🔵 Experian — $5.99]
[🟡 EQUIFAX — $5.99]
[🟣 LexisNexis — $9.99]
[⚪ WalletHub / Credit Karma — $7.99]
[⬅️ Back]
```

### 6.2 Credit Report Format (EN)
```
🛡️ **CR TransUnion**
**Details:** All credit cards (issuer, limit, balance, payment history), loans...
—
💵 **Price:** $4.99
⏱ **ETA:** 4-30 minutes
📖 **Full Instructions:** {tutorial_link}
—
✅ **Ready to order?** Send the data for immediate processing.

📘 Input guide:
{example_text}

➡️ After sending, the bot validates and prepares data for the next steps.
```

---

## 7. BANKS

### 7.1 Banks Main
```
EN: 🏦 BANKS — Choose a category:
RU: 🏦 БАНКИ — Выберите категорию:
```

### 7.2 Banks Main Keyboard
```
[💳 PERSONAL VCC [12]]
[🏦 PERSONAL BANKS [8]]
[🏢 BUSINESS BANKS [5]]
[🪙 CRYPTO BANKS [3]]
[🔓 Brute BANK [0]]
[⬅️ Back]
```

### 7.3 Banks Section
```
[📦 Available [15]]
[📝 Per Order [8]]
[🏠 Back to Categories]
```

### 7.4 Bank Item — Quantity Selection
```
{item_name}

💵 Price: $15 per item
💡 Bulk discount: 3+ (-2%), 5+ (-3%), 10+ (-5%)

📝 Enter quantity (1-100):
```

Keyboard:
```
[2️⃣]  [3️⃣ (-2%)]  [5️⃣ (-3%)]  [1️⃣0️⃣ (-5%)]
[📝 Custom Quantity]
[✅ Buy 1 item]
[📝 Order by Name]
[⬅️ Back to List]
```

---

## 8. FULLZ

### 8.1 Fullz Main
```
EN: 🧰 PROS & FULLZ — Choose type:
RU: 🧰 PROS & FULLZ — Выберите тип:
```

### 8.2 Fullz Keyboard
```
[👤 PERSONAL]
[🏢 BUSINESS]
[🔥 CUSTOM WITH CS/CR]
[🎖️ MILITARY]
[✈️ WORK & TRAVEL]
[🧒 YOUNG]
[🎲 RANDOM]
[⬅️ Back]
```

### 8.3 Business FULLZ Order Summary
```
🧾 **BUSINESS FULLZ ORDER**

📊 **Quantity:** 3
📍 **State:** California
🏢 **Company Type:** LLC
💰 **Loan Size:** $50K-$100K
💳 **Credit Score:** 700+

💵 **Total Cost:** $45.00
💳 **Current Balance:** $142.50
📊 **New Balance:** $97.50
🎁 Discount: -2% Save $0.92
```

---

## 9. eSIM

### 9.1 eSIM Main
```
EN: 📶 eSIM — Choose type:
```

Keyboard:
```
[🇺🇸 eSIM for SMS]
[📶 eSIM for Data]
[⬅️ Back]
```

### 9.2 eSIM SMS Operators
```
[📶 Verizon — $20/month]
[📶 AT&T — $35/month]
[📶 T-Mobile — $35/month]
[⬅️ Back]
```

### 9.3 eSIM Periods
```
[⏳ 1 month]
[⏳ 3 months]
[⏳ 6 months]
[⬅️ Back]
```

### 9.4 eSIM Data Plans
```
[📦 5 GB — $10]
[📦 10 GB — $20]
[📦 15 GB — $30]
[⬅️ Back]
```

### 9.5 eSIM Quantity
```
[2️⃣]  [3️⃣ (-2%)]  [5️⃣ (-3%)]
[🔟 (-5%)]
[✅ Buy 1 item]
[⬅️ Back]
```

### 9.6 eSIM Order Details
```
📶 eSIM Order

🇺🇸 Type: SMS
📶 Operator: Verizon
⏳ Period: 1 month(s)
💵 Price per item: $20
🕒 Delivery: 5-10 minutes (auto)
📖 Instructions: eSIM SMS

Select quantity or buy 1 item:
```

---

## 10. DOCUMENTS

### 10.1 Documents Main
```
Choose a category:
```

### 10.2 Documents Buttons
```
[🧑‍🎨 High-Quality Drawing]
[🤖 Robot Drawing (Soon)]
[🔥📸 Photo🔥]
[🪪 DL (Front & Back)]
[🤳 DL + Selfie]
[🛂 Passport]
[🧾 Business Docs]
```

---

## 11. SUBSCRIPTIONS / ACCOUNTS

### 11.1 Accounts Main
```
EN: 🧾 Subscriptions / Accounts — Choose a category:
RU: 🧾 Подписки / Аккаунты — Выберите категорию:
```

### 11.2 Accounts Buttons
```
[🔍 Background Accounts]
[💰 Lookup BA]
[⬅️ Back]
```

---

## 12. ADD INFO in CR

### 12.1 Add Info Main
```
EN: ✍️ Add info in CR — Choose a category:
RU: ✍️ Добавить инфо в CR — Выберите категорию:
```

### 12.2 Add Info Buttons
```
[📈 Add Info in Credit Report]
[🧾 Add Info in BG]
[🏢 Add Employer to CR]
[❄️ Unfreeze CR]
[⬅️ Back]
```

### 12.3 Add Info Format Example
```
✍️ Add info in TU — $25
⏱ ETA: 10-24 hours
📖 Instructions: Add info TU

📝 Enter data:
{example}
```

---

## 13. EDUCATION

### 13.1 Education Keyboard
```
[📅 Subscriptions [5]]
[📖 Manuals [12]]
[⬅️ Back]
```

---

## 14. CC

### 14.1 CC Keyboard (категории из БД)
```
[📂 Category 1 [count]]
[📂 Category 2 [count]]
[📂 Category 3 [count]]
[📂 Category 4 [count]]
[⬅️ Back]
```

---

## 15. SUPPORT

### 15.1 Support Main EN
```
📞 Support

Choose your inquiry category:

💰 Payment - questions about payments and balance
📦 Product - questions about orders and services
💬 General - general questions
🤝 Partnership - partnership proposals
```

### 15.2 Support Main RU
```
📞 Поддержка

Выберите категорию вашего обращения:

💰 Пополнение - вопросы по платежам и балансу
📦 Товар - вопросы по заказам и услугам
💬 Обращение - общие вопросы
🤝 Сотрудничество - предложения о партнерстве
```

### 15.3 Support Keyboard
```
[💰 Payment]
[📦 Product]
[💬 General]
[🤝 Partnership]
[📋 My tickets]
[⬅️ Back]
```

### 15.4 Ticket Detail
```
🎫 Ticket #42

Category: Payment
Status: Open
Created: 2024-03-15

━━━━━━━━━━━━━━━━━
```

Keyboard:
```
[✍️ Reply]
[📎 Attach files]
[⬅️ Back to my tickets]
```

### 15.5 Ticket Created
```
✅ Your inquiry #42 has been created!

Category: Payment
Status: Open

Our specialists will respond to you shortly.
You will receive a notification when a response arrives.

Would you like to attach files or screenshots?
```

---

## 16. PRODUCTS

### 16.1 Product Card (Bank Item)
```
🏛️ Chime VCC
📦 Category: VCC
💵 Price: $15
🕒 Delivery: 20-180 min
📝 Description: Virtual card with cash functionality

✅ Status: Available
Once payment is confirmed, the goods will be delivered automatically.

Select quantity or buy 1 piece:
```

### 16.2 Purchase Success
```
✅ **Purchase Successful!**

📦 **Product:** Chime VCC
💰 **Paid:** $15.00
💳 **New Balance:** $127.50

📁 **File has been sent to you!**

⚠️ *File will be deleted in 1 hour for security*
```

### 16.3 Bulk Purchase Confirmation
```
⚠️ **Purchase Confirmation**

📦 **Product:** Chime VCC
🔢 **Quantity:** 5 items
💵 **Unit Price:** $15.00
💸 **Discount:** 3%
💰 **Total Cost:** $72.75
💳 **Your Balance:** $142.50
📊 **Balance After Purchase:** $69.75

Are you sure you want to purchase 5 items for $72.75?

[✅ Confirm Purchase]
[❌ Cancel]
```

### 16.4 Purchase History
```
📦 My Purchases

[🗂 By Categories]
[👨‍💼 By Sellers]
```

---

## 17. ORDER NOTIFICATIONS

### 17.1 Order Created
```
✅ **Order Created Successfully!**

🎲 **SSN Lookup**
💵 **Price:** $2.80
⏱ **ETA:** 4-10 min
💳 **Balance:** $139.70

Your order has been sent to support team for processing.
```

### 17.2 Order Completed
```
✅ Order #123 completed!

Service: SSN Lookup

{result_text}

💰 Your balance: $139.70

Type /menu to return to main menu.
```

### 17.3 Bulk Order Completed
```
✅ Bulk Order #456 completed!

Service: SSN Lookup

{items_text}

💰 Refund for NOT FOUND: +$5.60
💰 Your balance: $145.30

Type /menu to return to main menu.
```

### 17.4 Not Found / Refund
```
Unfortunately, we couldn't find the requested information.
Your balance has been refunded automatically.
```

### 17.5 Order Cancelled
```
⚠️ Order Cancelled

Your order #789 has been cancelled.
Service: SSN Lookup
💰 Refund: $2.80 has been returned to your balance.
Your current balance: $142.50
If you have any questions, please contact support.
```

---

## 18. CALL SERVICE
```
📦 *Hold Ups / Order Issues*
• Clarifying the status of a package stuck in customs
• Changing the shipping address after placing an order
📞 *Contact Support:* @one1caller

💳 *PayPal*
• Linking a new bank account or card
• Removing limits and completing account verification
📞 *Contact Support:* @one1caller

📞 *Order Over the Phone*
• Purchasing limited items available only by phone
📞 *Contact Support:* @one1caller

🏦 *Bank Calls / Loans*
• Unblocking online access after failed login attempts
• Verifying a large transfer (wire transfer)
📞 *Contact Support:* @one1caller

💼 *Merchant Call*
• Setting up a merchant account and integrating payment systems
📞 *Contact Support:* @one1caller
```

---

## 19. ERROR MESSAGES
```
❌ Insufficient balance
💰 Your balance: $5.00
💳 Required: $15.00
Please top-up your balance to continue.

❌ Invalid data format
{error_message}
📝 Example: {example}

❌ Invalid amount
⚠️ Minimum: $10 · Maximum: $5000

❌ User not found. Please /start
❌ Payment system is not configured
❌ Invoice not found
⏳ Waiting for payment...
❌ Error creating payment: {error}
```

---

## 20. BAN / DEACTIVATION
```
🚫 Account Blocked
Your account has been blocked.
Reason: {reason}
If you believe this is a mistake, please contact support.

🚫 Bot Deactivated
This bot has been temporarily deactivated by the administrator.
Please contact support for more information.
```

---

## 21. ADMIN NOTIFICATIONS
```
📢 Message from Admin:
{text}

📢 Mass Broadcast from Administration:
{text}

💬 New reply in ticket #42
Category: Payment
Subject: My payment didn't arrive
Support response: {text}

📊 Ticket status changed #42
New status: Closed
```

---

## 22. PAGINATION (all screens)
```
[⬅️ Prev]  [📄 1/3]  [Next ➡️]
```

---

## 23. INLINE KEYBOARD LAYOUTS (code)

### profile_keyboard → 12 rows x 1 col
### lookup_keyboard → rows: [2] [3] [1] [3] [1] [1]
### topup_keyboard → 3 rows x 1 col
### banks_main_keyboard → 6 rows x 1 col
### support_categories_keyboard → 6 rows x 1 col
### credit_reports_keyboard → 6 rows x 1 col
### phone_search_keyboard → 4 rows x 1 col
### esim_main_keyboard → 3 rows x 1 col
### fullz_keyboard → 8 rows x 1 col
### bank_item_keyboard → [4] [1] [1] [1] [1]

---

## 24. FILES (photos used)
```
media/main.jpg        → Main menu photo
media/профиль.png     → Profile photo
media/реф.jpg         → Referral system photo
media/top up.jpg      → Top-up photo
media/правила.jpg     → Rules photo
```
