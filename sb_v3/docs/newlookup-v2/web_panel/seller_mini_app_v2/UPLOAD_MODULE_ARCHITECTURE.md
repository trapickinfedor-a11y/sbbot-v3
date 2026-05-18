# Upload Module — Полная Архитектура v2.1
> Исправленная версия · Правильное разделение Brute Bank / Selfreg BA · Без изменений БД

---

## 0. Ключевые различия (исправлено)

| Раздел | Каталог | Логика группировки |
|--------|---------|-------------------|
| **Brute Bank** | `BruteBankGroup` из БД (bank_code + attributes) | `group_key = make_brute_group_key(bank_code, attrs)` |
| **Selfreg BA** | `BANK_CATALOG` (VCC/Personal/Business/Crypto/Merchant) | Выбор категории → выбор банка из каталога |
| **Selfreg CC** | `SelfregCCCategory` из БД + запрос новой | Выбор банка → `SelfregCCCategoryRequest` |
| **Enroll** | `EnrollCategory` из БД + запрос нового | Выбор портала → `EnrollCategoryRequest` |
| **Banks (ATM)** | `BANK_CATALOG` (fallback) + `BankItem` из БД | Выбор категории → выбор банка |

---

## 1. Таблица всех разделов

| # | Раздел | Депозит | Bulk | File | Таблица БД |
|---|--------|---------|------|------|-----------|
| 1 | Banks (ATM) | $150 | ✗ | ✗ | `seller_bank_items` |
| 2 | Brute Bank | $150 | ✅ | ✅ | `brute_bank_groups` + `brute_bank_items` |
| 3 | CC | $200 | ✅ | ✅ | `seller_cc_items` |
| 4 | NFC | $150 | ✗ | ✅ | `seller_nfc_items` |
| 5 | OTP | $100 | ✗ | ✗ | `seller_otp_items` |
| 6 | Selfreg CC | $150 | ✗ | ✗ | `seller_selfreg_cc_items` |
| 7 | Enroll | $100 | ✗ | ✗ | `seller_enroll_items` |
| 8 | Logs | $200 | ✅ | ✅ | `seller_logs_items` |
| 9 | Checks | $150 | ✗ | ✅ | `seller_checks_items` |
| 10 | Selfreg BA | $100 | ✅ | ✅ | `seller_selfreg_ba_items` |

---

## 2. Brute Bank — Правильная Архитектура

### 2.1 Что такое Brute Bank

Brute Bank — это **сгруппированный каталог банковских аккаунтов** с логинами/паролями. Группировка происходит по паре `bank_code + attributes`, что создаёт уникальный `group_key`.

```
BruteBankGroup (витрина — то что видит покупатель)
├── group_key: "chase|an:rn+inst yodlee"
├── bank_code: "chase"
├── bank_name: "Chase"
├── category: "personal"
├── attributes: "AN:RN+INST YODLEE"
└── BruteBankItem[] (отдельные combos — то что продаётся)
    ├── credentials: {login: "john@gmail.com", password: "Pass123"}
    ├── balance_info: "$5,200"
    ├── balance_range: "$1K-$5K"
    ├── account_type: "CHECKING"
    └── price: 25.00
```

### 2.2 Как выглядит список Brute в Mini App

Продавец видит **существующие группы** из `brute_bank_groups` с количеством своих items:

```
┌─────────────────────────────────────────────────────┐
│  BRUTE BANK                                         │
│  [💳 VCC] [🏦 Personal] [🏢 Business] [🪙 Crypto]  │
│  [⚡ General]                                        │
├─────────────────────────────────────────────────────┤
│  Chase [AN:RN+INST YODLEE]                    [242] │
│  Wells Fargo [AN:RN+INST YODLEE+NAME+ADDRESS]  [26] │
│  BMO [AN:RN+INST YODLEE]                      [242] │
│  53 [AN:RN+INST YODLEE+INST FINICITY]        [1439] │
│  TD Bank [AN:RN]                               [88] │
│  ─────────────────────────────────────────────────  │
│  [+ Add to existing group]                          │
│  [+ Create new group]                               │
└─────────────────────────────────────────────────────┘
```

