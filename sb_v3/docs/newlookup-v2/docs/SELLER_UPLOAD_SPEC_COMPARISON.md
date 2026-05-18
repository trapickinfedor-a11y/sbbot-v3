# Сравнение спецификации загрузчика с текущей реализацией

Документ сопоставляет вашу спецификацию (CC, NFC, Enroll, OTP, Selfregs, Logs, Brute, Checks) с тем, что реализовано в коде.

---

## Общие вопросы

### Массовая загрузка

| Продукт | Ваша спецификация | Текущая реализация |
|---------|-------------------|---------------------|
| CC | ✅ Да (plain text) | ✅ Да — bulk paste, до 200 строк |
| NFC | ❌ Нет | ❌ Нет типа NFC |
| Enroll | ❌ Только поштучно (ZIP) | Bank/Enrol — bulk по stock_count |
| OTP CARD | ❌ Только поштучно | ❌ Нет типа OTP |
| Selfregs BA | ❌ Только поштучно | Bank selfreg — bulk через stock_count |
| Selfregs CC | ❌ Только поштучно | Bank selfreg — bulk через stock_count |
| Logs | ❌ Только поштучно | Bank log — bulk через stock_count |
| Brute Banks | ✅ Да | ✅ Да — bulk paste |
| Checks | ❌ Только поштучно | Частично (через bank + check в description) |

### Добавление категорий

- **CC:** категории берутся из каталога (`CC_CATALOG`), селлер выбирает готовую или создаёт новую.
- **Bank:** категории vcc, personal, business, crypto — фиксированы.
- **Brute:** без выбора категории, категория определяется по bank_code/group.

### Параметры в названии / описании

- Название (`item_name` / `bank_name`) — свободный текст.
- Описание (`description`) — свободный текст.
- Шаблоны из спецификации (BIN, Type, Country, State, ZIP, флаги) **не генерируются автоматически** — селлер вводит описание вручную.

---

## 💳 CC

### Выбор перед загрузкой

| Ваша спецификация | Текущая реализация |
|------------------|---------------------|
| [Standard] [NON-VBV] [With Fullz] [With ZIP] | Только [With ZIP] [With Fullz] |
| — | Standard и NON-VBV **отсутствуют** как отдельные подтипы |

### Формат файла / строки

| Ваша спецификация | Текущая реализация |
|-------------------|---------------------|
| `NUMBER \| EXP_MM \| EXP_YYYY \| CVV \| FNAME \| LNAME \| ADDRESS \| CITY \| STATE \| ZIP \| COUNTRY` | `BIN \| Card \| Exp \| CVC \| Type \| Level \| Bank \| Country \| ZIP \| Fullz` |
| Обязательные: NUMBER, EXP_MM, EXP_YYYY, CVV, ZIP | Обязательные зависят от подтипа: With ZIP → ZIP; With Fullz → fullz или ZIP |
| Exp как MM и YYYY отдельно | Exp как MM/YY (12/25) в одном поле |

**Маппинг полей:**

| Ваше поле | Текущее поле |
|-----------|--------------|
| NUMBER | card (полный номер), bin (первые 6) |
| EXP_MM, EXP_YYYY | exp (объединённо, напр. 12/25) |
| CVV | cvc |
| FNAME, LNAME, ADDRESS, CITY, STATE, ZIP, COUNTRY | fullz (всё в одном) или zip |

### Название в категории

- Ваш шаблон: `Visa Gold | Chase | US | NY`
- Реализация: `item_name` — свободный текст, селлер вводит сам.

### Подтверждение и пост-покупка

- 15 минут на проверку — реализовано для CC (`check_window_minutes=15`).
- Like/dislike, report — в коде есть `order.check_started_at`, `check_started_at`, но полноценного like/dislike/report flow нет.
- Report → чат с селлером — `has_chat` на Bank, для CC отдельно не реализовано.

---

## 📱 NFC

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| Тип | Apple Pay (AP) / Google Pay (GP) | ❌ Тип NFC **не реализован** |
| Банк | Chase, Citi, BoA, Wells Fargo, + свой | — |
| Country, State, ZIP | Да | — |
| Цена за запись | Вручную | — |
| Файл | .txt / .zip | — |
| Массовая загрузка | Нет | — |
| Окно проверки | 24 часа | — |

---

## 🔐 Enroll

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| card_credit_debit | credit / debit | ❌ Нет в Bank/Enrol |
| portal | FDECS / DIGITALCARDSERVICE / MYCARDINFO / CARDNAV | ❌ Нет |
| card_type | Visa / MC / Amex / Discover | ❌ Нет |
| balance | число | — |
| state, zip | Да | — |
| ssn, has_dob, has_name, has_address | true/false | ❌ Нет |
| phone_area_code | 917 | ❌ Нет |
| has_email, has_security_qa, has_docs, doc_type | true/false | ❌ Нет |
| Массовая загрузка | Нет | Bank/Enrol — bulk по stock_count |

Enrol в коде — это `product_type="enrol"` с `product_subtype="selfreg"`, без детальных полей портала.

---

## 📲 OTP CARD

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| bank | Chase, Citi, BoA, + свой | — |
| balance | Есть/нет, число | — |
| Fullz | Yes/No | — |
| Доступ к SMS | Через продавца / через аккаунт | `number_access_available`, `rental_days` — есть для Bank |
| Название | OTP \| Chase \| $3,200 | — |
| Массовая загрузка | Нет | — |

Тип OTP CARD **не реализован** как отдельный продукт. Частично пересекается с Bank (number_access).

---

