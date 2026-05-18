# Localization — Full Text Specification (v24)

This document contains all user-facing text strings for the Mirror Bot in **Russian (RU)** and **English (EN)** as the two primary languages. Spanish (ES) and Chinese (ZH) strings follow the same structure and can be added in a subsequent iteration.

The localization system uses a simple dictionary-based approach. The user's language preference is stored in the `users.language` column (default: `ru`).

---

## 1. Localization System Architecture

### `bots/mirror_bot/texts/__init__.py`

```python
from bots.mirror_bot.texts.ru import TEXTS as RU_TEXTS
from bots.mirror_bot.texts.en import TEXTS as EN_TEXTS

LOCALES = {
    "ru": RU_TEXTS,
    "en": EN_TEXTS,
}

def t(key: str, lang: str = "ru", **kwargs) -> str:
    """
    Translate a key to the specified language.
    Falls back to Russian if key not found in target language.
    Supports format string substitution via kwargs.
    """
    texts = LOCALES.get(lang, RU_TEXTS)
    template = texts.get(key) or RU_TEXTS.get(key, f"[MISSING: {key}]")
    if kwargs:
        return template.format(**kwargs)
    return template
```

---

## 2. Russian Texts (RU)

### `bots/mirror_bot/texts/ru.py`

```python
TEXTS = {
    # === GENERAL ===
    "btn_back": "⬅️ Назад",
    "btn_cancel": "❌ Отмена",
    "btn_confirm": "✅ Подтвердить",
    "btn_yes": "✅ Да",
    "btn_no": "❌ Нет",
    "loading": "⏳ Загрузка...",
    "error_generic": "❌ Произошла ошибка. Попробуйте позже.",
    "error_try_again": "❌ Ошибка. Попробуйте снова.",

    # === MAIN MENU ===
    "btn_catalog": "🛒 Каталог",
    "btn_profile": "💼 Мой профиль",
    "btn_history": "📦 История покупок",
    "btn_deposit": "💰 Пополнить баланс",
    "btn_dispute": "⚠️ Открыть спор",
    "btn_support": "🆘 Поддержка",

    "welcome": (
        "👋 Добро пожаловать в <b>Newlookup</b>!\n\n"
        "Здесь вы можете купить:\n"
        "• 🏦 Банковские аккаунты (Selfreg BA)\n"
        "• 💳 Кредитные карты и дампы\n"
        "• 📋 Логи и брут\n"
        "• 📱 eSIM\n\n"
        "Используйте меню ниже для навигации."
    ),

    # === CATALOG ===
    "catalog_header": "🛒 <b>Каталог товаров</b>\n\nВыберите категорию:",
    "catalog_empty_category": "📭 В категории <b>{category}</b> пока нет товаров.",
    "catalog_select_product": "📦 <b>{category}</b>\n\nВыберите товар:",

    "product_detail": (
        "📦 <b>{title}</b>\n\n"
        "📁 Категория: {category}\n"
        "💰 Цена: <b>${price:.2f}</b>\n"
        "📊 В наличии: {stock} шт.\n\n"
        "📝 {description}"
    ),

    "btn_buy_now": "✅ Купить",
    "btn_apply_coupon": "🎟 Применить купон",

    # === PURCHASE ===
    "purchase_confirm": (
        "✅ <b>Подтверждение покупки</b>\n\n"
        "📦 Товар: <b>{title}</b>\n"
        "🔢 Количество: {quantity} шт.\n"
        "💰 Итого: <b>${total_price:.2f}</b>\n"
        "{coupon_line}"
        "💳 Баланс после: <b>${balance_after:.2f}</b>\n\n"
        "Подтвердить покупку?"
    ),

    "purchase_success": (
        "🎉 <b>Покупка успешно совершена!</b>\n\n"
        "📦 Товар: <b>{title}</b>\n"
        "🔢 Количество: {quantity} шт.\n"
        "💰 Оплачено: <b>${total_price:.2f}</b>\n"
        "🆔 ID заказа: #{order_id}\n\n"
        "📎 Данные товара закреплены в этом чате.\n"
        "{archive_line}"
    ),

    "purchase_pinned": "📌 Данные товара #{order_id} закреплены в чате.",
    "purchase_archived": "📢 Данные также отправлены в ваш архив-канал.",
    "purchase_cancelled": "❌ Покупка отменена.",

    "error_insufficient_balance": (
        "❌ <b>Недостаточно средств</b>\n\n"
        "Необходимо: <b>${required:.2f}</b>\n"
        "Ваш баланс: <b>${balance:.2f}</b>\n"
        "Не хватает: <b>${deficit:.2f}</b>\n\n"
        "Пополните баланс и попробуйте снова."
    ),
    "error_out_of_stock": "❌ Товар закончился. Попробуйте позже или выберите другой.",
    "error_product_not_found": "❌ Товар не найден или был удалён.",

    # === PROFILE ===
    "profile_header": (
        "👤 <b>Ваш профиль</b>\n\n"
        "🆔 ID: {telegram_id}\n"
        "👤 Username: @{username}\n"
        "💰 Баланс: <b>${balance:.2f}</b>\n"
        "📅 Регистрация: {created_at}\n"
        "📦 Всего покупок: {total_orders}"
    ),

    "btn_activate_coupon": "🎟 Активировать купон",
    "btn_setup_archive": "📢 Настроить архив-канал",
    "btn_archive_configured": "✅ Архив-канал настроен",
    "btn_transactions": "💳 История транзакций",

    # === COUPONS ===
    "coupon_prompt": "🎟 Введите код купона:",
    "coupon_success": "✅ Купон <b>{code}</b> активирован! Скидка: <b>{discount}%</b>",
    "coupon_invalid": "❌ Купон недействителен или уже использован.",
    "coupon_already_activated": "❌ Вы уже активировали этот купон.",

    # === ARCHIVE CHANNEL ===
    "archive_channel_prompt": (
        "📢 <b>Настройка архив-канала</b>\n\n"
        "Для настройки:\n"
        "1. Создайте Telegram-канал\n"
        "2. Добавьте этого бота как администратора\n"
        "3. Отправьте ID канала (например: -1001234567890)\n\n"
        "Введите ID вашего канала:"
    ),
    "archive_channel_success": "✅ Архив-канал успешно настроен! Все будущие покупки будут отправляться туда.",
    "archive_channel_error": (
        "❌ Не удалось настроить канал.\n\n"
        "Убедитесь, что бот добавлен как администратор, и попробуйте снова."
    ),
    "archive_channel_invalid_id": "❌ Неверный формат ID. Введите числовой ID канала (например: -1001234567890).",

    # === PURCHASE HISTORY ===
    "history_header": "📦 <b>История покупок</b>\n\nФильтры:",
    "history_empty": "У вас пока нет покупок.",
    "history_filter_all": "📋 Все категории",

    # === DISPUTES ===
    "dispute_select_order": "⚠️ Выберите заказ для открытия спора:",
    "dispute_no_orders": "У вас нет заказов для открытия спора.",
    "dispute_enter_reason": "Опишите проблему с заказом #{order_id}:",
    "dispute_success": "✅ Спор #{dispute_id} открыт. Поддержка свяжется с вами в течение 24 часов.",
    "dispute_already_exists": "❌ Спор по этому заказу уже открыт.",
    "dispute_window_closed": "❌ Окно для открытия спора закрыто. Срок для подачи спора истёк.",

    # === SUPPORT ===
    "support_prompt": "🆘 Опишите вашу проблему, и мы вам поможем:",
    "support_ticket_created": "✅ Тикет #{ticket_id} создан. Ожидайте ответа.",

    # === DEPOSIT ===
    "deposit_select_method": "💰 Выберите метод пополнения:",
    "deposit_enter_amount": "Введите сумму пополнения (минимум $10):",
    "deposit_instructions": (
        "💳 <b>Инструкция по пополнению</b>\n\n"
        "Метод: <b>{method}</b>\n"
        "Сумма: <b>${amount:.2f}</b>\n"
        "Адрес: <code>{address}</code>\n\n"
        "⚠️ Отправьте точную сумму. Зачисление в течение 15 минут."
    ),
    "deposit_amount_too_low": "❌ Минимальная сумма пополнения: $10.00",

    # === BANNED ===
    "banned_message": (
        "🚫 Ваш аккаунт заблокирован.\n"
        "Причина: {reason}\n\n"
        "Обратитесь в поддержку."
    ),

    # === NOTIFICATIONS ===
    "notif_new_purchase": (
        "🛒 <b>Новая продажа!</b>\n\n"
        "📦 Товар: {product_title}\n"
        "🔢 Количество: {quantity}\n"
        "💰 Сумма: ${total_price:.2f}\n"
        "🆔 Заказ: #{order_id}"
    ),
    "notif_dispute_opened": (
        "⚠️ <b>Открыт спор #{dispute_id}</b>\n\n"
        "🆔 Заказ: #{order_id}\n"
        "📝 Причина: {reason}"
    ),
    "notif_dispute_resolved": (
        "✅ <b>Спор #{dispute_id} закрыт</b>\n\n"
        "Решение: {resolution}"
    ),
    "notif_deposit_confirmed": (
        "✅ <b>Пополнение подтверждено</b>\n\n"
        "Сумма: <b>${amount:.2f}</b>\n"
        "Новый баланс: <b>${new_balance:.2f}</b>"
    ),
}
```

