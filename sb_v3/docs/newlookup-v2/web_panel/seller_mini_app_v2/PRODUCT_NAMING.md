# Именование позиций в Orders / Listings / Batches

## Источники данных в БД

Название позиции формируется из нескольких полей в зависимости от `item_type`:

| Поле | Таблица | Описание |
|------|---------|---------|
| `bank_name` | `SellerBank` | Название банка заданное продавцом |
| `item_type` | `SellerOrder` | Тип товара: `bank_log`, `brute`, `cc`, `nfc`, `otp`, `selfreg_cc`, `enroll`, `logs`, `checks`, `selfreg_ba` |
| `category` | `SellerBank` | Подкатегория: Personal, Business, VCC, Crypto, Merchant |
| `attributes` | `BruteBankGroup` | Атрибуты brute: `AN:RN`, `AN:RN+INST YODLEE`, `ZELLE WIRE` и др. |
| `is_non_vbv` | `SellerCCItem` | Флаг NON VBV для CC |
| `bank_category` | `SellerSelfregCC` | Категория банка для Selfreg CC |
| `portal_name` | `SellerEnrollItem` | Портал для Enroll: FDECS, CardNav и др. |

---

## Формат названия `product_name`

Функция `_build_product_name(order)` в `seller_mini_app.py`:

```python
TYPE_LABELS = {
    "bank_log":   "Bank Log",
    "brute":      "Brute",
    "cc":         "CC",
    "nfc":        "NFC",
    "otp":        "OTP",
    "selfreg_cc": "Selfreg CC",
    "enroll":     "Enrollment",
    "logs":       "Logs",
    "checks":     "Check",
    "selfreg_ba": "Selfreg BA",
}

def _build_product_name(order: SellerOrder, seller_bank: SellerBank | None) -> str:
    type_label = TYPE_LABELS.get(order.item_type, order.item_type)
    bank = seller_bank.bank_name if seller_bank else "Unknown"

    if order.item_type == "brute":
        attrs = getattr(order, "brute_attributes", "") or ""
        return f"Brute · {bank} [{attrs}]" if attrs else f"Brute · {bank}"

    if order.item_type == "cc":
        non_vbv = " · NON VBV" if getattr(order, "is_non_vbv", False) else ""
        return f"CC · {bank}{non_vbv}"

    if order.item_type == "selfreg_cc":
        cat = getattr(order, "bank_category", "") or ""
        return f"Selfreg CC · {bank} · {cat}" if cat else f"Selfreg CC · {bank}"

    if order.item_type == "enroll":
        portal = getattr(order, "portal_name", "") or ""
        return f"Enrollment · {portal} · {bank}" if portal else f"Enrollment · {bank}"

    if order.item_type in ("bank_log", "banks"):
        cat = getattr(seller_bank, "category", "") or ""
        return f"Bank Log · {bank} · {cat}" if cat else f"Bank Log · {bank}"

    return f"{type_label} · {bank}"
```

---

## Примеры отображения

| item_type | product_name |
|-----------|-------------|
| `bank_log` | `Bank Log · Chase Business` |
| `bank_log` | `Bank Log · TD Bank · Business` |
| `brute` | `Brute · Wells Fargo [AN:RN]` |
| `brute` | `Brute · Chase [AN:RN+INST YODLEE]` |
| `cc` | `CC · Bank of America · NON VBV` |
| `cc` | `CC · Citi` |
| `selfreg_cc` | `Selfreg CC · Citi · Personal` |
| `selfreg_cc` | `Selfreg CC · Chase · Business` |
| `enroll` | `Enrollment · FDECS · Chase` |
| `nfc` | `NFC · Apple Pay · Chase` |
| `otp` | `OTP · Wells Fargo` |
| `checks` | `Check · Business · Chase` |
| `selfreg_ba` | `Selfreg BA · TD Bank · Personal` |
| `logs` | `Logs · Chase` |

---

## Отображение в Mini App (Orders)

```
┌─────────────────────────────────────────────┐
│ Bank Log · Chase Business          #1001    │
│ Mar 23, 06:38 AM · Buyer #4821              │
│                              $100.00 ● Active│
└─────────────────────────────────────────────┘
```

Формат строки в карточке заказа:
- **Строка 1:** `{product_name}` + `#{id}` справа
- **Строка 2:** `{дата}` · `Buyer: {buyer_label}`
- **Строка 3:** `${seller_amount}` + статус-бейдж

---

## Реализация в бэкенде

### Новый эндпоинт `/orders` должен возвращать:

```json
{
  "id": 1001,
  "status": "in_progress",
  "product_name": "Bank Log · Chase Business",
  "item_type": "bank_log",
  "bank_name": "Chase Business",
  "amount": 120.00,
  "seller_amount": 100.00,
  "buyer_label": "Buyer #4821",
  "created_at": "2026-03-23T06:38:00Z",
  "updated_at": "2026-03-23T07:08:00Z"
}
```

`product_name` вычисляется на стороне сервера через `_build_product_name()` и кешируется в `SellerOrder.product_name_cache` (nullable text column) — обновляется при каждом изменении заказа.

---

## Промт для Cursor (бэкенд)

```
Add product_name_cache column to SellerOrder model (nullable Text).
Implement _build_product_name(order, seller_bank) function in seller_mini_app.py
using TYPE_LABELS dict and item_type-specific formatting rules above.
Call it in the /orders GET endpoint and include product_name in the response.
Update it via after_update event listener on SellerOrder.
```
