# 🎛️ Metabase Web Admin Dashboards

**Дата:** March 25, 2026  
**Статус:** ✅ **6 ДАШБОРДОВ ДЛЯ ОСНОВНОЙ АДМИНКИ WEB PANEL**

---

## 📊 НОВЫЕ ДАШБОРДЫ (Основная Админка)

Создано **6 дашбордов** которые **дублируют и усиливают** функционал основной админки Web Panel:

| # | Дашборд | Файл | Аналог в Web Panel |
|---|---------|------|-------------------|
| 015 | 🎛️ **Web Admin Main** | `015_web_admin_main.yml` | `/api/dashboard.py` |
| 016 | 📦 **Orders Management** | `016_orders_management.yml` | `/api/orders.py` |
| 017 | 👥 **Users Management** | `017_users_management.yml` | `/api/users.py` |
| 018 | 👷 **Workers Management** | `018_workers_management.yml` | `/api/workers.py` |
| 019 | 📢 **Marketers Management** | `019_marketers_management.yml` | `/api/marketers.py` |
| 020 | 🤖 **Bots Management** | `020_bots_management.yml` | `/api/bots.py` |

---

## 🎛️ 015 - Web Admin Main (Основная Админка)

**Дублирует `/api/dashboard.py` + дополнительные метрики**

### Row 1: Key Stats (как в API)
- 👥 Total Users
- 🆕 New Users (period)
- 📦 Total Orders
- ⏳ Pending Orders
- ⚙️ Processing Orders
- ✅ Completed Orders

### Row 2: Finances
- 💰 Total Revenue
- 💵 Revenue (Period)
- 🛍️ Product Revenue
- 💳 User Balances Total

### Row 3: Moderation
- 🔍 Pending Moderation (Total)
- 🏦 Banks Pending
- 💳 CC Pending
- 📄 Documents Pending
- 📦 Other Pending

### Row 4: Support & Disputes
- 🎧 Open Tickets
- ⚖️ Open Disputes
- ⏳ Avg Response Time
- 🔴 Critical Tickets

### Row 5: Withdrawals
- 💸 Pending Withdrawals (All)
- 💰 Withdrawal Amount Pending
- 🏪 Seller Withdrawals Pending
- 👷 Worker Withdrawals Pending

### Row 6: Bots & Workers
- 🤖 Active Bots
- 👷 Total Workers
- 📢 Total Marketers
- 🏪 Total Sellers

### Row 7-8: Charts
- Revenue Trend (30 days)
- Orders by Status (pie)
- Orders by Category (bar)

---

## 📦 016 - Orders Management

**Дублирует `/api/orders.py` + расширенные фильтры**

### Summary (Row 1):
- 📦 Total Orders
- ⏳ Pending
- ⚙️ Processing
- ✅ Completed
- ❌ Cancelled
- 💰 Revenue

### Таблицы:
1. **All Orders** (Row 2) - все заказы с фильтрами:
   - Order ID, User ID, Status, Category filters
   - До 200 заказов
   - Actions: View / Assign / Edit

2. **Pending Orders** (Row 3) - ожидающие заказы:
   - Сортировка по created_at ASC
   - Actions: Assign Worker / View Details

3. **Processing Orders** (Row 4) - в работе:
   - С воркером
   - Время в работе (hours_in_progress)
   - Actions: View / Reassign

4. **Completed Orders** (Row 5) - завершенные:
   - С воркером
   - Время обработки (processing_minutes)
   - Feedback/Report статусы

### Charts (Row 6):
- Orders by Worker (bar)
- Processing Time by Category (bar)

---

## 👥 017 - Users Management

**Дублирует `/api/users.py` + расширенная аналитика**

### Summary (Row 1):
- 👥 Total Users
- 🆕 New Users
- 🚫 Banned Users
- 💰 Total Balances

### Таблицы:
1. **All Users** (Row 2) - все пользователи:
   - User ID, Username filters
   - Status: active/banned/new
   - Total orders, total spent
   - Actions: View / Edit / Ban / Adjust Balance

2. **Banned Users** (Row 3) - забаненные:
   - С причинами бана
   - Actions: Unban / Edit

3. **Top Users** (Row 4):
   - By Spending (20)
   - By Orders (20)

4. **Balance Distribution** (Row 5) - bar chart

5. **User Activity** (Row 5) - line chart (30 days)

6. **User Details** (Row 6) - для конкретного User ID:
   - Полная информация
   - Support tickets count
   - Product purchases count

7. **User Orders** (Row 7) - заказы пользователя

---

## 👷 018 - Workers Management

**Дублирует `/api/workers.py`**

