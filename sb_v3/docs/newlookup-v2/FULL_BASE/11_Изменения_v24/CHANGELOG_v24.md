# CHANGELOG v24

Автоматический журнал изменений проекта `newlookup`.

Формат записи:
- Время
- Краткое описание
- Затронутые файлы
- Полный стек/модули
- Риски

## Мониторинг запущен: 2026-03-14 16:33:08

## 2026-03-14 17:03:24

- Время: 2026-03-14 17:03:24
- Краткое описание: новые файлы: 1; изменены: 1. Файлы: NEWLOOKUP_FULL_BASE_v24 (1).zip, shared/database/models.py.
- Затронутые файлы:
  - `NEWLOOKUP_FULL_BASE_v24 (1).zip`
  - `shared/database/models.py`
- Полный стек/модули: PostgreSQL; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: database, shared
- Риски:
  - Изменён `shared/database/models.py`: нужна alembic-миграция и проверка совместимости схемы.

## 2026-03-14 17:33:26

- Время: 2026-03-14 17:33:26
- Краткое описание: изменены: 1. Файлы: shared/database/session.py.
- Затронутые файлы:
  - `shared/database/session.py`
- Полный стек/модули: PostgreSQL; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: database, shared
- Риски:
  - Явных критических рисков по путям файлов не обнаружено; нужна ручная проверка бизнес-логики после завершения изменений.

## 2026-03-14 17:48:27

- Время: 2026-03-14 17:48:27
- Краткое описание: изменены: 4. Файлы: seller_bot/handlers/chat.py, seller_bot/handlers/orders.py, support_bot/handlers/orders.py, support_bot/handlers/work_orders.py.
- Затронутые файлы:
  - `seller_bot/handlers/chat.py`
  - `seller_bot/handlers/orders.py`
  - `support_bot/handlers/orders.py`
  - `support_bot/handlers/work_orders.py`
- Полный стек/модули: Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: seller_bot, support_bot/worker_bot
- Риски:
  - Финансовая/заказная логика: проверить атомарность `async with session.begin()` и блокировки `SELECT FOR UPDATE` там, где это требуется.
  - Изменения в worker/support-потоке: проверить анонимность покупателя и фильтрацию контактов через `chat_filter`.
  - Изменения в seller-интерфейсах: убедиться, что seller не получает `buyer_user_id`, `username`, `telegram_id`.

## 2026-03-14 18:03:27

- Время: 2026-03-14 18:03:27
- Краткое описание: новые файлы: 1; изменены: 7. Файлы: docker-compose.yml, shared/requirements.txt, shared/services/seller_order_delivery_service.py, shared/tasks/__init__.py, shared/tasks/auto_complete.py и ещё 3.
- Затронутые файлы:
  - `docker-compose.yml`
  - `shared/requirements.txt`
  - `shared/services/seller_order_delivery_service.py`
  - `shared/tasks/__init__.py`
  - `shared/tasks/auto_complete.py`
  - `web_panel/auth.py`
  - `web_panel/main.py`
  - `web_panel/services/admin_service.py`
- Полный стек/модули: FastAPI; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: shared, web_panel
- Риски:
  - Финансовая/заказная логика: проверить атомарность `async with session.begin()` и блокировки `SELECT FOR UPDATE` там, где это требуется.

## 2026-03-14 18:18:28

- Время: 2026-03-14 18:18:28
- Краткое описание: изменены: 5. Файлы: support_bot/handlers/orders.py, web_panel/api/admins.py, web_panel/api/checks.py, web_panel/api/seller_mini_app.py, web_panel/templates/admins.html.
- Затронутые файлы:
  - `support_bot/handlers/orders.py`
  - `web_panel/api/admins.py`
  - `web_panel/api/checks.py`
  - `web_panel/api/seller_mini_app.py`
  - `web_panel/templates/admins.html`
- Полный стек/модули: FastAPI; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: support_bot/worker_bot, web_panel
- Риски:
  - Финансовая/заказная логика: проверить атомарность `async with session.begin()` и блокировки `SELECT FOR UPDATE` там, где это требуется.
  - Изменения в worker/support-потоке: проверить анонимность покупателя и фильтрацию контактов через `chat_filter`.

## 2026-03-14 19:18:31