Формат: `{bank_name} [{attributes}]` + `[{count}]` — количество items продавца в этой группе.

### 2.3 Режим Single (добавить в существующую группу)

```
┌─────────────────────────────────────────────────────┐
│  SELECT GROUP                                       │
│  🔍 Search groups...                                │
│                                                     │
│  ● Chase [AN:RN+INST YODLEE]              (242 items)│
│  ○ Wells Fargo [CHECKING]                  (26 items)│
│  ○ BMO [AN:RN+INST YODLEE]               (242 items)│
│                                                     │
│  [+ Create new group instead]                       │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  CREDENTIALS                                        │
│  Login (email/username)                             │
│  [john.doe@gmail.com                              ] │
│  Password                                           │
│  [Password123                                     ] │
│  Extra (optional — SSN, DOB, etc.)                  │
│  [                                                ] │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  BALANCE                                            │
│  Balance info (e.g. "$5,200")                       │
│  [                                                ] │
│  Balance range                                      │
│  [$1K-$5K ▼]                                       │
│  Account type                                       │
│  [CHECKING ▼]                                       │
│  State (US)                                         │
│  [CA ▼]                                             │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)                                 │
│  [25.00                                           ] │
└─────────────────────────────────────────────────────┘
```

### 2.4 Режим Create New Group

```
┌─────────────────────────────────────────────────────┐
│  NEW GROUP                                          │
│  Category                                           │
│  [🏦 Personal ▼]                                   │
│  Bank name                                          │
│  [Chase                                           ] │
│  Bank code (auto-generated)                         │
│  [chase                                           ] │  ← авто из bank_name
│  Attributes                                         │
│  [AN:RN+INST YODLEE ▼] [Custom...]                 │
│                                                     │
│  Preview group key: "chase|an:rn+inst yodlee"       │
└─────────────────────────────────────────────────────┘
```

### 2.5 Режим Bulk

```
┌─────────────────────────────────────────────────────┐
│  BULK UPLOAD                                        │
│  Format:                                            │
│  BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDR|ZIP  │
│  ─────────────────────────────────────────────────  │
│  Chase|john@gmail.com|Pass123|1234567890|021000021  │
│  |$5,200|CA|John Doe|123 Main St|90001              │
│                                                     │
│  [textarea: paste lines here...]                    │
│  ─── or ───                                         │
│  [📎 Upload .txt file]                              │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PREVIEW (auto-grouped)                             │
│  Chase [AN:RN] × 5                                  │
│  Wells Fargo [CHECKING] × 3                         │
│  BMO [AN:RN+INST YODLEE] × 2                        │
│  ─────────────────────────────────────────────────  │
│  Total: 10 accounts                                 │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [25.00]                        │
│  ☐ Use PRICE column from file (last column)         │
└─────────────────────────────────────────────────────┘
```

**Bulk формат строки:**
```
BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS|ZIP|ATTRIBUTES
```

**Авто-группировка в бэкенде:**
```python
# seller_mini_app.py — POST /upload/brute/bulk
for line in lines:
    parts = line.split("|")
    bank_name = parts[0].strip()
    bank_code = bank_name.lower().replace(" ", "_")
    attributes = parts[10].strip() if len(parts) > 10 else ""
    group_key = make_brute_group_key(bank_code, attributes)
    
    # find_or_create BruteBankGroup
    group = await get_or_create_brute_group(session, group_key, bank_name, bank_code, category, attributes)
    
    # create BruteBankItem
    item = BruteBankItem(
        seller_id=seller.id,
        group_id=group.id,
        bank_name=bank_name,
        bank_code=bank_code,
        credentials={"login": parts[1], "password": parts[2]},
        balance_info=parts[5],
        state=parts[6],
        price=price,
        moderation_status="pending",
        status="available",
    )
```

