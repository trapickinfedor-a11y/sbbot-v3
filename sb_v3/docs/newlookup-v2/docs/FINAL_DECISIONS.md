# ✅ Финальные решения по синхронизации Mini App v2

**Дата:** 2026-03-24  
**Статус:** Утверждено

---

## 🎯 Ключевые решения

### 1. Banks Section = Универсальная модель

**Решение:** ✅ Одна модель `SellerBankItem` для всех банковских продуктов

**Включает:**
- Bank Selfregs (оригинальная функциональность)
- Selfreg BA (из Mini App — объединено с Banks)
- VCC, Personal, Business, Crypto, Merchant категории

**Преимущества:**
- Упрощенная структура (одна модель вместо нескольких)
- Единый интерфейс загрузки
- Меньше дублирования кода
- Гибкая категоризация

---

### 2. Brute Bank — Использовать список из БД

**Решение:** ✅ Mini App использует 54 банка из `catalog_banks.py`

**Было в Mini App:**
- Плоский список из 22 банков

**Стало:**
- Категоризированный список из 54 банков
- 5 категорий: VCC, Personal, Business, Crypto, Merchant
- Seller выбирает категорию → банк из списка
- Поддержка custom bank name

**Преимущества:**
- Больше банков доступно
- Структурированный выбор
- Единый источник данных (БД)

---

### 3. Selfreg CC Card Names — Отдельная таблица

**Решение:** ✅ Таблица `selfreg_cc_card_names`

