# Проверка товара после покупки + Mini App селлера + оценка Like / Dislike

## 1. Цель

Нужно зафиксировать полную понятную логику того, что происходит после покупки товара селлера:

- как покупатель получает товар
- как он проверяет товар
- когда можно написать селлеру
- когда можно вернуть товар
- когда открывается dispute / report
- где появляется финальная оценка `Like / Dislike`
- что получает селлер после оценки

Эта логика должна быть одинаково понятна для:

- `Mirror Bot`
- `Seller Bot`
- `Mini App`
- backend-статусов заказа

---

## 2. Базовая модель

После покупки каждый товар должен быть отнесён к одному из двух режимов:

| Режим | Примеры | Чат | Проверка |
|------|---------|-----|----------|
| **С поддержкой** | `Bank log`, `Bank selfreg`, `Enrol`, `CC fullz`, другие позиции где селлер помогает | ✅ | Покупатель может написать селлеру и вручную подтвердить результат |
| **Без поддержки** | `Brute`, простые `CC`, любой fast-delivery без сопровождения | ❌ | Покупатель получает фиксированное окно проверки, затем подтверждает или возвращает |

Рекомендуемое поле в товаре:

```python
has_chat: bool = True
```

Правило:

- `has_chat=True` -> товар продаётся с поддержкой и чатом
- `has_chat=False` -> товар продаётся без чата, только окно проверки

---

## 3. Общий жизненный цикл заказа

### 3.1 Основные статусы

Рекомендуемый order-flow:

1. `pending_payment`
2. `paid`
3. `processing`
4. `delivered`
5. `check_pending`
6. одно из финальных:
   - `return_requested`
   - `moderation_review`
   - `confirmed`
   - `auto_confirmed`
   - `returned`
   - `disputed`
   - `refunded`

### 3.2 Когда начинается проверка

Проверка начинается только после того, как покупателю реально выдан товар или все данные для проверки:

- материал отправлен
- заказ помечен как доставленный
- buyer может открыть заказ и увидеть кнопки действий

То есть `check_pending` нельзя ставить раньше выдачи товара.

---

## 4. Логика для товара С ПОДДЕРЖКОЙ

## 4.1 Что видит покупатель

После выдачи товара покупатель получает:

- сам материал
- сообщение о том, что заказ доставлен
- нижний блок кнопок

Кнопки:

- `Write to Seller`
- `Open Dispute`
- `Item Works`

### 4.2 Что может делать покупатель

Покупатель может:

- написать селлеру по заказу
- отправить текст
- отправить фото
- отправить документы
- открыть репорт / dispute
- подтвердить, что товар рабочий

### 4.3 Что значит `Item Works`

Кнопка `Item Works` означает:

- покупатель проверил товар
- претензий по заказу нет
- заказ можно переводить в финальный подтверждённый статус

После этого:

- заказ становится `confirmed`
- чат становится read-only или закрывается для новых сообщений
- внизу появляется блок оценки селлера: `👍 Like` и `👎 Dislike`

### 4.4 Если покупатель сначала пишет селлеру

Если buyer не уверен, он сначала пишет селлеру.

Логика:

1. buyer пишет сообщение
2. seller получает push в `Seller Bot`
3. seller открывает `Mini App`
4. seller отвечает текстом или документом
5. buyer снова проверяет материал
6. buyer либо жмёт `Item Works`, либо открывает `Open Dispute`

### 4.5 Ограничения селлера в чате

| Роль | Фото | Документы | Текст |
|------|------|-----------|-------|
| Покупатель | ✅ | ✅ | ✅ |
| Селлер | ❌ | ✅ | ✅ |

Правила:

- seller не отправляет фото
- seller может отправлять только текст и документы
- buyer может отправлять текст, документы и фото-доказательства

---

## 5. Логика для товара БЕЗ ПОДДЕРЖКИ

## 5.1 Что видит покупатель

После выдачи товара buyer получает:

- материал
- сообщение: `У вас есть 15 минут на проверку товара`
- кнопки:
  - `Confirm`
  - `Return`

Чата с селлером здесь нет.

### 5.2 Логика окна проверки

Рекомендуемое окно:

- `15 минут` по умолчанию

Хранится в заказе:

