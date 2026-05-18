# Seller Hub Mini App v2 — Архитектура обновления

> **Версия:** 2.0.0 · **Дата:** Март 2026 · **Автор:** Manus AI

---

## 1. Обзор системы

Seller Hub Mini App — это Telegram WebApp, встроенный в бота-продавца платформы NewLookup. Приложение предоставляет продавцам полный операционный интерфейс: чаты с покупателями, управление заказами, загрузку товаров, аналитику и финансы — всё внутри Telegram без перехода в браузер.

Версия 2 полностью переписана с нуля на **React 19 + TypeScript + Tailwind CSS 4** с дизайн-системой **Obsidian Glass** (glassmorphism, Material You Dark). Архитектура разделена на три независимых слоя: Telegram Platform Layer, Frontend SPA и Backend API.

---

## 2. Архитектурная схема

```
┌─────────────────────────────────────────────────────────────────┐
│                     TELEGRAM PLATFORM                           │
│  ┌──────────────────┐    ┌────────────────────────────────────┐ │
│  │   Seller Bot     │    │      Telegram WebApp SDK           │ │
│  │  (aiogram 3.x)   │◄──►│  initData · HapticFeedback         │ │
│  │                  │    │  MainButton · BackButton           │ │
│  └──────────────────┘    └────────────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS + X-Telegram-Init-Data
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FRONTEND SPA (React 19)                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    App Shell                            │   │
│  │  ┌──────────────┐  ┌────────────────────────────────┐  │   │
│  │  │  AppHeader   │  │         BottomNav (6 tabs)     │  │   │
│  │  └──────────────┘  └────────────────────────────────┘  │   │
│  │                                                         │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │              Tab Content Area                   │   │   │
│  │  │  ChatsTab · OrdersTab · UploadsTab              │   │   │
│  │  │  AnalyticsTab · FinanceTab · SettingsTab        │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   AppContext     │  │  api.ts      │  │  telegram.ts     │  │
│  │  (Global State) │  │  (API Client)│  │  (TG SDK Wrapper)│  │
│  └─────────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST JSON + FormData
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND API (FastAPI)                         │
│                                                                 │
│  /api/seller-mini-app/*                                         │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │  /me      │ │  /orders │ │/uploads  │ │  /analytics      │ │
│  │/convs     │ │          │ │/listings │ │  /finance        │ │
│  │/messages  │ │          │ │/templates│ │  /settings       │ │
│  └───────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL + SQLAlchemy ORM                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Стек технологий

| Слой | Технология | Версия | Назначение |
|------|-----------|--------|-----------|
| Frontend Runtime | React | 19.x | UI компоненты и хуки |
| Язык | TypeScript | 5.6 | Типобезопасность |
| Стилизация | Tailwind CSS | 4.x | Utility-first CSS |
| Компоненты | shadcn/ui + Radix | latest | Accessible primitives |
| Анимации | Framer Motion | 12.x | Spring-based transitions |
| Графики | Recharts | 2.x | Bar/Line charts |
| Роутинг | Wouter | 3.x | Lightweight SPA routing |
| Сборщик | Vite | 7.x | HMR + production build |
| Иконки | Lucide React | 0.45 | Icon library |
| Уведомления | Sonner | 2.x | Toast notifications |
| Backend | FastAPI | 0.115+ | REST API |
| ORM | SQLAlchemy | 2.x | Database access |
| БД | PostgreSQL | 15+ | Primary datastore |
| Telegram SDK | WebApp JS | latest | Platform integration |

---

## 4. Структура файлов Frontend

```
client/
├── index.html                    # Telegram WebApp SDK подключён здесь
├── src/
│   ├── App.tsx                   # Root: ThemeProvider + Router
│   ├── main.tsx                  # React entry point
│   ├── index.css                 # Obsidian Glass design tokens
│   │
│   ├── pages/
│   │   ├── SellerApp.tsx         # Главная page-shell (AppProvider wrapper)
│   │   └── Home.tsx              # Redirect placeholder
│   │
│   ├── components/
│   │   ├── AppHeader.tsx         # Header: avatar, name, unread badge
│   │   ├── BottomNav.tsx         # Navigation: 6 tabs с badges
│   │   └── tabs/
│   │       ├── ChatsTab.tsx      # Чаты + inline chat view
│   │       ├── OrdersTab.tsx     # Список заказов с фильтрами
│   │       ├── UploadsTab.tsx    # Загрузка товаров (bank/brute/batches/listings)
│   │       ├── AnalyticsTab.tsx  # KPI + funnel + top products chart
│   │       ├── FinanceTab.tsx    # Баланс + вывод + экспорт CSV
│   │       └── SettingsTab.tsx   # Профиль + vacation + quiet hours
│   │
│   ├── contexts/
│   │   ├── AppContext.tsx        # Global state: seller, conversations, tab
│   │   └── ThemeContext.tsx      # Dark theme provider
│   │
│   ├── lib/
│   │   ├── api.ts                # Typed API client + все интерфейсы домена
│   │   ├── telegram.ts           # Telegram WebApp SDK wrapper
│   │   ├── mockData.ts           # Demo-mode fallback data
│   │   └── utils.ts              # cn, fmtMoney, fmtTime, fmtStatus, etc.
│   │
│   └── components/ui/            # shadcn/ui components
```

---

## 5. Слой Telegram Platform

### 5.1 Инициализация

При запуске Mini App вызывается `initTelegram()` из `telegram.ts`. Функция вызывает `WebApp.ready()` (скрывает splash screen) и `WebApp.expand()` (разворачивает на полный экран). Это должно происходить как можно раньше — в `useEffect` на верхнем уровне `AppProvider`.

### 5.2 Аутентификация

Telegram передаёт `initData` — подписанную строку с данными пользователя. Фронтенд отправляет её в каждом запросе через заголовок `X-Telegram-Init-Data`. Бэкенд верифицирует подпись с помощью `HMAC-SHA256` и секрета бота, затем извлекает `telegram_id` пользователя.

Для локальной разработки без Telegram используется query-параметр `?dev_tg_id=123456789`, который подставляется в заголовок `X-Dev-Seller-Telegram-Id`.

```
Production:  X-Telegram-Init-Data: query_id=...&user=...&hash=...
Development: X-Dev-Seller-Telegram-Id: 123456789
```

### 5.3 Haptic Feedback

Все интерактивные действия используют `haptic()` из `telegram.ts`:

| Действие | Тип |
|---------|-----|
| Нажатие на таб | `selection` |
| Отправка сообщения | `light` |
| Успешная операция | `success` |
| Ошибка | `error` |

---

## 6. Глобальное состояние (AppContext)

`AppContext` — единственный источник истины для всего приложения. Он инициализируется в `AppProvider` и предоставляет данные через хук `useApp()`.

### 6.1 Структура состояния

```typescript
interface AppState {
  seller: SellerMe | null;          // Профиль продавца
  conversations: Conversation[];    // Список чатов
  unreadTotal: number;              // Сумма непрочитанных
  activeTab: TabId;                 // Текущий активный таб
  isLoading: boolean;               // Начальная загрузка
  error: string | null;             // Глобальная ошибка
  isDemoMode: boolean;              // Fallback на mock data
}
```

### 6.2 Жизненный цикл

```
mount → initTelegram() → api.me() ──success──► setSeller + setDemoMode(false)
                                  └─failure──► setSeller(MOCK_SELLER) + setDemoMode(true)
                       → api.conversations() ──success──► setConversations
                                             └─failure──► setConversations(MOCK_CONVERSATIONS)
                       → setIsLoading(false)
                       → setInterval(refreshConversations, 15000)  // polling