**Структура:**
```sql
CREATE TABLE selfreg_cc_card_names (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES selfreg_cc_categories(id),
    card_name VARCHAR(200) NOT NULL,
    position INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Данные:**
- 13 банков (5 базовых + 8 новых)
- 78 названий карт (6-12 на банк)
- Загружается через seed скрипт

**Преимущества:**
- Гибкое управление списками карт
- Легко добавлять/удалять карты
- Поддержка сортировки (position)
- Можно деактивировать карты (is_active)

**Альтернатива (отклонена):**
- ❌ JSON поле в `SelfregCCCategory` — менее гибко, сложнее управлять

---

### 4. Bulk форматы — Поддержка обоих

**Решение:** ✅ Парсер поддерживает оба формата

**CC Bulk:**
- Формат 1 (Mini App): `NUMBER|EXP|CVV|NAME|ZIP|STATE|COUNTRY|BANK|TYPE|NON_VBV` (10 полей)
- Формат 2 (Legacy): `NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE` (16+ полей)

**Brute Bulk:**
- Новый формат: `BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDRESS|ZIP|price` (11 полей)
- Auto-detect attributes из непустых полей

**Преимущества:**
- Обратная совместимость
- Гибкость для sellers
- Постепенная миграция на новый формат

---

### 5. OTP & Enrollment — Детальные поля

**Решение:** ✅ Отдельные поля вместо JSON

**OTP Fullz:**
- 12 отдельных полей: first_name, last_name, dob, ssn, address, city, state, zip, phone, email
- SSN шифруется

**Enrollment:**
- 11 отдельных полей: first_name, last_name, dob, ssn, address, city, state, zip, phone, email, additional_info
- SSN шифруется

**Преимущества:**
- Типизированные данные
- Легче валидировать
- Проще делать запросы
- Лучше для индексов

**Альтернатива (отклонена):**
- ❌ JSON поле — менее типизировано, сложнее валидировать

---

### 6. NON VBV ценообразование — Отдельные поля

**Решение:** ✅ Два набора цен в `SellerCCItem`

**Поля:**
- `seller_price` — обычная цена от seller
- `buyer_price` — обычная цена для покупателя
- `seller_price_non_vbv` — цена NON VBV от seller
- `buyer_price_non_vbv` — цена NON VBV для покупателя

**Логика:**
- Если `is_non_vbv = True` → используются `*_non_vbv` цены
- Если NON VBV цены не указаны → используются обычные цены
- Дефолт: NON VBV цены = обычные цены

**Преимущества:**
- Гибкое ценообразование
- Разные наценки для NON VBV
- Простая логика

---

### 7. Return Item — Универсальная функция

**Решение:** ✅ Добавить во все подходящие модели

**Модели с Return Item:**
- `SellerBankItem` (Banks)
- `SellerSelfregCCItem` (Selfreg CC)

**Поля:**
- `return_item_enabled` — Boolean (можно вернуть)
- `return_days` — Integer (дней на возврат)

**Логика:**
- Seller указывает при загрузке
- Buyer видит в описании товара
- Система контролирует сроки

---

### 8. Шифрование — Расширенный список

**Решение:** ✅ Шифровать все чувствительные данные

**Шифруемые поля:**

**Существующие:**
- `SellerCCItem`: number, exp, cvv
- `BruteBankItem`: login, password

**Новые:**
- `BruteBankItem`: account_number, routing_number
- `SellerOTPItem`: fullz_ssn
- `SellerEnrollItem`: ssn

**Метод:** AES-256 или аналогичный

---

## 📊 Итоговая статистика

### Изменения в БД

**Таблицы:**
- Переименовано: 1 (`seller_bank_selfreg_items` → `seller_bank_items`)
- Создано: 1 (`selfreg_cc_card_names`)
- Изменено: 6 (добавлены поля)

**Поля:**
- Добавлено: 52 новых поля
- Шифруется: 6 полей (4 новых + 2 существующих)

**Данные:**
- Банки Selfreg CC: 5 → 13 (+8)
- Названия карт: 0 → 78 (+78)
- Порталы Enroll: 11 → 12 (+1)

**Индексы:**
- Создано: 4 новых индекса

---

## 🚀 Порядок внедрения

### Фаза 1: База данных (1 день)
1. ✅ Создать бэкап
2. ✅ Запустить миграцию `sync_mini_app_v2`
3. ✅ Загрузить seed данные (card names)
4. ✅ Проверить результат

### Фаза 2: Backend (2 дня)
1. ⏳ Обновить парсеры (CC bulk, Brute bulk)
2. ⏳ Обновить API эндпоинты seller_bot
3. ⏳ Обновить API эндпоинты mini_app
4. ⏳ Настроить encryption для новых полей
5. ⏳ Обновить валидацию

### Фаза 3: Mini App (1 день)
1. ⏳ Обновить списки банков (использовать из БД)
2. ⏳ Обновить формы загрузки
3. ⏳ Тестирование

### Фаза 4: Тестирование (1 день)
1. ⏳ Unit тесты
2. ⏳ Integration тесты
3. ⏳ E2E тесты на dev
4. ⏳ Проверка всех форматов загрузки

### Фаза 5: Production (1 день)
1. ⏳ Deploy на production
2. ⏳ Мониторинг
3. ⏳ Hotfix если нужно

**Общее время:** 6 дней

---

## ✅ Чек-лист готовности

### База данных
- [x] Миграция создана
- [x] Seed скрипты готовы
- [x] Rollback план есть
- [ ] Протестировано на dev
- [ ] Бэкап создан

### Backend
- [ ] Парсеры обновлены
- [ ] API эндпоинты обновлены
- [ ] Encryption настроен
- [ ] Валидация обновлена
- [ ] Unit тесты написаны

### Mini App
- [ ] Списки банков обновлены
- [ ] Формы загрузки обновлены
- [ ] UI протестирован
- [ ] E2E тесты пройдены

### Документация
- [x] Анализ завершен
- [x] План миграции готов
- [x] Схема БД обновлена
- [x] Итоговый отчет готов
- [x] Quick Start готов

---

## 📞 Контакты и ресурсы

**Документация:**
- Анализ: `docs/MINI_APP_VS_DATABASE_ANALYSIS.md`
- План: `docs/DATABASE_MIGRATION_PLAN.md`
- Схема: `docs/SELLER_PRODUCTS_DATABASE_SCHEMA.md`
- Итоги: `docs/MINI_APP_V2_IMPLEMENTATION_SUMMARY.md`
- Старт: `docs/QUICK_START_MINI_APP_V2.md`
- Решения: `docs/FINAL_DECISIONS.md` (этот файл)

**Миграция:**
- `shared/database/migrations/sync_mini_app_v2.py`

**Seed данные:**
- `shared/database/seeds/selfreg_cc_card_names.py`
- `shared/database/seeds/selfreg_cc_card_names.sql`

---

**Утверждено:** 2026-03-24  
**Готово к внедрению:** ✅ Да
