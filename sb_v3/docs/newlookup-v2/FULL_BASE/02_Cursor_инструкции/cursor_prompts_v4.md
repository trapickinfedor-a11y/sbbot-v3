# Newlookup — Готовые промты для Cursor v4

**Версия:** 4.0 (для v20)
**Дата:** 13.03.2026

> **Инструкция:** Перед каждым промтом в Cursor нажми `@`, выбери файл `newlookup_srs_v20_FINAL.md` и `database_schema_v2.sql`. Это даст AI полный контекст. Затем скопируй и вставь промт.

---

## Фаза 1: Ядро системы (Обновление до v20)

(Промты 1-5 из v3 остаются актуальными, но нужно обновить модели)

### Промт 6 (Обновление): Модели БД — Пользователи (user_related.py)

```
Перепиши модели в `app/db/models/user_related.py` согласно новой схеме `database_schema_v2.sql`. Основные изменения:
- В `User` добавь `trust_score: SmallInteger`.
- В `Seller` замени `rating` на `seller_score: Numeric(4,1)` и добавь `verification_tier: String(16)`.
- Убери `loyalty_level` из `User`.
```

### Промт 7 (Обновление): Модели БД — Товары (product_related.py)

```
Перепиши модели в `app/db/models/product_related.py` согласно новой схеме `database_schema_v2.sql`. Основные изменения:
- В `Order` добавь `parent_order_id: BigInteger` (FK на саму себя) для поддержки корзины.
```

---

## Фаза 2: Новые модули v20

### Промт 8 (Новый): Модели БД — Новые модули (system_related.py)

```
Добавь в `app/db/models/system_related.py` новые SQLAlchemy ORM модели согласно `database_schema_v2.sql`:

1.  **Coupon**: таблица `coupons`.
2.  **WishlistItem**: таблица `wishlist_items`.
3.  **ShoppingCart**: таблица `shopping_carts`.
4.  **CartItem**: таблица `cart_items`.
5.  **Notification**: таблица `notifications`.
6.  **AnalyticsEvent**: таблица `analytics_events`.

Создай все необходимые relationships.
```

### Промт 9 (Новый): Сервис Купонов (services/promo_service.py)

```
Создай файл `app/services/promo_service.py`. В нем реализуй класс `PromoService` со следующими методами:

- `__init__(self, db: AsyncSession)`
- `async def validate_coupon(self, code: str, user_id: int, cart_items: list) -> dict`: Проверяет купон и возвращает словарь с результатом (`is_valid`, `discount_amount`, `error_message`).
- `async def apply_coupon(self, code: str, order_id: int, user_id: int)`: Применяет купон к заказу, создает запись в `coupon_uses`.
- `async def create_coupon(self, coupon_data: dict) -> Coupon`: Создает новый купон в БД.
```

### Промт 10 (Новый): Логика Корзины (services/cart_service.py)

```
Создай файл `app/services/cart_service.py`. Реализуй класс `CartService`:

- `__init__(self, db: AsyncSession)`
- `async def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1)`
- `async def get_cart(self, user_id: int) -> ShoppingCart`
- `async def clear_cart(self, user_id: int)`
- `async def checkout(self, user_id: int) -> Order`: Создает родительский заказ и дочерние под-заказы для каждого продавца в корзине.
```

### Промт 11 (Новый): Хендлеры Корзины (bots/mirror_bot/handlers/cart_handlers.py)

```
Создай файл `app/bots/mirror_bot/handlers/cart_handlers.py`. Напиши хендлеры для `aiogram 3.x` для следующих команд:

- `[🛒 Добавить в корзину]` (CallbackQuery): использует `CartService.add_to_cart`.
- `[🛒 Корзина]` (Message): использует `CartService.get_cart` и показывает содержимое корзины.
- `[✅ Оплатить всё]` (CallbackQuery): использует `CartService.checkout`.
```

### Промт 12 (Новый): Хендлеры Вишлиста (bots/mirror_bot/handlers/wishlist_handlers.py)

```
Создай файл `app/bots/mirror_bot/handlers/wishlist_handlers.py`. Напиши хендлеры для:

- `[❤️ В вишлист]` (CallbackQuery): добавляет товар в `wishlist_items`.
- `[❤️ Вишлист]` (Message): показывает список товаров в вишлисте.
```

### Промт 13 (Новый): Фоновая задача для брошенных корзин (tasks/retention_tasks.py)

```
Создай файл `app/tasks/retention_tasks.py`. Напиши Celery-таску `check_abandoned_carts`, которая:

1.  Запускается каждые 30 минут.
2.  Находит корзины со статусом `active` и `updated_at` > 1 часа назад.
3.  Меняет их статус на `abandoned`.
4.  Отправляет пользователю уведомление `ABANDONED_CART_1H` через NotificationService.
```

### Промт 14 (Новый): Сервис Уведомлений (services/notification_service.py)

```
Создай файл `app/services/notification_service.py`. Реализуй класс `NotificationService`:

- `__init__(self, bot: Bot, db: AsyncSession)`
- `async def send_notification(self, user_id: int, event_code: str, **kwargs)`: 
  - Находит текст уведомления по `event_code` в `notifications_catalog.md` (представь, что он загружен в словарь).
  - Форматирует текст с помощью `kwargs`.
  - Отправляет сообщение пользователю через `bot.send_message`.
  - Сохраняет уведомление в таблице `notifications`.
```

### Промт 15 (Новый): API для Аналитики (web/admin/api/v1/analytics.py)

```
Создай файл `app/web/admin/api/v1/analytics.py`. Напиши эндпоинт для FastAPI, который возвращает ключевые метрики для дашборда в Admin Panel:

- `GET /api/v1/analytics/dashboard`
- Считает: `DAU`, `WAU`, `MAU`, `Total Revenue`, `New Users`, `Sales Count` за последние 24ч/7д/30д.
- Возвращает данные в формате JSON, готовом для отрисовки графиков.
```