```

### 6.3 Demo Mode

Если бэкенд недоступен (нет CORS, нет токена, сеть), приложение автоматически переключается в **Demo Mode**: все данные берутся из `mockData.ts`. Это позволяет продемонстрировать UI без бэкенда и не показывать пустые экраны. В `SettingsTab` отображается предупреждение о demo-режиме.

---

## 7. API Client

Все обращения к бэкенду централизованы в `api.ts`. Базовый путь: `/api/seller-mini-app`.

### 7.1 Методы API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `api.me()` | `GET /me` | Профиль продавца |
| `api.conversations()` | `GET /conversations` | Список чатов |
| `api.messages(id)` | `GET /messages?conversation_id=` | Сообщения чата |
| `api.send(fd)` | `POST /send` | Отправить сообщение/файл |
| `api.orders(filter)` | `GET /orders?status_filter=` | Заказы с фильтром |
| `api.batches()` | `GET /uploads/batches` | Батчи загрузок |
| `api.listings()` | `GET /listings` | Активные листинги |
| `api.analyticsSummary()` | `GET /analytics/summary` | KPI сводка |
| `api.analyticsFunnel()` | `GET /analytics/funnel` | Воронка конверсии |
| `api.abandonedCarts()` | `GET /analytics/abandoned-carts` | Брошенные корзины |
| `api.financeSummary()` | `GET /finance/summary` | Финансовая сводка |
| `api.financeExport()` | `GET /finance/export.csv` | CSV экспорт |
| `api.withdraw(amount, req)` | `POST /finance/withdraw` | Запрос вывода |
| `api.uploadSubmit(type, payload)` | `POST /uploads/submit` | Загрузка товара |
| `api.bulkPrice(mode, value)` | `POST /listings/bulk-price` | Массовое изменение цен |
| `api.setVacation(mode, ends)` | `POST /settings/vacation` | Режим отпуска |
| `api.setAutoPayout(enabled)` | `POST /settings/auto-payout` | Авто-вывод |
| `api.setQuietHours(from, to)` | `POST /settings/quiet-hours` | Тихие часы |

### 7.2 Обработка ошибок

Все методы бросают `Error` с текстом из поля `detail` ответа FastAPI. Компоненты ловят ошибки через `try/catch` и показывают `toast.error()`. При сетевой ошибке на уровне `AppContext` включается demo mode.

---

## 8. Компоненты и их ответственность

### 8.1 ChatsTab

Двухпанельный layout: список чатов слева (или полный экран на мобильном) и inline chat view справа. Поддерживает поиск по имени покупателя и продукту. Отправка сообщений через `FormData` с поддержкой файловых вложений. На мобильном — переключение между `list` и `chat` view через локальный state `mobileView`.

### 8.2 OrdersTab

Список заказов с фильтрами: `active | all | completed | disputed`. Каждая карточка раскрывается по клику, показывая детали. Статусы отображаются цветными бейджами через `statusBg()`. Диспуты выделяются красным предупреждением.

### 8.3 UploadsTab

Четыре под-таба: **Bank** (форма загрузки банковского аккаунта), **Brute** (single/bulk загрузка брутфорс данных), **Batches** (история загрузок с статусами модерации), **Listings** (активные листинги + массовое изменение цен + шаблоны).

### 8.4 AnalyticsTab

KPI-сетка (6 метрик), визуальная воронка конверсии с progress bars, bar chart топ-продуктов через Recharts, список брошенных корзин.

### 8.5 FinanceTab

Главная карточка с доступным балансом и pending, сетка из 4 финансовых метрик, форма вывода средств с валидацией, кнопка экспорта CSV.

### 8.6 SettingsTab

Профильная карточка с инициалами и статусами, тоглы vacation mode и auto-payout, форма тихих часов, информационные строки, ссылка на поддержку.

---

## 9. Дизайн-система Obsidian Glass

### 9.1 Цветовая палитра (OKLCH)

| Токен | Значение | Назначение |
|-------|---------|-----------|
| `--background` | `oklch(0.09 0.012 260)` | Основной фон (#0D1117) |
| `--card` | `oklch(0.13 0.014 260)` | Фон карточек |
| `--primary` | `oklch(0.62 0.22 258)` | Electric Blue — CTA, активные элементы |
| `--accent` | `oklch(0.70 0.18 196)` | Cyan-Teal — акценты |
| `--success` | `oklch(0.72 0.18 145)` | Зелёный — completed, approved |
| `--destructive` | `oklch(0.65 0.22 25)` | Rose — ошибки, disputed |
| `--warning` | `oklch(0.80 0.18 60)` | Amber — pending, vacation |

### 9.2 Компонентные классы

**`.glass-card`** — базовая стеклянная карточка:
```css
background: oklch(1 0 0 / 0.04);
border: 1px solid oklch(1 0 0 / 0.08);
backdrop-filter: blur(20px);
border-radius: 0.875rem;
```

**`.app-shell`** — контейнер приложения: `height: 100dvh`, `max-width: 480px`, `overflow: hidden`.

**`.tabular`** — моноширинные цифры для финансовых данных: `font-family: "DM Mono"`.

### 9.3 Типографика

| Шрифт | Использование |
|-------|--------------|
| DM Sans 300–700 | Основной интерфейсный шрифт |
| DM Mono 400–500 | Числа, коды, финансовые данные |

---

## 10. Инструкция по обновлению бэкенда

### 10.1 Новые эндпоинты (требуют реализации)

Следующие эндпоинты используются в v2, но могут отсутствовать в текущем бэкенде:

| Эндпоинт | Метод | Приоритет | Описание |
|----------|-------|-----------|----------|
| `/api/seller-mini-app/analytics/funnel` | GET | High | Воронка конверсии |
| `/api/seller-mini-app/analytics/abandoned-carts` | GET | Medium | Брошенные корзины |
| `/api/seller-mini-app/templates` | GET/POST/DELETE | Medium | Шаблоны загрузок |
| `/api/seller-mini-app/settings/quiet-hours` | POST | Low | Тихие часы уведомлений |
| `/api/seller-mini-app/settings/auto-payout` | POST | Medium | Авто-вывод |
| `/api/seller-mini-app/listings/bulk-price` | POST | High | Массовое изменение цен |
| `/api/seller-mini-app/finance/export.csv` | GET | High | CSV экспорт транзакций |

### 10.2 Изменения в существующих эндпоинтах

**`GET /conversations`** — добавить поле `unread_count: int` в ответ каждого объекта.

**`GET /orders`** — параметр `status_filter` должен принимать значения: `active`, `all`, `completed`, `disputed`. Значение `active` должно возвращать заказы со статусами `approved` и `in_progress`.

**`GET /analytics/summary`** — добавить поля:
- `orders_30d: int` — заказы за 30 дней
- `revenue_30d: float` — выручка за 30 дней
- `avg_order_value: float` — средний чек
- `conversion_rate: int` — конверсия в %
- `active_listings: int` — активные листинги
- `items_sold: int` — продано товаров
- `disputes: int` — количество диспутов
- `completion_rate: int` — % завершённых заказов
- `top_products: list[{id, bank_name, revenue, count}]`

**`GET /finance/summary`** — добавить поле `markup_percent: float | null`.

### 10.3 Схема аутентификации

```python
# FastAPI dependency для Telegram Mini App auth
async def get_seller_from_telegram(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Seller:
    init_data = request.headers.get("X-Telegram-Init-Data")
    dev_id = request.headers.get("X-Dev-Seller-Telegram-Id")

    if init_data:
        # Production: verify HMAC-SHA256
        telegram_id = verify_telegram_init_data(init_data, BOT_TOKEN)
    elif dev_id and settings.DEBUG:
        # Development: trust dev header
        telegram_id = int(dev_id)
    else:
        raise HTTPException(401, "Unauthorized")

    seller = await db.get_seller_by_telegram_id(telegram_id)
    if not seller:
        raise HTTPException(403, "Seller not found")
    return seller
```

### 10.4 CORS настройка

Для работы Mini App в Telegram WebView необходимо разрешить CORS для домена `*.telegram.org` и домена вашего фронтенда:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.telegram.org",
        "https://your-mini-app-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Telegram-Init-Data", "X-Dev-Seller-Telegram-Id"],
)
```

---

## 11. Деплой и интеграция

### 11.1 Переменные окружения фронтенда

| Переменная | Описание |
|-----------|---------|
| `VITE_ANALYTICS_ENDPOINT` | URL Umami analytics |
| `VITE_ANALYTICS_WEBSITE_ID` | ID сайта в Umami |
| `VITE_APP_TITLE` | Название приложения |

### 11.2 Регистрация в Telegram

В BotFather необходимо установить URL Mini App через команду `/newapp` или `/editapp`. URL должен указывать на задеплоенный фронтенд. Для разработки можно использовать ngrok или аналог.

### 11.3 Порядок деплоя

1. Собрать фронтенд: `pnpm build`
2. Загрузить `dist/` на CDN или статический хостинг
3. Обновить URL в BotFather
4. Задеплоить бэкенд с новыми эндпоинтами
5. Проверить CORS и аутентификацию через Telegram WebApp

---

## 12. Сравнение v1 vs v2

| Аспект | v1 (web_panel) | v2 (seller_mini_app_v2) |
|--------|---------------|------------------------|
| Технологии | Jinja2 + Vanilla JS + CSS | React 19 + TypeScript + Tailwind 4 |
| Типизация | Нет | Полная TypeScript |
| Дизайн | Bootstrap-like, светлая тема | Obsidian Glass, тёмная тема |
| Анимации | Нет | Framer Motion spring-анимации |
| Offline/Demo | Нет | Автоматический fallback на mock data |
| Telegram SDK | Базовая интеграция | Полная: haptic, expand, initData auth |
| Графики | Нет | Recharts (bar chart, funnel) |
| Производительность | Полная перезагрузка страниц | SPA с tab-switching без reload |
| Polling чатов | Нет | Каждые 15 секунд |
| Мобильная навигация | Bottom nav | Bottom nav + inline chat view |
| Загрузка файлов | Базовая | Drag & drop + file preview |
| Bulk операции | Нет | Bulk reprice с режимами percent/delta/set |
| Шаблоны загрузок | Нет | Сохранение и переиспользование шаблонов |

---

## 13. Roadmap следующих версий

Следующие функции запланированы для реализации в последующих итерациях:

**v2.1 — Push Notifications.** Интеграция с Telegram Bot API для отправки уведомлений о новых заказах и сообщениях напрямую в чат продавца.

**v2.2 — Real-time чаты.** Замена polling на WebSocket соединение через FastAPI WebSocket endpoint для мгновенной доставки сообщений.

**v2.3 — Расширенная аналитика.** Временные графики выручки (7d/30d/90d), когортный анализ покупателей, тепловая карта активности по часам.

**v2.4 — Dispute Resolution UI.** Встроенный интерфейс для работы с диспутами: просмотр доказательств, отправка контраргументов, история решений.

**v2.5 — Multi-seller (Helper mode).** Полноценный интерфейс для помощников продавца с разграничением прав: upload-only, chat-only, full-access.
