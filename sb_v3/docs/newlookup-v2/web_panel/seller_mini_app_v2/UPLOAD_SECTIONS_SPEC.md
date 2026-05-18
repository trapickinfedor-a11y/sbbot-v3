# Seller Hub — Разделы загрузки: полная спецификация

> Все 10 типов товаров загружаются через Mini App. Seller Bot — только уведомления, управление помощниками и оплата депозитов через BTCPay.

---

## 1. Таблица разделов и страховых депозитов

| Раздел | `category_code` | Депозит | Форма в Mini App |
|--------|----------------|---------|-----------------|
| 🏦 **Banks** | `bank` | $150 | Wizard 6 шагов |
| 🔓 **Brute Bank** | `brute` | $150 | Single / Bulk paste+файл |
| 💳 **CC** | `cc` | $200 | Single / Bulk paste+файл |
| 📱 **NFC** | `nfc` | $150 | Форма + файл |
| 📲 **OTP** | `otp` | $100 | Простая форма |
| 🏧 **Selfreg CC** | `selfreg_cc` | $150 | Форма + категории |
| 🔐 **Enroll** | `enroll` | $100 | Форма + порталы |
| 📋 **Logs** | `logs` | $200 | Bulk paste + файл |
| 🖊 **Checks** | `checks` | $150 | Форма + фото |
| 🏦 **Selfreg BA** | `selfreg_ba` | $100 | Bulk paste + файл |

> **Важно:** Это страховой депозит, не оплата за доступ. Депозит возвращается при закрытии аккаунта (за вычетом штрафов).

---

## 2. Где платить депозит: архитектура

### 2.1 Принципиальное решение

**Депозит оплачивается только через Seller Bot** (BTCPay). Mini App не обрабатывает платежи напрямую — только отображает статус и направляет в бот для оплаты.

Это правильно по трём причинам:
1. BTCPay уже интегрирован в seller_bot, переписывать не нужно.
2. Платёжная логика (webhook, подтверждение, начисление) — серверная, не фронтендная.
3. Telegram Mini App не может принимать крипто-платежи напрямую.

### 2.2 Флоу оплаты депозита

```
Mini App (Settings → Access)
  → Продавец видит список разделов с замками
  → Нажимает [Unlock — $150]
  → Mini App вызывает Telegram.openTelegramLink(
      `https://t.me/seller_bot?start=deposit_bank`
    )
  → Seller Bot открывается, показывает инструкцию + BTCPay инвойс
  → Продавец платит крипту
  → BTCPay webhook → seller_bot → обновляет seller.security_deposit_categories
  → Seller Bot отправляет уведомление: "✅ Banks unlocked"
  → Mini App при следующем /me запросе видит обновлённый allowed_categories
```

### 2.3 Где что живёт

| Функция | Seller Bot | Mini App |
|---------|-----------|----------|
| Оплата депозита (BTCPay) | ✅ | ❌ |
| Просмотр статуса депозитов | ✅ уведомления | ✅ основной UI |
| Загрузка всех 10 типов товаров | ✅ FSM (дублирует) | ✅ основной UI |
| Управление помощниками | ✅ | ✅ вкладка Team |
| Уведомления о заказах/чатах | ✅ push в Telegram | ✅ polling |
| Аналитика | ❌ | ✅ |
| Финансы / вывод | ❌ | ✅ |

### 2.4 Апгрейд (доплата разницы)

Продавец уже купил Banks ($150). Хочет добавить CC ($200).

```
Mini App показывает:
  ✅ Banks — $150 [Active]
  🔒 CC — $200 [Unlock for $200]

Нажимает [Unlock for $200]
  → t.me/seller_bot?start=deposit_cc

Seller Bot:
  → Проверяет что Banks уже оплачен
  → Создаёт инвойс только на $200 (не на $150+$200)
  → После оплаты: seller.security_deposit_categories += ["cc"]
```

При апгрейде до пакета — доплачивает только разницу:

```python
def calculate_upgrade_cost(seller, bundle_code):
    already_paid = set(seller.security_deposit_categories or [])
    bundle_cats = BUNDLE_PACKAGES[bundle_code]["categories"]
    new_cats = set(bundle_cats) - already_paid
    return sum(CATEGORY_DEPOSITS[c] for c in new_cats)