### Summary (Row 1):
- 👷 Total Workers
- 📦 Busy Workers
- ⏳ Free Workers
- 💰 Total Worker Balances

### Таблицы:
1. **All Workers** (Row 2) - все воркеры:
   - Worker ID filter
   - Status: active/inactive
   - Completed orders, total revenue
   - Actions: Activate/Deactivate/View/Assign

2. **Worker Performance** (Row 3) - статистика (30 days):
   - Orders completed
   - Total revenue
   - Avg minutes per order
   - Balance, total_earned

3. **Worker Withdrawals Pending** (Row 4):
   - Все заявки на вывод
   - Actions: Approve/Reject

4. **Worker Violations** (Row 5):
   - Нарушения воркеров
   - Суммы штрафов

5. **Worker Activity** (Row 6) - line chart (7 days)

---

## 📢 019 - Marketers Management

**Дублирует `/api/marketers.py`**

### Summary (Row 1):
- 📢 Total Marketers
- 👥 Total Referrals
- 💰 Total Marketer Balances
- 💸 Pending Withdrawals

### Таблицы:
1. **All Marketers** (Row 2):
   - Marketer ID filter
   - Commission rate
   - Referrals count, active referrals
   - Actions: View / Edit / Deactivate

2. **Marketer Performance** (Row 3):
   - New referrals
   - Referrals orders
   - Commission earned
   - Actions: View Details

3. **Referrals by Marketer** (Row 4) - bar chart:
   - Top 20 маркетологов

4. **Marketer Withdrawals Pending** (Row 5):
   - Заявки на вывод
   - Actions: Approve/Reject

---

## 🤖 020 - Bots Management

**Дублирует `/api/bots.py`**

### Summary (Row 1):
- 🤖 Total Bots
- ✅ Active Bots
- ⏸️ Inactive Bots
- 👑 Total Bot Owners

### Таблицы:
1. **All Bots** (Row 2):
   - Bot ID, Status, Type filters
   - Owner username
   - Users count, orders count, revenue
   - Actions: View / Activate/Deactivate / Stats

2. **Bot Owners** (Row 3):
   - Balance, total_earned, total_withdrawn
   - Bots count
   - Pending withdrawals
   - Actions: View Bots / Withdrawals

3. **Bot Statistics** (Row 4):
   - Per bot stats
   - Users, orders, revenue
   - Period revenue

4. **Bot Activity** (Row 5) - line chart (7 days):
   - По каждому боту

5. **Bot Owner Withdrawals Pending** (Row 6):
   - Заявки владельцев ботов
   - Actions: Approve/Reject

---

## 📋 ИТОГОВАЯ СТАТИСТИКА

| Метрика | Значение |
|---------|----------|
| **Всего дашбордов** | **20** |
| Основных (аналитика) | 8 |
| Админских (модерация) | 6 |
| **Web Panel (основная админка)** | **6** |
| **SQL запросов** | **~200** |
| **Строк YAML** | **~4,500** |
| Таблиц используется | 30 |

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

### 3. Создать коллекцию "🎛️ Web Admin Panel"
```
Browse → Collections → + New Collection
Name: "🎛️ Web Admin Panel"
```

### 4. Импортировать 6 дашбордов Web Admin:
- 015_web_admin_main.yml
- 016_orders_management.yml
- 017_users_management.yml
- 018_workers_management.yml
- 019_marketers_management.yml
- 020_bots_management.yml

---

## ✅ ПРЕИМУЩЕСТВА METABASE vs WEB PANEL

| Характеристика | Web Panel | Metabase |
|----------------|-----------|----------|
| **Real-time данные** | ✅ Да | ✅ Да |
| **Фильтры** | ✅ Базовые | ✅ Расширенные |
| **Графики** | ⚠️ Ограничено | ✅ Много типов |
| **Экспорт** | ✅ CSV/Excel | ✅ CSV/Excel/PDF |
| **Алерты** | ❌ Нет | ✅ Email/Slack |
| **История** | ⚠️ Ограничена | ✅ 30 дней |
| **Кастомизация** | ❌ Fixed UI | ✅ Гибко |

---

## 💡 РЕКОМЕНДАЦИИ

### Для ежедневного использования:
1. **Web Admin Main (015)** - общий обзор
2. **Orders Management (016)** - управление заказами
3. **Users Management (017)** - работа с пользователями

### Для периодической проверки:
4. **Workers Management (018)** - воркеры и задания
5. **Marketers Management (019)** - рефералы и комиссии
6. **Bots Management (020)** - статистика ботов

---

**Статус:** ✅ **ГОТОВО К ИСПОЛЬЗОВАНИЮ**  
**Дата:** March 25, 2026
