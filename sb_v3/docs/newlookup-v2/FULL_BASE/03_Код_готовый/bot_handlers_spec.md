# aiogram Bot Handlers — Full Specification (v24)

This document provides the complete, copy-ready aiogram handler code for the **Mirror Bot** (the main buyer-facing bot). It includes all FSM states, keyboards, and message texts.

---

## 1. Project Structure (Bot Layer)

```
bots/
├── mirror_bot/
│   ├── main.py              # Bot startup, dispatcher setup
│   ├── handlers/
│   │   ├── start.py         # /start command, main menu
│   │   ├── catalog.py       # Product catalog browsing
│   │   ├── purchase.py      # Purchase flow (FSM)
│   │   ├── profile.py       # User profile, balance, coupons, archive channel
│   │   ├── history.py       # Purchase history with filters
│   │   ├── disputes.py      # Dispute opening and tracking
│   │   └── support.py       # Support ticket creation
│   ├── keyboards/
│   │   ├── main_menu.py
│   │   ├── catalog.py
│   │   ├── profile.py
│   │   └── inline.py
│   ├── states/
│   │   └── fsm.py           # All FSM state groups
│   └── texts/
│       └── ru.py            # All message texts in Russian (default)
```

---

## 2. FSM States

### `bots/mirror_bot/states/fsm.py`

```python
from aiogram.fsm.state import State, StatesGroup

class PurchaseStates(StatesGroup):
    """States for the product purchase flow."""
    selecting_category = State()
    selecting_product = State()
    confirming_quantity = State()
    confirming_purchase = State()  # Shows final price with coupon applied
    entering_coupon = State()

class ProfileStates(StatesGroup):
    """States for profile management."""
    viewing = State()
    entering_coupon_code = State()
    entering_archive_channel_id = State()
    confirming_archive_channel = State()

class DisputeStates(StatesGroup):
    """States for opening a dispute."""
    selecting_order = State()
    entering_reason = State()
    confirming = State()

class SupportStates(StatesGroup):
    """States for creating a support ticket."""
    entering_message = State()
    confirming = State()

class DepositStates(StatesGroup):
    """States for depositing funds."""
    selecting_method = State()
    entering_amount = State()
    awaiting_payment = State()
```

---

## 3. Keyboards

### `bots/mirror_bot/keyboards/main_menu.py`

```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard for the Mirror Bot."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Каталог"), KeyboardButton(text="💼 Мой профиль")],
            [KeyboardButton(text="📦 История покупок"), KeyboardButton(text="💰 Пополнить баланс")],
            [KeyboardButton(text="⚠️ Открыть спор"), KeyboardButton(text="🆘 Поддержка")],
        ],
        resize_keyboard=True
    )
```

### `bots/mirror_bot/keyboards/catalog.py`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

CATEGORIES = [
    ("🏦 Selfreg BA", "cat_selfreg_ba"),
    ("💳 CC / Dumps", "cat_cc_dumps"),
    ("📋 Logs", "cat_logs"),
    ("🔑 Brute", "cat_brute"),
    ("📱 eSIM", "cat_esim"),
]

def get_categories_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard with product categories."""
    buttons = []
    for name, callback in CATEGORIES:
        buttons.append([InlineKeyboardButton(text=name, callback_data=callback)])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_products_keyboard(products: List[dict], category: str) -> InlineKeyboardMarkup:
    """Inline keyboard listing products in a category."""
    buttons = []
    for product in products:
        label = f"{product['title']} — ${product['price']:.2f} (x{product['stock']})"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"product_{product['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_detail_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Keyboard for a single product detail view."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Купить", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="🎟 Применить купон", callback_data=f"coupon_{product_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_products")],
    ])
```

### `bots/mirror_bot/keyboards/profile.py`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_profile_keyboard(has_archive_channel: bool) -> InlineKeyboardMarkup:
    """Inline keyboard for the user profile section."""
    archive_btn_text = "✅ Архив-канал настроен" if has_archive_channel else "📢 Настроить архив-канал"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 Активировать купон", callback_data="activate_coupon")],
        [InlineKeyboardButton(text=archive_btn_text, callback_data="setup_archive_channel")],
        [InlineKeyboardButton(text="💳 История транзакций", callback_data="view_transactions")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")],
    ])
```

---

## 4. Message Texts

### `bots/mirror_bot/texts/ru.py`

```python
# All message texts for Mirror Bot in Russian

WELCOME = """
👋 Добро пожаловать в <b>Newlookup</b>!