```python
check_window_minutes: int = 15
check_started_at: Optional[datetime] = None
check_expires_at: Optional[datetime] = None
check_confirmed_at: Optional[datetime] = None
```

Flow:

1. заказ доставлен
2. backend ставит `check_pending`
3. записываются `check_started_at` и `check_expires_at`
4. buyer либо подтверждает товар, либо возвращает его

### 5.3 Возможные исходы

| Действие | Результат |
|----------|-----------|
| buyer нажал `Confirm` в течение окна | заказ -> `confirmed` |
| buyer ничего не сделал до дедлайна | заказ -> `auto_confirmed` |
| buyer нажал `Return` в течение окна | заказ -> `return_requested` или `moderation_review`, в зависимости от типа товара |

### 5.4 Правило авто-подтверждения

Если покупатель ничего не сделал до конца окна:

- система автоматически завершает проверку
- заказ переводится в `auto_confirmed`
- buyer получает сообщение, что окно проверки завершено
- после этого внизу заказа также показывается оценка `👍 Like / 👎 Dislike`

### 5.5 Когда возврат уже нельзя делать

Возврат нельзя делать если:

- истёк `check_expires_at`
- заказ уже `confirmed`
- заказ уже `auto_confirmed`
- заказ уже закрыт через dispute / refund

---

## 6. Репорт / dispute

### 6.1 Когда он нужен

`Open Dispute` нужен только для товаров с поддержкой или для специальных случаев, где админ должен вмешаться.

Он используется если:

- seller не отвечает
- seller прислал не тот материал
- товар явно не соответствует описанию
- нужен ручной разбор

### 6.2 Что делает dispute

После открытия dispute:

- заказ получает статус `disputed`
- seller получает уведомление
- support/moderation получает уведомление
- buyer больше не может финально подтвердить заказ до решения саппорта

### 6.3 Важное правило

`Dislike` не заменяет dispute.

То есть:

- `👎 Dislike` = оценка качества после завершения заказа
- `Open Dispute` = отдельный процесс жалобы / возврата / разбирательства

---

## 7. Финальная оценка товара и селлера

## 7.1 Где показывать оценку

После завершения проверки внизу заказа должен появляться отдельный нижний блок:

- `👍 Like`
- `👎 Dislike`

Показывать его только когда заказ уже финализирован:

- `confirmed`
- `auto_confirmed`

Не показывать если заказ:

- `returned`
- `refunded`
- `disputed` и ещё не решён

### 7.2 Что оценивает buyer

Эта оценка фиксирует общее впечатление от заказа:

- соответствовал ли товар описанию
- был ли seller полезен
- насколько быстро и нормально всё прошло

Это не только "товар рабочий / не рабочий", а общий финальный feedback по заказу.

### 7.3 Правила голосования

Простая логика:

- один заказ = одна оценка
- buyer может выбрать только `like` или `dislike`
- повторное голосование отключено
- если голос уже отправлен, кнопки становятся неактивны или заменяются текстом результата

Рекомендуемые поля:

```python
buyer_rating: Optional[str] = None      # like / dislike
buyer_rating_at: Optional[datetime] = None
buyer_rating_reason: Optional[str] = None
```

### 7.4 Нужно ли спрашивать причину

Базовая версия:

- `Like` -> сразу сохранить
- `Dislike` -> сразу сохранить, без лишней сложности

Расширенная версия позже:

- после `Dislike` спросить короткую причину:
  - `Wrong description`
  - `Bad material`
  - `Seller slow`
  - `No help`
  - `Other`

Сейчас лучше оставить без обязательной причины, чтобы flow был быстрым.

### 7.5 Что происходит после Like

Если buyer нажал `👍 Like`:

- в заказ пишется `buyer_rating=like`
- seller увеличивает счётчик положительных оценок
- seller получает push:
  - `Buyer rated order #123: 👍 Like`

### 7.6 Что происходит после Dislike

Если buyer нажал `👎 Dislike`:

- в заказ пишется `buyer_rating=dislike`
- seller увеличивает счётчик отрицательных оценок
- seller получает push:
  - `Buyer rated order #123: 👎 Dislike`

`Dislike` сам по себе:

- не делает refund
- не открывает dispute автоматически
- не откатывает already confirmed order

### 7.7 Что показывать buyer после оценки