```

---

## 3. Пакетные скидки

| Пакет | Разделы | Полная цена | Цена пакета | Скидка |
|-------|---------|------------|------------|--------|
| **Starter** | Banks + Brute | $300 | $200 | −33% |
| **Digital** | CC + Selfreg CC + NFC + OTP | $600 | $400 | −33% |
| **Full Access** | Все 10 разделов | $1350 | $750 | −44% |

> Пакет — это просто набор категорий со скидкой. Технически: одна оплата → несколько записей в `security_deposit_categories`.

---

## 4. Все разделы: форма + инструкция

---

### 4.1 🏦 Banks — $150

**Что это:** Банковские аккаунты и VCC. Самый популярный раздел. Поддерживает Available (конкретные штуки в стоке) и Per Order (бесконечный, исполняется вручную).

**Подтипы:**

| product_type | product_subtype | Описание |
|---|---|---|
| `bank` | `log` | Банковский лог (credentials + cookies) |
| `bank` | `selfreg` | Самозарегистрированный аккаунт |
| `enrol` | `log` | Enroll через банковский портал |
| `enrol` | `selfreg` | Selfreg enroll |

**Категории:** VCC 💳 / Personal 🏦 / Business 🏢 / Crypto 🪙 / Merchant 🏪

**Форма (6 шагов):**

```
① Тип и подтип
   [Bank ▼] × [Log / Selfreg]

② Категория и банк
   Категория: [VCC / Personal / Business / Crypto / Merchant]
   Банк: поиск из каталога или свободный текст

③ Наличие и цена
   Тип: [Available — конкретные штуки] / [Per Order — ∞]
   Цена: $___
   Кол-во в стоке: ___ (только для Available)

④ Описание
   Описание: ___________________
   Инструкция для покупателя: ___
   Ссылка на туториал: ___

⑤ Настройки
   Поддержка: [Chat] / [No Chat]
   Доступ к номеру: [Yes] / [No]
   ── Если Enrol ──────────────────
   Портал: [выбор из списка]
   Тип карты: [Credit / Debit]
   Штат: __ ZIP: ____
   SSN: [Y/N] DOB: [Y/N] Docs: [Y/N]
   ────────────────────────────────

⑥ Превью → [Submit]
```

**Инструкция для продавца:**

> Banks — это аккаунты с доступом к онлайн-банкингу. Log = credentials + cookies, Selfreg = аккаунт зарегистрированный на реального человека. Available означает что у вас есть конкретные штуки готовые к отправке сразу после оплаты. Per Order — вы исполняете заказ вручную в течение 1-6 часов. Enrol — аккаунты с доступом к enrollment порталам (FDECS, CardNav и др.), покупатель сам регистрирует карту.

---

### 4.2 💳 CC — $200

**Что это:** Кредитные карты с полными данными (номер, CVV, exp, holder, billing address и др.).

**Категории:** USA CC / World CC / NON VBV

**Формат строки (bulk):**
```
NUMBER|EXP|CVV|TYPE|BRAND|LEVEL|BANK|COUNTRY|HOLDER|ADDRESS|STATE|CITY|ZIP|Info|REF|PRICE
```

**Форма (5 шагов):**

```
① Категория
   [USA CC] / [World CC]
   NON VBV: [Yes / No]

② Режим загрузки
   [Single card] / [Bulk — paste или файл]

③ Данные
   Single: NUMBER | EXP | CVV | TYPE | BRAND | BANK | COUNTRY | ZIP | HOLDER | EMAIL | SSN | DOB
   Bulk: textarea (paste) или загрузка .txt/.csv
         → превью первых 5 строк с парсингом

④ Цена и описание
   Цена: $___
   Название: ___
   Описание / инструкция: ___