Здесь вы можете купить:
• 🏦 Банковские аккаунты (Selfreg BA)
• 💳 Кредитные карты и дампы
• 📋 Логи и брут
• 📱 eSIM

Используйте меню ниже для навигации.
"""

CATALOG_HEADER = "🛒 <b>Каталог товаров</b>\n\nВыберите категорию:"

PRODUCT_DETAIL = """
📦 <b>{title}</b>

📁 Категория: {category}
💰 Цена: <b>${price:.2f}</b>
📊 В наличии: {stock} шт.

📝 {description}
"""

PURCHASE_CONFIRM = """
✅ <b>Подтверждение покупки</b>

📦 Товар: <b>{title}</b>
🔢 Количество: {quantity} шт.
💰 Итого: <b>${total_price:.2f}</b>
{coupon_line}
💳 Баланс после покупки: <b>${balance_after:.2f}</b>

Подтвердить покупку?
"""

PURCHASE_SUCCESS = """
🎉 <b>Покупка успешно совершена!</b>

📦 Товар: <b>{title}</b>
🔢 Количество: {quantity} шт.
💰 Оплачено: <b>${total_price:.2f}</b>
🆔 ID заказа: #{order_id}

📎 Данные товара закреплены в этом чате.
{archive_line}
"""

PURCHASE_PINNED = "📌 Данные товара #{order_id} закреплены в чате."

PURCHASE_ARCHIVED = "📢 Данные также отправлены в ваш архив-канал."

INSUFFICIENT_BALANCE = """
❌ <b>Недостаточно средств</b>

Необходимо: <b>${required:.2f}</b>
Ваш баланс: <b>${balance:.2f}</b>
Не хватает: <b>${deficit:.2f}</b>

Пополните баланс и попробуйте снова.
"""

OUT_OF_STOCK = "❌ Товар закончился. Попробуйте позже или выберите другой."

PROFILE_HEADER = """
👤 <b>Ваш профиль</b>

🆔 ID: {telegram_id}
👤 Username: @{username}
💰 Баланс: <b>${balance:.2f}</b>
📅 Регистрация: {created_at}
📦 Всего покупок: {total_orders}
"""

COUPON_ACTIVATE_PROMPT = "🎟 Введите код купона:"

COUPON_SUCCESS = "✅ Купон <b>{code}</b> успешно активирован! Скидка: <b>{discount}%</b>"

COUPON_INVALID = "❌ Купон недействителен или уже использован."

ARCHIVE_CHANNEL_PROMPT = """
📢 <b>Настройка архив-канала</b>

Для настройки:
1. Создайте Telegram-канал
2. Добавьте этого бота как администратора
3. Отправьте ID канала (например: -1001234567890)

Введите ID вашего канала:
"""

ARCHIVE_CHANNEL_SUCCESS = "✅ Архив-канал успешно настроен! Все будущие покупки будут отправляться туда."

ARCHIVE_CHANNEL_ERROR = "❌ Не удалось настроить канал. Убедитесь, что бот добавлен как администратор."

HISTORY_HEADER = "📦 <b>История покупок</b>\n\nФильтры:"

HISTORY_EMPTY = "У вас пока нет покупок."

DISPUTE_PROMPT = "⚠️ Выберите заказ для открытия спора:"

DISPUTE_REASON_PROMPT = "Опишите проблему с заказом #{order_id}:"

DISPUTE_SUCCESS = "✅ Спор #{dispute_id} открыт. Поддержка свяжется с вами в течение 24 часов."

SUPPORT_PROMPT = "🆘 Опишите вашу проблему, и мы вам поможем:"

SUPPORT_TICKET_CREATED = "✅ Тикет #{ticket_id} создан. Ожидайте ответа."

DEPOSIT_SELECT_METHOD = "💰 Выберите метод пополнения:"

DEPOSIT_ENTER_AMOUNT = "Введите сумму пополнения (минимум $10):"

DEPOSIT_INSTRUCTIONS = """
💳 <b>Инструкция по пополнению</b>

Метод: <b>{method}</b>
Сумма: <b>${amount:.2f}</b>
Адрес: <code>{address}</code>

