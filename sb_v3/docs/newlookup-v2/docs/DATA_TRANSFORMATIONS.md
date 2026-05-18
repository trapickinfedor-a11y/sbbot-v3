# ПРЕОБРАЗОВАНИЯ ДАННЫХ
## Mini App ↔ Telegram Bot ↔ Database

---

## 📊 ОБЩАЯ СХЕМА

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Mini App    │─────▶│  Admin API   │─────▶│  Database    │
│  (TypeScript)│      │   (Python)   │      │  (SQLite)    │
└──────────────┘      └──────────────┘      └──────────────┘
     │                       │                       │
     │  FormData/JSON        │  SQLAlchemy           │
     │  string values        │  type conversion      │  typed columns
     └───────────────────────┴───────────────────────┘
                  Преобразования данных
```

---

## 🔄 ТИПЫ ПРЕОБРАЗОВАНИЙ

### 1. Даты (Date Conversion)

**Формат Mini App:** `"MM/DD/YYYY"` (string)  
**Формат БД:** `DATE` (datetime.date)

```typescript
// Mini App (отправка)
const regDate = "03/15/2025";  // MM/DD/YYYY

// Python API (получение → БД)
from datetime import datetime
reg_date = datetime.strptime(reg_date_str, "%m/%d/%Y").date()
# Result: datetime.date(2025, 3, 15)
```

**Обратное преобразование (БД → Mini App):**
```python
# Python API (БД → отправка)
reg_date.strftime("%m/%d/%Y")
# Result: "03/15/2025"
```

---

### 2. Boolean (True/False)

**Формат Mini App:** `"true"` / `"false"` (string)  
**Формат БД:** `BOOLEAN` (bool)

```typescript
// Mini App (отправка)
fd.append("email_access", String(emailAccess));  // "true" or "false"

// Python API (получение → БД)
email_access = form_data.get("email_access", "false").lower() == "true"
# Result: True or False (bool)
```

**Обратное преобразование:**
```python
# Python API (БД → отправка)
"true" if item.email_access else "false"
```

---

### 3. Числа (Numbers)

#### 3.1 Price (Float)

**Формат Mini App:** `"15.00"` (string)  
**Формат БД:** `FLOAT` (float)

```typescript
// Mini App
fd.append("price", price);  // "15.00"

// Python API
price = float(form_data.get("price", "0.00"))
# Result: 15.0 (float)
```

#### 3.2 Balance (Money Format)

**Формат Mini App:** `"$5,000"` (string with $ and ,)  
**Формат БД:** `FLOAT` (float)

```typescript
// Mini App
const balance = "$5,240.50";

// Python API
balance_str = form_data.get("balance", "$0").replace("$", "").replace(",", "")
balance = float(balance_str)
# Result: 5240.50 (float)
```

#### 3.3 Integer (Phone Days, Return Days)

**Формат Mini App:** `"30"` (string)  
**Формат БД:** `INTEGER` (int)

```typescript
// Mini App
fd.append("phone_rental_days", phoneDays);  // "30"

// Python API
phone_days = int(form_data.get("phone_rental_days", "0"))
# Result: 30 (int)
```

---

### 4. Строки (Strings)

#### 4.1 Category

**Формат Mini App:** `"vcc"`  
**Формат БД:** `VARCHAR(20)`

```typescript
// Mini App
fd.append("category", cat);  // "vcc", "personal", "business"...

// Python API - без изменений
category = form_data.get("category")
# Result: "vcc" (str)
```

#### 4.2 State (2 Letters)

**Формат Mini App:** `"CA"`  
**Формат БД:** `VARCHAR(10)`

```typescript
// Mini App
fd.append("state", state);  // "CA", "NY"...

// Python API - без изменений
state = form_data.get("state", "").upper()[:2]
# Result: "CA" (str)
```

#### 4.3 ZIP

**Формат Mini App:** `"90210"`  
**Формат БД:** `VARCHAR(20)`

```typescript
// Mini App
fd.append("zip", zip);  // "90210"

// Python API - без изменений
zip_code = form_data.get("zip")
# Result: "90210" (str)
```

---

### 5. Списки (Arrays)

#### 5.1 Product Types

**Mini App:**
```typescript
const PRODUCT_TYPES = {
  vcc: ["Virtual Card", "Prepaid Card", "Gift Card"],
  personal: ["Checking Account", "Savings Account", ...],
  // ...
};
```

**БД:** `VARCHAR(100)` (single value)

```typescript
// Mini App (выбор одного значения)
fd.append("product_type", productType);  // "Virtual Card"

// Python API - без изменений
product_type = form_data.get("product_type")
# Result: "Virtual Card" (str)
```

---

### 6. Файлы (Files)

#### 6.1 Access File

**Формат Mini App:** `FormData` с файлом  
**Формат БД:** `VARCHAR(500)` (путь к файлу)

```typescript
// Mini App
fd.append("access_file", accessFile);  // File object

# Python API (сохранение → путь)
file = form_data.get("access_file")
file_path = f"data/uploads/{seller_id}/{uuid4()}.txt"
with open(file_path, "wb") as f:
    f.write(file.read())