После клика вместо активных кнопок можно показывать:

- `Your rating: 👍 Like`
- или `Your rating: 👎 Dislike`

---

## 8. Что должен видеть селлер

## 8.1 В Seller Bot

Селлер должен получать:

- новый заказ
- новое сообщение buyer
- открытие dispute
- подтверждение заказа
- авто-подтверждение заказа
- финальную оценку `Like / Dislike`

### 8.2 В статистике селлера

Рекомендуется добавить:

- `likes_count`
- `dislikes_count`
- `rating_score`

Формула для отображения:

```text
rating_score = likes_count / max(1, likes_count + dislikes_count) * 100
```

Можно показывать:

- `95% positive`
- `120 👍 / 6 👎`

### 8.3 Где отображать рейтинг

Рейтинг селлера можно показывать:

- в seller dashboard
- в admin panel
- в moderation / CRM
- опционально в buyer catalog позже

---

## 9. Изменения в БД

### 9.1 SellerBank

```python
has_chat: bool = True
```

### 9.2 SellerOrder

```python
check_window_minutes: int = 15
check_started_at: Optional[datetime] = None
check_expires_at: Optional[datetime] = None
check_confirmed_at: Optional[datetime] = None
buyer_rating: Optional[str] = None
buyer_rating_at: Optional[datetime] = None
buyer_rating_reason: Optional[str] = None
```

### 9.3 Seller

```python
likes_count: int = 0
dislikes_count: int = 0
```

### 9.4 Миграции

Нужно добавить:

- `has_chat` в `seller_banks`
- `check_window_minutes` в `seller_orders`
- `check_started_at` в `seller_orders`
- `check_expires_at` в `seller_orders`
- `check_confirmed_at` в `seller_orders`
- `buyer_rating` в `seller_orders`
- `buyer_rating_at` в `seller_orders`
- `buyer_rating_reason` в `seller_orders`
- `likes_count` в `sellers`
- `dislikes_count` в `sellers`

---

## 10. Кнопки в интерфейсе

## 10.1 Для заказа с поддержкой

После доставки:

- `Write to Seller`
- `Open Dispute`
- `Item Works`

После финального подтверждения:

- `👍 Like`
- `👎 Dislike`

## 10.2 Для заказа без поддержки

Во время окна проверки:

- `Confirm`
- `Return`

После `Confirm` или `auto_confirmed`:

- `👍 Like`
- `👎 Dislike`

---

## 11. Уведомления

Нужно отправлять следующие события:

### Buyer

- order delivered
- check window started
- check window expired
- order confirmed
- order auto-confirmed
- order returned
- dispute created
- rating saved

### Seller

- buyer wrote message
- dispute opened
- order confirmed
- order auto-confirmed
- buyer rated like
- buyer rated dislike

---

## 12. Mini App для селлера

Mini App нужен именно для заказов с поддержкой.

### 12.1 Что внутри

- список активных диалогов
- история сообщений
- поле ввода
- отправка документа
- быстрый переход по заказу
- работа owner и helpers в одном seller workspace

### 12.2 API

```text
GET  /api/seller/chat/conversations
GET  /api/seller/chat/messages?conv_id=&offset=
POST /api/seller/chat/send
```

Авторизация:

- Telegram WebApp `initData`
- поиск seller по `telegram_id`

Если вошёл helper:

- система ищет `SellerHelper`
- определяет его роль
- даёт доступ только к разрешённым чатам и действиям

### 12.3 Ограничения

- seller не может отправлять фото
- seller не может писать вне своего заказа
- seller не видит чужие диалоги

Ограничения по ролям:

- `upload_helper` не видит buyer chats
- `support_helper` видит только чаты и support-related order context
- `manager_helper` видит чаты и товары, но не вывод средств и не управление депозитом

### 12.4 Кнопки для helper в чате

`support_helper` и `manager_helper` в экране чата могут иметь:

- `Send Reply`
- `Send Document`
- `Open Order`
- `Escalate to Support`
- `Request Moderation`

Owner дополнительно может иметь:

- `Block Helper Access`
- `Reassign Chat`

### 12.5 Логика распределения чатов

Рекомендуемая простая модель:

- chat может быть `unassigned`
- owner может назначить chat на helper
- helper видит свои assigned chats
- manager может видеть все active chats

