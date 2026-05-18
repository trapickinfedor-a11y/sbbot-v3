# 🎛️ Metabase Admin Dashboards

**Дата:** March 25, 2026  
**Статус:** ✅ **6 СПЕЦИАЛЬНЫХ ДАШБОРДОВ ДЛЯ АДМИНКИ**

---

## 📊 НОВЫЕ ДАШБОРДЫ ДЛЯ АДМИНКИ

Создано **6 специализированных дашбордов** для администраторов платформы:

| # | Дашборд | Файл | Назначение |
|---|---------|------|------------|
| 009 | 🎛️ Admin Main | `009_admin_dashboard.yml` | Главная панель - все ключевые метрики |
| 010 | 🔍 Moderation Queue | `010_moderation_queue.yml` | Очередь модерации товаров |
| 011 | 💸 Withdrawals Admin | `011_withdrawals_admin.yml` | Управление выводами средств |
| 012 | 👥 Users Admin | `012_users_admin.yml` | Управление пользователями |
| 013 | 🏪 Sellers Admin | `013_sellers_admin.yml` | Управление селлерами |
| 014 | 🎧 Support Admin | `014_support_admin.yml` | Поддержка и диспуты |

---

## 🎛️ 009 - Admin Main Dashboard

**Главная панель администратора - быстрый обзор всего**

### Метрики (Row 1):
- 👥 Total Users
- 📈 Active Users (24h)
- 🤖 Active Bots
- 💰 Total Revenue
- 📦 Total Orders
- ⚠️ Pending Orders

### Модерация (Row 2):
- 🔍 Pending Moderation (All Types) - сумма по всем 10 типам товаров
- 🏦 Banks Pending
- 💳 CC Pending
- 📄 Documents Pending
- 📊 Other Pending

### Поддержка (Row 3):
- 🎧 Open Support Tickets
- 🔴 Critical Priority
- ⏳ Avg Response Time
- ⚖️ Open Disputes
- 🔥 Awaiting Admin Action

### Финансы (Row 4):
- 💸 Pending Withdrawals (все типы)
- 💰 Total Withdrawal Amount
- 🏦 User Balances Total
- 📊 Today's Revenue

### Графики:
- Revenue Trend (7 days) - линейный график
- Orders by Status - pie chart
- Orders by Category - bar chart

---

## 🔍 010 - Moderation Queue

**Очередь модерации - приоритетная задача для админов**

### Summary (Row 1):
- 📊 Total Pending - общее количество
- 🏦 Banks
- 💳 CC
- 📄 Documents
- 🎫 Enroll
- 📝 Logs
- 📱 NFC
- 🔐 OTP
- 💳 Selfreg CC
- ✅ Checks
- 📦 Fullz

### Таблицы на модерацию (Rows 2-11):
Для каждого типа товаров отдельная таблица с полями:
- ID
- Seller ID
- Название/описание товара
- Цена
- Количество
- Дата создания
- Кнопка действия "Approve/Reject"

**Таблицы:**
1. 🏦 Pending Banks
2. 💳 Pending CC Items
3. 📄 Pending Documents
4. 🎫 Pending Enroll
5. 📝 Pending Logs
6. 📱 Pending NFC
7. 🔐 Pending OTP
8. 💳 Pending Selfreg CC
9. ✅ Pending Checks
10. 📦 Pending Fullz

---

## 💸 011 - Withdrawals Admin

**Управление всеми выводами средств**

### Summary (Row 1):
- 📊 Total Pending - все заявки
- 💰 Total Amount Pending - общая сумма
- ✅ Completed Today - выполнено сегодня
- 💵 Paid Today - выплачено сегодня

### Таблицы заявок (Rows 2-5):
1. 🏪 Seller Withdrawals
2. 👷 Worker Withdrawals
3. 📢 Marketer Withdrawals
4. 🤖 Bot Owner Withdrawals

Каждая таблица содержит:
- ID заявки
- User ID и username
- Сумма
- Payment method/network
- Реквизиты
- TX hash (для crypto)
- Статус
- Дата создания/обработки
- Кнопка "Approve/Reject"

### Статистика (Row 6):
- Withdrawals by Status - pie chart
- Withdrawals Trend - line chart

---

## 👥 012 - Users Admin

**Администрирование пользователей**

### Summary (Row 1):
- 👥 Total Users
- 🚫 Banned Users
- 🆕 New Users (24h)
- 💰 Total User Balances

### Таблицы (Rows 2-3):
1. 🚫 Banned Users - все забаненные с причинами
2. 🔍 Search User - поиск по User ID с фильтрами

### Топы (Row 4):
1. 💎 Top Users by Spending
2. 🎰 Top Users by Orders

