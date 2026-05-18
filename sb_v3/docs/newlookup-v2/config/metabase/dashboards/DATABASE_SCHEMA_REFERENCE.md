# 📋 Metabase Dashboards - Database Schema Reference

**Важно:** Используйте реальные названия таблиц и полей из этой схемы!

---

## ✅ **АКТУАЛЬНАЯ СХЕМА БАЗЫ ДАННЫХ**

### **Основные таблицы**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `users` | Пользователи | `id`, `user_id`, `username`, `balance`, `language`, `is_banned`, `mirror_bot_id`, `created_at` |
| `mirror_bots` | Боты | `id`, `bot_token`, `bot_username`, `owner_user_id`, `is_active`, `created_at` |
| `orders` | Заказы | `id`, `user_id`, `mirror_bot_id`, `category`, `service_name`, `price`, `status`, `created_at`, `completed_at` |
| `transactions` | Транзакции | `id`, `user_id`, `transaction_type`, `amount`, `status`, `created_at` |
| `support_tickets` | Тикеты поддержки | `id`, `user_id`, `subject`, `status`, `category`, `created_at`, `resolved_at` |

---

## 🏪 **Таблицы селлеров (10 таблиц)**

**Не существует таблицы `seller_products`!** Используйте отдельные таблицы:

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `sellers` | Профили селлеров | `id`, `user_id`, `is_active`, `balance`, `total_earned` |
| `seller_banks` | BANKS товары | `id`, `seller_id`, `bank_name`, `type`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_cc_items` | CC товары | `id`, `seller_id`, `category_code`, `bin`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_enroll_items` | Enroll товары | `id`, `seller_id`, `category_id`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_logs_items` | Logs товары | `id`, `seller_id`, `shop_name`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_nfc_items` | NFC товары | `id`, `seller_id`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_otp_items` | OTP товары | `id`, `seller_id`, `service_type`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_selfreg_cc_items` | Selfreg CC | `id`, `seller_id`, `category_id`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_check_items` | Check товары | `id`, `seller_id`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_document_items` | Documents | `id`, `seller_id`, `country`, `type`, `price`, `stock_quantity`, `moderation_status`, `is_active` |
| `seller_fullz_items` | Fullz товары | `id`, `seller_id`, `state`, `price`, `stock_quantity`, `moderation_status`, `is_active` |

---

## 🛒 **Таблицы заказов селлеров**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `seller_orders` | Заказы селлеров (универсальная) | `id`, `seller_id`, `buyer_id`, `product_type`, `product_id`, `total_amount`, `seller_amount`, `platform_fee`, `status` |
| `seller_withdrawals` | Выводы селлеров | `id`, `seller_id`, `amount`, `status`, `created_at`, `processed_at` |
| `seller_order_disputes` | Споры | `id`, `order_id`, `seller_id`, `buyer_id`, `status`, `resolution`, `refund_amount` |

---

## 💰 **Финансовые таблицы**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `transactions` | Транзакции | `id`, `user_id`, `transaction_type` (deposit/purchase/withdrawal/commission/refund), `amount`, `status` |
| `bot_owners` | Владельцы ботов | `id`, `owner_user_id`, `balance`, `total_earned`, `total_withdrawn` |
| `bot_owner_withdrawals` | Выводы владельцев | `id`, `owner_user_id`, `amount`, `status` |
| `worker_withdrawals` | Выводы воркеров | `id`, `worker_id`, `amount`, `status` |
| `marketer_withdrawals` | Выводы маркетологов | `id`, `marketer_id`, `amount`, `status` |

---

## 🤖 **Таблицы воркеров**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `workers` | Воркеры | `id`, `user_id`, `is_active`, `balance`, `total_earned` |
| `worker_orders` | Заказы воркеров | `id`, `order_id`, `worker_id`, `status`, `earned_amount` |
| `worker_withdrawals` | Выводы | `id`, `worker_id`, `amount`, `status` |
| `worker_violations` | Нарушения | `id`, `worker_id`, `violation_type`, `penalty_amount` |

---

## 📦 **Таблицы товаров (покупки)**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `products` | Товары (цифровые) | `id`, `name`, `price`, `category`, `is_active` |
| `product_purchases` | Покупки товаров | `id`, `user_id`, `product_id`, `purchased_at` |
| `product_catalog_services` | Каталог услуг | `id`, `name`, `category`, `price` |

---

## 🎯 **Таблицы маркетологов**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `marketers` | Маркетологи | `id`, `user_id`, `commission_rate`, `is_active` |
| `marketer_stats` | Статистика | `id`, `marketer_id`, `date`, `referrals_count`, `earnings` |
| `referrals` | Рефералы | `id`, `referrer_id`, `referred_id`, `created_at` |

---

## 📊 **Таблицы образования**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `education_categories` | Категории | `id`, `name`, `price` |
| `education_subscriptions` | Подписки | `id`, `user_id`, `category_id`, `expires_at` |
| `education_manuals` | Мануалы | `id`, `category_id`, `title`, `content` |

---