Это позволяет работать в двух режимах:

- один helper на всё -> owner назначает все chats и support-задачи одному `manager_helper`
- несколько helpers -> owner распределяет chats и задачи между разными helpers

Пример:

- helper A -> только загрузки, чаты не видит
- helper B -> только support chats
- helper C -> все active chats как `manager_helper`

Suggested fields:

```python
assigned_helper_id: Optional[int] = None
assigned_at: Optional[datetime] = None
assigned_by: Optional[int] = None
```

---

## 13. Анти-абуз правила

Чтобы система не ломалась:

- buyer не может поставить и `Like`, и `Dislike`
- buyer не может голосовать дважды
- seller не может сам влиять на оценку
- auto-confirm не должен запускаться для заказов `has_chat=True`
- `Return` не должен работать после истечения окна
- `Dislike` не должен автоматически создавать refund

---

## 14. Специальные правила по типам товара

## 14.0 Финальная матрица проверки через support / moderation

| Тип товара | Что получает buyer | Как проверяет | Кнопки buyer | Когда идёт в support/moderation | Refund logic | Финальная оценка |
|-----------|--------------------|---------------|--------------|----------------------------------|--------------|------------------|
| `Bank / Log / Selfreg / Enrol` | материал + статус доступа к номеру + срок аренды или флаг замены номера | проверяет доступ, качество материала, условия аренды, ответы seller | `Write to Seller`, `Open Dispute`, `Item Works` | если seller не решил вопрос, если доступ/номер/условия не совпадают с описанием | не instant refund, спор через `support/moderation` | после `confirmed` -> `👍 Like / 👎 Dislike` |
| `CC` | данные карты / ZIP / Fullz по подтипу | buyer проверяет соответствие заявленным данным | `Confirm`, `Return` | при любом `Return` buyer обязан выбрать причину, затем заказ идёт в `moderation_review` | refund только после решения модерации | после `confirmed` или решения кейса -> `👍 Like / 👎 Dislike` |
| `Brute` | credentials / bank / range / account_type / balance info | быстрый check валидности и соответствия описанию | `Confirm`, `Return` | если причина спорная или недостаточно proof, кейс идёт в `moderation_review` | быстрый return возможен только в рамках check-window и правил; спорные кейсы через moderation | после `confirmed` / `auto_confirmed` -> `👍 Like / 👎 Dislike` |
| `Roots / root-like` | root/access credentials + обещанный уровень доступа | buyer проверяет, есть ли обещанный доступ и соответствует ли он описанию | `Confirm`, `Return` | любые спорные кейсы лучше вести через `support/moderation`, потому что товар чувствительный | не instant refund по спорным кейсам | после финального закрытия -> `👍 Like / 👎 Dislike` |

### Главное правило этой матрицы

- `support` и `moderation` должны быть центральной точкой для спорных ситуаций
- seller сначала пытается решить проблему сам
- если решение не найдено, кейс переходит в `support/moderation`
- buyer не должен получать бесконтрольный instant refund по спорным товарам

## 14.1 Bank

Для `Bank`, `Log`, `Selfreg`, `Enrol` нужно хранить отдельную логику доступа к номеру.

Рекомендуемые поля:

```python
number_access_available: bool = False
rental_days: Optional[int] = None
adaptive_report_enabled: bool = False
number_change_allowed: bool = False
```

Правило:

- если `number_access_available=True`, seller обязан указать `rental_days`
- если `number_access_available=True`, seller обязан указать логику `adaptive report`
- если `number_access_available=False`, seller обязан указать, можно ли менять номер

### Логика проверки Bank

Покупатель после доставки должен видеть:

- есть ли доступ к номеру
- срок аренды доступа, если он есть
- можно ли менять номер, если доступа нет
- есть ли поддержка seller

Если доступ к номеру есть:

- buyer проверяет, что доступ реально получен
- buyer видит `Rental active for N days`
- seller/worker отправляет adaptive report по сроку аренды

Рекомендуемый adaptive report:

- `1-3 дня` -> стартовый отчёт + финальный отчёт
- `4-7 дней` -> стартовый отчёт + короткий daily status + финальный отчёт
- `8+ дней` -> стартовый отчёт + ежедневный статус + важные алерты по смене состояния + финальный отчёт