---

## 3. Selfreg BA — Правильная Архитектура

### 3.1 Что такое Selfreg BA

Selfreg BA — это **самостоятельно зарегистрированные банковские аккаунты**. В отличие от Brute Bank, здесь нет группировки по `group_key`. Продавец выбирает **категорию из BANK_CATALOG** (VCC/Personal/Business/Crypto/Merchant) и **банк из каталога**, затем загружает данные аккаунта.

### 3.2 Как выглядит форма Selfreg BA

```
┌─────────────────────────────────────────────────────┐
│  SELFREG BA                                         │
│  CATEGORY                                           │
│  [💳 VCC] [🏦 Personal] [🏢 Business]              │
│  [🪙 Crypto] [🔷 Merchant]                          │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  BANK                                               │
│  🔍 Search bank...                                  │
│  ─────────────────────────────────────────────────  │
│  🏦 Chase                                           │
│  🏦 WellsFargo                                      │
│  🏦 Bank of America                                 │
│  🏦 TD Bank                                         │
│  🏦 Citi Personal                                   │
│  ... (из BANK_CATALOG[selectedCategory])            │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  ACCOUNT DATA                                       │
│  Account type   [CHECKING ▼]                        │
│  Account number [                                 ] │
│  Routing number [                                 ] │
│  Balance        [$5,200                           ] │
│  State          [CA ▼]                              │
│  Name           [John Doe                         ] │
│  Address        [123 Main St                      ] │
│  ZIP            [90001                            ] │
│  SSN            [                                 ] │
│  DOB            [                                 ] │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  CREDENTIALS                                        │
│  Login          [john@gmail.com                   ] │
│  Password       [Password123                      ] │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [35.00                       ] │
└─────────────────────────────────────────────────────┘
```

### 3.3 Bulk Selfreg BA

```
┌─────────────────────────────────────────────────────┐
│  BULK SELFREG BA                                    │
│  Format:                                            │
│  BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDR|ZIP  │
│  |TYPE|SSN|DOB                                      │
│                                                     │
│  [textarea: paste lines here...]                    │
│  ─── or ───                                         │
│  [📎 Upload .txt file]                              │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PREVIEW                                            │
│  Detected: 12 accounts                              │
│  Chase × 5 / WellsFargo × 4 / TD Bank × 3          │
└─────────────────────────────────────────────────────┘
```

**Bulk формат строки:**
```
BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS|ZIP|TYPE|SSN|DOB
```

---

## 4. CC — Правильная Архитектура

### 4.1 Три режима в одном экране

```
┌─────────────────────────────────────────────────────┐
│  CC                                                 │
│  [🇺🇸 USA CC] [🌍 World CC]                        │
│  ☐ NON VBV ⛔  ← красная рамка когда активен       │
│  [Single Entry] [Bulk Upload]                       │
└─────────────────────────────────────────────────────┘
```

- Таб `🇺🇸 USA CC` → `category_code = "usa"`, `country = "US"`
- Таб `🌍 World CC` → `category_code = "world"`, `country ≠ "US"`
- Чекбокс `NON VBV ⛔` → `is_non_vbv = true` для всего батча

### 4.2 Single mode

```
┌─────────────────────────────────────────────────────┐
│  CARD DATA                                          │
│  Card Number *  [4111 1111 1111 1111              ] │
│  EXP *          [12/27]  CVV * [123]               │
│  Type           [Credit ▼]  Brand [VISA ▼]         │
│  Level          [CLASSIC ▼]                         │
│  Bank name      [Chase                            ] │
│  Country        [US ▼]  State [CA ▼]               │
│  ZIP            [90001]                             │
│  Holder name    [JOHN DOE                         ] │
│  Email          [john@gmail.com                   ] │
│  Phone          [+1 555 000 0000                  ] │
│  SSN            [                                 ] │
│  DOB            [                                 ] │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [25.00                       ] │
│  Item name      [Chase VISA Classic USA           ] │
└─────────────────────────────────────────────────────┘
```

