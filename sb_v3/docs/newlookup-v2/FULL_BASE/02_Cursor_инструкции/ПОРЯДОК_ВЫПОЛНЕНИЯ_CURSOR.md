# Порядок выполнения в Cursor — newlookup v2 → v24

> Следуй строго по порядку. Не переходи к следующему шагу пока не завершил текущий.

---

## Подготовка (делается один раз)

### Шаг 0 — Открыть проект в Cursor

1. Скачай `CURSOR_COMPLETE_GUIDE_v4_FINAL.zip` и распакуй в отдельную папку, например `newlookup-docs/`
2. Открой Cursor
3. `File` → `Open Folder` → выбери папку с твоим проектом `newlookup_v2_work/`
4. Дополнительно открой папку `newlookup-docs/` как второй workspace (или просто держи рядом)

### Шаг 0.1 — Настрой контекст в Cursor

В Cursor нажми `Cmd+Shift+P` (Mac) или `Ctrl+Shift+P` (Windows) → `Cursor Settings` → `Rules for AI` и вставь:

```
Ты работаешь над проектом newlookup — мультибот-маркетплейс на aiogram 3.x + SQLAlchemy async + PostgreSQL.
Всегда читай @shared/database/models.py перед любыми изменениями.
Покупатель АНОНИМЕН — seller и worker никогда не видят buyer_user_id, username, telegram_id.
Все финансовые операции атомарны (используй async with session.begin()).
SELECT FOR UPDATE обязателен при покупке товара.
```

---

## Этап 1 — База данных (делать первым, всё зависит от этого)

### Шаг 1.1 — Добавить колонки в models.py

**Открой в Cursor:** `shared/database/models.py`

**Промт в Cursor Chat:**
```
@shared/database/models.py @models_v24_additions.py

В файле models.py добавь следующие изменения:

1. В класс Product добавь колонки:
   - is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
   - moderation_status: Mapped[str] = mapped_column(String(30), default="pending_moderation", nullable=False)
   - moderation_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
   - moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
   - moderated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

2. В класс SellerOrder добавь колонки:
   - escrow_released: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
   - escrow_released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
   - auto_complete_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
   - marketer_commission_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

3. В класс Worker добавь колонки:
   - violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
   - last_violation_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
   - is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

4. Создай новую таблицу WorkerViolation:
   - id: int PK
   - worker_id: BigInteger FK → workers.user_id
   - order_id: int FK → seller_orders.id
   - violation_type: String(50) — "contact_info", "link", "phone", "email"
   - original_text: Text
   - detected_at: DateTime(timezone=True)

5. Создай новую таблицу SystemSetting:
   - key: String(100) PK
   - value: String(500)
   - description: String(500)
   - updated_at: DateTime(timezone=True)

Не удаляй существующие колонки. Добавляй только новые.
```

---

### Шаг 1.2 — Создать и применить миграцию Alembic

**В терминале Cursor (`Ctrl+`` `):**

```bash
# Убедись что находишься в папке проекта
cd newlookup_v2_work

# Скопируй готовую миграцию из архива
cp ../newlookup-docs/v24_001_additions.py alembic/versions/v24_001_additions.py

# Применить миграцию
docker-compose exec api alembic upgrade head
```

**Если нет docker-compose exec:**
```bash
alembic upgrade head
```

**Проверка:**
```bash
docker-compose exec db psql -U postgres -d newlookup -c "\d products"
# Должны появиться колонки: is_active, moderation_status, moderation_comment
```

---

## Этап 2 — Безопасность (критично — делать вторым)

### Шаг 2.1 — Заменить chat_filter.py

**В терминале:**
```bash
cp ../newlookup-docs/chat_filter_v24.py shared/utils/chat_filter.py
```

