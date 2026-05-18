# Агенты 3, 4, 5: Seller, Worker и Support боты

Этот документ описывает полный UX/UI, тексты и логику для ботов, обслуживающих внутренние процессы: `Seller Bot` для продавцов, `Worker Bot` для исполнителей системных услуг и `Support Bot` для модераторов поддержки.

## 3.1. Агент 3: Seller Bot

**Seller Bot** — это инструмент для продавцов, позволяющий им управлять своими товарами, отслеживать продажи и выводить средства.

### 3.1.1. Авторизация и главное меню

Доступ к боту имеют только пользователи, добавленные в таблицу `sellers` в Admin Panel.

**Текст 25: Доступ запрещен**
```
❌ **Access Denied**

You are not registered as a seller. Contact administrator to get access.
```

**Текст 26: Главное меню Seller Bot**
```
👤 **Seller Menu**

Welcome, {seller_name}!

Select an option to manage your sales.
```
*   **Клавиатура (Inline)**:
    *   `[🗂️ My Banks]` -> Управление товарами
    *   `[➕ Add Bank]` -> Добавление нового товара
    *   `[📦 My Orders]` -> Просмотр заказов
    *   `[💬 Messages ({unread_count})]` -> Чат с покупателями
    *   `[👤 Profile]` -> Просмотр профиля и статистики

### 3.1.2. Профиль продавца

**Текст 27: Профиль (`[👤 Profile]`)**
```
👤 **Seller Profile**

📛 Name: **{seller.display_name}**
📱 Username: @{seller.username or 'N/A'}
🏷 Type: {seller.seller_type}
📊 Markup: {seller.markup_percent}%

🏦 **Banks:**
   Total: {total_banks}
   In Stock: {in_stock_banks}

📦 **Orders:**
   Active: {active_orders}
   Completed: {completed_orders}
   Total: {seller.total_orders}

💰 Total earned: **${seller.total_earned:.2f}**
📅 Registered: {seller.created_at_str}
```
*   **Клавиатура**: Та же, что и в главном меню.

### 3.1.3. Управление товарами (`My Banks`)

**Текст 28: Список банков (`[🗂️ My Banks]`)**
```
🏦 **My Banks** ({count} total)

✅ In stock: {in_stock}
❌ Out of stock: {out_of_stock}

Tap a bank to manage it:
```
*   **Клавиатура (Inline)**: Динамический список банков продавца.
    *   `[✅ Chase Bank | $50.00]`
    *   `[❌ Wells Fargo | $45.00]`
    *   `[➕ Add Bank]`
    *   `[⬅️ Back]`

**Текст 29: Детали банка**
```
**{bank_name}**

**Price:** ${seller_price}
**Buyer Price:** ${buyer_price}
**Status:** {status}

**Description:**
{description}
```
*   **Клавиатура (Inline)**:
    *   `[✅ Set In Stock]` / `[❌ Set Out of Stock]`
    *   `[✏️ Change Price]`
    *   `[🗑️ Delete]`
    *   `[⬅️ Back to My Banks]`

**Логика:**
*   `Buyer Price` рассчитывается как `seller_price * (1 + markup_percent / 100)`.
*   При изменении статуса или цены, в `AdminAuditLog` делается запись.

--- 

### 3.1.4. Добавление товара (`Add Bank`)

**Текст 30: Шаг 1 - Выбор категории**
```
➕ **Add New Bank**

Select the category:
```
*   **Клавиатура (Inline)**: `[VCC]`, `[Personal Bank]`, `[Business Bank]`, `[Crypto]`

**Текст 31: Шаг 2 - Выбор типа**
```
📝 Category: **{category_name}**

Choose how to add:
• **Add to existing type** — select from catalog (Chime, Chase, etc.)
• **Create new type** — enter your own bank name
```
*   **Клавиатура (Inline)**: `[Add to existing type]`, `[Create new type]`

**Текст 32: Шаг 3 - Ввод данных (для нового типа)**
```
Enter the name of the new bank type (e.g., "Revolut Business"):
```