## 🃏 **Таблицы CC (Credit Cards)**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `cc_categories` | Категории CC | `id`, `code`, `name`, `region` |
| `cc_items` | CC товары | `id`, `category_id`, `card_number`, `price`, `is_sold` |
| `seller_cc_orders` | Заказы CC | `id`, `seller_id`, `buyer_id`, `item_id`, `amount` |

---

## 🏦 **Таблицы BANKS**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `bank_items` | BANKS товары | `id`, `bank_name`, `type`, `price`, `is_sold` |
| `brute_bank_items` | Brute BANKS | `id`, `bank_name`, `group_id`, `price`, `stock` |
| `brute_bank_orders` | Заказы Brute | `id`, `item_id`, `buyer_id`, `amount` |

---

## 🎫 **Таблицы купонов**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `coupons` | Купоны | `id`, `code`, `discount_type`, `discount_value`, `min_amount`, `max_uses` |
| `user_coupons` | Купоны пользователей | `id`, `user_id`, `coupon_code`, `is_used` |
| `coupon_redemptions` | Использования | `id`, `coupon_id`, `user_id`, `order_id`, `discount_amount` |

---

## 📝 **Таблицы администрирования**

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| `admins` | Админы | `id`, `user_id`, `role`, `permissions` |
| `admin_roles` | Роли | `id`, `name`, `permissions` |
| `admin_audit_logs` | Аудит | `id`, `admin_id`, `action`, `details`, `created_at` |
| `audit_logs` | Общий аудит | `id`, `user_id`, `action`, `entity_type`, `entity_id` |

---

## 🔧 **ПРАВИЛЬНЫЕ SQL ЗАПРОСЫ**

### ✅ Total Users
```sql
SELECT COUNT(*) as total_users
FROM users;
```

### ✅ Active Bots
```sql
SELECT COUNT(*) as active_bots
FROM mirror_bots
WHERE is_active = true;
```

### ✅ Total Sellers (ИСПРАВЛЕНО!)
```sql
SELECT COUNT(*) as total_sellers
FROM sellers
WHERE is_active = true;
```

### ✅ All Seller Products (ИСПРАВЛЕНО!)
```sql
-- UNION ALL для всех категорий товаров селлеров
SELECT 
  'banks' as category,
  id, seller_id, 
  bank_name as service_name,
  price, stock_quantity,
  moderation_status, is_active, created_at
FROM seller_banks

UNION ALL

SELECT 
  'cc' as category,
  id, seller_id,
  CONCAT(card_name, ' ', bin) as service_name,
  price, stock_quantity,
  moderation_status, is_active, created_at
FROM seller_cc_items

UNION ALL

SELECT 
  'enroll' as category,
  id, seller_id,
  CONCAT('Enroll ', category_id) as service_name,
  price, stock_quantity,
  moderation_status, is_active, created_at
FROM seller_enroll_items

-- ... повторить для всех 10 категорий
```

### ✅ Seller Orders (ИСПРАВЛЕНО!)
```sql
SELECT 
  so.id,
  so.seller_id,
  so.buyer_id,
  so.product_type,  -- 'bank', 'cc', 'enroll', etc.
  so.product_id,
  so.total_amount,
  so.seller_amount,
  so.platform_fee,
  so.status,
  so.created_at
FROM seller_orders so
WHERE so.created_at BETWEEN {{date_range.start}} AND {{date_range.end}}
```

### ✅ Transactions (ИСПРАВЛЕНО!)
```sql
SELECT 
  id,
  user_id,
  transaction_type,  -- deposit, purchase, withdrawal, commission, refund
  amount,
  status,
  created_at
FROM transactions
WHERE transaction_type IN ('deposit', 'purchase', 'withdrawal')
  AND created_at BETWEEN {{date_range.start}} AND {{date_range.end}}
```

### ✅ Bot Activity (ИСПРАВЛЕНО!)
```sql
-- Используем заказы как метрику активности
SELECT 
  DATE(created_at) as date,
  COUNT(*) as orders_count,
  COUNT(DISTINCT user_id) as unique_users
FROM orders
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date;
```

---

## ❌ **НЕПРАВИЛЬНЫЕ НАЗВАНИЯ (НЕ ИСПОЛЬЗОВАТЬ!)**

| ❌ Не существует | ✅ Правильное название |
|-----------------|----------------------|
| `mirror_bot` | `mirror_bots` |
| `seller_products` | `seller_banks`, `seller_cc_items`, ... (10 таблиц) |
| `bot_messages` | (не существует, использовать `orders`) |
| `bot_commands` | (не существует) |
| `users.role` | (не существует, селлеры в `sellers`) |
| `orders.refunded` | (статус не существует, использовать `transactions.type='refund'`) |

---

## 📊 **ПРИМЕРЫ ДАШБОРДОВ С ИСПРАВЛЕНИЯМИ**

См. файлы:
- `001_overview_FIXED.yml` - Исправленный Platform Overview
- `004_sellers_FIXED.yml` - Исправленный Sellers Analytics (с UNION)
- `008_bots_FIXED.yml` - Исправленный Bots Monitoring (без bot_messages)

---

**Обновлено:** March 25, 2026  
**Статус:** ✅ Актуальная схема базы данных