### 4.3 Bulk mode

```
┌─────────────────────────────────────────────────────┐
│  FORMAT                                             │
│  NUM|EXP|CVV|TYPE|BRAND|LEVEL|BANK|COUNTRY|HOLDER  │
│  |ADDR|STATE|CITY|ZIP|Info|REF|PRICE                │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  [textarea: paste cards here...]                    │
│  ─── or ───                                         │
│  [📎 Upload .txt / .csv file]                       │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  LIVE PREVIEW                                       │
│  🇺🇸 12 USA  🌍 3 World  ⛔ 4 NON-VBV detected     │
│  ─────────────────────────────────────────────────  │
│  4111111111111111 | 12/27 | VISA | Chase | US       │
│  5500005555555559 | 06/26 | MC | HSBC | GB          │
│  ... (max 5 строк)                                  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [25.00]                        │
│  ☐ Use PRICE column from file (column 16)           │
└─────────────────────────────────────────────────────┘
```

**Авто-детект NON-VBV:** если в поле Info (индекс 13) содержится "NON-VBV" или "NONVBV".

---

## 5. Selfreg CC — Правильная Архитектура

### 5.1 Отличие от Selfreg BA

Selfreg CC использует **отдельный каталог банков** `SelfregCCCategory` из БД (не BANK_CATALOG). Продавец может запросить добавление нового банка через `SelfregCCCategoryRequest`.

```
┌─────────────────────────────────────────────────────┐
│  SELFREG CC                                         │
│  BANK (from SelfregCCCategory table)                │
│  🔍 Search bank...                                  │
│  ─────────────────────────────────────────────────  │
│  Chase                                              │
│  Bank of America                                    │
│  Wells Fargo                                        │
│  Capital One                                        │
│  ... (из БД)                                        │
│  ─────────────────────────────────────────────────  │
│  [📝 Request new bank]  ← SelfregCCCategoryRequest  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  CARD DETAILS                                       │
│  Card type      [Credit ▼]                          │
│  Country        [US ▼]  State [CA ▼]               │
│  ZIP            [90001]                             │
│  ☐ Has SSN  ☐ Has DOB  ☐ Has Docs                  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [45.00                       ] │
└─────────────────────────────────────────────────────┘
```

---

## 6. Enroll — Правильная Архитектура

```
┌─────────────────────────────────────────────────────┐
│  ENROLL                                             │
│  PORTAL (from EnrollCategory table)                 │
│  🔍 Search portal...                                │
│  ─────────────────────────────────────────────────  │
│  FDECS                                              │
│  Digital Card Service                               │
│  MyCardPlace                                        │
│  ... (из БД)                                        │
│  ─────────────────────────────────────────────────  │
│  [📝 Request new portal]  ← EnrollCategoryRequest   │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  CARD DETAILS                                       │
│  Card type      [Credit ▼]                          │
│  Card ZIP       [90001]  Card State [CA ▼]          │
│  ☐ Has SSN  ☐ Has DOB  ☐ Has Docs                  │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [55.00                       ] │
└─────────────────────────────────────────────────────┘
```

---

## 7. Logs — Архитектура

```
┌─────────────────────────────────────────────────────┐
│  LOGS                                               │
│  Category       [Personal ▼]                        │
│                                                     │
│  FORMAT:                                            │
│  SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING      │
│  |NAME|ADDR|ZIP|PHONE|EMAIL|SSN|DOB|IP|FLAGS        │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  [textarea: paste logs here...]                     │
│  ─── or ───                                         │
│  [📎 Upload .txt / .zip file]                       │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  AUTO-COUNT                                         │
│  Total lines:    1,240                              │
│  CVV entries:      387                              │
│  Zelle entries:    198                              │
│  Wire entries:     142                              │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  PRICE                                              │
│  Price per item ($)  [2.50                        ] │
└─────────────────────────────────────────────────────┘
```