**Промт в Cursor Chat для проверки:**
```
@shared/utils/chat_filter.py

Проверь что функция filter_message:
1. Фильтрует: @username, t.me/ссылки, номера телефонов (+7, 8, международные), email-адреса, Discord теги
2. Принимает параметры: text: str, worker_id: int, order_id: int, session: AsyncSession
3. Возвращает: tuple[str, bool] — (очищенный текст, было_ли_нарушение)
4. При нарушении создаёт запись WorkerViolation в БД
5. Увеличивает worker.violation_count

Если чего-то не хватает — добавь.
```

### Шаг 2.2 — Убрать buyer_user_id из seller_bot

**Открой в Cursor:** `seller_bot/handlers/orders.py`

**Промт:**
```
@seller_bot/handlers/orders.py

Найди все места где отображается buyer_user_id, buyer username, telegram_id покупателя.
Удали эти строки полностью.

Продавец должен видеть ТОЛЬКО:
- Номер заказа (order.id)
- Название товара
- Банк оплаты
- Сумму
- Статус
- Дату создания
- Комментарий покупателя (если есть)

НЕ показывать: buyer_user_id, username, telegram_id, любые идентификаторы покупателя.

Замени файл используя готовый код из @orders_v24.py как образец.
```

---

## Этап 3 — Логика покупки (критично — race condition)

### Шаг 3.1 — Добавить SELECT FOR UPDATE в product_service.py

**Открой в Cursor:** `mirror_bot/services/product_service.py`

**Промт:**
```
@mirror_bot/services/product_service.py @product_service_v24.py

В методе purchase_product добавь:

1. SELECT FOR UPDATE при получении товара:
   result = await session.execute(
       select(Product)
       .where(Product.id == product_id)
       .with_for_update()
   )
   product = result.scalar_one_or_none()

2. Проверку is_active перед покупкой:
   if not product or not product.is_active:
       raise ValueError("Товар недоступен")

3. Проверку moderation_status:
   if product.moderation_status != "approved":
       raise ValueError("Товар на модерации")

4. Установку auto_complete_at при создании заказа:
   order.auto_complete_at = datetime.utcnow() + timedelta(hours=24)

Используй @product_service_v24.py как образец полного кода.
```

---

## Этап 4 — Автозавершение заказов (Celery)

### Шаг 4.1 — Создать файл задач

**В терминале:**
```bash
cp ../newlookup-docs/auto_complete.py shared/tasks/auto_complete.py
```

**Промт в Cursor Chat:**
```
@shared/tasks/auto_complete.py

Проверь что в файле есть:

1. Задача auto_complete_orders — находит заказы где:
   - status = "completed" (воркер сдал работу)
   - auto_complete_at <= datetime.utcnow()
   - escrow_released = False
   Для каждого: меняет статус на "auto_completed", вызывает release_escrow

2. Задача release_escrow — идемпотентная:
   - Проверяет order.escrow_released == False перед выплатой
   - Устанавливает order.escrow_released = True ПЕРЕД созданием транзакции
   - Создаёт Transaction для продавца
   - Если marketer_id есть и marketer_commission_paid == False — создаёт Transaction для маркетолога
   - Устанавливает marketer_commission_paid = True

3. Beat расписание: auto_complete_orders каждые 5 минут

Если чего-то нет — добавь.
```

### Шаг 4.2 — Добавить Celery в docker-compose.yml

**Открой в Cursor:** `docker-compose.yml`

**Промт:**
```
@docker-compose.yml

Добавь сервис celery_worker после сервиса api:

  celery_worker:
    build: .
    command: celery -A shared.tasks.celery_app worker --loglevel=info -Q default
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    volumes:
      - .:/app

  celery_beat:
    build: .
    command: celery -A shared.tasks.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    volumes:
      - .:/app

Также добавь сервис redis если его нет:

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
```

---

## Этап 5 — Модерация товаров

### Шаг 5.1 — Добавить эндпоинты модерации в web_panel

**Открой в Cursor:** `web_panel/api/products.py`

