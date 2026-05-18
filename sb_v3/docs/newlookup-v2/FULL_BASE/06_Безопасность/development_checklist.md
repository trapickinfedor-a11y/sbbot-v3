# Newlookup — Мастер-чеклист разработки

## Фаза 1: Ядро и База Данных

- [ ] **1.1. Конфигурация:** Создать `app/core/config.py` с Pydantic-моделью.
- [ ] **1.2. Модели (User):** Создать `app/db/models/user_related.py` с моделями `users`, `sellers`, `marketers`, `staff`, `workers`.
- [ ] **1.3. Модели (Product):** Создать `app/db/models/product_related.py` с моделями `products`, `categories`, `orders`.
- [ ] **1.4. Модели (System):** Создать `app/db/models/system_related.py` с остальными моделями.
- [ ] **1.5. Подключение к БД:** Написать `app/core/db.py` с `create_async_engine` и `async_sessionmaker`.

## Фаза 2: Клиентский бот (Mirror Bot)

- [ ] **2.1. Регистрация:** Реализовать хендлер `/start` в `app/bots/mirror_bot/handlers.py`.
- [ ] **2.2. Главное меню:** Реализовать клавиатуру главного меню в `app/bots/mirror_bot/keyboards.py`.
- [ ] **2.3. Профиль:** Реализовать экран профиля и его кнопки.
- [ ] **2.4. Пополнение баланса:** Реализовать флоу пополнения через BTC/USDT/XMR.
- [ ] **2.5. Покупка товара:** Реализовать флоу покупки товара In Stocks.

---

... и так далее для всех 50+ задач ...