---

## 8. Полная схема Upload Center (как выглядит главный экран)

При полном доступе (все 10 разделов разблокированы):

```
┌─────────────────────────────────────────────────────┐
│  UPLOAD CENTER                              [?] [+] │
├─────────────────────────────────────────────────────┤
│  🏦 Banks (ATM)                              $150   │
│  Single upload · Wizard 6 steps                     │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  💥 Brute Bank                               $150   │
│  Single / Bulk · group_key auto-grouping            │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  💳 CC                                       $200   │
│  USA / World / NON-VBV · Bulk with price            │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  📱 NFC                                      $150   │
│  Apple Pay / Google Pay · File upload               │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  🔑 OTP                                      $100   │
│  Via Seller / Direct                                │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  🆕 Selfreg CC                               $150   │
│  Bank catalog + request new                         │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  🎓 Enroll                                   $100   │
│  Portal catalog + request new                       │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  📋 Logs                                     $200   │
│  Bulk / File · CVV/Zelle/Wire auto-count            │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  🧾 Checks                                   $150   │
│  Scan photo upload                                  │
│  [Upload]                                           │
├─────────────────────────────────────────────────────┤
│  🏛️ Selfreg BA                               $100   │
│  BANK_CATALOG · Bulk / File                         │
│  [Upload]                                           │
└─────────────────────────────────────────────────────┘
```

При частичном доступе — заблокированные разделы показываются с замком:

```
├─────────────────────────────────────────────────────┤
│  🔒 CC                                              │
│  Deposit required: $200                             │
│  [Unlock for $200 →]                                │
├─────────────────────────────────────────────────────┤
```

---

## 9. Пакеты депозитов (скидки)

| Пакет | Разделы | Цена | Полная цена | Скидка |
|-------|---------|------|-------------|--------|
| Starter | Banks + Brute | $200 | $300 | $100 |
| Digital | CC + NFC + OTP + Selfreg CC | $400 | $600 | $200 |
| Pro | Brute + CC + Logs + Selfreg BA | $450 | $700 | $250 |
| Full Access | Все 10 разделов | $750 | $1350 | $600 |

**Апгрейд:** всегда доплата разницы. Если уже оплачен Banks ($150) и запрашивается Starter ($200) → доплата $50.

---

## 10. Промт для Cursor