⑤ Превью → [Submit]
```

**Инструкция для продавца:**

> CC — кредитные карты с полными данными. USA CC — карты выпущенные в США. World CC — все остальные страны. NON VBV — карты без 3D Secure верификации, проходят без OTP. Bulk загрузка: каждая строка = одна карта. Поля после CVV опциональны, но чем больше данных — тем выше цена. PRICE в конце строки перезаписывает цену batch.

---

### 4.3 🔓 Brute Bank — $150

**Что это:** Банковские аккаунты с credentials (login/pass) для brute-force атак. Группируются по банку и атрибутам.

**Типы аккаунтов:** CHECKING / SAVINGS / BUSINESS / MONEY MARKET

**Формат строки (bulk):**
```
BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS
```

**Форма Single (6 шагов):**

```
① Режим: [Single] / [Bulk]

② Банк
   Название: _______________
   Bank code: ___ (авто из названия, lowercase)

③ Атрибуты группы
   Attributes: ___ (напр. "AN:RN+INST YODLEE") или [-]
   ⚠️ Если группа уже существует — предложить добавить к ней

④ Параметры варианта
   Balance range: ___ (напр. "9-12k" или "$500-$1000")
   Account type: [Checking / Savings / Business / Money Market]
   Credentials (key: value, каждый с новой строки):
   ┌──────────────────────────┐
   │ login: user@bank.com     │
   │ password: Qwerty123      │
   │ account: 1234567890      │
   └──────────────────────────┘
   Balance info: ___ (опционально)

⑤ Цена: $___

⑥ Превью → [Submit]
```

**Инструкция для продавца:**

> Brute Bank — аккаунты с credentials для прямого доступа. Группируйте по банку и атрибутам (например AN:RN означает Account Number + Routing Number, INST = instant verification, YODLEE = поддерживает Yodlee). Balance range — диапазон баланса на аккаунте. Credentials вводите в формате "ключ: значение" каждый с новой строки. Bulk: одна строка = один аккаунт.

---

### 4.4 📱 NFC — $150

**Что это:** NFC токены для бесконтактных платежей. Apple Pay, Google Pay и другие. Поставляется как ZIP-архив с данными токена.

**Типы:** Apple Pay 🍎 / Google Pay 🤖 / Other 📎

**Форма (5 шагов):**

```
① Тип NFC
   [Apple Pay] / [Google Pay] / [Other]

② Банк и локация
   Банк: _______________
   Страна: [US / UK / CA / AU / ...]
   Штат: ___ (опционально)
   ZIP: ___ (опционально)

③ Файл
   Загрузка .zip или .txt (до 10MB)
   → показывает имя файла и размер

④ Цена: $___

⑤ Превью → [Submit]
```

**Инструкция для продавца:**

> NFC — данные для добавления карты в Apple Pay или Google Pay. Файл должен содержать токен устройства, DPAN, криптограммы или другие данные необходимые для provisioning. Формат зависит от банка — обычно это JSON или текстовый файл с полями token, expiry, cryptogram. Упакуйте в ZIP если несколько файлов.

---

### 4.5 📲 OTP — $100

**Что это:** OTP карты с SMS-доступом. Продавец либо сам передаёт OTP покупателю (Via Seller), либо даёт прямой доступ к аккаунту (Direct Access).

**Форма (4 шага):**

```
① Банк и баланс
   Банк: _______________
   Баланс аккаунта: $___

② Параметры
   Fullz included: [Yes / No]
   SMS access: [Via Seller] / [Direct Account Access]
   Примечания: ___

③ Цена: $___

④ Превью → [Submit]
```

**Инструкция для продавца:**

> OTP — аккаунты где для транзакций нужен одноразовый код из SMS. Via Seller: покупатель запрашивает OTP у вас через чат, вы получаете SMS и передаёте код. Direct Account Access: покупатель получает доступ к аккаунту и сам запрашивает OTP. Fullz = к аккаунту прилагаются полные личные данные владельца.

---

### 4.6 🏧 Selfreg CC — $150

**Что это:** Самозарегистрированные кредитные карты. Карты оформлены на реальных людей, продавец имеет полный доступ к онлайн-аккаунту.

**Категории (предзагруженные):** Citi, Chase, Wells Fargo, ONEPAY, BOA + возможность запросить новую.

**Форма (5 шагов):**

```
① Категория банка
   [Citi / Chase / Wells Fargo / ONEPAY / BOA / ...]
   [+ Запросить новую категорию → модерация 1-6ч]

