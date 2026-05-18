# План: Выплаты (Marketing/Seller) + Управление разделами навигации

## Часть 1. Текущее состояние выплат

### Seller Bot (продавцы)
| Компонент | Где | Что есть |
|-----------|-----|----------|
| **Основная модель (current)** | `SellerWithdrawal` | amount, requisites, status, processed_at, processed_by, reject_reason |
| **Compatibility alias** | `withdrawal-tasks` routes | старые route names поверх main-DB flow |
| **Бот** | `seller_bot/handlers/withdrawal.py` | Создание заявки: сумма → реквизиты → сохранение в main DB |
| **Web API** | `web_panel/api/seller_crm.py` | Основной UI работает через `withdrawals`; `withdrawal-tasks` оставлен как compatibility alias |
| **UI** | `seller_crm.html` | Список pending, кнопки Одобрить/Отклонить для `withdrawals` |

### Marketer Bot (маркетологи)
| Компонент | Где | Что есть |
|-----------|-----|----------|
| **Модель** | `MarketerWithdrawal` | Аналогично SellerWithdrawal |
| **Бот** | `marketer_bot/handlers/withdrawal.py` | Создание заявки (сумма → реквизиты) |
| **Web API** | `web_panel/api/marketers.py` | GET withdrawals, approve, reject |
| **UI** | `marketers.html` | Список pending, approve/reject |

### Cryptomus (интеграция)
- **Сервис:** `mirror_bot/services/cryptomus.py` — `create_payout`, `get_payout_info`, `get_payout_history`, `get_payout_services`
- **Конфиг:** `CRYPTOMUS_PAYOUT_KEY` в .env
- **Сейчас:** Cryptomus payout не используется для seller/marketer — только ручное approve/reject

---

## Часть 2. Текущее состояние навигации и категорий

### A. Навигация админки (`_nav.html`)
**Жёстко захардкожена в шаблоне:**

| Группа | Пункты |
|--------|--------|
| Аналитика | Обзор, Аналитика, Отчёты |
| Юзеры | Пользователи, Боты, Депозиты |
| Команда | Воркеры, Селлеры, Seller CRM, Маркетологи |
| Заказы | Заказы, Жалобы, Чат |
| Каталог | Товары, Банки, Brute Bank, Аккаунты, eSIM, CC, Education, Another |
| Настройки | Цены, Категории, Рассылки, Инструкции |
| Система (super_admin) | Админы, Роли, Audit |

**Нельзя:** менять названия, порядок, добавлять/удалять без правки кода.

### B. Категории товаров (`web_panel/api/categories.py`)
| Что | Где | Управление |
|-----|-----|------------|
| **Category** | БД (таблица) | CRUD API: create, update, delete, toggle, order |
| **Service** | БД | Привязаны к Category |
| **Страница** | `/categories` | Есть UI для категорий |

### C. Константы (`web_panel/constants/categories.py`)
- **CATEGORIES_DATA** — ~200 строк хардкода: eSIM, DOCUMENTS, PROS & FULLZ, BANKS, Subscriptions, Add info in CR, Search, CREDIT REPORTS
- **SERVICE_TO_CATEGORY_MAPPING** — маппинг кодов сервисов на категории
- Используется для отчётов, аналитики, не для навигации

### D. Другие каталоги (свои БД)
- **CC:** `CCCategory`, `CCItem` — API `/api/cc/categories`, CRUD
- **Education:** `EducationCategory` — API `/api/education/categories`
- **BankItem:** `bank_items` — категории vcc, personal, business, crypto
- **Accounts, eSIM, Another** — свои структуры

---

## Часть 3. План расширения

### 3.1. Большая система выплат (Marketing + Seller)

**Сложность: средняя–высокая**

#### Что добавить

1. **Модели (расширение):**
   - `payout_method` — crypto / card / manual
   - `cryptomus_uuid` — ID выплаты в Cryptomus
   - `cryptomus_status` — статус в Cryptomus
   - `min_amount`, `max_amount` — лимиты (в настройках или в модели)
   - `fee_percent` — комиссия

