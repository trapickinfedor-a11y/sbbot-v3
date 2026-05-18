# Агент 1: Mirror Bot (Клиентский бот)

Этот документ описывает полный UX/UI, тексты и логику для **Mirror Bot** — основного бота, с которым взаимодействуют конечные пользователи.

## 1.1. Первый запуск и принятие правил

При первом запуске бота (`/start`) пользователь проходит процесс онбординга, который включает выбор языка и обязательное принятие правил сервиса.

**Текст 1: Приветствие и выбор языка (`/start`)**
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
*   **Клавиатура**: `[🇬🇧 English] [🇷🇺 Русский] [🇨🇳 中文]`

**Текст 2: Запрос на принятие правил (после выбора языка)**
*   **Картинка**: `media/rules.jpg`
*   **Текст**: 
    ```
    📜 **Rules of Service**

    Before you start, please read and accept our rules. This is required for using our services.
    ```
*   **Клавиатура**: `[✅ I accept the rules] [❌ I decline]`

**Текст 3: Полный текст правил (появляется после текста 2)**
```markdown
**ONE PROJECT | RULES**

**1. GENERAL PROVISIONS**
1.1. By using the bot, you automatically agree to these rules.
1.2. Ignorance of the rules does not exempt you from responsibility.
1.3. The administration reserves the right to change the rules at any time without notifying users.

**2. FINANCIAL OPERATIONS**
2.1. All payments are final. Refunds are only possible if the service was not provided due to a fault of the service.
2.2. A commission is charged for balance top-ups. The final amount is displayed before payment.
2.3. Attempts to use fraudulent payment methods will result in an immediate and permanent ban of your account.

**3. GUARANTEE AND REPLACEMENTS**
3.1. The replacement time for goods is specified in the description of each category.
3.2. To request a replacement, create a ticket in the Support section, providing the order number and a detailed description of the problem.
3.3. The administration has the right to refuse a replacement if the user violates the rules of use or cannot provide evidence of the item's invalidity.

**4. PROHIBITED ACTIONS**
4.1. It is forbidden to insult the administration and other users.
4.2. It is forbidden to use the service for any illegal purposes.
4.3. It is forbidden to transfer your account to third parties.

**5. SUPPORT**
5.1. Support is provided only through the ticket system in the bot.
5.2. The standard response time for a ticket is up to 24 hours.
```

**Логика:**
*   Если пользователь нажимает `[✅ I accept the rules]`, его `user.has_accepted_rules` в БД становится `True`, и ему показывается главное меню (Раздел 1.2).
*   Если пользователь нажимает `[❌ I decline]`, бот отправляет сообщение `You have declined the rules. Access to the bot is restricted.` и ничего не происходит, пока он снова не нажмет `/start`.
*   Если пользователь уже принял правила, при повторном `/start` ему сразу показывается главное меню.

## 1.2. Главное меню

После принятия правил пользователь видит главное меню. Оно состоит из картинки, приветственного текста и Reply-клавиатуры.

**Текст 4: Главное меню**
*   **Картинка**: `media/main_menu.jpg`
*   **Текст**: `🏠 Main Menu`

**Клавиатура главного меню (ReplyKeyboardMarkup):**

| Ряд | Кнопка 1 | Кнопка 2 |
| --- | --- | --- |
| 1 | `[👤 My profile]` | `[💳 Top-up balance]` |
| 2 | `[🏦 BANKS]` | `[💳 CC]` |
| 3 | `[🧰 PROS & FULLZ]` | `[📄 DOCUMENTS]` |
| 4 | `[📈 CREDIT REPORTS]` | `[🔎 Search]` |
| 5 | `[📶 eSIM]` | `[🧾 Subscriptions / Accounts]` |
| 6 | `[📚 Education]` | `[📞 Support]` |

**Логика:**
*   Каждая кнопка ведет в соответствующий раздел, описанный ниже.
*   Команда `/menu` в любой момент возвращает пользователя в это меню, отправляя сообщение заново.