⚠️ Отправьте точную сумму. Зачисление в течение 15 минут.
"""

BANNED_MESSAGE = "🚫 Ваш аккаунт заблокирован.\nПричина: {reason}\n\nОбратитесь в поддержку."
```

---

## 5. Handler Implementations

### `bots/mirror_bot/handlers/start.py`

```python
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from bots.mirror_bot.keyboards.main_menu import get_main_menu_keyboard
from bots.mirror_bot.texts.ru import WELCOME, BANNED_MESSAGE
from app.services.user_service import UserService

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, db_session):
    """
    Handle /start command.
    1. Get or create user in the database.
    2. Show welcome message with main menu keyboard.
    """
    service = UserService(db_session)
    user = service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    if user.is_banned:
        await message.answer(BANNED_MESSAGE.format(reason=user.ban_reason))
        return

    await message.answer(
        WELCOME,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )
```

### `bots/mirror_bot/handlers/catalog.py`

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bots.mirror_bot.keyboards.catalog import (
    get_categories_keyboard, get_products_keyboard, get_product_detail_keyboard
)
from bots.mirror_bot.texts.ru import CATALOG_HEADER, PRODUCT_DETAIL
from bots.mirror_bot.states.fsm import PurchaseStates
from app.services.product_service import ProductService

router = Router()

@router.message(F.text == "🛒 Каталог")
async def show_catalog(message: Message, state: FSMContext):
    """Show the product category selection menu."""
    await state.set_state(PurchaseStates.selecting_category)
    await message.answer(CATALOG_HEADER, parse_mode="HTML", reply_markup=get_categories_keyboard())

@router.callback_query(F.data.startswith("cat_"))
async def show_products_in_category(callback: CallbackQuery, state: FSMContext, db_session):
    """Show products in the selected category."""
    category_key = callback.data.replace("cat_", "")
    category_map = {
        "selfreg_ba": "Selfreg BA",
        "cc_dumps": "CC / Dumps",
        "logs": "Logs",
        "brute": "Brute",
        "esim": "eSIM",
    }
    category = category_map.get(category_key, category_key)

    service = ProductService(db_session)
    products = service.list_products(category=category, limit=20)

    await state.update_data(selected_category=category)
    await state.set_state(PurchaseStates.selecting_product)

    if not products:
        await callback.message.edit_text(
            f"📭 В категории <b>{category}</b> пока нет товаров.",
            parse_mode="HTML",
            reply_markup=get_categories_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"📦 <b>{category}</b>\n\nВыберите товар:",
            parse_mode="HTML",
            reply_markup=get_products_keyboard(
                [{"id": p.id, "title": p.title, "price": p.price, "stock": p.stock} for p in products],
                category
            )
        )
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def show_product_detail(callback: CallbackQuery, state: FSMContext, db_session):
    """Show detailed information about a selected product."""
    product_id = int(callback.data.replace("product_", ""))
    service = ProductService(db_session)
    product = service.get_product(product_id)

    if not product or not product.is_active:
        await callback.answer("❌ Товар недоступен.", show_alert=True)
        return

    await state.update_data(selected_product_id=product_id)
    await state.set_state(PurchaseStates.confirming_quantity)

    text = PRODUCT_DETAIL.format(
        title=product.title,
        category=product.category,
        price=product.price,
        stock=product.stock,
        description=product.description or "Нет описания"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_product_detail_keyboard(product_id)
    )
    await callback.answer()
```

### `bots/mirror_bot/handlers/purchase.py`

```python
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bots.mirror_bot.states.fsm import PurchaseStates
from bots.mirror_bot.texts.ru import (
    PURCHASE_CONFIRM, PURCHASE_SUCCESS, PURCHASE_PINNED,
    PURCHASE_ARCHIVED, OUT_OF_STOCK
)
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.services.product_service import ProductService

router = Router()

@router.callback_query(F.data.startswith("buy_"))
async def initiate_purchase(callback: CallbackQuery, state: FSMContext, db_session):
    """Start the purchase confirmation flow."""
    product_id = int(callback.data.replace("buy_", ""))
    state_data = await state.get_data()

    user_service = UserService(db_session)
    product_service = ProductService(db_session)

    user = user_service.get_by_telegram_id(callback.from_user.id)
    product = product_service.get_product(product_id)

    if not product or product.stock < 1:
        await callback.answer(OUT_OF_STOCK, show_alert=True)
        return

    quantity = 1
    total_price = product.price * quantity
    balance_after = user.balance - total_price

    coupon_code = state_data.get("coupon_code")
    coupon_line = ""
    if coupon_code:
        coupon_line = f"🎟 Купон: <b>{coupon_code}</b> (-{state_data.get('discount_percent', 0)}%)\n"

    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_buy_{product_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_purchase")],
    ])

    await state.set_state(PurchaseStates.confirming_purchase)
    await state.update_data(product_id=product_id, quantity=quantity, total_price=total_price)

    text = PURCHASE_CONFIRM.format(
        title=product.title,
        quantity=quantity,
        total_price=total_price,
        coupon_line=coupon_line,
        balance_after=balance_after
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=confirm_keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_purchase(callback: CallbackQuery, state: FSMContext, db_session, bot):
    """
    Execute the purchase after user confirmation.
    Steps:
    1. Create order (deducts balance, updates stock, records transaction)
    2. Pin the purchase message in the bot chat
    3. Forward to archive channel if configured
    4. Clear FSM state
    """
    product_id = int(callback.data.replace("confirm_buy_", ""))
    state_data = await state.get_data()

    order_service = OrderService(db_session)
    user_service = UserService(db_session)

    user = user_service.get_by_telegram_id(callback.from_user.id)

    try:
        order = order_service.create_order(
            buyer_id=user.id,
            product_id=product_id,
            quantity=state_data.get("quantity", 1),
            coupon_code=state_data.get("coupon_code")
        )
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)
        return

    product = order.product
    archive_line = ""

    success_text = PURCHASE_SUCCESS.format(
        title=product.title,
        quantity=order.quantity,
        total_price=order.total_price,
        order_id=order.id,
        archive_line=archive_line
    )
    sent_message = await callback.message.answer(success_text, parse_mode="HTML")

    # Pin the message in the chat
    try:
        await bot.pin_chat_message(
            chat_id=callback.message.chat.id,
            message_id=sent_message.message_id,
            disable_notification=True
        )
        await callback.message.answer(PURCHASE_PINNED.format(order_id=order.id), parse_mode="HTML")
    except Exception:
        pass

    # Forward to archive channel if configured
    if user.archive_channel_id:
        try:
            await bot.forward_message(
                chat_id=user.archive_channel_id,
                from_chat_id=callback.message.chat.id,
                message_id=sent_message.message_id
            )
            await callback.message.answer(PURCHASE_ARCHIVED, parse_mode="HTML")
        except Exception:
            pass

    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_purchase")
async def cancel_purchase(callback: CallbackQuery, state: FSMContext):
    """Cancel the purchase and return to main menu."""
    await state.clear()
    await callback.message.edit_text("❌ Покупка отменена.")
    await callback.answer()
```

### `bots/mirror_bot/handlers/profile.py`

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bots.mirror_bot.keyboards.profile import get_profile_keyboard
from bots.mirror_bot.texts.ru import (
    PROFILE_HEADER, COUPON_ACTIVATE_PROMPT, COUPON_SUCCESS, COUPON_INVALID,
    ARCHIVE_CHANNEL_PROMPT, ARCHIVE_CHANNEL_SUCCESS, ARCHIVE_CHANNEL_ERROR
)
from bots.mirror_bot.states.fsm import ProfileStates
from app.services.user_service import UserService
from app.services.coupon_service import CouponService

router = Router()

@router.message(F.text == "💼 Мой профиль")
async def show_profile(message: Message, db_session):
    """Show the user's profile page."""
    service = UserService(db_session)
    user = service.get_by_telegram_id(message.from_user.id)

    text = PROFILE_HEADER.format(
        telegram_id=user.telegram_id,
        username=user.username or "Нет username",
        balance=user.balance,
        created_at=user.created_at.strftime("%d.%m.%Y"),
        total_orders=service.get_order_count(user.id)
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_profile_keyboard(has_archive_channel=bool(user.archive_channel_id))
    )