2. **Сервис выплат (общий):**
   - `shared/services/payout_service.py`
   - `create_crypto_payout(seller_id|marketer_id, amount, wallet, currency)` → Cryptomus
   - `get_payout_status(uuid)`
   - `process_manual_payout()` — для ручных выплат

3. **Интеграция Cryptomus:**
   - При approve: если `payout_method=crypto` и реквизиты — валидный адрес → создать payout через Cryptomus
   - Webhook для статусов Cryptomus → обновить `SellerWithdrawal`/`MarketerWithdrawal`

4. **Web UI:**
   - Единая страница «Выплаты» или отдельные вкладки Seller/Marketer
   - Фильтры: статус, дата, тип
   - Выбор метода: crypto / manual
   - История выплат

5. **Боты:**
   - Выбор метода вывода (crypto / card)
   - Ввод реквизитов (адрес кошелька / карта)
   - Уведомления: заявка создана, одобрена, выплата отправлена, отклонена

6. **Лимиты и комиссии:**
   - Таблица `PayoutSettings` или поля в конфиге
   - Минимум/максимум вывода, комиссия %

---

### 3.2. Полное управление разделами навигации

**Сложность: средняя**

#### Вариант A: Навигация в БД

**Модели:**
```python
AdminNavGroup:  id, code, label, order, is_active, roles_required (JSON)
AdminNavItem:   id, group_id, label, href, icon, order, is_active, roles_required
```

**API:**
- `GET /api/admin-nav` — список групп и пунктов (для роли)
- `POST/PUT/DELETE` — CRUD для super_admin

**Шаблон:**
- `_nav.html` рендерит из `GET /api/admin-nav` или через Jinja context (передавать nav при рендере)

**Сложность:** нужно пройти все страницы и добавить роуты в `main.py`; при добавлении нового пункта — создавать роут и шаблон.

#### Вариант B: Гибрид (рекомендуется)

- **Группы и пункты** — в БД, с `order`, `label`, `href`, `icon`
- **Роуты** — остаются в коде (FastAPI не поддерживает динамические роуты из БД без доп. логики)
- **Смысл:** меняешь названия, порядок, скрываешь пункты — без деплоя кода

**Миграция:** скрипт заполняет `AdminNavGroup` и `AdminNavItem` из текущего `_nav.html`.

---

### 3.3. Управление категориями каталога (CATEGORIES_DATA)

**Сложность: высокая**

Сейчас `CATEGORIES_DATA` — это:
- Категории верхнего уровня (eSIM, DOCUMENTS, BANKS и т.д.)
- Подкатегории (eSIM for receive SMS, eSIM for Data)
- Сервисы с `code` и `name`

**Чтобы перенести в БД:**
- `CatalogCategory` (parent_id, code, name, order)
- `CatalogService` (category_id, code, name, order)
- `CatalogServiceGroup` (категория, подгруппа типа "eSIM for receive SMS")

**Проблема:** много мест в коде используют `CATEGORIES_DATA` и `SERVICE_TO_CATEGORY_MAPPING`. Нужно:
- Заменить все обращения на вызовы API или сервиса
- Обновить боты, отчёты, аналитику

---

## Часть 4. Оценка трудозатрат

| Задача | Сложность | Оценка |
|--------|-----------|--------|
| Расширенные выплаты (модели + Cryptomus + UI) | Средняя | 2–3 дня |
| Управление навигацией (БД + API + UI) | Средняя | 1–2 дня |
| Полный перенос CATEGORIES_DATA в БД | Высокая | 3–5 дней |

---

## Часть 5. Что имеем сейчас (кратко)

### Выплаты
- `SellerWithdrawal` — текущий seller payout flow
- `SellerWithdrawal` — legacy seller payout flow, требует миграционного решения
- `MarketerWithdrawal` — текущая модель маркетологов
- Web: approve/reject вручную
- Cryptomus: API есть, но не используется для выплат

### Навигация
- `_nav.html` — хардкод
- 6 групп, ~25 пунктов

### Категории
- `Category` + `Service` в БД — для страницы /categories
- `CATEGORIES_DATA` — хардкод для отчётов/маппинга
- CC, Education, Banks — свои таблицы в БД
