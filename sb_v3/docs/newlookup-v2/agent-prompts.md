# NewLookup — Промты для параллельных агентов

## Правила изоляции
- Каждый агент работает в своей ветке git
- Агенты НЕ трогают файлы друг друга
- Shared модули (shared/) — только агент #4 (рефералы БД)
- После завершения всех — мерж в feat/v2

---

## Агент 1: Docker ENV + Role-based (ветка feat/env-roles)

```
Проект: /Users/user/Desktop/Проекты/newlookup

Задача 1: Замени все хардкод Docker-имена на ENV переменные.
- grep -rn "http://main_bot:" "http://worker_bot:" --include="*.py" | замени на os.getenv()
- Добавь в .env: MAIN_BOT_API_URL=http://localhost:8080, WORKER_BOT_API_URL=http://localhost:8181
- НЕ трогай: shared/database/, shared/models/, marketer_bot/handlers/referral*

Задача 2: Role-based доступ в админке.
- В web_panel/ добавь декоратор @require_role("owner","moderator") на роуты
- 4 роли уже в БД: owner, moderator, accountant, manager
- Скрой пункты меню по роли из сессии в шаблонах
- НЕ трогай: seller_mini_app_v2/, любые боты

Ветка: git checkout -b feat/env-roles
Коммиты: отдельный на каждую задачу
```

## Агент 2: i18n система (ветка feat/i18n)

```
Проект: /Users/user/Desktop/Проекты/newlookup

Создай систему интернационализации для 4 языков: EN, RU, ES, ZH.

1. Создай shared/i18n/ модуль:
   - shared/i18n/__init__.py — функция t(key, lang) → строка
   - shared/i18n/locales/en.json, ru.json, es.json, zh.json
2. Заполни en.json и ru.json ключами из существующих строк ботов
3. Для es.json и zh.json — оставь пустые значения с TODO
4. В каждом боте: добавь выбор языка в /start (inline keyboard EN/RU/ES/ZH)
5. Сохраняй язык юзера в БД (поле language в таблице users — добавь если нет)

НЕ трогай: web_panel/templates/, seller_mini_app_v2/, shared/database/session.py
Ветка: git checkout -b feat/i18n
```

## Агент 3: Mirror Bot типы заказов + ETA (ветка feat/mirror-orders)

```
Проект: /Users/user/Desktop/Проекты/newlookup

Доработай mirror_bot/ для поддержки 3 типов заказов:

1. Order — выполняется в реальном времени
2. Order+Catalog — воркер загружает позиции или выполняет если нет
3. Catalog — полная загрузка ассортимента

Реализация:
- Добавь поле order_type ENUM('order','order_catalog','catalog') в таблицу orders (alembic migration)
- Добавь поле eta_minutes в таблицу orders + service_categories
- В mirror_bot/handlers/ — показывай ETA юзеру при заказе
- В web_panel/templates/ — добавь настройку ETA по категориям (admin)
- В web_panel/templates/ — добавь управление ссылками услуг (только Order и Order+Catalog)

НЕ трогай: seller_mini_app_v2/client/src/, shared/i18n/, marketer_bot/
Ветка: git checkout -b feat/mirror-orders
```

## Агент 4: Реферальная система БД + shared (ветка feat/referral-system)

```
Проект: /Users/user/Desktop/Проекты/newlookup
ТЗ: Folders/newlookup-docs/referral-system-spec.md

Создай фундамент реферальной системы:

1. Новые таблицы (alembic migration):
   - referrals: id, referrer_id, referred_id, source_bot, level, referral_chain(JSON), status, created_at
   - referral_rewards: id, user_id, from_referral_id, level, display_percent, real_percent, amount, status(pending_moderation/approved/rejected/paid), reviewed_by, reviewed_at
   - referral_settings: id, level, display_percent, real_percent, max_daily, cooldown_hours
2. Shared модуль shared/referral/:
   - service.py — create_referral(), process_purchase_rewards(), get_referral_stats()
   - Логика parent_chain: при регистрации сохранять массив до 5 parent IDs
3. Заполни referral_settings дефолтами: 15/7, 7/3, 3/1, 1/0.2, 0.5/0
4. Middleware для всех ботов: обработка /start ref_XXX

НЕ трогай: web_panel/templates/, seller_mini_app_v2/, mirror_bot/handlers/
Ветка: git checkout -b feat/referral-system
```

## Агент 5: Marketer Bot рефералы (ветка feat/referral-marketer)

```
Проект: /Users/user/Desktop/Проекты/newlookup
Зависит от: Агент 4 (shared/referral/ должен существовать)

Добавь реферальные команды в marketer_bot/:

1. /referral — генерация уникальной ссылки t.me/BOT?start=ref_USERID + кнопка "Скопировать"
2. /referral_stats — статистика: приглашено/подтверждено/заработано/на модерации
3. /referral_history — история начислений с датами
4. /referral_withdraw — запрос вывода → status=pending_moderation
5. Уведомления: новый реферал, первая покупка, вывод одобрен/отклонён
6. Inline-кнопки шаринга ссылки

Используй shared/referral/service.py для всей логики.
НЕ трогай: web_panel/, seller_mini_app_v2/, mirror_bot/, shared/database/session.py
Ветка: git checkout -b feat/referral-marketer
```

## Агент 6: Admin рефералы + рассылки (ветка feat/admin-referral-broadcast)

```
Проект: /Users/user/Desktop/Проекты/newlookup
Зависит от: Агент 4 (таблицы referrals, referral_rewards)

1. Admin → новый раздел "Рефералы":
   - Таблица реферальных связей с фильтрами
   - Модерация выводов: approve/reject с комментарием
   - Настройки процентов по уровням
   - Статистика: топ рефереры, конверсия

2. Admin → Рассылки (переработка):
   - Шаблон рассылки с WYSIWYG
   - Выбор бота: Marketer / Worker / Seller
   - Выбор языка или "все 4"
   - Scheduler (будильник): дата+время отправки
   - Кнопки с категориями для юзерских рассылок

Всё в web_panel/templates/ и web_panel/routers/
НЕ трогай: seller_mini_app_v2/client/src/, боты (кроме API вызовов)
Ветка: git checkout -b feat/admin-referral-broadcast
```

---

## Порядок запуска
1. Параллельно: Агенты 1, 2, 3, 4 (независимые)
2. После #4: Агенты 5, 6 (зависят от shared/referral/)
3. Мерж всех веток в feat/v2
4. Тест через browser_agent