- Время: 2026-03-14 19:18:31
- Краткое описание: изменены: 5. Файлы: mirror_bot/services/product_service.py, seller_bot/handlers/chat.py, shared/services/seller_deposit_service.py, shared/tasks/auto_complete.py, web_panel/static/seller_mini_app.js.
- Затронутые файлы:
  - `mirror_bot/services/product_service.py`
  - `seller_bot/handlers/chat.py`
  - `shared/services/seller_deposit_service.py`
  - `shared/tasks/auto_complete.py`
  - `web_panel/static/seller_mini_app.js`
- Полный стек/модули: FastAPI; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: mirror_bot, seller_bot, shared, web_panel
- Риски:
  - Изменения в seller-интерфейсах: убедиться, что seller не получает `buyer_user_id`, `username`, `telegram_id`.

## 2026-03-14 19:33:32

- Время: 2026-03-14 19:33:32
- Краткое описание: изменены: 4. Файлы: seller_bot/handlers/chat.py, seller_bot/handlers/orders.py, support_bot/handlers/work_orders.py, web_panel/api/seller_mini_app.py.
- Затронутые файлы:
  - `seller_bot/handlers/chat.py`
  - `seller_bot/handlers/orders.py`
  - `support_bot/handlers/work_orders.py`
  - `web_panel/api/seller_mini_app.py`
- Полный стек/модули: FastAPI; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: seller_bot, support_bot/worker_bot, web_panel
- Риски:
  - Финансовая/заказная логика: проверить атомарность `async with session.begin()` и блокировки `SELECT FOR UPDATE` там, где это требуется.
  - Изменения в worker/support-потоке: проверить анонимность покупателя и фильтрацию контактов через `chat_filter`.
  - Изменения в seller-интерфейсах: убедиться, что seller не получает `buyer_user_id`, `username`, `telegram_id`.

## 2026-03-14 19:48:32

- Время: 2026-03-14 19:48:32
- Краткое описание: изменены: 4. Файлы: seller_bot/handlers/orders.py, support_bot/handlers/complaints.py, support_bot/handlers/orders.py, support_bot/services/order_channel_service.py.
- Затронутые файлы:
  - `seller_bot/handlers/orders.py`
  - `support_bot/handlers/complaints.py`
  - `support_bot/handlers/orders.py`
  - `support_bot/services/order_channel_service.py`
- Полный стек/модули: Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: seller_bot, support_bot/worker_bot
- Риски:
  - Финансовая/заказная логика: проверить атомарность `async with session.begin()` и блокировки `SELECT FOR UPDATE` там, где это требуется.
  - Изменения в worker/support-потоке: проверить анонимность покупателя и фильтрацию контактов через `chat_filter`.
  - Изменения в seller-интерфейсах: убедиться, что seller не получает `buyer_user_id`, `username`, `telegram_id`.

## 2026-03-14 20:18:34

- Время: 2026-03-14 20:18:34
- Краткое описание: новые файлы: 1; изменены: 5. Файлы: mirror_bot/services/product_service.py, tests/test_product_service.py, web_panel/api/seller_crm.py, web_panel/api/sellers.py, web_panel/templates/seller_crm.html и ещё 1.
- Затронутые файлы:
  - `mirror_bot/services/product_service.py`
  - `tests/test_product_service.py`
  - `web_panel/api/seller_crm.py`
  - `web_panel/api/sellers.py`
  - `web_panel/templates/seller_crm.html`
  - `web_panel/templates/sellers.html`
- Полный стек/модули: FastAPI; Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: mirror_bot, tests, web_panel
- Риски:
  - Есть тестовые изменения: сверить, что покрытие соответствует новому поведению.

## 2026-03-14 20:33:34

- Время: 2026-03-14 20:33:34
- Краткое описание: новые файлы: 1; изменены: 1. Файлы: shared/tasks/auto_complete.py, tests/test_auto_complete.py.
- Затронутые файлы:
  - `shared/tasks/auto_complete.py`
  - `tests/test_auto_complete.py`
- Полный стек/модули: Python 3.11; SQLAlchemy async; aiogram 3.x; Modules: shared, tests
- Риски:
  - Есть тестовые изменения: сверить, что покрытие соответствует новому поведению.

