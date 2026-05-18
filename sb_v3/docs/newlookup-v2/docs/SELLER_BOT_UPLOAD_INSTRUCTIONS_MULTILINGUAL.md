# Seller Bot Upload Instructions

## Purpose

This document defines seller-facing upload instructions for all supported languages in `seller_bot`.

Supported languages:

- `en`
- `ru`
- `zh`
- `es`

Applies to these sections:

- `Bank`
- `Enrol`
- `CC`
- `Brute`

---

## Global Rules

### What seller should understand

- choose the correct section before upload
- use one listing/batch for one logical product
- price is seller price
- buyer price is calculated automatically by system logic
- upload goes to moderation before becoming available

### Bulk upload scope

Keep bulk simple:

- `CC bulk` -> `text only`
- `Brute bulk` -> `text only`
- no complex bulk file logic for now

### File formats

- `Bank / Enrol / single uploads` may use ordinary bot input or future file flows
- `CC bulk` uses pasted text
- `Brute bulk` uses pasted text

### Main seller rules before deposit

Before making a deposit and before uploading goods, seller accepts these rules:

- do not leave your nickname, Telegram, Jabber, contact, watermark, signature, or hidden mark inside files/materials
- do not write your nickname in logs, screenshots, documents, card dumps, bank data, brute data, or archives
- do not redirect buyers to outside contacts
- do not upload mixed-quality or fake material under a wrong subtype

Penalty logic:

- first violation -> warning or temporary freeze
- repeated violation -> suspension
- severe violation -> ban

Hard rule:

- writing your own nickname inside uploaded material = `BAN / warning`

### Bank-specific fields seller must specify

For `Bank` and bank-like `Enrol` listings, seller should additionally specify phone/number access logic.

Required logic:

- `number_access_available`: `yes / no`
- if `yes` -> seller must set `rental_days`
- if `yes` -> seller must define `adaptive_report`
- if `no` -> seller must define `number_change_allowed: yes / no`

Recommended meaning:

- `number_access_available=yes` -> buyer receives temporary access to the linked number
- `rental_days` -> how many days this number access stays valid
- `adaptive_report` -> seller or worker provides status reports during the rental period
- `number_change_allowed=yes` -> if number access is not included, buyer may request number replacement when the product description allows it

Adaptive report rule:

- `1-3 days` -> start report + final report
- `4-7 days` -> start report + daily short report + final report
- `8+ days` -> start report + daily report + important status-change alerts + final report

### Auto-unpublish / auto-unload

Seller may optionally set listing lifetime.

Suggested fields:

- `auto_unpublish_enabled`
- `listing_duration_days`
- `auto_unpublish_at`

Logic:

- seller chooses how many days item should stay active
- when time expires, item is automatically removed from active stock
- no new orders can start after expiry
- active orders remain accessible until they are finished
- listing is unpublished, not hard-deleted
- seller may manually renew and send item to moderation again if needed

### Worker communication logic

Buyer should not talk to worker directly by default.

Recommended communication matrix:

- stock item from seller -> buyer talks only to seller
- manual/custom order handled by worker -> buyer talks to seller/support, worker stays internal
- if worker needs clarification -> request goes to moderation/support, then is relayed to buyer
- if buyer sends proof/problem -> it can be forwarded to worker internally without exposing worker contacts

This keeps:

- worker identity hidden
- one controlled communication channel
- less fraud and less off-platform contact

### Anti-abuse rule for CC returns

To prevent instant buy-and-cancel behavior for cards:

- `Return` must not instantly refund
- buyer must choose a reason first
- order then moves to `moderation_review`
- moderation checks reason, timing, and any proof
- only after moderation decision does order become `refunded` or `confirmed`

Suggested return reasons:

- `Card dead`
- `Wrong data`
- `Invalid ZIP / Fullz`
- `Duplicate / already used`
- `Seller description mismatch`
- `Other`

---

## English

## Bank

### Bank upload

1. Choose `Bank` or `Enrol`
2. Choose subtype
3. Choose category
4. Select existing type or create a new one
5. Enter your seller price
6. Add description
7. Add instruction
8. Choose support mode
9. Enter quantity
10. Submit for moderation

### Notes

