# Worker Bot (Support Bot) — структура и взаимосвязи

## Обзор

**Support Bot** — Telegram-бот для воркеров (помощников), которые обрабатывают заказы. Воркеры назначаются в админке, получают уведомления о новых заказах и работают с ними через бота.

---

## 1. Архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ВНЕШНИЕ ИСТОЧНИКИ ЗАКАЗОВ                                 │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │  mirror_bot создаёт Order
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  shared.services.order_notification_service                                 │
│  HTTP POST → http://support_bot:8181/api/notifications/new-order            │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPPORT BOT                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  API Server (port 8181)                                                │  │
│  │  POST /api/notifications/new-order     →  OrderNotificationService     │  │
│  │  POST /api/notifications/order-to-channel →  OrderChannelService      │  │
│  │  POST /api/notifications/complaint-resolved → WorkerNotificationService│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Telegram Bot (polling)                                                │  │
│  │  WorkerAuthMiddleware → handlers (orders, bulk, etc.)                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │  Worker CRUD, статистика
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WEB PANEL (Admin)                                    │
│  /workers  →  workers.html  →  API /api/workers/*                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Модель данных (Worker)

**Таблица:** `workers`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | PK |
| `telegram_id` | bigint | Telegram ID (уникальный) |
| `username` | str | @username |
| `categories` | JSON | Список категорий (например: `["🔎 Search", "📈 CREDIT REPORTS"]`) |
| `services` | JSON | Список сервисов (например: `["ssn_dob", "dl", "credit"]`). **Обязательно** для уведомлений |
| `balance` | decimal | Баланс |
| `orders_completed` | int | Количество выполненных заказов |
| `is_active` | bool | Активен ли воркер |
| `can_load_products` | bool | Доступ к загрузке товаров |
| `created_at` | datetime | Дата создания |

**Связанные таблицы:**
- `orders` — заказы воркера (`worker_id`)
- `worker_stats` — статистика по категориям и датам

---

## 3. Управление воркерами (Web Panel)

**URL:** `/workers`  
**API:** `/api/workers`

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/workers` | Список воркеров (фильтр: active/inactive) |
| POST | `/api/workers` | Создать воркера |
| GET | `/api/workers/{id}` | Детали воркера |
| PUT | `/api/workers/{id}` | Обновить |
| DELETE | `/api/workers/{id}` | Удалить |
| POST | `/api/workers/{id}/toggle` | Вкл/выкл |
| GET | `/api/workers/{id}/analytics` | Аналитика |

**Создание воркера:** `telegram_id`, `username`, `categories`, `services`, `can_load_products`.

**Важно:** для получения уведомлений у воркера должны быть заполнены `services` (и `categories`).

---

## 4. Авторизация в боте

**Файл:** `support_bot/middlewares/worker_auth.py`

- **WorkerAuthMiddleware** — проверяет каждый Message и CallbackQuery.
- **Порядок проверки:**
  1. `ADMIN_IDS` → `is_admin=True`, `is_worker=True`.
  2. Иначе → проверка в БД: `WorkerService.is_worker_active(telegram_id)`.
  3. Если не воркер и не админ → блокировка, сообщение «Access Denied».

**Конфиг:** `ADMIN_IDS` в `.env` — список Telegram ID (через запятую).

---

## 5. Меню и кнопки воркера

**Главное меню** (`main_menu_keyboard`):

| Кнопка | callback_data | Описание |
|--------|---------------|----------|
| 📦 Available Orders | `orders_available` | Список доступных заказов |
| 🔄 My Orders (Processing) | `orders_my_processing` | Заказы в работе |
| 📚 Order History | `orders_history` | История |
| 📊 My Statistics | `statistics` | Статистика |
| 👤 Profile | `profile` | Профиль |
| 📋 Описание | `bot_description` | Описание бота |

**Кнопки заказа (взятый воркером):**

| Кнопка | callback_data | Действие |
|--------|---------------|----------|
| ✅ DONE | `order_done:{id}` | Завершить успешно |
| ❌ NF | `order_nf:{id}` | Not Found |
| 📎 DONE + Files | `order_send_file:{id}` | Отправить файлы |
| 💬 DONE + TXT | `order_reply_text:{id}` | Отправить текст |
| ✍️ WRITE CLIENT | `order_addinfo:{id}` | Add Info (24h/48h/72h) |
| ❌ Cancel Order | `order_cancel:{id}` | Отменить |
| ⚠️ Report Client | `order_complaint:{id}` | Жалоба на клиента |

---

## 6. Цепочка уведомлений о заказах

```
1. mirror_bot (или main_bot) создаёт Order
   → mirror_bot/services/order_service.py: OrderService.create_order()

2. shared.services.order_notification_service: notify_new_order(order_data)
   → HTTP POST http://support_bot:8181/api/notifications/new-order
   → env: SUPPORT_BOT_URL (для локального запуска: http://localhost:8181)

3. support_bot/api/notifications.py: notify_new_order()
   → OrderNotificationService.notify_workers_about_new_order(session, temp_order)

4. support_bot/services/order_notification_service.py:
   → Выбор воркеров: is_active=True, категория совпадает, services не пуст
   → can_worker_access_order(categories, services, order.category, order.service_name)
   → Отправка в Telegram каждому воркеру с notification_keyboard(order_id)

5. Отправка в канал (если настроен):
   → OrderNotificationService.send_order_to_channel()
   → ORDERS_CHANNEL_ID в .env
```

---

## 7. Доступ воркера к заказам

**Файл:** `support_bot/services/order_service.py`

- `can_worker_access_order_category()` — проверка категории.
- `can_worker_access_order()` — категория + сервис.
- **Маппинг:** `support_bot/services/order_service.py` → `CATEGORY_MAPPING`.
- **Условие:** `worker.services` не пуст, иначе воркер не получает уведомления и не видит заказы.

---

## 8. Сервисы Support Bot

| Сервис | Файл | Назначение |
|--------|------|------------|
| WorkerService | `worker_service.py` | get_worker, is_worker_active, create_worker |
| OrderService | `order_service.py` | get_available_orders, take_order, complete_order |
| OrderNotificationService | `order_notification_service.py` | notify_workers_about_new_order, send_order_to_channel |
| WorkerNotificationService | `worker_notification_service.py` | notify_workers, notify_complaint_resolved |
| OrderDeliveryService | `order_delivery_service.py` | Доставка результата клиенту через mirror bot |
| NotificationService | `notification_service.py` | Уведомления клиенту о завершении |
| OrderChannelService | `order_channel_service.py` | Публикация заказов в канал |
| SupportLogger | `support_logger.py` | Логирование действий воркеров |

---

## 9. Роутеры (handlers)

| Роутер | Файл | Описание |
|--------|------|----------|
| start | `start.py` | /start, приветствие |
| work_orders | `work_orders.py` | Заказы в работе |
| orders | `orders.py` | Single-заказы |
| bulk_orders | `bulk_orders.py` | Bulk-заказы |
| history | `history.py` | История |
| statistics | `statistics.py` | Статистика |
| profile | `profile.py` | Профиль |
| files | `files.py` | Файлы |
| upload_product | `upload_product.py` | Загрузка товаров |
| complaints | `complaints.py` | Жалобы |
| user_info | `user_info.py` | Информация о пользователях |
| seller_orders | `seller_orders.py` | Заказы селлеров |
| seller_moderation | `seller_moderation.py` | Модерация селлеров |

---

## 10. Конфигурация (.env)

| Переменная | Описание |
|------------|----------|
| `SUPPORT_BOT_TOKEN` | Токен бота |
| `ORDERS_CHANNEL_ID` | ID канала для заказов (опционально) |
| `SUPPORT_LOG_CHAT_ID` | Чат для логов |
| `ADMIN_IDS` | Telegram ID админов (через запятую) |
| `SUPPORT_BOT_URL` | URL API для локального запуска (по умолчанию `http://support_bot:8181`) |

---

## 11. Связь с другими компонентами

| Компонент | Связь с Support Bot |
|-----------|---------------------|
| **mirror_bot** | Создаёт заказы → HTTP POST уведомления |
| **main_bot** | Запускает mirror bots, те же заказы |
| **web_panel** | CRUD воркеров, просмотр заказов |
| **seller_bot** | Воркеры модерируют заказы селлеров |
| **AdminNotificationService** | Уведомления админам о новых заказах, взятии, покупках товаров |

## 12. Покупки товаров (Products)

- **Товары** — готовые файлы (docs, pros_fullz), покупаются без воркера.
- При покупке: `AdminNotificationService.notify_product_purchased()` → уведомление админам.
- В аналитике: `product_purchases`, `product_revenue` в summary, by-category, revenue breakdown.
- Маппинг категорий товаров: `docs` → 📄 DOCUMENTS, `pros_fullz` → 🧰 PROS & FULLZ.

---

## 13. Файловая структура

```
support_bot/
├── bot.py                 # Точка входа
├── api_server.py          # FastAPI (port 8181)
├── config.py
├── api/
│   └── notifications.py   # API уведомлений
├── handlers/
│   ├── start.py
│   ├── orders.py
│   ├── bulk_orders.py
│   ├── work_orders.py
│   ├── history.py
│   ├── statistics.py
│   ├── profile.py
│   ├── files.py
│   ├── complaints.py
│   ├── upload_product.py
│   ├── seller_orders.py
│   ├── seller_moderation.py
│   └── user_info.py
├── middlewares/
│   ├── database.py
│   └── worker_auth.py
├── services/
│   ├── worker_service.py
│   ├── order_service.py
│   ├── order_notification_service.py
│   ├── worker_notification_service.py
│   ├── order_delivery_service.py
│   ├── notification_service.py
│   ├── order_channel_service.py
│   ├── complaint_service.py
│   └── support_logger.py
├── keyboards/
│   └── inline.py
└── constants/
    └── service_names.py
```
