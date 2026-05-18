# 🚀 Быстрый старт: Внедрение Mini App v2

## Что готово

✅ **4 документа:**
1. `docs/MINI_APP_VS_DATABASE_ANALYSIS.md` — детальный анализ
2. `docs/DATABASE_MIGRATION_PLAN.md` — план миграции
3. `docs/SELLER_PRODUCTS_DATABASE_SCHEMA.md` — обновленная схема БД
4. `docs/MINI_APP_V2_IMPLEMENTATION_SUMMARY.md` — итоговый отчет

✅ **Миграция:**
- `shared/database/migrations/sync_mini_app_v2.py` — Alembic миграция

✅ **Seed данные:**
- `shared/database/seeds/selfreg_cc_card_names.py` — Python скрипт
- `shared/database/seeds/selfreg_cc_card_names.sql` — SQL файл (78 карт)

---

## Основные изменения

### 🔴 Критично

1. **Banks** — универсальная секция (5 категорий, 54 банка)
   - Объединяет Bank Selfregs + Selfreg BA
   - Один интерфейс для всех банковских продуктов
2. **Brute Bank** — +9 полей (AN, RN, holder, address, docs)
3. **CC** — NON VBV ценообразование (2 цены)
4. **Selfreg CC** — 5→13 банков + таблица названий карт (78 шт)
5. **OTP** — +12 Fullz полей (имя, адрес, SSN, DOB, контакты)
6. **Enrollment** — +11 детальных полей

### 📊 Статистика

- **Таблиц:** переименовано 1, создано 1, изменено 6
- **Полей:** добавлено 52 новых
- **Данных:** +8 банков, +78 карт, +1 портал
- **Индексов:** создано 4

---

## Запуск миграции

```bash
# 1. Бэкап
pg_dump -U postgres -d lookup_db > backup_$(date +%Y%m%d).sql

# 2. Миграция
alembic upgrade head

# 3. Seed данные
psql -U postgres -d lookup_db -f shared/database/seeds/selfreg_cc_card_names.sql

# 4. Проверка
psql -U postgres -d lookup_db -c "SELECT COUNT(*) FROM selfreg_cc_categories;"
# Ожидается: 13

psql -U postgres -d lookup_db -c "SELECT COUNT(*) FROM selfreg_cc_card_names;"
# Ожидается: 78
```

---

## Откат (если нужно)

```bash
alembic downgrade -1
```

---

## Что дальше

### Обязательно:
1. ✅ Обновить парсеры в `seller_upload_pipeline_service.py`
2. ✅ Обновить API эндпоинты seller_bot
3. ✅ Обновить API эндпоинты mini_app
4. ✅ Настроить encryption для новых полей (SSN, AN, RN)
5. ✅ Протестировать на dev окружении

### Опционально:
- Обновить документацию API
- Добавить валидацию для новых полей
- Создать UI для управления card_names в админке

---

## Вопросы для обсуждения

1. **Banks Section** — оставить как расширение `SellerBankItem` или создать отдельную модель?
   - ✅ Рекомендация: оставить как есть (универсальная модель)

2. **Bulk форматы** — поддерживать оба или выбрать один?
   - ✅ Рекомендация: поддерживать оба (обратная совместимость)

3. **Списки банков** — синхронизировать Mini App с БД или наоборот?
   - ✅ Рекомендация: использовать списки из БД (54 банка)

---

## Контакты

Все документы в `docs/`:
- Анализ: `MINI_APP_VS_DATABASE_ANALYSIS.md`
- План: `DATABASE_MIGRATION_PLAN.md`
- Схема: `SELLER_PRODUCTS_DATABASE_SCHEMA.md`
- Итоги: `MINI_APP_V2_IMPLEMENTATION_SUMMARY.md`