# Result: "data/uploads/123/abc-123.txt" (str)
```

---

## 📋 ТАБЛИЦА ВСЕХ ПРЕОБРАЗОВАНИЙ

| Поле | Mini App Type | Mini App Format | Python Type | DB Type | Преобразование |
|------|---------------|-----------------|-------------|---------|----------------|
| `registration_date` | string | "MM/DD/YYYY" | date | DATE | `strptime("%m/%d/%Y")` |
| `dob` | string | "MM/DD/YYYY" | date | DATE | `strptime("%m/%d/%Y")` |
| `email_access` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `phone_access` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `has_phone` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `has_ssn` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `has_docs` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `return_item_enabled` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `phone_can_swap` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `phone_renewable` | string | "true"/"false" | bool | BOOLEAN | `.lower()=="true"` |
| `price` | string | "15.00" | float | FLOAT | `float(value)` |
| `balance` | string | "$5,000" | float | FLOAT | `replace("$","").replace(",","")` |
| `exact_balance` | string | "5000.50" | float | FLOAT | `float(value)` |
| `credit_limit` | string | "5000" | float | FLOAT | `float(value)` |
| `vcc_limit` | string | "2000" | float | FLOAT | `float(value)` |
| `amount` (Check) | string | "2500.00" | float | FLOAT | `float(value)` |
| `phone_days_remaining` | string | "30" | int | INTEGER | `int(value)` |
| `return_days` | string | "7" | int | INTEGER | `int(value)` |
| `category` | string | "vcc" | str | VARCHAR(20) | ✅ |
| `bank_code` | string | "vcc_chime" | str | VARCHAR(50) | ✅ |
| `product_type` | string | "Virtual Card" | str | VARCHAR(100) | ✅ |
| `state` | string | "CA" | str | VARCHAR(10) | ✅ |
| `zip` | string | "90210" | str | VARCHAR(20) | ✅ |
| `country` | string | "US" | str | VARCHAR(2) | ✅ |
| `bank_name` | string | "Chase" | str | VARCHAR(200) | ✅ |
| `first_name` | string | "John" | str | VARCHAR(100) | ✅ |
| `last_name` | string | "Doe" | str | VARCHAR(100) | ✅ |
| `card_number` | string | "4111111111111111" | str | VARCHAR(19) | ✅ |
| `exp_month` | string | "12" | int | INTEGER | `int(value)` |
| `exp_year` | string | "27" | int | INTEGER | `int(value)` |
| `cvv` | string | "123" | str | VARCHAR(4) | ✅ |
| `login` | string | "user123" | str | VARCHAR(200) | ✅ |
| `password` | string | "pass123" | str | VARCHAR(200) | ✅ |
| `account_number` | string | "123456789" | str | VARCHAR(50) | ✅ |
| `routing_number` | string | "021000021" | str | VARCHAR(50) | ✅ |

---

## 🛠 ПРИМЕРЫ КОДА

### Mini App (TypeScript) - Отправка

```typescript
// Banks форма
const submit = async () => {
  const fd = new FormData();
  
  // Strings (без изменений)
  fd.append("category", cat);  // "vcc"
  fd.append("bank_id", finalBankId);  // "vcc_chime"
  fd.append("bank_name", finalBankName);  // "Chime VCC"
  fd.append("product_type", productType);  // "Virtual Card"
  
  // Date (MM/DD/YYYY format)
  const regDate = [regMm, regDd, regYyyy].filter(Boolean).join("/");
  fd.append("registration_date", regDate);  // "03/15/2025"
  
  // Booleans (string "true"/"false")
  fd.append("email_access", String(emailAccess));  // "true"
  fd.append("phone_access", String(phoneAccess));  // "false"
  fd.append("phone_can_extend", String(phoneExtend));  // "true"
  fd.append("phone_can_swap", String(phoneSwap));  // "false"
  fd.append("return_item", String(returnItem));  // "true"
  
  // Numbers (strings)
  fd.append("phone_rental_days", phoneDays);  // "30"
  fd.append("return_days", returnDays);  // "7"
  fd.append("price", price);  // "45.00"
  
  // File
  if (accessFile) fd.append("access_file", accessFile);
  
  await apiFormData("/api/seller-mini-app/uploads/submit", fd);
};
```

### Python API (FastAPI) - Получение

```python
@router.post("/uploads/submit")
async def submit_upload(
    request: Request,
    item_type: str = Form(...),
    category: str = Form(None),
    bank_id: str = Form(None),
    bank_name: str = Form(None),
    product_type: str = Form(None),
    registration_date: str = Form(None),  # "MM/DD/YYYY"
    email_access: str = Form("false"),  # "true"/"false"
    phone_access: str = Form("false"),
    phone_rental_days: str = Form("0"),
    price: str = Form(...),
    access_file: UploadFile = File(None),
):
    # Преобразование даты
    reg_date = None
    if registration_date:
        reg_date = datetime.strptime(registration_date, "%m/%d/%Y").date()
    
    # Преобразование boolean
    email_access_bool = email_access.lower() == "true"
    phone_access_bool = phone_access.lower() == "true"
    
    # Преобразование numbers
    phone_days = int(phone_rental_days)
    price_float = float(price)
    
    # Сохранение файла
    file_path = None
    if access_file:
        file_path = f"data/uploads/{seller_id}/{uuid4()}.txt"
        with open(file_path, "wb") as f:
            f.write(await access_file.read())
    
    # Создание записи в БД
    item = SellerBankItem(
        category=category,
        bank=bank_name,
        product_type=product_type,
        registration_date=reg_date,  # datetime.date
        email_access=email_access_bool,  # bool
        phone_access=phone_access_bool,  # bool
        phone_days_remaining=phone_days,  # int
        price=price_float,  # float
        ...
    )
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕТКИ

1. **Все boolean поля** в FormData отправляются как строки `"true"`/`"false"`
2. **Даты** всегда в формате `MM/DD/YYYY` (американский формат)
3. **Цены** всегда с двумя знаками после запятой: `"15.00"`
4. **Balance** может содержать `$` и `,`: `"$5,240.50"` → `5240.50`
5. **State** всегда 2 буквы: `"CA"`, `"NY"` (верхний регистр)
6. **ZIP** может быть 5 или 10 цифр: `"90210"` или `"90210-1234"`

---

**ВЕРСИЯ:** 1.0  
**ДАТА:** 2026-03-24