### Распределение (Row 5):
- 💰 Balance Distribution - bar chart
- 📈 User Activity (7 days) - line chart

### Нарушения (Row 6):
- ⚠️ Recent Violations - таблица нарушений воркеров

---

## 🏪 013 - Sellers Admin

**Управление селлерами**

### Summary (Row 1):
- 🏪 Total Sellers
- ✅ Active Sellers
- ⏸️ Inactive Sellers
- 💰 Total Seller Balances

### Таблицы (Row 2):
- 🏪 All Sellers - все селлеры с фильтрами
  - Показывает: balance, total_earned, total_withdrawn, is_active, deposit_paid
  - Количество товаров по категориям
  - Количество заказов
  - Кнопки действий

### Топы (Row 3):
1. 💎 Top Sellers by Revenue (30 дней)
2. 📦 Top Sellers by Products

### Статистика (Row 4):
- 📊 Products by Seller - bar chart (топ 30)

### Новые (Row 5):
- 🆕 Recent Seller Registrations (7 дней)

### Активность (Row 6):
- 📈 Seller Activity (7 days) - line chart

---

## 🎧 014 - Support Admin

**Администрирование поддержки**

### Summary (Row 1):
- 🎫 Open Tickets
- 🔴 Critical
- 🟠 High Priority
- ⏳ Avg Response Time
- ⏱️ Avg Resolution Time

### Таблицы (Row 2-3):
1. 🎫 All Tickets - все тикеты с фильтрами по статусу и приоритету
2. ⚖️ Open Disputes - открытые диспуты

### Статистика (Row 4):
1. 📊 Tickets by Status - pie chart
2. 📊 Tickets by Priority - bar chart с avg response time
3. 📊 Disputes by Outcome - pie chart

### Активность (Row 5):
- 📈 Support Activity (7 days) - line chart

### Агенты (Row 6):
- 👥 Support Agents Performance - таблица эффективности

---

## 📋 ИСПОЛЬЗУЕМЫЕ ТАБЛИЦЫ

Все дашборды используют **реальные таблицы** из `shared/database/models.py`:

| Таблица | Дашборды |
|---------|----------|
| `users` | 009, 012 |
| `mirror_bots` | 009 |
| `orders` | 009 |
| `seller_banks` | 009, 010 |
| `seller_cc_items` | 009, 010 |
| `seller_enroll_items` | 009, 010 |
| `seller_logs_items` | 009, 010 |
| `seller_nfc_items` | 009, 010 |
| `seller_otp_items` | 009, 010 |
| `seller_selfreg_cc_items` | 009, 010 |
| `seller_check_items` | 009, 010 |
| `seller_document_items` | 009, 010 |
| `seller_fullz_items` | 009, 010 |
| `sellers` | 013 |
| `seller_withdrawals` | 009, 011 |
| `worker_withdrawals` | 009, 011 |
| `marketer_withdrawals` | 009, 011 |
| `bot_owner_withdrawals` | 009, 011 |
| `support_tickets` | 009, 014 |
| `seller_order_disputes` | 009, 014 |
| `worker_violations` | 012 |
| `admins` | 014 |

---

## 🚀 КАК ИСПОЛЬЗОВАТЬ

### 1. Запустить Metabase
```bash
docker-compose -f docker-compose.metabase.yml up -d
```

### 2. Открыть в браузере
```
http://localhost:3000
```

### 3. Создать коллекцию "Admin Dashboards"
```
Browse → Collections → + New Collection
Name: "🎛️ Admin Dashboards"
```

### 4. Импортировать каждый дашборд
Для каждого YAML файла:
1. Открыть файл
2. Создать вопросы по SQL запросам
3. Добавить на дашборд
4. Расположить карточки согласно `position`

---

## ✅ ПРЕИМУЩЕСТВА

1. **Централизованное управление** - все в одном месте
2. **Приоритетная очередь** - модерация по типам товаров
3. **Быстрые действия** - кнопки Approve/Reject
4. **Полная статистика** - графики и тренды
5. **Фильтрация** - по статусам, приоритетам, датам
6. **Поиск** - по User ID, Seller ID, Ticket ID

---

## 📊 ОБЩАЯ СТАТИСТИКА

| Метрика | Значение |
|---------|----------|
| Всего дашбордов | 14 (8 основных + 6 админских) |
| Админских дашбордов | 6 |
| SQL запросов в админских | ~60 |
| Таблиц используется | 22 |
| Файлов создано | 6 YAML + 1 MD |

---

**Статус:** ✅ **ГОТОВО К ИСПОЛЬЗОВАНИЮ**  
**Дата:** March 25, 2026