**Промт:**
```
@web_panel/api/products.py @shared/database/models.py

Добавь эндпоинты для модерации товаров:

1. GET /api/products/pending — список товаров со статусом pending_moderation
   Возвращает: id, title, description, price, seller_id, created_at

2. POST /api/products/{product_id}/approve — одобрить товар
   Устанавливает: moderation_status="approved", moderated_by=admin_id, moderated_at=now()

3. POST /api/products/{product_id}/reject — отклонить товар
   Тело запроса: {"comment": "причина отклонения"}
   Устанавливает: moderation_status="rejected", moderation_comment=comment

4. Только авторизованный admin может вызывать эти эндпоинты (проверяй JWT токен)
```

### Шаг 5.2 — Добавить уведомление продавцу о результате модерации

**Открой в Cursor:** `seller_bot/handlers/products.py`

**Промт:**
```
@seller_bot/handlers/products.py @shared/database/models.py

При создании нового товара:
1. Установи product.moderation_status = "pending_moderation"
2. Установи product.is_active = False
3. Отправь продавцу сообщение: "✅ Товар отправлен на модерацию. Обычно проверка занимает до 2 часов."

Добавь хендлер для уведомления продавца когда товар одобрен/отклонён.
Уведомление отправляется через seller_bot когда admin меняет moderation_status через web_panel.
```

---

## Этап 6 — Нарушения воркеров

### Шаг 6.1 — Добавить эндпоинты нарушений в web_panel

**Открой в Cursor:** `web_panel/api/workers.py`

**Промт:**
```
@web_panel/api/workers.py @shared/database/models.py

Добавь эндпоинты:

1. GET /api/workers/{worker_id}/violations — список нарушений воркера
   Возвращает: id, order_id, violation_type, original_text, detected_at

2. GET /api/workers/suspended — список приостановленных воркеров
   Возвращает: user_id, username, violation_count, last_violation_at, is_suspended

3. POST /api/workers/{worker_id}/unsuspend — снять приостановку
   Устанавливает: is_suspended=False, violation_count=0

4. Добавь автоматическую приостановку в chat_filter_v24.py:
   если worker.violation_count >= 3 за последние 30 дней — установи is_suspended=True
```

---

## Этап 7 — Динамические константы

### Шаг 7.1 — Заполнить таблицу system_settings

**В терминале:**
```bash
docker-compose exec db psql -U postgres -d newlookup -c "
INSERT INTO system_settings (key, value, description, updated_at) VALUES
('PLATFORM_FEE', '0.15', 'Комиссия платформы (15%)', NOW()),
('MARKETER_FEE', '0.05', 'Комиссия маркетолога (5%)', NOW()),
('DISPUTE_WINDOW_HOURS', '24', 'Часов на открытие спора после покупки', NOW()),
('AUTO_COMPLETE_HOURS', '24', 'Часов до автозавершения заказа', NOW()),
('MIN_WITHDRAWAL', '100', 'Минимальная сумма вывода', NOW()),
('MAX_WITHDRAWAL_DAY', '50000', 'Максимальная сумма вывода в день', NOW())
ON CONFLICT (key) DO NOTHING;
"
```

### Шаг 7.2 — Использовать константы из БД

**Промт в Cursor Chat:**
```
@shared/database/models.py @shared/utils/

Создай файл shared/utils/settings.py со следующим кодом:

from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.database.models import SystemSetting

async def get_setting(key: str, session: AsyncSession, default=None):
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else default

async def get_platform_fee(session: AsyncSession) -> float:
    val = await get_setting("PLATFORM_FEE", session, "0.15")
    return float(val)

async def get_marketer_fee(session: AsyncSession) -> float:
    val = await get_setting("MARKETER_FEE", session, "0.05")
    return float(val)

async def get_dispute_window(session: AsyncSession) -> int:
    val = await get_setting("DISPUTE_WINDOW_HOURS", session, "24")
    return int(val)

Затем замени все хардкоженные 0.15, 0.10, 24 в product_service.py и auto_complete.py
на вызовы этих функций.
```

---

## Этап 8 — Проверка и тестирование

### Шаг 8.1 — Перезапустить все сервисы

```bash
docker-compose down
docker-compose up -d --build
docker-compose logs -f --tail=50
```

