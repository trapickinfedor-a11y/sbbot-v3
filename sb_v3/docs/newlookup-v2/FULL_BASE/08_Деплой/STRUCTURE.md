# 📁 Полная структура проекта NewLookup

## 🏗️ Обзор архитектуры

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEWLOOKUP — Маркетплейс банков/CC                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  ПОКУПАТЕЛИ   │           │   СЕЛЛЕРЫ     │           │    АДМИН      │
│  Mirror Bot   │◄─────────►│  Seller Bot   │◄─────────►│ Web Panel    │
│  (много ботов)│   чат     │  (1 бот)      │  модерация │ Support Bot  │
└───────────────┘           └───────────────┘           └───────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
                        ┌─────────────────────────┐
                        │  PostgreSQL / SQLite    │
                        │  shared/database/       │
                        └─────────────────────────┘
```

---

## 📂 Структура директорий

```
newlookup/
├── main_bot/              # Главный бот (точка входа для mirror)
├── mirror_bot/            # Боты покупателей (каждый магазин = свой бот)
├── support_bot/           # Админ-бот: заказы, модерация, уведомления
├── seller_bot/            # Бот для селлеров (склад, заказы, чат)
├── marketer_bot/          # Реферальная система
├── web_panel/             # Веб-панель админа (FastAPI)
├── shared/                # Общий код: БД, утилиты, сервисы
├── scripts/               # Миграции, утилиты
├── run_local.py           # Локальный запуск (SQLite)
├── docker-compose.yml     # Docker-запуск (PostgreSQL)
└── .env                   # Конфигурация
```

---

## 🤖 Seller Bot — полная структура

### Файлы и модули

```
seller_bot/
├── bot.py                 # Точка входа, роутеры
├── config.py              # SELLER_BOT_TOKEN, admin_ids
├── run.py                 # Запуск
├── utils.py               # get_seller_unread_count()
│
├── handlers/
│   ├── start.py           # /start, /register, главное меню
│   ├── stock.py           # Banks: добавить, список, toggle, цена
│   ├── orders.py          # Мои заказы, детали, Complete
│   ├── chat.py            # Чат с покупателями
│   ├── profile.py         # Профиль селлера
│   ├── cc_stock.py        # CC товары
│   ├── brute_bank.py      # Brute Bank
│   ├── withdrawal.py      # Вывод средств
│   └── broadcast.py      # Рассылки (если есть)
│
├── middlewares/
│   ├── database.py        # Сессия БД
│   └── seller_auth.py     # Проверка is_seller, is_admin
│
├── keyboards/
│   └── inline.py          # seller_main_menu, order_keyboard, chat_keyboard
│
└── services/
    ├── seller_service.py  # Регистрация, approve
    ├── stock_service.py   # Работа со складом банков
    └── cc_stock_service.py
```

### Поток данных Seller Bot

```
Покупатель (mirror_bot) покупает банк
    → SellerOrder создаётся (pending_admin)
    → Support Bot уведомляет админа
    → Админ одобряет (Support Bot)
    → Seller Bot уведомляет селлера
    → Селлер видит заказ в "My Orders"
    → Селлер может: Complete / Chat
```

---

## 💬 Чат селлер ↔ клиент

### Схема

```
┌─────────────────┐                    ┌─────────────────┐
│   ПОКУПАТЕЛЬ   │                    │     СЕЛЛЕР      │
│   (mirror_bot) │                    │  (seller_bot)   │
└────────┬────────┘                    └────────┬────────┘
         │                                     │
         │  buyer_chat:123                     │  seller_chat:123
         │  My Orders → Chat                  │  My Orders → Chat
         │                                     │
         └──────────────┬──────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   seller_chats      │
              │   (БД)              │
              │   - seller_order_id │
              │   - sender_type     │
              │   - message_text    │
              │   - files           │
              └─────────────────────┘
```

### Файлы чата

| Компонент | Файл | Роль |
|-----------|------|------|
| Покупатель | `mirror_bot/handlers/buyer_chat.py` | Вход в чат, отправка, dispute |
| Селлер | `seller_bot/handlers/chat.py` | Вход в чат, отправка, список непрочитанных |
| Общее | `shared/utils/chat_render.py` | build_chat_text, клавиатуры, пагинация |
| Фильтр | `shared/utils/chat_filter.py` | Блокировка ссылок/контактов |
| Модель | `shared/database/models.py` | SellerChat, SellerOrder |

### Пересылка сообщений

- **Покупатель → Селлер**: `_forward_to_seller()` в buyer_chat.py → send в seller_bot
- **Селлер → Покупатель**: `_forward_to_buyer()` в chat.py → send через mirror_bot

---

## 📦 Модели БД (связь селлер–клиент)

```
Seller
  └── seller_orders[] → SellerOrder
          ├── seller_id
          ├── buyer_user_id      # Telegram ID покупателя
          ├── mirror_bot_id      # Через какой бот купил
          ├── seller_bank_id
          ├── status
          └── chat_messages[] → SellerChat
                  ├── sender_type  # buyer | seller | admin
                  ├── message_text
                  ├── files
                  └── is_read
```

---

## 🌐 Web Panel — Seller CRM

| URL | Описание |
|-----|----------|
| `/seller-crm` | Kanban заказов (Новые, Ожидают, В работе, Завершены) |
| `/sellers` | Список селлеров, approve/toggle |
| `/api/seller-crm/orders` | API заказов |
| `/api/seller-crm/withdrawals` | Выводы средств |

---

## 🔧 Запуск

```bash
# Локально (SQLite)
DATABASE_URL="sqlite+aiosqlite:///./data/newlookup.db" python3 run_local.py

# Docker (PostgreSQL)
docker-compose up -d
```

---

## 📋 Улучшения (реализовано)

- [x] **Быстрые ответы (шаблоны)** — в чате селлера: "Got it", "Soon", "Info", "Done"
- [x] **Быстрые ответы для покупателя** — "When ready?", "Status?", "Got it"
- [x] **Кнопка "Reply"** — в push-уведомлениях покупателю при сообщении от селлера
- [x] **Группировка заказов** — активные (approved, in_progress) показываются первыми
- [x] **Компактный список заказов** — короткие статусы (Wait, Work, Done)

## 📋 Возможные доработки

- [ ] Просмотр чата в Web Panel (Seller CRM)
- [ ] Push-уведомления о новых сообщениях (звук)
