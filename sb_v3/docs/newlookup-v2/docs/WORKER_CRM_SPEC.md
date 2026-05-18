# Worker CRM — спецификация

## 1. Оплата воркеров

### Логика выбора цены (приоритет)
1. **fixed_price** — если задана в админке для воркера, используется фиксированная сумма за заказ
2. **commission_percent** — если задан %, воркер получает `(order_income * commission_percent / 100)`
3. **По умолчанию** — 100% от дохода заказа (Order.price с учётом bulk/NF)

### Где настраивать
- **Админка** → Воркеры → редактирование воркера
- Поля: `fixed_price` (число), `commission_percent` (число 0–100)

### Начисление
- При завершении заказа (`OrderService.complete_order`) вызывается `credit_worker_on_order_complete`
- Сумма зачисляется на `Worker.balance` и `Worker.total_earned`

---

## 2. Вывод средств (как у селлеров/маркетологов)

### Support Bot
- Кнопка **💸 Withdraw** в главном меню (если balance > 0)
- Шаги: сумма → реквизиты → заявка создаётся в `worker_withdrawals` (main DB)

### Worker CRM (админка)
- **URL:** `/worker-crm` → вкладка «Выводы»
- Список pending заявок
- Кнопки: Одобрить / Отклонить
- При одобрении: выполняется ledger reservation/finalize flow, а `worker.balance` и `worker.total_withdrawn` обновляются как projection

---

## 3. Отчёты о расходах

### Support Bot
- **Profile** → «Submit Expense Report»
- Шаги: сумма → категория (subscription/tools/other) → описание
- Сохраняется в `worker_expense_reports`

### Worker CRM
- Вкладка «Отчёты о расходах»
- Список с фильтром по статусу
- Одобрить / Отклонить (для учёта расходов на воркеров)

---

## 4. HR-метрики

### Обязательные метрики
| Метрика | Описание |
|---------|----------|
| **Время выполнения заказа** | `completed_at - taken_at` (минуты) |
| **Среднее время** | Среднее по всем заказам за период |
| **Мин/Макс время** | Минимальное и максимальное время |
| **Заказов на воркера** | Количество выполненных заказов |
| **Доход на воркера** | Сумма Order.price по выполненным заказам |
| **Количество воркеров** | Уникальных воркеров за период |

### API
- `GET /api/worker-crm/hr-metrics?period_days=30`
- Возвращает: `summary` (общие метрики), `by_worker` (разбивка по воркерам)

### Дополнительно (можно расширить)
- Время до первого ответа (taken_at - created_at)
- Success rate (DONE vs NF)
- Заказов в день по воркеру

---

## 5. Структура данных

### Worker (доп. поля)
- `fixed_price` — фикс. сумма за заказ (nullable)
- `commission_percent` — % от Order.price (nullable)
- `total_earned` — всего заработано
- `total_withdrawn` — всего выведено

### WorkerWithdrawal (main DB)
- Основной payout flow воркеров
- Support Bot и Worker CRM работают через main DB withdrawal records

### tasks DB
- Не используется как источник worker payout records
- Оставлен только для reminder/background задач

### WorkerExpenseReport
- worker_id, amount, category, description, status, receipt_file_id