---

## 3. English Texts (EN)

### `bots/mirror_bot/texts/en.py`

```python
TEXTS = {
    # === GENERAL ===
    "btn_back": "⬅️ Back",
    "btn_cancel": "❌ Cancel",
    "btn_confirm": "✅ Confirm",
    "btn_yes": "✅ Yes",
    "btn_no": "❌ No",
    "loading": "⏳ Loading...",
    "error_generic": "❌ An error occurred. Please try again later.",
    "error_try_again": "❌ Error. Please try again.",

    # === MAIN MENU ===
    "btn_catalog": "🛒 Catalog",
    "btn_profile": "💼 My Profile",
    "btn_history": "📦 Purchase History",
    "btn_deposit": "💰 Deposit",
    "btn_dispute": "⚠️ Open Dispute",
    "btn_support": "🆘 Support",

    "welcome": (
        "👋 Welcome to <b>Newlookup</b>!\n\n"
        "Here you can buy:\n"
        "• 🏦 Bank Accounts (Selfreg BA)\n"
        "• 💳 Credit Cards & Dumps\n"
        "• 📋 Logs & Brute\n"
        "• 📱 eSIM\n\n"
        "Use the menu below to navigate."
    ),

    # === CATALOG ===
    "catalog_header": "🛒 <b>Product Catalog</b>\n\nSelect a category:",
    "catalog_empty_category": "📭 No products available in <b>{category}</b> yet.",
    "catalog_select_product": "📦 <b>{category}</b>\n\nSelect a product:",

    "product_detail": (
        "📦 <b>{title}</b>\n\n"
        "📁 Category: {category}\n"
        "💰 Price: <b>${price:.2f}</b>\n"
        "📊 In stock: {stock} pcs.\n\n"
        "📝 {description}"
    ),

    "btn_buy_now": "✅ Buy",
    "btn_apply_coupon": "🎟 Apply Coupon",

    # === PURCHASE ===
    "purchase_confirm": (
        "✅ <b>Purchase Confirmation</b>\n\n"
        "📦 Product: <b>{title}</b>\n"
        "🔢 Quantity: {quantity} pcs.\n"
        "💰 Total: <b>${total_price:.2f}</b>\n"
        "{coupon_line}"
        "💳 Balance after: <b>${balance_after:.2f}</b>\n\n"
        "Confirm purchase?"
    ),

    "purchase_success": (
        "🎉 <b>Purchase successful!</b>\n\n"
        "📦 Product: <b>{title}</b>\n"
        "🔢 Quantity: {quantity} pcs.\n"
        "💰 Paid: <b>${total_price:.2f}</b>\n"
        "🆔 Order ID: #{order_id}\n\n"
        "📎 Product data is pinned in this chat.\n"
        "{archive_line}"
    ),

    "purchase_pinned": "📌 Order #{order_id} data pinned in chat.",
    "purchase_archived": "📢 Data also sent to your archive channel.",
    "purchase_cancelled": "❌ Purchase cancelled.",

    "error_insufficient_balance": (
        "❌ <b>Insufficient Balance</b>\n\n"
        "Required: <b>${required:.2f}</b>\n"
        "Your balance: <b>${balance:.2f}</b>\n"
        "Shortfall: <b>${deficit:.2f}</b>\n\n"
        "Please deposit funds and try again."
    ),
    "error_out_of_stock": "❌ Product is out of stock. Try again later or choose another.",
    "error_product_not_found": "❌ Product not found or has been removed.",

    # === PROFILE ===
    "profile_header": (
        "👤 <b>Your Profile</b>\n\n"
        "🆔 ID: {telegram_id}\n"
        "👤 Username: @{username}\n"
        "💰 Balance: <b>${balance:.2f}</b>\n"
        "📅 Registered: {created_at}\n"
        "📦 Total orders: {total_orders}"
    ),

    "btn_activate_coupon": "🎟 Activate Coupon",
    "btn_setup_archive": "📢 Setup Archive Channel",
    "btn_archive_configured": "✅ Archive Channel Configured",
    "btn_transactions": "💳 Transaction History",

    # === COUPONS ===
    "coupon_prompt": "🎟 Enter coupon code:",
    "coupon_success": "✅ Coupon <b>{code}</b> activated! Discount: <b>{discount}%</b>",
    "coupon_invalid": "❌ Coupon is invalid or has already been used.",
    "coupon_already_activated": "❌ You have already activated this coupon.",

    # === ARCHIVE CHANNEL ===
    "archive_channel_prompt": (
        "📢 <b>Archive Channel Setup</b>\n\n"
        "To set up:\n"
        "1. Create a Telegram channel\n"
        "2. Add this bot as an administrator\n"
        "3. Send the channel ID (e.g., -1001234567890)\n\n"
        "Enter your channel ID:"
    ),
    "archive_channel_success": "✅ Archive channel configured! All future purchases will be forwarded there.",
    "archive_channel_error": (
        "❌ Failed to configure channel.\n\n"
        "Make sure the bot is added as an administrator and try again."
    ),
    "archive_channel_invalid_id": "❌ Invalid ID format. Enter a numeric channel ID (e.g., -1001234567890).",

    # === PURCHASE HISTORY ===
    "history_header": "📦 <b>Purchase History</b>\n\nFilters:",
    "history_empty": "You have no purchases yet.",
    "history_filter_all": "📋 All Categories",

    # === DISPUTES ===
    "dispute_select_order": "⚠️ Select an order to open a dispute:",
    "dispute_no_orders": "You have no orders eligible for a dispute.",
    "dispute_enter_reason": "Describe the issue with order #{order_id}:",
    "dispute_success": "✅ Dispute #{dispute_id} opened. Support will contact you within 24 hours.",
    "dispute_already_exists": "❌ A dispute for this order is already open.",
    "dispute_window_closed": "❌ The dispute window has closed. The deadline for opening a dispute has passed.",

    # === SUPPORT ===
    "support_prompt": "🆘 Describe your issue and we'll help you:",
    "support_ticket_created": "✅ Ticket #{ticket_id} created. Please wait for a response.",

    # === DEPOSIT ===
    "deposit_select_method": "💰 Select deposit method:",
    "deposit_enter_amount": "Enter deposit amount (minimum $10):",
    "deposit_instructions": (
        "💳 <b>Deposit Instructions</b>\n\n"
        "Method: <b>{method}</b>\n"
        "Amount: <b>${amount:.2f}</b>\n"
        "Address: <code>{address}</code>\n\n"
        "⚠️ Send the exact amount. Credited within 15 minutes."
    ),
    "deposit_amount_too_low": "❌ Minimum deposit amount: $10.00",

    # === BANNED ===
    "banned_message": (
        "🚫 Your account has been banned.\n"
        "Reason: {reason}\n\n"
        "Contact support."
    ),

    # === NOTIFICATIONS ===
    "notif_new_purchase": (
        "🛒 <b>New Sale!</b>\n\n"
        "📦 Product: {product_title}\n"
        "🔢 Quantity: {quantity}\n"
        "💰 Amount: ${total_price:.2f}\n"
        "🆔 Order: #{order_id}"
    ),
    "notif_dispute_opened": (
        "⚠️ <b>Dispute #{dispute_id} opened</b>\n\n"
        "🆔 Order: #{order_id}\n"
        "📝 Reason: {reason}"
    ),
    "notif_dispute_resolved": (
        "✅ <b>Dispute #{dispute_id} closed</b>\n\n"
        "Resolution: {resolution}"
    ),
    "notif_deposit_confirmed": (
        "✅ <b>Deposit confirmed</b>\n\n"
        "Amount: <b>${amount:.2f}</b>\n"
        "New balance: <b>${new_balance:.2f}</b>"
    ),
}
```