- `Log` and `Selfreg` use the normal bank flow
- `Brute` uses a separate brute flow
- `Enrol` is uploaded through the bank-like flow with `Enrol / Selfreg`
- seller must specify if number access is available
- if number access is available, seller must specify rental days and adaptive report logic
- if number access is not available, seller must specify whether number replacement is allowed
- seller may optionally set auto-unpublish by days

## CC

### Single CC upload

1. Choose `With ZIP` or `With Fullz`
2. Choose category
3. Select existing type or create a new type
4. Enter seller price
5. Add description
6. Add instruction
7. Choose upload mode
8. For single upload, send card data
9. Submit for moderation

### CC bulk upload

Bulk is intentionally simple:

- paste text only
- one batch = one BIN
- all rows in one batch must belong to the same BIN

Suggested row format:

```text
BIN|Card|Exp|CVC|Type|Level|Bank|Country|ZIP|Fullz
```

Rules:

- `With ZIP` requires ZIP data
- `With Fullz` should include fullz or extra attached data
- mixed BINs in one batch should be rejected

## Brute

### Brute single upload

1. Open `Brute Bank`
2. Choose single or bulk
3. Enter bank name
4. Enter bank code
5. Enter range
6. Choose account type
7. Enter credentials/data
8. Enter balance info
9. Enter price
10. Review and submit

### Brute bulk upload

- paste text only
- one batch = one brute group / one bank template
- every row is one brute item
- no category selection for brute uploads

Current simple row format:

```text
login|password|balance|price|balance_range|account_type|extra
```

Future flexible logic may support rows with only `AN/RN` and no login.

---

## Russian

## Bank

### Загрузка Bank

1. Выберите `Bank` или `Enrol`
2. Выберите подтип
3. Выберите категорию
4. Выберите готовый тип или создайте новый
5. Введите цену селлера
6. Добавьте описание
7. Добавьте инструкцию
8. Выберите режим поддержки
9. Укажите количество
10. Отправьте на модерацию

### Примечания

- `Log` и `Selfreg` идут через обычный bank-flow
- `Brute` загружается через отдельный brute-flow
- `Enrol` идёт через bank-подобный flow с типом `Enrol / Selfreg`
- селлер должен указать, есть ли доступ к номеру
- если доступ к номеру есть, нужно указать срок аренды в днях и логику adaptive report
- если доступа к номеру нет, нужно указать, можно ли менять номер
- селлер может дополнительно указать авто-снятие товара по дням

## CC

### Одиночная загрузка CC

1. Выберите `With ZIP` или `With Fullz`
2. Выберите категорию
3. Выберите существующий тип или создайте новый
4. Введите цену селлера
5. Добавьте описание
6. Добавьте инструкцию
7. Выберите режим загрузки
8. Для single отправьте данные карты
9. Отправьте на модерацию

### Массовая загрузка CC

Массовая загрузка должна быть простой:

- только вставка текста
- одна партия = один BIN
- все строки в партии должны относиться к одному BIN

Формат строки:

```text
BIN|Card|Exp|CVC|Type|Level|Bank|Country|ZIP|Fullz
```

Правила:

- `With ZIP` требует ZIP
- `With Fullz` должен содержать fullz или доп. данные
- если в одном batch разные BIN, загрузка отклоняется

## Brute

### Одиночная загрузка Brute

1. Откройте `Brute Bank`
2. Выберите single или bulk
3. Введите название банка
4. Введите код банка
5. Введите range
6. Выберите тип счета
7. Введите credentials/данные
8. Введите баланс
9. Введите цену
10. Проверьте и отправьте

### Массовая загрузка Brute

- только вставка текста
- одна партия = одна brute group / один bank template
- одна строка = один brute item
- для brute категория не выбирается

Текущий простой формат:

```text
login|password|balance|price|balance_range|account_type|extra
```

Позже можно расширить до гибкого формата с `AN/RN` без обязательного логина.

---

## Chinese

## Bank

### Bank 上传

1. 选择 `Bank` 或 `Enrol`
2. 选择子类型
3. 选择分类
4. 选择现有类型或创建新类型
5. 输入卖家价格
6. 添加描述
7. 添加说明
8. 选择支持模式
9. 输入数量
10. 提交审核

### 说明