## 🏦 Selfregs BA

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| bank | Chase, BoA, Wells Fargo, + свой | bank_name, bank_code |
| state, zip | TX, 75001 | ❌ Нет в модели |
| has_phone, phone_days_remaining, phone_renewable | true/false, число | number_access_available, rental_days |
| email_access, способ смены | true/false, call/lk+hold | number_change_allowed |
| has_ssn, has_docs, doc_type | true/false | ❌ Нет |
| Название | Chase \| price \| TX \| Phone 14d | item_name свободный |
| Массовая загрузка | Нет | bulk через stock_count |

---

## 💳 Selfregs CC

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| bank | Citi, Chase, BoA, + свой | — |
| Название кредитки | Своё | — |
| VCC, виртуальный лимит | Да/Нет, лимит | ❌ Нет |
| state, zip | FL, 33101 | — |
| credit_limit | 5000 | — |
| has_email, has_phone, days, renewable, changeable | true/false | number_access для Bank |
| online_access | true/false | — |
| Массовая загрузка | Нет | — |

Selfregs CC как отдельный продукт **не реализован**.

---

## 📋 Logs

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| Подкатегории | Нет, всё в одном | Bank log — без подкатегорий |
| Пагинация | Да | Да (в mirror_bot) |
| Банк, счета, балансы | Выбор банка, несколько счетов | bank_name, bank_code, description |
| screen (optional) | autowatermark | ❌ Нет |
| Типы счетов | Checking, Savings, CC, Invest, Line of credit, BUS * | ❌ Нет структурированных типов |
| Крупные банки, инвестиционные, кредитные союзы | Списки | catalog_banks.py — частично |
| Флаги | has_cvv, bt_available, promo_available, zelle_enroll, wire_available, billpay_available, external_available, safepass_unlocked, need_phone_enroll | ❌ Нет в модели |
| Название | bank \| price \| balance | bank_name свободный |
| Массовая загрузка | Нет | bulk через stock_count |
| Report window | 6 hours | 15 min по умолчанию |

---

## 💥 Brute Banks

### Формат строки

| Ваша спецификация | Текущая реализация |
|-------------------|---------------------|
| `BANK \| LOGIN \| PASS \| ACCOUNT_NUMBER \| ROUTING \| BALANCE \| STATE \| NAME \| ADDRESS` | `login \| password \| balance \| price \| balance_range \| account_type \| extra` |
| Или `BANK \| no \| no \| ACCOUNT_NUMBER \| ROUTING \| BALANCE \| STATE \| NAME \| ADDRESS` | — |
| Обязательные: BANK, LOGIN, PASS, BALANCE | Обязательные: login, password, balance, price (в bulk) |

**Различия:**

- У вас BANK в начале строки; в коде bank_name задаётся отдельно для batch.
- ACCOUNT_NUMBER, ROUTING, STATE, NAME, ADDRESS — у вас отдельные поля; в коде — в `extra`.
- Формат `no|no|AN|RN|...` (без логина) — не поддерживается.

### Название

- Ваш шаблон: `GTE \| $3,200 \| FL \| Name ✅ \| Routing ✅`
- Реализация: bank_name + balance_info в description.

---

## 🖊 Checks

| Параметр | Ваша спецификация | Текущая реализация |
|----------|-------------------|---------------------|
| check_type | Personal / Business / Payroll / Cashier's | ❌ Нет (определяется по description) |
| bank | Chase, BoA, Wells Fargo, + свой | bank_name |
| amount | 1200 | — |
| state, zip | NY | — |
| has_holder_name, has_address | true/false | — |
| check_date | 03/2026 | — |
| seller_description | Текст | description |
| Status | Scan / photo / PS | — |
| scan.jpg | Обязательно | ❌ Нет загрузки файла для check |
| Название | Status \| $1,200 \| NY | — |
| Report window | 1 hour | 15 min по умолчанию |

Checks определяются по ключевым словам (check, cheque) в bank_name/bank_code/description для наценки, но отдельной модели и flow для Checks нет.

---

## Резюме: что нужно добавить/изменить

1. **CC**
   - Добавить подтипы Standard и NON-VBV.
   - Расширить формат: NUMBER, EXP_MM, EXP_YYYY, FNAME, LNAME, ADDRESS, CITY, STATE, ZIP, COUNTRY.
   - Опционально: автогенерация названия/описания по шаблону.

2. **NFC**
   - Новый тип продукта с полями: тип (AP/GP), банк, country, state, zip, цена, файл.

3. **Enroll**
   - Расширить модель: portal, card_type, balance, state, zip, ssn, has_dob, has_name, has_address, has_email, has_security_qa, has_docs, doc_type, phone_area_code.

4. **OTP CARD**
   - Новый тип продукта: bank, balance, Fullz, SMS access.

5. **Selfregs BA / CC**
   - Добавить state, zip, has_ssn, has_docs, doc_type.
   - Для Selfregs CC: VCC, credit_limit, online_access.

6. **Logs**
   - Структурированные типы счетов и флаги (has_cvv, bt_available, billpay_available и т.д.).
   - Отдельные report windows (например, 6 hours).

7. **Brute**
   - Поддержка формата `BANK|LOGIN|PASS|ACCOUNT|ROUTING|BALANCE|STATE|NAME|ADDRESS`.
   - Поддержка варианта без логина (no|no|AN|RN|...).

8. **Checks**
   - Отдельная модель/flow: check_type, amount, state, zip, has_holder_name, has_address, check_date, обязательная загрузка scan.
   - Report window 1 hour.

9. **Post-purchase**
   - Like/dislike после проверки.
   - Report → чат с селлером для всех типов.