---

## 4. Language Selection

### Language Setting in User Profile

```python
# In profile handler, add language selection button
@router.callback_query(F.data == "change_language")
async def change_language(callback: CallbackQuery, db_session):
    """Allow user to change their language preference."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
    ])
    await callback.message.answer("Select language / Выберите язык:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, db_session):
    """Save the selected language to the user's profile."""
    lang = callback.data.replace("lang_", "")
    service = UserService(db_session)
    user = service.get_by_telegram_id(callback.from_user.id)
    service.update_language(user_id=user.id, language=lang)

    from bots.mirror_bot.texts import t
    await callback.message.answer(t("welcome", lang=lang), parse_mode="HTML")
    await callback.answer()
```

---

## 5. Usage in Handlers

```python
# Example: Using the t() function in handlers
from bots.mirror_bot.texts import t

@router.message(F.text.in_(["🛒 Каталог", "🛒 Catalog"]))
async def show_catalog(message: Message, state: FSMContext, db_session):
    user = UserService(db_session).get_by_telegram_id(message.from_user.id)
    lang = user.language or "ru"

    await message.answer(
        t("catalog_header", lang=lang),
        parse_mode="HTML",
        reply_markup=get_categories_keyboard(lang=lang)
    )
```

---

## 6. Notes for Cursor Implementation

When implementing the localization system:

1. Add a `language` column (`VARCHAR(5)`, default `'ru'`) to the `users` table.
2. Use the `t()` function everywhere user-facing text is displayed.
3. The main menu keyboard buttons must match the text in the user's language (for text-based button matching in handlers).
4. For text-based button handlers, use `F.text.in_(["🛒 Каталог", "🛒 Catalog"])` to match both languages.
5. Alternatively, switch to inline keyboards (callback-based) to avoid language-dependent text matching.