② Данные карты
   Card name: _______________
   Credit limit: $___ (опционально)
   VCC limit: $___ (опционально)

③ Локация и доступы
   Штат: ___  ZIP: ____
   Email access: [Yes / No]
   Phone access: [Yes / No]
     ↳ если Yes: дней осталось: ___
                 Renewable: [Yes/No]
                 Смена номера: [Yes/No]
   Online access: [Yes / No]

④ Цена: $___

⑤ Превью → [Submit]
```

**Инструкция для продавца:**

> Selfreg CC — карты оформленные на реальных людей через онлайн-заявку. У вас есть полный доступ к онлайн-аккаунту банка. Credit limit — кредитный лимит карты. VCC limit — лимит для виртуальных карт. Phone access означает что у вас есть доступ к телефону привязанному к аккаунту (для OTP). Если запрашиваете новую категорию — модерация займёт 1-6 часов.

---

### 4.7 🔐 Enroll — $100

**Что это:** Банковские аккаунты с доступом к enrollment порталам. Покупатель регистрирует карту через портал (FDECS, CardNav и др.) для получения виртуальной карты.

**Порталы:** FDECS, DIGITALCARDSERVICE, MYCARDINFO, CARD SUITE LIGHT, CardNav, FIREFIGHTERS, COAST CENTRAL, WEB ACCESS, Card Suite, Myaccountaccess, CENTRESUITE (minik) + запрос нового.

**Форма (5 шагов):**

```
① Портал
   [FDECS / DIGITALCARDSERVICE / MYCARDINFO / ...]
   [+ Запросить новый портал → модерация 1-6ч]

② Банк и баланс
   Банк: _______________
   Баланс: $___

③ Локация и тип карты
   Card ZIP: ____
   Card State: __
   Тип карты: [Credit / Debit]

④ Цена: $___

⑤ Превью → [Submit]
```

**Инструкция для продавца:**

> Enroll — аккаунты для enrollment порталов. Покупатель использует данные аккаунта чтобы зарегистрировать карту на портале и получить VCC или цифровую карту. FDECS, CardNav и другие порталы работают с конкретными банками — убедитесь что ваш банк поддерживает выбранный портал. Баланс — реальный баланс на аккаунте.

---

### 4.8 📋 Logs — $200

**Что это:** Полные банковские логи с credentials, cookies, screenshots и флагами (CVV, BT, Promo, Zelle, Wire, SafePass). Самый ценный тип — высокий депозит.

**Формат строки:**
```
SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|BT|PROMO|ZELLE|WIRE|SAFEPASS|EMAIL|SCREENSHOT
```

**Флаги (показываются только если true):**

| Флаг | Описание |
|------|---------|
| CVV | CVV карты доступен |
| BT | Balance transfer доступен |
| Promo | Промо-предложения активны |
| Zelle | Zelle подключён |
| Wire | Wire transfer доступен |
| SafePass | SafePass разблокирован |

**Форма (4 шага):**

```
① Режим загрузки
   [Bulk — paste] / [Bulk — файл .txt/.csv]

② Данные
   Paste режим: textarea с форматом SITE|LOGIN|PASS|...
   Файл режим: загрузка .txt/.csv (до 10MB)
   → Превью первых 5 строк с парсингом флагов
   → Показывает: найдено X записей, Y с CVV, Z с Zelle...

③ Цена за штуку: $___
   (можно переопределить для каждой строки добавив |PRICE в конец)

④ Превью батча → [Submit]
```

**Инструкция для продавца:**

> Logs — полные банковские логи. Это наиболее ценный тип товара, поэтому депозит выше. Каждая строка = один лог. COOKIES — base64 или JSON строка с cookies сессии. BALANCE — баланс в числовом формате (например 5000 или 5000.00). Флаги CVV, BT, ZELLE и др. — 1 если доступно, 0 или пусто если нет. SCREENSHOT — путь к файлу или URL (опционально). Цену можно задать глобально для всего батча или индивидуально для каждой строки добавив |PRICE в конец.

---

### 4.9 🖊 Checks — $150

**Что это:** Банковские чеки с фото-сканом. Типы: Personal, Business, Payroll, Cashier.

**Форма (5 шагов):**

```
① Тип чека
   [Personal] / [Business] / [Payroll] / [Cashier]