@router.callback_query(F.data == "activate_coupon")
async def prompt_coupon_code(callback: CallbackQuery, state: FSMContext):
    """Prompt the user to enter a coupon code. Available ONLY in Profile section."""
    await state.set_state(ProfileStates.entering_coupon_code)
    await callback.message.answer(COUPON_ACTIVATE_PROMPT, parse_mode="HTML")
    await callback.answer()

@router.message(ProfileStates.entering_coupon_code)
async def process_coupon_code(message: Message, state: FSMContext, db_session):
    """Process the coupon code entered by the user."""
    code = message.text.strip().upper()
    service = UserService(db_session)
    coupon_service = CouponService(db_session)

    user = service.get_by_telegram_id(message.from_user.id)
    result = coupon_service.activate_coupon(user_id=user.id, code=code)

    if result:
        await message.answer(
            COUPON_SUCCESS.format(code=code, discount=result.coupon.discount_percent),
            parse_mode="HTML"
        )
    else:
        await message.answer(COUPON_INVALID, parse_mode="HTML")

    await state.clear()

@router.callback_query(F.data == "setup_archive_channel")
async def prompt_archive_channel(callback: CallbackQuery, state: FSMContext):
    """Prompt the user to enter their archive channel ID. Available ONLY in Profile section."""
    await state.set_state(ProfileStates.entering_archive_channel_id)
    await callback.message.answer(ARCHIVE_CHANNEL_PROMPT, parse_mode="HTML")
    await callback.answer()

