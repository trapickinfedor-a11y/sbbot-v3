# 📚 ИНДЕКС ДОКУМЕНТАЦИИ
## Seller Mini App + Mirror Bot

---

## 📋 СОЗДАННЫЕ ДОКУМЕНТЫ

### 1. [COMPLETE_SECTIONS_AUDIT.md](./COMPLETE_SECTIONS_AUDIT.md)
**Полный аудит всех разделов** (Основной документ)

**Содержание:**
- 11 активных разделов (Selfreg BA удален)
- Поля товаров для каждого раздела
- Каталог банков (51 банк в Banks, 67 в Brute)
- Названия карт (49 уникальных в Selfreg CC)
- Moderation Request flow
- Описания товаров для покупателей
- Bulk форматы

**Объем:** ~1000 строк

---

### 2. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**Краткий справочник разработчика**

**Содержание:**
- Сводная таблица всех разделов
- Списки банков (быстрый доступ)
- Moderation Request flow
- Bulk форматы
- Важные заметки
- Модели данных (ключевые поля)
- Приоритеты доработки Mini App

**Объем:** ~200 строк

---

### 3. [DATA_TRANSFORMATIONS.md](./DATA_TRANSFORMATIONS.md)
**Преобразования данных Mini App ↔ Bot ↔ БД**

**Содержание:**
- Типы преобразований (Date, Boolean, Numbers, Strings, Files)
- Таблица всех преобразований (35+ полей)
- Примеры кода (TypeScript + Python)
- Важные заметки по форматам

**Объем:** ~400 строк

---

## 🔗 СУЩЕСТВУЮЩАЯ ДОКУМЕНТАЦИЯ

### Из предыдущих аудитов:

- [SELLER_SECTIONS_REVIEW.md](./SELLER_SECTIONS_REVIEW.md) - Первоначальный аудит
- [SELLER_ARCHITECTURE.md](./SELLER_ARCHITECTURE.md) - Архитектура Seller Bot
- [SELLER_MINI_APP_COMPLETE.md](../SELLER_MINI_APP_COMPLETE.md) - Завершение Mini App
- [WEB_PANEL_COMPLETE.md](../WEB_PANEL_COMPLETE.md) - Web Panel

---

## 📊 СТРУКТУРА ДОКУМЕНТАЦИИ

```
docs/
├── INDEX.md (этот файл)
├── COMPLETE_SECTIONS_AUDIT.md (полный аудит)
├── QUICK_REFERENCE.md (шпаргалка)
├── DATA_TRANSFORMATIONS.md (преобразования)
├── SELLER_SECTIONS_REVIEW.md (первый аудит)
├── SELLER_ARCHITECTURE.md (архитектура)
└── ... другие документы
```

---

## 🎯 НАВИГАЦИЯ ПО РАЗДЕЛАМ

### Для быстрого старта:
1. Читать: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) (5 мин)
2. Открыть: [COMPLETE_SECTIONS_AUDIT.md](./COMPLETE_SECTIONS_AUDIT.md) (подробности)
3. Использовать: [DATA_TRANSFORMATIONS.md](./DATA_TRANSFORMATIONS.md) (при коде)

### Для глубокого понимания:
1. [SELLER_SECTIONS_REVIEW.md](./SELLER_SECTIONS_REVIEW.md) - проблемные места
2. [COMPLETE_SECTIONS_AUDIT.md](./COMPLETE_SECTIONS_AUDIT.md) - полная спецификация
3. [DATA_TRANSFORMATIONS.md](./DATA_TRANSFORMATIONS.md) - технические детали

---

## 📋 ТАБЛИЦА РАЗДЕЛОВ

| Раздел | Статус | Страница в COMPLETE | Страница в QUICK |
|--------|--------|---------------------|------------------|
| Banks | ✅ | 4-9 | 3 |
| Brute Bank | ✅ | 10-12 | 3 |
| CC/Debit | ✅ | 13-15 | 3 |
| NFC | ✅ | 16-17 | 3 |
| OTP | ✅ | 18-19 | 3 |
| Selfreg CC | ✅ | 20-24 | 3 |
| Enrollment | ✅ | 25-28 | 3 |
| Logs | ✅ | 29-31 | 3 |
| Checks | ✅ | 32-33 | 3 |
| Documents | ✅ | 34-35 | 3 |
| Fullz | ✅ | 36-37 | 3 |
| ~~Selfreg BA~~ | ❌ | - | 3 |

---

## 🔑 КЛЮЧЕВЫЕ ФАЙЛЫ

### Mini App (Frontend)
```
/private/tmp/seller_mini_app_temp/seller_mini_app_v2/
├── client/src/components/tabs/UploadsTab.tsx (114KB)
├── client/src/lib/api.ts
└── docs/ (архитектура)
```

### Seller Bot (Backend)
```
seller_bot/
├── handlers/
│   ├── stock.py (Banks)
│   ├── brute_bank.py (Brute)
│   ├── cc_stock.py (CC/Debit)
│   └── special_products.py (NFC, OTP, Selfreg CC, Enrollment, Checks)
├── services/
└── keyboards/
```

### Mirror Bot (Buyer Bot)
```
mirror_bot/
├── handlers/
│   ├── banks.py
│   ├── brute_bank.py
│   ├── cc.py
│   └── ...
├── services/
│   ├── menu_counts_service.py
│   └── product_descriptions.py
└── constants/
```

### Database Models
```
shared/database/models.py
├── SellerBankItem (Banks)
├── BruteBankItem (Brute)
├── SellerCCItem (CC/Debit)
├── SellerNFCItem (NFC)
├── SellerOTPItem (OTP)
├── SellerSelfregCCItem (Selfreg CC)
├── SellerEnrollItem (Enrollment)
├── SellerLogsItem (Logs)
├── SellerCheckItem (Checks)
├── Product (Documents)
└── SellerFullzItem (Fullz)
```

---

## 📊 СТАТИСТИКА

- **Всего разделов:** 11 активных + 1 удален
- **Всего банков:** 51 (Banks) + 67 (Brute) + 20 (NFC/OTP) = 138 уникальных
- **Всего карт:** 49 названий (Selfreg CC)
- **Всего порталов:** 12 (Enrollment)
- **Всего полей:** ~200 across all models
- **Объем документации:** ~1600 строк

---

## ✅ ЧТО ДОБАВИТЬ В MINI APP

Согласно аудиту, необходимо добавить:

1. **Кнопки "Request new bank"**
   - Banks форма
   - Brute Bank форма

2. **Генерацию описаний**
   - renderBankDescription()
   - renderCCDescription()
   - renderNFCDescription()
   - renderOTPDescription()
   - renderSelfregCCDescription()
   - renderEnrollDescription()
   - renderLogsDescription()
   - renderCheckDescription()

3. **Исправление форматов**
   - format: "bank" вместо "selfreg_ba"
   - Преобразование boolean
   - Преобразование дат

4. **Валидацию**
   - Формат дат (MM/DD/YYYY)
   - ZIP коды
   - Phone rental days

---

## 🔄 UPDATE HISTORY

| Дата | Документ | Изменения |
|------|----------|-----------|
| 2026-03-24 | COMPLETE_SECTIONS_AUDIT.md | Создан |
| 2026-03-24 | QUICK_REFERENCE.md | Создан |
| 2026-03-24 | DATA_TRANSFORMATIONS.md | Создан |
| 2026-03-24 | INDEX.md | Создан |

---

**ВЕРСИЯ:** 1.0  
**ДАТА:** 2026-03-24  
**СТАТУС:** ✅ Индекс создан