## 1.3. Профиль и Баланс

Раздел `[👤 My profile]` предоставляет пользователю всю информацию о его аккаунте, балансе и реферальной программе.

**Текст 5: Экран профиля (`[👤 My profile]`)**
*   **Картинка**: `media/profile.png`
*   **Текст**:
    ```
    👤 Profile

    🧩 Your ID: {user_id}
    💰 Balance: {balance} USD
    🕓 Registered: {created_at}

    🔗 Referral link: {referral_link}
    👥 Number of referrals: {referrals_count}
    ```
*   **Клавиатура (Inline)**:
    *   `[💳 Top-up balance]` -> Флоу пополнения (см. ниже)
    *   `[💸 My Orders]` -> Список заказов (Раздел 1.9)
    *   `[🤝 Referral System]` -> Экран реферальной системы
    *   `[⚙️ Settings]` -> Настройки (смена языка)
    *   `[⬅️ Back to Main Menu]` -> Возврат в главное меню

--- 

### 1.3.1. Пополнение баланса

При нажатии на `[💳 Top-up balance]` запускается пошаговый процесс пополнения.

**Текст 6: Шаг 1 - Выбор системы**
*   **Картинка**: `media/top_up.jpg`
*   **Текст**: `🪙 Step 1 — Choose Payment System`
*   **Клавиатура (Inline)**: `[CryptoBot] [Cryptomus]`

**Текст 7: Шаг 2 - Ввод суммы (для CryptoBot)**
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

**Текст 8: Шаг 3 - Ссылка на оплату (для CryptoBot)**
```
🔗 Step 3 — Payment Link

💰 Amount: ${amount} USD

⚠️ IMPORTANT! CryptoBot is a third-party service!
After topping up your balance in CryptoBot, you MUST pay the invoice using the link below.
Money will NOT arrive to your balance until you pay the invoice!

ℹ️ A payment processing fee applies
📌 Accepted cryptocurrencies:
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ Invoice expires in 1 hour

Tap below to complete your transaction:
```
*   **Клавиатура (Inline)**: `[💳 Pay Invoice]` (ссылка на `invoice.pay_url`)

**Текст 9: Успешное пополнение**
```
✅ Balance successfully topped-up by +{amount}$

💼 Your new balance has been updated automatically.

🔁 Type /menu to return to the main interface.

⚡ Thank you for using ONE PROJECT — your ecosystem for smart automation.
```

**Логика:**
*   Система создает инвойс через выбранную платежную систему (`CryptoPay` или `Cryptomus`).
*   Сумма к оплате рассчитывается с учетом комиссии: `amount_to_pay = desired_amount / (1 - fee_percent / 100)`.
*   После успешной оплаты (получение webhook от платежной системы) баланс пользователя обновляется, и ему отправляется сообщение об успехе.
*   Если инвойс не оплачен в течение часа, он аннулируется.

## 1.4. Каталог товаров

Этот раздел описывает взаимодействие с основными категориями товаров: `BANKS`, `CC` и `PROS & FULLZ`.

--- 

### 1.4.1. BANKS

**Текст 10: Главное меню BANKS**
*   **Картинка**: `media/banks.jpg`
*   **Текст**:
    ```
    🏦 **BANKS**

    Welcome to the Banks section.

    Here you can purchase accounts from various banks. All products are verified and ready to use.

    Please select a category:
    ```
*   **Клавиатура (Inline)**:
    *   `[💳 PERSONAL VCC]`
    *   `[🏦 PERSONAL BANKS]`
    *   `[🏢 BUSINESS BANKS]`
    *   `[🪙 CRYPTO BANKS]`
    *   `[⬅️ Back to Main Menu]`

**Текст 11: Список товаров в категории**
```
🏦 **{category_name}**

Select an item to view details and purchase:
```
*   **Клавиатура (Inline)**: Динамически генерируемый список товаров из `SellerBank` со статусом `approved`.
    *   `[✅ Chase Bank | $50.00]` (если в наличии)
    *   `[❌ Wells Fargo | $45.00]` (если нет в наличии, кнопка неактивна)
    *   Пагинация `[⬅️ Prev] [1/3] [Next ➡️]`
    *   `[⬅️ Back to Categories]`

