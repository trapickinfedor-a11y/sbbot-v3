# Синхронизация Seller CRM с NocoDB

Заказы Seller CRM (bank + cc) можно синхронизировать в NocoDB для работы в no-code интерфейсе.

## Настройка

### 1. Переменные окружения (.env)

```env
NOCODB_BASE_URL=https://your-nocodb-instance.com
NOCODB_API_TOKEN=your_api_token
NOCODB_TABLE_ID=mtxxxxxxxxxxxxxxxx
```

- **NOCODB_BASE_URL** — URL инстанса NocoDB (без слэша в конце)
- **NOCODB_API_TOKEN** — API токен (xc-token). Создаётся в NocoDB: Project Settings → Tokens
- **NOCODB_TABLE_ID** — ID таблицы. Виден в URL при открытии таблицы: `.../nc/xxx/p/yyy/m/` — часть после `m/` это table_id

### 2. Таблица в NocoDB

Создайте таблицу с колонками (названия можно настроить через маппинг в коде):

| Колонка NocoDB | Тип   | Описание                    |
|----------------|-------|-----------------------------|
| InternalId     | Text  | bank_123 / cc_456           |
| OrderType      | Text  | bank / cc                   |
| OrderId        | Number| ID заказа                   |
| SellerId       | Number| ID продавца                 |
| SellerName     | Text  | Имя продавца                |
| ItemName       | Text  | Название товара             |
| BuyerUserId    | Number| Telegram ID покупателя      |
| Status         | Text  | pending_admin, approved, in_progress, completed |
| PriceForBuyer  | Number| Цена для покупателя         |
| PriceForSeller | Number| Цена для продавца           |
| Quantity       | Number| Количество                 |
| CreatedAt      | DateTime | Дата создания            |
| AdminApprovedAt| DateTime | Одобрено админом         |
| TakenAt        | DateTime | Взято в работу           |
| CompletedAt    | DateTime | Завершено                |

### 3. Синхронизация

- **Ручная**: кнопка «📤 NocoDB Sync» на странице Seller CRM
- Логика: новые заказы создаются в NocoDB, уже синхронизированные — обновляются (по InternalId)
- Состояние синхронизации хранится в `data/nocodb_sync_state.json`

## API

- `GET /api/seller-crm/nocodb/status` — проверка настройки
- `POST /api/seller-crm/nocodb/sync` — запуск синхронизации
- `POST /api/seller-crm/nocodb/test` — проверка подключения