### Шаг 8.2 — Проверить миграцию

```bash
docker-compose exec db psql -U postgres -d newlookup -c "
SELECT column_name FROM information_schema.columns
WHERE table_name = 'products'
ORDER BY ordinal_position;
"
# Должны быть: is_active, moderation_status, moderation_comment, moderated_at, moderated_by
```

### Шаг 8.3 — Проверить анонимность покупателя

**Промт в Cursor Chat:**
```
@seller_bot/handlers/orders.py

Найди ВСЕ места где может быть показан buyer_user_id или любой идентификатор покупателя.
Выведи список строк с контекстом. Если найдёшь — удали.
```

### Шаг 8.4 — Проверить идемпотентность эскроу

**Промт:**
```
@shared/tasks/auto_complete.py

Проверь что функция release_escrow:
1. Перед выплатой делает: if order.escrow_released: return (ранний выход)
2. Устанавливает escrow_released = True ВНУТРИ транзакции ПЕРЕД созданием Transaction
3. Использует SELECT FOR UPDATE при получении order
4. Вся логика обёрнута в async with session.begin()

Если что-то не так — исправь.
```

---

## Этап 9 — Финальный чеклист перед деплоем

Выполни каждый пункт и поставь галочку:

```
[ ] 1. alembic upgrade head — миграция применена
[ ] 2. system_settings заполнены (6 записей)
[ ] 3. buyer_user_id не отображается у продавца
[ ] 4. chat_filter фильтрует: @, t.me, телефон, email, Discord
[ ] 5. SELECT FOR UPDATE в purchase_product
[ ] 6. escrow_released проверяется перед выплатой
[ ] 7. Celery worker запущен (docker-compose ps)
[ ] 8. Celery beat запущен (docker-compose ps)
[ ] 9. Redis запущен (docker-compose ps)
[ ] 10. Новые товары создаются со статусом pending_moderation
[ ] 11. Товары с pending_moderation не видны покупателям
[ ] 12. auto_complete_at устанавливается при создании заказа
[ ] 13. Все боты отвечают на /start
[ ] 14. Логи без ошибок (docker-compose logs)
```

---

## Порядок промтов в Cursor — краткая шпаргалка

| Этап | Файл | Действие |
|---|---|---|
| 1 | `shared/database/models.py` | Добавить колонки |
| 2 | `alembic/versions/` | Скопировать и применить миграцию |
| 3 | `shared/utils/chat_filter.py` | Заменить файл |
| 4 | `seller_bot/handlers/orders.py` | Убрать buyer_user_id |
| 5 | `mirror_bot/services/product_service.py` | SELECT FOR UPDATE |
| 6 | `shared/tasks/auto_complete.py` | Создать новый файл |
| 7 | `docker-compose.yml` | Добавить Celery + Redis |
| 8 | `web_panel/api/products.py` | Эндпоинты модерации |
| 9 | `seller_bot/handlers/products.py` | Уведомление о модерации |
| 10 | `web_panel/api/workers.py` | Эндпоинты нарушений |
| 11 | `shared/utils/settings.py` | Создать файл констант |
| 12 | Все файлы | Финальная проверка |

---

## Правила при работе с Cursor

**Всегда добавляй в контекст:**
- `@shared/database/models.py` — при любых изменениях данных
- `@newlookup_srs_v24_FINAL.md` — при вопросах о логике
- `@CURSOR_COMPLETE_GUIDE_v4.md` — при вопросах о структуре

**Никогда не делай:**
- Не генерируй весь проект одним промтом
- Не меняй models.py без последующей миграции
- Не удаляй существующие колонки из models.py
- Не показывай buyer_user_id продавцу или воркеру

**Шаблон промта для любого файла:**
```
@[файл который меняешь] @shared/database/models.py

[Что нужно сделать — конкретно и по пунктам]

Требования:
- Покупатель анонимен (не показывать buyer_user_id)
- Финансовые операции атомарны (async with session.begin())
- Не удалять существующий код, только добавлять
```