Если доступа к номеру нет:

- buyer проверяет основной материал
- отдельно видит флаг `Number change allowed: yes/no`
- если `yes`, buyer может запросить замену номера только в рамках описания и только до финального подтверждения
- если `no`, замена номера не допускается и спор идёт только через dispute/moderation

### Возврат / dispute для Bank

Для `Bank` не должно быть логики "мгновенный refund одной кнопкой".

Правильный flow:

1. buyer получает материал
2. buyer проверяет доступ / состояние
3. если есть вопрос -> пишет seller
4. если проблема не решена -> открывает `Open Dispute`
5. решение делает moderation/support

## 14.2 CC

Для `CC` нужно защититься от сценария:

- buyer купил карту
- сразу нажал отмену
- попытался получить быстрый refund без нормальной проверки

### Правильная логика возврата CC

При нажатии `Return` buyer не получает мгновенный refund.

Вместо этого:

1. buyer обязан выбрать причину
2. при необходимости добавляется текст или proof
3. заказ получает `moderation_review`
4. seller и moderation получают уведомление
5. только после решения модерации заказ переходит в:
   - `refunded`
   - `confirmed`
   - `changes_requested` / ожидание доп. данных

Обязательные причины возврата для CC:

- `Card dead`
- `Wrong card data`
- `Invalid ZIP`
- `Invalid Fullz`
- `Duplicate / used`
- `Description mismatch`
- `Other`

Дополнительные правила для CC:

- buyer не может отменить без причины
- buyer не может открыть несколько возвратов по одному заказу
- seller может дать пояснение в ответ
- moderation видит причину, тайминг покупки, переписку и приложенные proof

## 14.3 Brute и root-like товары

Для `Brute` и похожих `root/root-like` товаров проверка должна быть короткой и жёстко ограниченной по времени.

Базовая модель:

- чат обычно отключён
- есть фиксированное окно проверки
- buyer получает материал
- buyer должен быстро подтвердить или запросить возврат/модерацию в рамках окна

Рекомендуемая логика проверки:

1. выдать материал
2. показать таймер проверки
3. buyer проверяет валидность credentials / access
4. если всё ок -> `Confirm`
5. если не ок -> `Return` с причиной или `moderation_review`, если товар относится к чувствительной категории

Что проверяет buyer:

- credentials вообще рабочие или нет
- соответствует ли банк / тип / range описанию
- соответствует ли `account_type`
- соответствует ли `balance_range`, если он заявлен
- для root-like товаров: есть ли обещанный уровень доступа

Если под `рутами` ты имеешь в виду отдельную категорию `Roots`, лучше использовать ту же базовую модель, что и у `Brute`:

- без свободного долгого чата
- короткое окно проверки
- чёткие причины возврата
- спорные кейсы через moderation

## 14.4 Переписка с воркером

Нужно разделять seller-chat и worker-communication.

### Сценарий A. In-stock seller item

- buyer общается только с seller
- worker не участвует

### Сценарий B. Order/custom/manual task через worker

- buyer не видит worker напрямую
- worker получает внутреннюю задачу
- если нужны уточнения, worker пишет во внутренний интерфейс
- support/seller пересылает вопрос buyer
- ответ buyer возвращается worker через внутренний канал

### Сценарий C. Спорный случай

- buyer открывает dispute
- worker может приложить внутренний комментарий или proof
- buyer всё равно не получает прямой контакт worker
- финальное решение остаётся за moderation/support

Главное правило:

- прямую переписку `buyer <-> worker` лучше не открывать
- наружу должен смотреть только seller/support слой

## 14.4A Переписка buyer -> seller -> support/moderation

Это должен быть основной внешний flow.

### Сценарий 1. Обычный вопрос по товару

1. buyer пишет seller
2. seller отвечает в чате или через `Mini App`
3. если вопрос решён -> buyer жмёт `Item Works` или `Confirm`

### Сценарий 2. Seller не отвечает или тянет

1. buyer пишет seller
2. ответа нет в разумный срок
3. buyer жмёт `Open Dispute`
4. кейс уходит в `support/moderation`

### Сценарий 3. Seller отвечает, но проблема не решена

1. buyer пишет seller
2. seller пытается помочь
3. buyer прикладывает proof
4. если всё ещё проблема -> `support/moderation`