**Текст 12: Карточка товара (банка)**
```
**{bank_name}**

{bank_description}

**Price:** ${price}
**Seller:** {seller_name}

Select quantity:
```
*   **Клавиатура (Inline)**:
    *   `[✅ Buy 1 item]`
    *   `[📝 Custom Quantity]`
    *   `[⬅️ Back to List]`

**Логика:**
*   При нажатии `[✅ Buy 1 item]` создается `Order` со статусом `pending`.
*   Деньги списываются с баланса пользователя.
*   Заказ отправляется в `Seller Bot` для обработки продавцом.
*   Если товара нет в наличии (`is_in_stock = False`), кнопка в списке отображается как неактивная, и при нажатии выводится alert `❌ This bank is currently out of stock`.

--- 

### 1.4.2. CC (Credit Cards)

Флоу аналогичен `BANKS`, но использует данные из `CCItem` и `SellerCCItem`.

--- 

### 1.4.3. PROS & FULLZ

**Текст 13: Главное меню FULLZ**
*   **Картинка**: `media/Fullz.jpg`
*   **Текст**: `🧰 **PROS & FULLZ**

Select a profile type:`
*   **Клавиатура (Inline)**:
    *   `[👤 PERSONAL]`
    *   `[🏢 BUSINESS]`
    *   `[⬅️ Back to Main Menu]`

**Текст 14: Выбор профиля Personal Fullz**
```
👤 **Personal Fullz**

Select a profile that meets your requirements:
```
*   **Клавиатура (Inline)**:
    *   `[🔥 CUSTOM WITH CS/CR]`
    *   `[🎖️ MILITARY]`
    *   `[✈️ WORK & TRAVEL]`
    *   `[🧒 YOUNG]`
    *   `[🎲 RANDOM]`
    *   `[⬅️ Back]`

**Логика:**
*   После выбора профиля и штата (если применимо) система создает `Order`.
*   Заказ отправляется в `Worker Bot` (`Support Bot`) для обработки воркером, так как `Fullz` — это системная услуга, а не товар от селлера.

## 1.5. Системные услуги

Эти услуги выполняются воркерами через `Worker Bot` и их цены управляются в Admin Panel через таблицу `service_prices`.

--- 

### 1.5.1. DOCUMENTS

**Текст 15: Главное меню Documents**
```
📄 **DOCUMENTS**

Select the document you need. All documents are generated based on the data you provide.
```
*   **Клавиатура (Inline)**:
    *   `[🪪 DL (Front & Back)]`
    *   `[🤳 DL + Selfie]`
    *   `[🛂 Passport]`
    *   `[🧾 Business Docs]`
    *   `[⬅️ Back to Main Menu]`

**Текст 16: Ввод данных для документа (на примере DL)**
```
🪪 **Driver's License (Front & Back)**

**Price:** ${price}
**ETA:** {eta}

Please provide the data in the following format (each field on a new line):

First Name
Last Name
Address
City
State (e.g., CA)
ZIP Code
Date of Birth (MM/DD/YYYY)
DL Number
```

**Логика:**
*   Пользователь отправляет данные одним сообщением.
*   Система парсит данные, создает `Order` и отправляет его в `Worker Bot`.
*   После выполнения воркер прикрепляет файлы, и они становятся доступны пользователю в разделе `My Orders`.

--- 

### 1.5.2. CREDIT REPORTS

**Текст 17: Главное меню Credit Reports**
```
📈 **CREDIT REPORTS**

Select the credit report you need:
```
*   **Клавиатура (Inline)**:
    *   `[🟢 TransUnion — $4.99]`
    *   `[🔵 Experian — $5.99]`
    *   `[🟡 EQUIFAX — $5.99]`
    *   `[⬅️ Back to Main Menu]`