```
You are implementing the Upload Center for a Telegram Mini App (seller dashboard).
Stack: React 19 + TypeScript + Tailwind CSS 4 + Framer Motion.
DO NOT modify any existing database tables or models.

## Architecture Overview

There are 10 upload sections. Each has its own deposit requirement and UI form.
The key distinction between sections:

- **Brute Bank**: uses BruteBankGroup catalog from DB (grouped by bank_code + attributes).
  Seller picks an existing group OR creates a new one. group_key = make_brute_group_key(bank_code, attrs).
  
- **Selfreg BA**: uses BANK_CATALOG (VCC/Personal/Business/Crypto/Merchant hardcoded list).
  Seller picks category → picks bank from that category's list.
  
- **Selfreg CC**: uses SelfregCCCategory table from DB (requestable via SelfregCCCategoryRequest).
  
- **Enroll**: uses EnrollCategory table from DB (requestable via EnrollCategoryRequest).

## Task: Rewrite CCForm and BruteForm in UploadsTab.tsx

### File: client/src/components/tabs/UploadsTab.tsx

---

### CCForm Requirements

Three modes controlled by two UI elements:
1. Tab selector: [🇺🇸 USA CC] [🌍 World CC] — sets category_code ("usa" | "world")
2. Checkbox: ☐ NON VBV ⛔ — sets is_non_vbv boolean

When NON VBV is checked:
- Checkbox label turns red: text-red-400
- Card border turns red: border-red-500/40 bg-red-500/5

Mode selector: [Single Entry] [Bulk Upload]

**Single mode fields:**
```
Card Number*, EXP* (MM/YY), CVV*, Type (Credit/Debit), Brand (VISA/MC/AMEX/DISCOVER),
Level (CLASSIC/GOLD/PLATINUM/SIGNATURE), Bank name, Country (ISO), State, ZIP,
Holder name, Email, Phone, SSN (optional), DOB (optional)
Price per item ($)*
Item name (auto-generated from: "{Brand} {Level} {Country}")
```

**Bulk mode:**
- Textarea for paste + file upload button (.txt, .csv)
- Format hint line: `NUM|EXP|CVV|TYPE|BRAND|LEVEL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE`
- Live parser: on every textarea change, parse lines and show:
  ```
  🇺🇸 {usaCount} USA  🌍 {worldCount} World  ⛔ {nonVbvCount} NON-VBV detected
  ```
  - USA detection: parts[7].toUpperCase() === "US"
  - NON-VBV detection: parts[13]?.toUpperCase().includes("NON-VBV") || parts[13]?.toUpperCase().includes("NONVBV")
- Preview: show first 5 parsed lines in monospace, text-[11px] text-zinc-500
- Price: single input OR checkbox "☐ Use PRICE column from file (col 16)"

---

### BruteForm Requirements

The Brute Bank form shows EXISTING GROUPS from the API (not BANK_CATALOG).

**Add this constant:**
```typescript
const BRUTE_ATTRIBUTES_PRESETS = [
  "AN:RN",
  "AN:RN+INST YODLEE",
  "AN:RN+INST FINICITY",
  "AN:RN+INST YODLEE+INST FINICITY",
  "AN:RN+NAME+ADDRESS",
  "AN:RN+INST YODLEE+NAME+ADDRESS",
  "CHECKING",
  "SAVINGS",
  "$1K-$5K",
  "$5K-$10K",
  "$10K-$50K",
  "$50K+",
];

const BRUTE_CATEGORIES = ["vcc", "personal", "business", "crypto", "general"] as const;
```

**Mock groups for demo mode:**
```typescript
const MOCK_BRUTE_GROUPS = [
  { id: 1, group_key: "chase|an:rn+inst yodlee", bank_name: "Chase", bank_code: "chase", category: "personal", attributes: "AN:RN+INST YODLEE", count: 242 },
  { id: 2, group_key: "wells|an:rn+inst yodlee+name+address", bank_name: "Wells Fargo", bank_code: "wells", category: "personal", attributes: "AN:RN+INST YODLEE+NAME+ADDRESS", count: 26 },
  { id: 3, group_key: "bmo|an:rn+inst yodlee", bank_name: "BMO", bank_code: "bmo", category: "business", attributes: "AN:RN+INST YODLEE", count: 242 },
  { id: 4, group_key: "53|an:rn+inst yodlee+inst finicity", bank_name: "53 Bank", bank_code: "53", category: "personal", attributes: "AN:RN+INST YODLEE+INST FINICITY", count: 1439 },
  { id: 5, group_key: "td|an:rn", bank_name: "TD Bank", bank_code: "td", category: "personal", attributes: "AN:RN", count: 88 },
];
```

**UI Layout:**

Step 1 — Category filter tabs:
```
[💳 VCC] [🏦 Personal] [🏢 Business] [🪙 Crypto] [⚡ General]
```
Filters the groups list by category.

Step 2 — Group selector:
```
🔍 Search groups...
─────────────────────────────────────
Chase [AN:RN+INST YODLEE]        (242)
Wells Fargo [AN:RN+INST YODLEE+NAME+ADDRESS]  (26)
BMO [AN:RN+INST YODLEE]         (242)
─────────────────────────────────────
[+ Add to existing group]   ← selected by default
[+ Create new group]        ← shows new group form
```

Format for each group item: `{bank_name} [{attributes}]` + `({count})` right-aligned.

**Mode selector:** [Single Entry] [Bulk Upload]

**Single mode — when existing group selected:**
```
Credentials:
  Login (email/username)*
  Password*
  Extra (SSN, DOB, etc.) — optional