② Банк и параметры
   Банк: _______________
   Сумма чека: $___
   Штат: __ (2 буквы)

③ Скан
   Загрузка фото/документа (.jpg, .png, .pdf, до 10MB)
   → Превью загруженного файла

④ Цена: $___

⑤ Превью → [Submit]
```

**Инструкция для продавца:**

> Checks — бумажные банковские чеки. Personal — личный чек физического лица. Business — корпоративный чек. Payroll — зарплатный чек от работодателя. Cashier — кассирский чек (наиболее надёжный). Загрузите чёткое фото или скан чека. Сумма — номинал чека. Покупатель получает скан и использует его для mobile deposit или ACH.

---

### 4.10 🏦 Selfreg BA — $100

**Что это:** Самозарегистрированные банковские аккаунты (checking/savings). Полный доступ к онлайн-банкингу.

**Формат строки:**
```
BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS|ZIP|SSN|DOCS|EMAIL|PHONE|PHONE_DAYS
```

**Форма (4 шага):**

```
① Режим загрузки
   [Bulk — paste] / [Bulk — файл .txt/.csv]

② Данные
   Paste режим: textarea с форматом BANK|LOGIN|PASS|...
   Файл режим: загрузка .txt/.csv (до 10MB)
   → Превью первых 5 строк
   → Показывает: найдено X записей, Y с SSN, Z с Docs...

③ Цена за штуку: $___

④ Превью батча → [Submit]
```

**Инструкция для продавца:**

> Selfreg BA — банковские аккаунты зарегистрированные на реальных людей. У вас есть полный доступ к онлайн-банкингу. ACCOUNT_NUMBER и ROUTING — реквизиты для ACH. SSN — 1 если есть SSN владельца, 0 если нет. DOCS — 1 если есть документы (DL, паспорт). PHONE_DAYS — сколько дней осталось на привязанном телефоне.

---

## 5. Навигация Upload Tab (полная структура)

```
📦 Uploads
│
├── ── Мои разделы ─────────────────────────────────
│   ├── ✅ 🏦 Banks          $150  [Upload →]
│   ├── ✅ 🔓 Brute Bank     $150  [Upload →]
│   ├── 🔒 💳 CC             $200  [Unlock for $200]
│   ├── 🔒 📱 NFC            $150  [Unlock for $150]
│   ├── ✅ 📲 OTP            $100  [Upload →]
│   ├── 🔒 🏧 Selfreg CC     $150  [Unlock for $150]
│   ├── 🔒 🔐 Enroll         $100  [Unlock for $100]
│   ├── 🔒 📋 Logs           $200  [Unlock for $200]
│   ├── ✅ 🖊 Checks         $150  [Upload →]
│   └── 🔒 🏦 Selfreg BA     $100  [Unlock for $100]
│
├── ── Мои загрузки ────────────────────────────────
│   ├── 📊 Batches           → список батчей + статусы модерации
│   ├── 📋 Listings          → активные листинги + bulk reprice
│   └── 📐 Templates         → сохранённые шаблоны форм
│
└── ── Пакеты (если не Full Access) ────────────────
    ├── Starter Bundle       Banks + Brute — $200 (экономия $100)
    ├── Digital Bundle       CC+NFC+OTP+SelfregCC — $400 (экономия $200)
    └── Full Access          Все 10 разделов — $750 (экономия $600)
```

---

## 6. Промт для Cursor — Upload Module

```
## Upload Module — NewLookup Seller Hub Mini App

### Core Rule
ALL 10 upload types are handled directly in the Mini App.
There are NO deep links to seller_bot for uploads.
Seller Bot is only used for: deposit payments (BTCPay), notifications, helper management.

### Deposit Architecture
- Each category has its own deposit (insurance, refundable)
- Deposits are paid via seller_bot → BTCPay → webhook updates seller.security_deposit_categories
- Mini App shows locked/unlocked state based on /me response (allowed_categories field)
- Locked section: show card with lock icon, deposit amount, "Unlock" button
- Unlock button: Telegram.openTelegramLink(`https://t.me/${BOT_USERNAME}?start=deposit_${category_code}`)
- NEVER hide locked sections — always show them