@router.message(ProfileStates.entering_archive_channel_id)
async def process_archive_channel(message: Message, state: FSMContext, db_session, bot):
    """
    Process the archive channel ID.
    Verifies that the bot is an admin in the channel before saving.
    """
    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID канала.")
        return

    # Verify bot is admin in the channel
    try:
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        if chat_member.status not in ("administrator", "creator"):
            raise Exception("Bot is not admin")
    except Exception:
        await message.answer(ARCHIVE_CHANNEL_ERROR, parse_mode="HTML")
        await state.clear()
        return

    service = UserService(db_session)
    user = service.get_by_telegram_id(message.from_user.id)
    service.set_archive_channel(user_id=user.id, channel_id=channel_id)

    await message.answer(ARCHIVE_CHANNEL_SUCCESS, parse_mode="HTML")
    await state.clear()
```

### `bots/mirror_bot/handlers/history.py`

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.services.order_service import OrderService
from app.services.user_service import UserService
from bots.mirror_bot.texts.ru import HISTORY_HEADER, HISTORY_EMPTY

router = Router()

CATEGORY_FILTERS = [
    ("🏦 Selfreg BA", "Selfreg BA"),
    ("💳 CC / Dumps", "CC / Dumps"),
    ("📋 Logs", "Logs"),
    ("🔑 Brute", "Brute"),
    ("📱 eSIM", "eSIM"),
    ("📋 Все категории", None),
]

def get_history_filter_keyboard(active_category: str = None) -> InlineKeyboardMarkup:
    """Keyboard for filtering purchase history by category."""
    buttons = []
    for name, cat in CATEGORY_FILTERS:
        check = "✅ " if cat == active_category else ""
        buttons.append([InlineKeyboardButton(
            text=f"{check}{name}",
            callback_data=f"hist_cat_{cat or 'all'}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "📦 История покупок")
async def show_history(message: Message, db_session):
    """Show purchase history with category filter options."""
    await message.answer(
        HISTORY_HEADER,
        parse_mode="HTML",
        reply_markup=get_history_filter_keyboard()
    )

@router.callback_query(F.data.startswith("hist_cat_"))
async def filter_history_by_category(callback: CallbackQuery, db_session):
    """Filter purchase history by the selected category."""
    category_raw = callback.data.replace("hist_cat_", "")
    category = None if category_raw == "all" else category_raw

    user_service = UserService(db_session)
    order_service = OrderService(db_session)

    user = user_service.get_by_telegram_id(callback.from_user.id)
    orders = order_service.get_user_orders(
        buyer_id=user.id,
        category=category,
        limit=20
    )

    if not orders:
        await callback.message.edit_text(
            HISTORY_EMPTY,
            reply_markup=get_history_filter_keyboard(category)
        )
        await callback.answer()
        return

    lines = [f"📦 <b>История покупок</b> {'— ' + category if category else '(все)'}\n"]
    for order in orders:
        lines.append(
            f"• #{order.id} | {order.product.title} | ${order.total_price:.2f} | "
            f"{order.created_at.strftime('%d.%m.%Y')} | {order.status.value}"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=get_history_filter_keyboard(category)
    )
    await callback.answer()
```