- `Log` 和 `Selfreg` 使用普通 bank 流程
- `Brute` 使用单独的 brute 流程
- `Enrol` 通过 `Enrol / Selfreg` 的 bank 类流程上传
- seller 必须说明是否包含号码访问权限
- 如果包含号码访问权限，必须填写租用天数和 adaptive report 逻辑
- 如果不包含号码访问权限，必须说明是否允许更换号码
- seller 也可以设置按天自动下架

## CC

### 单个 CC 上传

1. 选择 `With ZIP` 或 `With Fullz`
2. 选择分类
3. 选择现有类型或创建新类型
4. 输入卖家价格
5. 添加描述
6. 添加说明
7. 选择上传模式
8. 单个上传时发送卡数据
9. 提交审核

### CC 批量上传

批量上传应尽量简单：

- 只支持粘贴文本
- 一个 batch = 一个 BIN
- 同一 batch 中所有行必须属于同一个 BIN

建议格式：

```text
BIN|Card|Exp|CVC|Type|Level|Bank|Country|ZIP|Fullz
```

规则：

- `With ZIP` 必须包含 ZIP
- `With Fullz` 应包含 fullz 或额外数据
- 如果一个 batch 中混入多个 BIN，应拒绝上传

## Brute

### 单个 Brute 上传

1. 打开 `Brute Bank`
2. 选择 single 或 bulk
3. 输入银行名称
4. 输入银行代码
5. 输入范围
6. 选择账户类型
7. 输入凭据/数据
8. 输入余额信息
9. 输入价格
10. 检查后提交

### Brute 批量上传

- 只支持粘贴文本
- 一个 batch = 一个 brute group / 一个银行模板
- 每一行 = 一个 brute item
- brute 上传不选择分类

当前简单格式：

```text
login|password|balance|price|balance_range|account_type|extra
```

未来可扩展为只含 `AN/RN`、无需登录的灵活格式。

---

## Spanish

## Bank

### Carga de Bank

1. Elige `Bank` o `Enrol`
2. Elige subtipo
3. Elige categoría
4. Selecciona un tipo existente o crea uno nuevo
5. Ingresa tu precio de seller
6. Agrega descripción
7. Agrega instrucción
8. Elige modo de soporte
9. Ingresa cantidad
10. Envía a moderación

### Notas

- `Log` y `Selfreg` usan el flujo normal de bank
- `Brute` usa un flujo separado
- `Enrol` se carga por un flujo tipo bank con `Enrol / Selfreg`
- el seller debe indicar si existe acceso al número
- si existe acceso al número, debe indicar días de renta y lógica de adaptive report
- si no existe acceso al número, debe indicar si el número puede cambiarse
- el seller también puede configurar auto-despublicación por días

## CC

### Carga individual de CC

1. Elige `With ZIP` o `With Fullz`
2. Elige categoría
3. Selecciona tipo existente o crea uno nuevo
4. Ingresa precio del seller
5. Agrega descripción
6. Agrega instrucción
7. Elige modo de carga
8. Para single, envía los datos de la tarjeta
9. Envía a moderación

### Carga masiva de CC

La carga masiva debe ser simple:

- solo texto pegado
- un batch = un BIN
- todas las líneas del batch deben pertenecer al mismo BIN

Formato sugerido:

```text
BIN|Card|Exp|CVC|Type|Level|Bank|Country|ZIP|Fullz
```

Reglas:

- `With ZIP` requiere ZIP
- `With Fullz` debe incluir fullz o datos extra
- si un batch contiene BINs mezclados, se rechaza

## Brute

### Carga individual de Brute

1. Abre `Brute Bank`
2. Elige single o bulk
3. Ingresa nombre del banco
4. Ingresa código del banco
5. Ingresa rango
6. Elige tipo de cuenta
7. Ingresa credenciales/datos
8. Ingresa balance
9. Ingresa precio
10. Revisa y envía

### Carga masiva de Brute

- solo texto pegado
- un batch = un brute group / una plantilla de banco
- una línea = un brute item
- brute no usa selección de categoría

Formato simple actual:

```text
login|password|balance|price|balance_range|account_type|extra
```

Más adelante puede ampliarse a formato flexible con `AN/RN` sin login obligatorio.