### Сценарий 4. Custom/manual order с worker внутри

1. buyer пишет seller/support
2. seller/support передаёт вопрос worker
3. worker отвечает внутренне
4. seller/support возвращает ответ buyer

### Почему так правильно

- buyer не видит worker-контакт
- seller не уводит buyer вне системы
- support/moderation видит всю историю спора
- проще принимать решения по refund / reject / confirm

## 14.5 Автоудаление / автовыгрузка товаров

Seller может сам задать срок жизни товара.

Рекомендуемые поля:

```python
auto_unpublish_enabled: bool = False
listing_duration_days: Optional[int] = None
auto_unpublish_at: Optional[datetime] = None
```

Логика:

- seller указывает количество дней
- после этого backend считает `auto_unpublish_at`
- по достижении времени товар снимается с активной выдачи
- новые заказы создать уже нельзя
- старые заказы и история товара сохраняются
- seller может заново активировать товар через повторную модерацию

## 14.6 Правила до депозита и загрузки

Перед внесением депозита seller должен согласиться с правилами качества.

Жёсткие запреты:

- нельзя оставлять в файлах свой никнейм
- нельзя оставлять Telegram/contact данные
- нельзя оставлять watermark / подпись / hidden mark
- нельзя пытаться увести buyer во внешний контакт

Санкции:

- предупреждение
- заморозка товара
- блокировка seller

Правило без двусмысленности:

- свой никнейм в файлах = `BAN / warning`

---

## 15. Кнопки seller-а в чате и в работе с заказом

## 15.1 Кнопки в push-уведомлении seller-а

Когда buyer пишет по заказу, seller в `Seller Bot` должен получать:

- `Open Chat`
- `Open Order`
- `Open Mini App`

Если открыт dispute:

- `Open Dispute`
- `Open Order`

Если buyer поставил rating:

- `Open Order`

## 15.2 Кнопки внутри списка чатов seller-а

В списке диалогов seller должен видеть:

- `Open Chat`
- `Open Order`
- `Mark Read`

Опционально:

- `Pin`
- `Mute`

## 15.3 Кнопки внутри экрана чата seller-а

Основные:

- `Send Reply`
- `Send Document`
- `Open Order`
- `Open Buyer Profile` или `Buyer Info`
- `Escalate to Support`

Быстрые ответы:

- `Got it`
- `Soon`
- `Info`
- `Done`

Если seller не может решить вопрос:

- `Escalate to Support`
- `Request Moderation`

### Что значит каждая кнопка

- `Open Chat` -> открыть текущий диалог
- `Open Order` -> перейти в карточку заказа
- `Open Mini App` -> открыть web chat / расширенный экран работы
- `Mark Read` -> убрать unread
- `Send Reply` -> отправить текст
- `Send Document` -> отправить документ
- `Escalate to Support` -> передать кейс в саппорт
- `Request Moderation` -> передать спор на модерацию

## 15.4 Чего seller не должен иметь в кнопках

- прямой кнопки на instant refund
- прямого раскрытия контакта worker
- возможности удалить историю спора
- возможности закрыть dispute без support/moderation

---

## 16. Рекомендуемый порядок реализации

### Этап 1

- добавить `has_chat`
- добавить поля окна проверки
- добавить кнопки `Confirm / Return`

### Этап 2

- добавить post-delivery flow для товаров с чатом
- добавить `Write to Seller / Open Dispute / Item Works`
- подключить seller mini app

### Этап 3

- добавить `buyer_rating`
- добавить кнопки `👍 Like / 👎 Dislike`
- сохранить rating в заказ и в статистику seller

### Этап 4

- добавить push-уведомления seller о rating
- вывести рейтинг в seller dashboard и admin panel

---

## 17. Итоговое правило

Финальная логика должна быть очень простой для покупателя:

1. Получил товар
2. Если товар с поддержкой -> пиши селлеру или жми `Item Works`
3. Если товар без поддержки -> за `15 минут` жми `Confirm` или `Return`
4. После успешного завершения -> оцени seller через `👍 Like` или `👎 Dislike`

Именно такой flow будет понятным, коротким и не конфликтующим с текущей структурой `Mirror Bot + Seller Bot + Mini App`.