### Deposit Amounts (canonical, do not change)
bank: $150, brute: $150, cc: $200, nfc: $150, otp: $100,
selfreg_cc: $150, enroll: $100, logs: $200, checks: $150, selfreg_ba: $100

### Bundle Packages
starter:     [bank, brute]                    → $200 (vs $300)
digital:     [cc, selfreg_cc, nfc, otp]       → $400 (vs $600)
full_access: [all 10]                          → $750 (vs $1350)
Upgrade = pay difference only (calculate_access_cost returns delta)

### Upload Forms — Rules
1. Every upload type has a multi-step wizard (3-6 steps)
2. Save progress to localStorage on every step (key: upload_draft_{item_type})
3. Restore from localStorage on mount (ask user to continue or start fresh)
4. Final step always shows preview card (call POST /uploads/preview)
5. File uploads (NFC, Checks) → POST /uploads/submit-with-file (multipart)
6. Bulk text uploads (CC, Brute, Logs, SelfregBA) → POST /uploads/parse-file first, then /uploads/submit
7. Single item uploads → POST /uploads/preview then /uploads/submit

### Upload Types and Form Complexity
bank:       6 steps — type/subtype, category/bank, stock/price, description, settings, preview
cc:         5 steps — category, mode(single/bulk), data, price/desc, preview
brute:      6 steps — mode, bank, attributes, variant params, price, preview
nfc:        5 steps — type, bank/location, file, price, preview
otp:        4 steps — bank/balance, params, price, preview
selfreg_cc: 5 steps — category, card data, location/access, price, preview
enroll:     5 steps — portal, bank/balance, location/card type, price, preview
logs:       4 steps — mode(paste/file), data+preview, price, submit
checks:     5 steps — check type, bank/params, scan file, price, preview
selfreg_ba: 4 steps — mode(paste/file), data+preview, price, submit

### Bulk Format Strings
CC:         NUMBER|EXP|CVV|TYPE|BRAND|LEVEL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE
Brute:      BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS
Logs:       SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING|NAME|ADDRESS|ZIP|CVV|BT|PROMO|ZELLE|WIRE|SAFEPASS|EMAIL|SCREENSHOT
SelfregBA:  BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS|ZIP|SSN|DOCS|EMAIL|PHONE|PHONE_DAYS

### File Upload Constraints
NFC:    .zip, .txt — max 10MB
Checks: .jpg, .jpeg, .png, .pdf — max 10MB
Bulk:   .txt, .csv — max 1MB (parse-file endpoint)
Validate both content-type AND file extension.

### Batch Status Flow
pending_moderation → approved | rejected | changes_requested
approved:           items live in catalog
rejected:           show reason, allow new batch
changes_requested:  show comment, PATCH /batches/{id}/resubmit

### Category Requests (SelfregCC + Enroll)
POST /api/seller-mini-app/uploads/request-category
Body: { category_type: "selfreg_cc" | "enroll", name: string }
→ Creates pending request, moderation 1-6h
→ Bot notifies seller when approved/rejected

### Templates
GET    /api/seller-mini-app/templates?item_type=bank
POST   /api/seller-mini-app/templates  { item_type, name, payload }
DELETE /api/seller-mini-app/templates/{id}
Show "Load template" button on step 1 if templates exist for that item_type.

### Access Check (Backend)
Every upload endpoint checks in order:
1. seller_actor.can_upload() — role check
2. SellerDepositService.has_category_access(seller, category_code) — deposit check
If either fails → 403

ITEM_TYPE_TO_CATEGORY = {
  "bank": "bank", "cc_single": "cc", "cc_bulk": "cc",
  "brute_single": "brute", "brute_bulk": "brute",
  "nfc": "nfc", "otp": "otp", "selfreg_cc": "selfreg_cc",
  "enroll": "enroll", "logs": "logs", "checks": "checks", "selfreg_ba": "selfreg_ba"
}
```