**Текст 33: Шаг 4 - Ввод цены**
```
Enter your price for this bank (in USD). This is the amount you will receive.

Example: `55.50`
```

**Текст 34: Шаг 5 - Ввод описания**
```
Enter a description for the bank. This will be shown to the buyer.
```

**Текст 35: Товар на модерации**
```
✅ **Bank Submitted for Moderation**

Your bank "{bank_name}" has been sent to the administrators for review. You will be notified once it is approved.
```

**Логика:**
*   После ввода всех данных создается `SellerBank` со статусом `pending_admin`.
*   Уведомление отправляется в Admin Panel для модерации (см. Раздел 4).

## 3.2. Агент 4: Worker Bot (Support Bot в коде)

**Worker Bot** — это интерфейс для исполнителей (воркеров), которые обрабатывают системные заказы, такие как `Fullz`, `Documents`, `Lookup` и т.д. В кодовой базе он называется `support_bot`.

### 3.2.1. Авторизация и главное меню

Доступ к боту имеют только пользователи из таблицы `workers` со статусом `is_active = True`.

**Текст 36: Доступ запрещен / Аккаунт отключен**
```
❌ **Access Denied**

You are not registered as a support worker. Contact administrator to get access.
```

**Текст 37: Главное меню Worker Bot**
```
👋 **Welcome, {worker_name}!**

🆔 Support ID: {worker.id}
📊 Total Orders: {worker.orders_completed}

📋 **Your Categories:**
   • {category_1}
   • {category_2}

Choose an option:
```
*   **Клавиатура (Inline)**:
    *   `[📬 New Orders ({new_orders_count})]`
    *   `[📝 My Active Orders ({active_orders_count})]`
    *   `[📈 My Statistics]`

### 3.2.2. Обработка заказов

**Текст 38: Список новых заказов (`[📬 New Orders]`)**
```
**New Orders**

Here are the latest orders available in your categories. Tap to take an order.
```
*   **Клавиатура (Inline)**: Список заказов со статусом `pending`.
    *   `[#12345 | Lookup SSN | $1.50]`
    *   `[#12346 | Fullz Military | $25.00]`
    *   `[⬅️ Back]`

**Текст 39: Детали заказа**
```
**Order #{order_id}**

**Service:** {service_name}
**Price:** ${worker_payout}
**Created:** {created_at}

**Data:**
   • 👤 **Name:** `John Smith`
   • 🏙️ **Location:** `New York, NY, 10001`
   • 🎂 **DOB:** `01/15/1990`
```
*   **Клавиатура (Inline)**:
    *   `[✅ Take Order]` (для новых)
    *   `[✅ Complete Order]` (для взятых в работу)
    *   `[❌ Report Issue]`
    *   `[⏰ Remind Later (1h)]`
    *   `[⬅️ Back to List]`

**Текст 40: Завершение заказа (`[✅ Complete Order]`)**
```
**Completing Order #{order_id}**

Please send the result as a text message. You can also attach files (e.g., PDF, ZIP).
```

**Логика:**
*   Когда воркер нажимает `[✅ Take Order]`, `order.worker_id` обновляется, и статус меняется на `processing`.
*   При `[✅ Complete Order]` бот ожидает сообщение с результатом. После получения, статус заказа меняется на `completed`, и результат отправляется покупателю.
*   `[❌ Report Issue]` позволяет воркеру написать причину проблемы. Статус заказа меняется на `issue`, и админы получают уведомление.
*   `worker_payout` определяется из `service_prices.worker_price`.

## 3.3. Агент 5: Support Bot (для модераторов)

Этот бот используется командой поддержки для ответов на тикеты пользователей. Он не реализован в текущей кодовой базе и является концепцией для будущего.

**Логика:**
*   Бот агрегирует все тикеты из `SupportTicket`.
*   Модераторы могут видеть список открытых тикетов, отвечать на них и закрывать.
*   Все ответы сохраняются в `SupportMessage` и пересылаются пользователю в `Mirror Bot`.