Balance:
  Balance info (e.g. "$5,200")
  Balance range: [$1K-$5K ▼]
  Account type: [CHECKING ▼] options: CHECKING, SAVINGS, BUSINESS, MONEY MARKET
  State (US): [CA ▼]

Price:
  Price per item ($)*
```

**Single mode — when creating new group:**
```
New Group:
  Category: [Personal ▼]
  Bank name*: [Chase]
  Bank code (auto): [chase] ← toLowerCase().replace(/\s+/g, '_') of bank_name
  Attributes: [AN:RN+INST YODLEE ▼] + [Custom...] text input
  Preview: group_key = "chase|an:rn+inst yodlee"

Then same credential/balance/price fields as above.
```

**Bulk mode:**
```
Format hint: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDR|ZIP|ATTRIBUTES

Textarea for paste + file upload (.txt)

Live preview — auto-grouped:
  Chase [AN:RN] × 5
  Wells Fargo [CHECKING] × 3
  BMO [AN:RN+INST YODLEE] × 2
  ─────────────────────────
  Total: 10 accounts

Price:
  Price per item ($)*
  ☐ Use PRICE column from file (last column)
```

---

### SelfregBAForm Requirements (also rewrite this)

**Uses BANK_CATALOG — NOT BruteBankGroup.**

Add this constant:
```typescript
const BANK_CATALOG = {
  vcc: [
    { id: "vcc_chime", name: "🤩 Chime VCC" },
    { id: "vcc_paypal", name: "🏦 PayPal VCC" },
    { id: "vcc_onepay", name: "🤩 One Pay VCC" },
    { id: "vcc_current", name: "🤩 Current VCC" },
    { id: "vcc_neteller", name: "🏦 Neteller VCC" },
    { id: "vcc_wise", name: "🎰 Wise Personal VCC" },
    { id: "vcc_netspend", name: "🤩 Netspend VCC" },
    { id: "vcc_greenfi", name: "🤩 GreenFi VCC" },
    { id: "vcc_quickbooks", name: "🏦 QuickBooks VCC" },
    { id: "vcc_go2bank", name: "🏛️ Go2Bank + VCC" },
    { id: "vcc_venmo", name: "🏛️ Venmo" },
    { id: "vcc_kikoff", name: "🏛️ Kikoff" },
    { id: "vcc_shopify", name: "🏛️ Shopify" },
    { id: "vcc_varo", name: "🏛️ Varo + VCC" },
  ],
  personal: [
    { id: "pers_citi", name: "🏦 Citi Personal" },
    { id: "pers_citi_gold", name: "🏦 Citi Gold Bank" },
    { id: "pers_usalliance", name: "🏦 Usalliance" },
    { id: "pers_usbank", name: "🏦 US Bank" },
    { id: "pers_ally", name: "🏦 Ally Bank" },
    { id: "pers_regions", name: "🏦 Regions Bank" },
    { id: "pers_chase", name: "🏦 Chase" },
    { id: "pers_wells", name: "🏦 WellsFargo" },
    { id: "pers_schwab", name: "🏦 Charles Schwab" },
    { id: "pers_citizens", name: "🏦 Citizens Bank" },
    { id: "pers_huntington", name: "🏦 Huntington Bank" },
    { id: "pers_td", name: "🏦 TD bank" },
    { id: "pers_boa", name: "🏦 BankOFAmerica" },
    { id: "pers_alliant", name: "🏦 Alliant Cu" },
    { id: "pers_pnc", name: "🏦 Pnc Bank" },
  ],
  business: [
    { id: "biz_quickbooks", name: "🏢 QuickBooks (LLC/CORP)" },
    { id: "biz_bmo", name: "🏢 Bmo Business" },
    { id: "biz_boa", name: "🏢 BankOFAmerica" },
    { id: "biz_usbank", name: "🏢 Us Business" },
    { id: "biz_north_one", name: "🏢 North One (LLC/Corp)" },
    { id: "biz_lili", name: "🏢 Lili Business Vcc" },
    { id: "biz_pnc", name: "🏢 Pnc Business" },
    { id: "biz_capital_one", name: "🏢 Capital One Business" },
    { id: "biz_chase", name: "🏢 Chase Business" },
    { id: "biz_wells", name: "🏢 Wells Fargo Business" },
  ],
  crypto: [
    { id: "crypto_cashapp", name: "💸 Cash App + BTC" },
    { id: "crypto_blockchain", name: "💸 Blockchain Gold" },
    { id: "crypto_kraken", name: "💸 Kraken" },
    { id: "crypto_coinbase", name: "💸 CoinBase" },
    { id: "crypto_crypto_com", name: "💸 Crypto.com" },
    { id: "crypto_binance", name: "💸 Binance" },
  ],
  merchant: [
    { id: "mrch_mercury", name: "🔷 Mercury LLC" },
    { id: "mrch_rho", name: "🔷 Rho LLC" },
    { id: "mrch_relay", name: "🔷 Relay LLC Europe/USA Owner" },
    { id: "mrch_revolut_biz", name: "🔷 Revolut Business LLC" },
    { id: "mrch_bluevine", name: "🔷 Blue Vine LLC" },
    { id: "mrch_novobank", name: "🔷 Novobank LLC" },
    { id: "mrch_wise_biz", name: "🔷 Wise Business LLC" },
    { id: "mrch_payoneer", name: "🔷 Payoneer LLC" },
    { id: "mrch_revolut_pers", name: "🔷 Revolut Personal on EMU" },
  ],
} as const;
```

**UI Layout:**
```
CATEGORY: [💳 VCC] [🏦 Personal] [🏢 Business] [🪙 Crypto] [🔷 Merchant]

