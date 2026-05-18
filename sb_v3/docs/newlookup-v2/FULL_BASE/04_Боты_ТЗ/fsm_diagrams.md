# Newlookup - Диаграммы конечных автоматов (FSM)

**Версия:** 1.0
**Дата:** 12.03.2026

> Этот документ содержит визуальные диаграммы конечных автоматов (FSM) для ключевых многошаговых процессов в ботах системы Newlookup. Диаграммы представлены в формате Mermaid.js и наглядно демонстрируют логику переходов между состояниями.

---

## 1. Seller Bot: FSM добавления товара (Selfreg BA)

**Описание:** Этот 14-шаговый процесс является самым сложным FSM в системе. Он собирает все необходимые атрибуты для создания продукта категории "Selfreg Bank Account".

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Start

    state Start {
        direction LR
        [*] --> bank_name: Ввод названия банка
    }

    state bank_name {
        direction LR
        [*] --> account_type: Выбор типа счета
    }

    state account_type {
        direction LR
        [*] --> balance: Ввод баланса
    }

    state balance {
        direction LR
        [*] --> has_online_access: Есть онлайн-доступ?
    }

    state has_online_access {
        direction LR
        [*] --> has_phone_access: Есть доступ к телефону?
    }

    state has_phone_access {
        direction LR
        [*] --> has_email_access: Есть доступ к email?
    }

    state has_email_access {
        direction LR
        [*] --> state_prov: Ввод штата
    }

    state state_prov {
        direction LR
        [*] --> registration_date: Ввод даты регистрации
    }

    state registration_date {
        direction LR
        [*] --> auto_delete_days: Ввод дней автоудаления
    }

    state auto_delete_days {
        direction LR
        [*] --> price: Ввод цены
    }

    state price {
        direction LR
        [*] --> file_upload: Загрузка файла
    }

    state file_upload {
        direction LR
        [*] --> confirm: Финальное подтверждение
    }

    state confirm {
        direction LR
        [*] --> End: Публикация
    }

    state End
```

---

## 2. Mirror Bot: FSM заказа услуги (Credit Score)

**Описание:** Процесс заказа услуги, которая выполняется "под заказ" (Per Order). Включает в себя ввод данных, оплату и ожидание выполнения.

```mermaid
stateDiagram-v2
    [*] --> EnterData: Пользователь нажимает "Order"

    state EnterData {
        description "Ввод данных для проверки (SSN, Name, etc.)"
        [*] --> ConfirmOrder: Данные введены
    }

    state ConfirmOrder {
        description "Показать детали заказа и цену"
        [*] --> Payment: Пользователь нажимает "Confirm & Pay"
        ConfirmOrder --> [*]: Отмена
    }

    state Payment {
        description "Списание средств с баланса"
        [*] --> CreateTask: Успешное списание
        Payment --> InsufficientFunds: Недостаточно средств
    }

    state InsufficientFunds {
        description "Сообщение о нехватке средств"
        [*] --> [*]: Пользователь выходит или пополняет баланс
    }

    state CreateTask {
        description "Создание заказа и задачи в automation_tasks"
        [*] --> WaitForCompletion: Задача создана
    }

    state WaitForCompletion {
        description "Ожидание выполнения Celery-задачи"
        [*] --> DeliverResult: Задача выполнена
        WaitForCompletion --> TaskFailed: Ошибка выполнения
    }

    state DeliverResult {
        description "Отправка файла с результатом пользователю"
        [*] --> [*]
    }

    state TaskFailed {
        description "Уведомление об ошибке, возврат средств"
        [*] --> [*]
    }
```

---

## 3. Support Bot: FSM обработки спора

**Описание:** Процесс работы модератора над открытым спором. Включает в себя просмотр деталей и принятие решения.

```mermaid
stateDiagram-v2
    [*] --> NewDispute: Уведомление о новом споре

    state NewDispute {
        description "Модератор видит новый спор в списке"
        [*] --> Reviewing: Модератор нажимает "Review"
    }

    state Reviewing {
        description "Просмотр деталей заказа, переписки, логов"
        [*] --> ResolveForBuyer: Решить в пользу покупателя
        Reviewing --> ResolveForSeller: Решить в пользу продавца
        Reviewing --> RequestInfo: Запросить доп. информацию
    }

    state RequestInfo {
        description "Отправка сообщения покупателю/продавцу"
        [*] --> Reviewing: Получен ответ
    }

    state ResolveForBuyer {
        description "Возврат средств покупателю, уведомление сторон"
        [*] --> [*]
    }

    state ResolveForSeller {
        description "Перевод средств продавцу, уведомление сторон"
        [*] --> [*]
    }
```

---

## 4. Marketer Bot: FSM создания бота-прокси

**Описание:** Простой, но важный процесс добавления нового зеркального бота маркетологом.

```mermaid
stateDiagram-v2
    [*] --> AwaitingToken: Пользователь нажимает "Create Bot"

    state AwaitingToken {
        description "Ожидание токена от пользователя"
        [*] --> ValidatingToken: Пользователь вводит токен
    }

    state ValidatingToken {
        description "Проверка токена через Telegram API (getMe)"
        [*] --> TokenValid: Успешная валидация
        ValidatingToken --> TokenInvalid: Ошибка валидации
    }

    state TokenInvalid {
        description "Сообщение об ошибке"
        [*] --> AwaitingToken: Предложить ввести токен снова
    }

    state TokenValid {
        description "Проверка лимитов и уникальности"
        [*] --> CreateBotRecord: Все проверки пройдены
        TokenValid --> LimitExceeded: Превышен лимит ботов
    }

    state LimitExceeded {
        description "Сообщение о превышении лимита"
        [*] --> [*]
    }

    state CreateBotRecord {
        description "Сохранение бота в `mirror_bots`"
        [*] --> Success: Запись создана
    }

    state Success {
        description "Сообщение об успешном подключении"
        [*] --> [*]
    }
```

---

## 5. Seller Bot: FSM запроса на вывод средств

**Описание:** Процесс создания заявки на вывод заработанных средств продавцом.

```mermaid
stateDiagram-v2
    [*] --> AwaitingAmount: Пользователь нажимает "Withdraw"

    state AwaitingAmount {
        description "Запрос суммы для вывода"
        [*] --> AwaitingMethod: Сумма введена
        AwaitingAmount --> InvalidAmount: Некорректная сумма
    }

    state InvalidAmount {
        description "Сообщение об ошибке (сумма < min)"
        [*] --> AwaitingAmount
    }

    state AwaitingMethod {
        description "Выбор метода вывода (BTC, USDT, XMR)"
        [*] --> AwaitingAddress: Метод выбран
    }

    state AwaitingAddress {
        description "Запрос адреса кошелька"
        [*] --> ConfirmWithdrawal: Адрес введен
    }

    state ConfirmWithdrawal {
        description "Показать детали и запросить подтверждение"
        [*] --> CreateRequest: Пользователь подтверждает
        ConfirmWithdrawal --> [*]: Отмена
    }

    state CreateRequest {
        description "Создание записи в `withdrawal_requests`"
        [*] --> NotifySupport: Заявка создана
    }

    state NotifySupport {
        description "Отправка уведомления в Support Bot"
        [*] --> [*]
    }
```
