# Multilingual Notifications And Bots Spec

## 1. Scope

This document fixes the target logic for:

- multilingual notifications in `mirror_bot`
- standard notifications in `seller_bot`
- standard notifications in `marketer_bot`
- direct buttons from notifications to specific positions/screens
- top-up notifications in 4 languages
- current time handling and known inconsistencies

Supported languages in codebase right now:

- `en`
- `ru`
- `zh`
- `es`

Confirmed in:

- `mirror_bot/constants/language_loader.py`
- `seller_bot/constants/language_loader.py`

---

## 2. Current State

### 2.1 Mirror Bot

Current state:

- multilingual buyer texts already exist for `en/ru/zh/es`
- payment success notifications to users already exist
- seller chat notifications already support buttons
- direct product-position buttons are only partially implemented depending on section

Current direct buttons already used in buyer/seller chat:

- `Open in Bot`
- `Open Mini App`

### 2.2 Seller Bot

Current state:

- seller bot already supports `en/ru/zh/es`
- seller receives standard workflow messages in bot
- mini app button already exists
- order/chat/upload sections are present

### 2.3 Marketer Bot

Current state:

- marketer bot exists
- withdrawal/log/promo/broadcast flows exist
- no unified multilingual notification matrix is fixed yet
- standard push notifications should be added explicitly

### 2.4 Admin Notifications

Current state:

- `AdminNotificationService` is centralized
- time in admin notifications is rendered in `UTC`
- admin notifications are plain text HTML messages without per-event inline action buttons

---

## 3. Time Handling Status

### 3.1 What works now

Most backend events are timestamped with `datetime.utcnow()`.

That means:

- order events are written consistently in UTC
- seller moderation/admin actions are mostly UTC
- upload batches are mostly UTC
- admin notification timestamps are UTC

### 3.2 What is inconsistent now

There is still mixed usage of:

- `datetime.utcnow()`
- `datetime.now()`
- browser local time rendering via `toLocaleString()`

This can lead to visible time mismatches between:

- bot notifications
- mini app/browser pages
- payment expiration countdown

### 3.3 Target rule

Use this rule everywhere:

- backend stores and computes in `UTC`
- bot notifications explicitly say `UTC` if raw timestamp is shown
- frontend converts to local time only for visual display
- payment expiration logic must use one consistent time source per flow

### 3.4 Required follow-up

Audit and normalize:

- `mirror_bot/handlers/payment.py`
- `mirror_bot/services/payment_monitor.py`
- mini app time rendering
- any remaining `datetime.now()` usages in payment and expiry logic

Until this audit is finished, time handling should be considered:

- `mostly working`
- `not fully normalized`

---

## 4. Notification Matrix

## 4.1 Mirror Bot notifications

Mirror bot should send multilingual notifications for:

- top-up success
- top-up pending/created
- top-up expired
- top-up failed
- seller wrote to buyer
- order ready
- order confirmed
- order returned
- dispute opened
- broadcast

### Direct buttons allowed in mirror bot notifications

Allowed button targets:

- open category directly
- open concrete item directly
- open order directly
- open chat directly
- open payment page directly

Examples:

- `Top up balance`
- `Open BANKS`
- `Open Brute`
- `Open CC`
- `Open My Orders`
- `Open Seller Chat`

### Required direct-link rule

Every important buyer notification should include at least one action button if there is a clear next step.

Examples:

- top-up success -> `Open Catalog` / `Top up again`
- seller message -> `Open Chat`
- order ready -> `My Orders`
- direct promo/top-up campaign -> button to exact section

---

## 4.2 Seller Bot notifications

Seller bot should send standard notifications for:

- new order
- complaint/dispute
- new buyer message
- moderation approved
- moderation rejected
- payout created
- payout approved
- payout rejected
- buyer rated order like
- buyer rated order dislike
- important system broadcasts

### Direct buttons allowed in seller bot

- `Open Order`
- `Open Chat`
- `Open Mini App`
- `Open Uploads`
- `Open Withdraw`

### Existing good pattern

Buyer-to-seller chat pushes already use:

- open in bot
- open mini app

This should be kept as the standard pattern for seller-facing pushes.

---

## 4.3 Marketer Bot notifications

Marketer bot should receive ordinary notifications for:

- a specific marketer promo code was linked to a user
- a new user registered via a specific marketer promo code
- user made first top-up
- user made normal top-up
- marketer reward credited
- withdrawal created
- withdrawal approved
- withdrawal rejected
- system broadcast

### Direct buttons allowed in marketer bot

- `Open Dashboard`
- `Open Logs`
- `Open Promo`
- `Open Withdraw`

Marketer pushes do not need complex deep-links to product positions.

---

## 5. Top-up Notifications In 4 Languages

This section fixes the requirement:

- one event
- 4 language templates
- one defined action button
- optional direct button to exact position/category

Supported languages:

- `en`
- `ru`
- `zh`
- `es`

## 5.1 Event: Top-up success

### English

```text
Balance top-up successful

Amount: ${amount}
New balance: ${balance}

Choose where to go next.
```

### Russian

```text
Пополнение баланса успешно

Сумма: ${amount}
Новый баланс: ${balance}

Выберите, куда перейти дальше.
```

### Chinese

```text
余额充值成功

金额：${amount}
新余额：${balance}

请选择下一步操作。
```

### Spanish