--- 

### 1.5.3. Search (Lookup)

Раздел `[🔎 Search]` предоставляет доступ к различным lookup-сервисам.

**Текст 18: Главное меню Lookup**
```
🔎 **Lookup Service**

Select a service:
```
*   **Клавиатура (Inline)**:
    *   `[🧾 SSN & DOB — $2.8-$3]`
    *   `[📉 Credit Score — $1.6-$2]`
    *   `[🪪 DL — $6.50-$7]`
    *   `[📞 Phone Search]`
    *   `[⬅️ Back to Main Menu]`

**Текст 19: Ввод данных для SSN & DOB Lookup (Single)**
```markdown
**SSN & DOB Lookup**

**Price:** ${price}
**Bulk Price (2-20):** ${bulk_price} per item

Provide data in the format: `First Name;Last Name;State`

*Example:*
`John;Smith;CA`
```
*   **Клавиатура (Inline)**: `[📦 Bulk Order (2-20)]`

**Текст 20: Ввод данных для SSN & DOB Lookup (Bulk)**
```markdown
**SSN & DOB Lookup (Bulk Order)**

**Price:** ${price} per item

Enter up to 20 lines, each in the format: `First Name;Last Name;State`

*Example:*
`John;Smith;CA`
`Jane;Doe;NY`
`Peter;Jones;TX`
```

**Логика Bulk Order:**
1.  Пользователь отправляет сообщение с несколькими строками.
2.  Система парсит каждую строку.
3.  Создается один `Order` с `is_bulk = True` и `bulk_count` = кол-во строк.
4.  В `BulkOrderItem` создается отдельная запись для каждой строки.
5.  Заказ уходит в `Worker Bot`, где воркер видит каждый под-заказ и может отметить его как `Done` или `Not Found`.
6.  Итоговая стоимость заказа пересчитывается на основе количества успешно выполненных под-заказов (`Done`). Деньги за `Not Found` возвращаются на баланс пользователя.

## 1.6. Поддержка (Support)

Раздел `[📞 Support]` позволяет пользователям создавать тикеты для решения проблем.

**Текст 21: Главное меню поддержки**
*   **Картинка**: `media/support.png`
*   **Текст**:
    ```
    📞 **Support**

    If you have any questions or issues, please create a ticket.

    Select a category that best fits your issue:
    ```
*   **Клавиатура (Inline)**:
    *   `[💰 Payment]`
    *   `[📦 Product]`
    *   `[💬 General]`
    *   `[🤝 Partnership]`
    *   `[📋 My tickets]`
    *   `[⬅️ Back to Main Menu]`

**Текст 22: Создание тикета**
```
**New Ticket | {category_name}**

Please describe your issue in detail. You can also attach files or images.
```

**Текст 23: Список тикетов (`[📋 My tickets]`)**
```
**My Tickets**

Here is a list of your support tickets:
```
*   **Клавиатура (Inline)**: Динамический список тикетов.
    *   `[🟢 #12345 - Payment | Open]`
    *   `[🔴 #12344 - Product | Closed]`
    *   `[⬅️ Back to Support]`

**Текст 24: Просмотр тикета**
```
**Ticket #{ticket_id} | {category}**

**Status:** {status}
**Created:** {created_at}

**History:**

[You] {message_1_text}
__{timestamp}__

[Support] {message_2_text}
__{timestamp}__
```
*   **Клавиатура (Inline)**:
    *   `[✍️ Reply]`
    *   `[📎 Attach files]`
    *   `[❌ Close Ticket]` (если статус `Open`)
    *   `[⬅️ Back to my tickets]`

**Логика:**
*   Когда пользователь создает тикет, в `SupportTicket` создается новая запись.
*   Уведомление о новом тикете отправляется в специальный чат модераторов/админов.
*   Ответы администраторов из Admin Panel (или специального бота) добавляются в `SupportMessage` и пересылаются пользователю.
*   Весь диалог сохраняется в рамках одного тикета.