### `bots/mirror_bot/handlers/disputes.py`

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bots.mirror_bot.states.fsm import DisputeStates
from bots.mirror_bot.texts.ru import DISPUTE_PROMPT, DISPUTE_REASON_PROMPT, DISPUTE_SUCCESS
from app.services.dispute_service import DisputeService
from app.services.order_service import OrderService
from app.services.user_service import UserService

router = Router()

@router.message(F.text == "⚠️ Открыть спор")
async def show_dispute_orders(message: Message, state: FSMContext, db_session):
    """Show recent orders eligible for dispute."""
    user_service = UserService(db_session)
    order_service = OrderService(db_session)

    user = user_service.get_by_telegram_id(message.from_user.id)
    orders = order_service.get_user_orders(buyer_id=user.id, status="completed", limit=10)

    if not orders:
        await message.answer("У вас нет заказов для открытия спора.")
        return

    buttons = []
    for order in orders:
        buttons.append([InlineKeyboardButton(
            text=f"#{order.id} — {order.product.title} (${order.total_price:.2f})",
            callback_data=f"dispute_order_{order.id}"
        )])

    await state.set_state(DisputeStates.selecting_order)
    await message.answer(
        DISPUTE_PROMPT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("dispute_order_"), DisputeStates.selecting_order)
async def select_dispute_order(callback: CallbackQuery, state: FSMContext):
    """Select an order to dispute and ask for reason."""
    order_id = int(callback.data.replace("dispute_order_", ""))
    await state.update_data(dispute_order_id=order_id)
    await state.set_state(DisputeStates.entering_reason)
    await callback.message.answer(
        DISPUTE_REASON_PROMPT.format(order_id=order_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(DisputeStates.entering_reason)
async def submit_dispute(message: Message, state: FSMContext, db_session):
    """Submit the dispute with the provided reason."""
    state_data = await state.get_data()
    order_id = state_data.get("dispute_order_id")
    reason = message.text.strip()

    user_service = UserService(db_session)
    dispute_service = DisputeService(db_session)

    user = user_service.get_by_telegram_id(message.from_user.id)

    try:
        dispute = dispute_service.open_dispute(
            buyer_id=user.id,
            order_id=order_id,
            reason=reason
        )
        await message.answer(
            DISPUTE_SUCCESS.format(dispute_id=dispute.id),
            parse_mode="HTML"
        )
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")

    await state.clear()
```

### `bots/mirror_bot/handlers/support.py`

```python
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bots.mirror_bot.states.fsm import SupportStates
from bots.mirror_bot.texts.ru import SUPPORT_PROMPT, SUPPORT_TICKET_CREATED
from app.services.support_service import SupportService
from app.services.user_service import UserService

router = Router()

@router.message(F.text == "🆘 Поддержка")
async def prompt_support(message: Message, state: FSMContext):
    """Prompt user to describe their issue."""
    await state.set_state(SupportStates.entering_message)
    await message.answer(SUPPORT_PROMPT, parse_mode="HTML")

@router.message(SupportStates.entering_message)
async def create_support_ticket(message: Message, state: FSMContext, db_session):
    """Create a support ticket from the user's message."""
    user_service = UserService(db_session)
    support_service = SupportService(db_session)

    user = user_service.get_by_telegram_id(message.from_user.id)
    ticket = support_service.create_ticket(
        user_id=user.id,
        message=message.text.strip()
    )

    await message.answer(
        SUPPORT_TICKET_CREATED.format(ticket_id=ticket.id),
        parse_mode="HTML"
    )
    await state.clear()
```

---

## 6. Bot Startup

### `bots/mirror_bot/main.py`

```python
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from bots.mirror_bot.handlers import start, catalog, purchase, profile, history, disputes, support
from app.db import SessionLocal

BOT_TOKEN = "YOUR_MIRROR_BOT_TOKEN"
REDIS_URL = "redis://localhost:6379/0"

async def main():
    logging.basicConfig(level=logging.INFO)

    storage = RedisStorage.from_url(REDIS_URL)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Register all routers
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(purchase.router)
    dp.include_router(profile.router)
    dp.include_router(history.router)
    dp.include_router(disputes.router)
    dp.include_router(support.router)

    # Middleware to inject db_session into handlers
    # dp.update.middleware(DatabaseMiddleware(SessionLocal))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```