```text
Recarga de saldo exitosa

Monto: ${amount}
Nuevo saldo: ${balance}

Elige a dónde ir ahora.
```

### Buttons

Base buttons:

- `Open Catalog`
- `Top Up Again`

Optional campaign-specific direct buttons:

- `Open BANKS`
- `Open CC`
- `Open BRUTE`
- `Open NFC`
- `Open specific promoted position`

---

## 5.2 Event: Top-up pending / invoice created

### English

```text
Top-up invoice created

Amount: ${amount}
Method: ${method}

Complete the payment before it expires.
```

### Russian

```text
Инвойс на пополнение создан

Сумма: ${amount}
Метод: ${method}

Оплатите до истечения срока.
```

### Chinese

```text
充值订单已创建

金额：${amount}
方式：${method}

请在过期前完成支付。
```

### Spanish

```text
Factura de recarga creada

Monto: ${amount}
Método: ${method}

Completa el pago antes de que expire.
```

### Buttons

- `Pay Now`
- `Cancel`

---

## 5.3 Event: Top-up expired

### English

```text
Top-up invoice expired

Amount: ${amount}
You can create a new payment.
```

### Russian

```text
Инвойс на пополнение истёк

Сумма: ${amount}
Вы можете создать новый платёж.
```

### Chinese

```text
充值订单已过期

金额：${amount}
您可以重新创建支付。
```

### Spanish

```text
La factura de recarga expiró

Monto: ${amount}
Puedes crear un nuevo pago.
```

### Buttons

- `Top Up Again`
- `Write To Support`

---

## 5.4 Event: Top-up failed

### English

```text
Top-up failed

Amount: ${amount}
Method: ${method}

Please try again or contact support.
```

### Russian

```text
Пополнение не удалось

Сумма: ${amount}
Метод: ${method}

Попробуйте снова или напишите в поддержку.
```

### Chinese

```text
充值失败

金额：${amount}
方式：${method}

请重试或联系支持。
```

### Spanish

```text
La recarga falló

Monto: ${amount}
Método: ${method}

Inténtalo de nuevo o contacta al soporte.
```

### Buttons

- `Top Up Again`
- `Write To Support`

---

## 6. Direct Buttons To Exact Positions

## 6.1 Rule

Notification buttons may target:

- exact section
- exact category
- exact item

### Recommended callback/deeplink patterns

- `open_section:banks`
- `open_section:cc`
- `open_category:banks:brute`
- `open_category:cc:with_zip`
- `open_item:banks:<bank_code>`
- `open_item:cc:<cc_code>`

If deep callback is not safe from every context, use:

- first button to open section
- second button to open the exact list/search state

## 6.2 Use cases

### Example A. Top-up campaign for brute

Notification text:

- user topped up
- show “Brute available now”

Buttons:

- `Open Brute`
- `My Balance`

### Example B. Top-up campaign for CC with ZIP

Buttons:

- `Open CC With ZIP`
- `Search BIN`

### Example C. Seller message

Buttons:

- `Open Chat`
- `Open Mini App`

---

## 7. Notification Implementation Rules

### 7.1 Language resolution

Use one of:

- user language from DB
- seller language from DB
- marketer language from DB
- fallback to `en`

### 7.2 Message generation

Every notification event should have:

- event code
- recipient type
- language templates
- button template

Recommended service:

- `shared/services/multilingual_notification_service.py`

Responsibilities:

- resolve language
- render text
- attach buttons
- log delivery result

### 7.3 Logging

Every sent notification should be logged via notification log service with:

- `event_type`
- `channel`
- `recipient_id`
- `status`
- `payload`

---

## 8. Bot-Specific Required Notifications

## 8.1 Mirror Bot required

- top-up success
- top-up expired
- top-up failed
- seller message
- order ready
- order confirmed
- return/refund result
- campaign push with direct section button

## 8.2 Seller Bot required

- buyer wrote message
- order created
- order approved
- order rejected
- moderation approved
- moderation rejected
- payout status changed
- buyer rated order like/dislike
- direct open mini app button where useful

## 8.3 Marketer Bot required

- promo linked to a specific marketer promo code
- referred user first top-up
- marketer commission added
- withdrawal created
- withdrawal approved
- withdrawal rejected
- broadcast message

---

## 9. Current Gaps

Current gaps before this system is considered fully done:

- no unified multilingual notification template registry
- admin notifications are not multilingual
- top-up direct-to-position campaign buttons are not standardized
- marketer bot ordinary notification matrix is not fixed in code
- seller bot ordinary notification matrix is only partially standardized
- time handling is not fully normalized across payment and frontend flows

---

## 10. Recommended Next Steps

### Phase 1

- normalize time handling
- create multilingual notification registry for `en/ru/zh/es`
- standardize mirror bot top-up notifications with buttons

### Phase 2

- add ordinary seller bot notification templates
- add ordinary marketer bot notification templates
- add direct section/category buttons for campaign pushes

### Phase 3

- add unified notification service
- connect all major events through one service
- log and retry failed notifications

---

## 11. Delivery Definition

This spec should be considered complete when:

- same notification event exists in `en/ru/zh/es`
- mirror bot top-up notification can open exact section or position
- seller bot receives standardized order/chat/moderation pushes
- marketer bot receives standardized earning/withdrawal pushes
- time display is normalized and documented as UTC/backend + local/frontend