BANK: searchable list from BANK_CATALOG[selectedCategory]

MODE: [Single Entry] [Bulk Upload]
```

**Single mode fields:**
```
Account type: CHECKING / SAVINGS / BUSINESS / MONEY MARKET
Account number*, Routing number*
Balance info, State (US), Name, Address, ZIP
SSN (optional), DOB (optional)
Login*, Password*
Price per item ($)*
```

**Bulk mode:**
```
Format: BANK|LOGIN|PASS|AN|RN|BALANCE|STATE|NAME|ADDR|ZIP|TYPE|SSN|DOB
Textarea + file upload
Preview: "Chase × 5 / WellsFargo × 4 / TD Bank × 3 — Total: 12 accounts"
Price per item ($)*
```

---

### Design Rules (DO NOT change)

- Background: bg-white/[0.05] cards, border-white/[0.08] borders
- Active tab: bg-blue-500 text-white rounded-lg
- Inactive tab: text-zinc-400 hover:text-white
- NON VBV active: border-red-500/40 bg-red-500/5, label text-red-400
- Bank/group list items: hover:bg-blue-500/10, selected: bg-blue-500/20 border-blue-500/40
- Bulk preview: font-mono text-[11px] text-zinc-500
- Detected counts: inline colored text (usa=text-blue-400, world=text-green-400, nonvbv=text-red-400)
- All form inputs: bg-white/[0.05] border-white/[0.08] rounded-lg px-3 py-2

### DO NOT change these existing components:
- SectionCard (home view cards)
- UploadForm wrapper
- BatchesPane and ListingsPane
- SECTIONS constant
- BUNDLES constant
- BankForm, NFCForm, OTPForm, SelfregCCForm, EnrollForm, LogsForm, ChecksForm
- TypeScript types CategoryCode, UploadSection
```
