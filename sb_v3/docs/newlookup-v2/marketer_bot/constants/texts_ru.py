"""Русские тексты для Marketer Bot"""


class MarketerTexts:

    CHOOSE_LANGUAGE = "🌍 Выберите язык / Choose language"

    # ── Welcome & Rules ──
    WELCOME_INTRO = (
        "👋 <b>Добро пожаловать в Marketer Bot!</b>\n\n"
        "Здесь вы можете создать до <b>10 ботов-клонов</b>, "
        "привлекать пользователей и зарабатывать процент с каждой их покупки.\n\n"
        "<b>📋 Как это работает:</b>\n"
        "1. Создайте бота через @BotFather\n"
        "2. Добавьте его токен в разделе «Мои боты»\n"
        "3. Привлекайте пользователей в своих ботов\n"
        "4. Получайте комиссию с каждой покупки\n\n"
        "<b>💰 Уровневая программа:</b>\n"
        "🥉 <b>Старт</b> — 7% (0–499 пользователей)\n"
        "🥈 <b>Продвинутый</b> — 9% (500–4 999 пользователей)\n"
        "🥇 <b>Элита</b> — 12% (5 000+ пользователей)\n\n"
        "Процент считается по <b>общему числу пользователей</b> "
        "во всех ваших ботах. Чем больше привлечёте — тем выше ставка!"
    )
    RULES_TEXT = (
        "📜 <b>Правила партнёрской программы:</b>\n\n"
        "1. Запрещён спам и накрутка пользователей\n"
        "2. Запрещены мошеннические схемы\n"
        "3. Нельзя выдавать бота за официальный сервис\n"
        "4. Боты с нарушениями будут удалены без предупреждения\n"
        "5. Администрация оставляет за собой право изменить условия\n"
        "6. Максимум 10 ботов на одного маркетолога\n"
        "7. Вывод средств — по запросу администратору\n\n"
        "Нажимая «Принимаю», вы подтверждаете, что согласны с правилами."
    )
    BTN_ACCEPT_RULES = "✅ Принимаю правила"

    # ── Dashboard ──
    DASHBOARD_TITLE = "📊 <b>Панель маркетолога</b>"
    TIER_LEVEL = "Уровень"
    TIER_MAX = "Максимальный уровень!"
    TIER_NEXT = 'До <b>{name}</b> ({percent}%): ещё <b>{left}</b> польз.'
    TOTAL_USERS = "👥 Всего пользователей"
    BOTS_COUNT = "🤖 Ботов"
    ORDERS_COUNT = "🛒 Заказов"
    TOTAL_EARNED = "💰 Общий заработок"
    TODAY = "📅 Сегодня"
    LAST_30D = "📊 За 30 дней"
    REGISTRATIONS = "📝 Регистрации"
    BUYERS = "👥 Покупатели"
    SALES = "🛒 Продажи"
    EARNED = "💰 Заработок"
    REG_SHORT = "📝 Рег"
    TIERS_LABEL = "Уровни"

    # ── Buttons ──
    BTN_MY_BOTS = "🤖 Мои боты"
    BTN_ANALYTICS = "📈 Аналитика"
    BTN_REFERRAL_MENU = "🔗 Рефералы"
    BTN_LOGS = "📋 Лог действий"
    BTN_REFRESH = "🔄 Обновить"
    BTN_BACK = "◀️ Назад"
    BTN_BACK_MAIN = "◀️ Главная"
    BTN_BACK_BOTS = "◀️ Мои боты"
    BTN_CREATE_BOT = "➕ Создать нового бота"
    BTN_EDIT_WELCOME = "✏️ Приветствие"
    BTN_TOGGLE_OFF = "⏸ Отключить"
    BTN_TOGGLE_ON = "▶️ Включить"
    BTN_DELETE = "🗑 Удалить"
    BTN_CANCEL = "❌ Отмена"
    BTN_BY_BOTS = "🤖 По ботам"
    BTN_TRENDS_7 = "📉 Тренды 7д"
    BTN_TRENDS_14 = "📉 Тренды 14д"
    BTN_TRENDS_30 = "📉 Тренды 30д"
    BTN_LANGUAGE = "🌐 Язык"

    # ── Periods ──
    PERIOD_DAY = "Сегодня"
    PERIOD_WEEK = "Неделя"
    PERIOD_MONTH = "Месяц"
    PERIOD_ALL = "Всё время"

    # ── My Bots ──
    MY_BOTS_TITLE = "🤖 <b>Мои боты</b>"
    BOT_ACTIVE = "✅ Активен"
    BOT_INACTIVE = "❌ Отключён"
    BOT_USERS = "👥 Пользователей"
    BOT_ORDERS = "🛒 Заказов"
    BOT_EARNED = "💰 Заработано"
    BOT_RATE = "📊 Текущая ставка"
    BOT_WELCOME = "💬 Приветствие"
    BOT_WELCOME_DEFAULT = "стандартное"
    USERS_SHORT = "польз."
    NO_BOTS_YET = "У вас пока нет ботов.\nСоздайте бота через @BotFather и добавьте его здесь!"
    TIER_UNTIL = "📈 До {percent}%: ещё <b>{left}</b> польз."
    BOT_LIMIT = "Лимит ботов: {max}"
    BOT_CREATED = '🎉 <b>Бот @{username} добавлен!</b>\n\n📊 Текущий уровень: {icon} {tier} — {percent}%\n👥 Всего пользователей: {total}\n\nПривлекайте пользователей в своих ботов и повышайте уровень!'
    BOT_ACTIVATED = "активирован ✅"
    BOT_DEACTIVATED = "отключён ❌"
    BOT_DELETED = "Бот удалён"
    WELCOME_UPDATED = "✅ Приветствие обновлено!"
    NOT_FOUND = "Не найден"

    # ── Create bot FSM ──
    CREATE_BOT_TITLE = "🤖 <b>Создание нового бота</b>"
    CREATE_STEP1 = (
        "<b>Шаг 1:</b> Создайте бота в @BotFather:\n"
        "1. Откройте @BotFather\n"
        "2. Отправьте /newbot\n"
        "3. Укажите имя и username\n"
        "4. Скопируйте токен и отправьте его сюда\n\n"
        "<i>Пример: 1234567890:AAxxxxxx...</i>"
    )
    CREATE_BAD_TOKEN = "❌ Неверный формат токена. Попробуйте снова или нажмите Отмена."
    CREATE_DUPLICATE = "❌ Этот токен уже зарегистрирован."
    CREATE_INVALID = "❌ Токен недействителен. Проверьте и попробуйте снова."
    CREATE_FOUND = (
        '✅ Бот <b>@{username}</b> найден и добавлен!\n\n'
        '⚠️ <b>Не забудьте:</b> установите аватар бота в @BotFather '
        '(команда /setuserpic), добавьте описание (/setdescription) '
        'и краткое описание (/setabouttext) — это повысит доверие пользователей!'
    )
    ENTER_WELCOME = "✏️ Введите новое приветственное сообщение:"
    FIRST_START = "Сначала /start"

    # ── Analytics ──
    ANALYTICS_TITLE = "📈 <b>Аналитика — {period}</b>"
    TREND_LABEL = "(тренд)"
    CHART_TITLE = "Неделя"
    TOPUP_AMOUNT = "💵 Сумма пополнений"
    EFFICIENCY = "Показатели эффективности"
    CONVERSION = "📊 Конверсия (рег→покуп)"
    AVG_CHECK = "🧾 Средний чек"
    AVG_DAILY = "📅 Среднее/день"
    AVG_REG = "рег."
    BOTS_STATS_TITLE = "📊 <b>Статистика по ботам</b>"
    BOTS_TOTAL = "Итого"
    LAST_ACTIVITY = "Посл.акт"
    TREND_TITLE = "📉 <b>Тренды ({days} дн.)</b>"
    TREND_HEADER = "<i>Заработок | Рег | Продажи</i>"
    NO_DATA = "Нет данных."

    # ── Logs ──
    LOGS_TITLE = "📋 <b>Лог действий</b>"
    LOGS_TITLE_COUNT = "📋 <b>Лог действий</b> (последние {n})"
    LOGS_EMPTY = "Пока нет записей."
    LOG_REGISTRATION = "🆕 Регистрация"
    LOG_EARNING = "💰 Начисление"
    LOG_TIER_UPGRADE = "📈 Повышение уровня"
    LOG_BOT_CREATED = "🤖 Бот создан"
    LOG_BOT_DELETED = "🗑 Бот удалён"

    # ── Help ──
    HELP_TEXT = (
        "📖 <b>Справка Marketer Bot</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — Панель маркетолога\n"
        "/bots — Мои боты\n"
        "/logs — Лог действий\n"
        "/help — Эта справка\n\n"
        "<b>Как работает:</b>\n"
        "1. Создайте бота в @BotFather\n"
        "2. Добавьте его токен через «Мои боты»\n"
        "3. Привлекайте пользователей в свои боты\n"
        "4. Получайте % с каждой покупки\n\n"
        "<b>Уровневая программа:</b>\n"
        "🥉 Старт — 7% (до 500 польз.)\n"
        "🥈 Продвинутый — 9% (от 500 польз.)\n"
        "🥇 Элита — 12% (от 5 000 польз.)\n\n"
        "<b>📈 Аналитика:</b>\n"
        "• Статистика за день / неделю / месяц / всё время\n"
        "• Конверсия, средний чек, среднее/день\n"
        "• Тренды за 7 / 14 / 30 дней\n"
        "• Детальная разбивка по каждому боту\n\n"
        "<b>📬 Ежедневный отчёт:</b>\n"
        "Каждый день в 21:00 (МСК) бот присылает полную сводку.\n\n"
        "Можно создать до 10 ботов."
    )

    # ── Withdrawal ──
    BTN_WITHDRAW = "💸 Вывод средств"
    WITHDRAW_TITLE = "💸 <b>Вывод средств</b>"
    WITHDRAW_BALANCE = "💰 Ваш баланс: <b>${balance}</b>"
    WITHDRAW_MIN = "Минимальная сумма вывода: <b>${min}</b>"
    WITHDRAW_NO_FUNDS = "❌ Недостаточно средств для вывода."
    WITHDRAW_ENTER_AMOUNT = "Введите сумму вывода (в $):"
    WITHDRAW_BAD_AMOUNT = "❌ Некорректная сумма. Введите число от ${min} до ${max}."
    WITHDRAW_CHOOSE_WALLET = "💳 Выберите тип кошелька для получения:"
    BTN_WALLET_BTC = "₿ BTC"
    BTN_WALLET_USDT = "₮ USDT"
    WITHDRAW_ENTER_ADDRESS_BTC = "📤 Введите ваш <b>BTC</b> адрес кошелька:"
    WITHDRAW_ENTER_ADDRESS_USDT = "📤 Введите ваш <b>USDT TRC-20</b> адрес кошелька:"
    WITHDRAW_ENTER_REQUISITES = (
        "💳 Введите реквизиты для получения:\n"
        "<i>(кошелёк USDT TRC-20, номер карты и т.д.)</i>"
    )
    WITHDRAW_CONFIRM = (
        "📋 <b>Подтвердите заявку:</b>\n\n"
        "💰 Сумма: <b>${amount}</b>\n"
        "💳 Реквизиты: <code>{requisites}</code>\n\n"
        "Подтвердить?"
    )
    BTN_CONFIRM_WITHDRAW = "✅ Подтвердить"
    WITHDRAW_CREATED = (
        "✅ <b>Заявка на вывод создана!</b>\n\n"
        "💰 Сумма: <b>${amount}</b>\n"
        "📋 Статус: ожидает обработки\n\n"
        "Администратор рассмотрит заявку в ближайшее время."
    )
    WITHDRAW_HISTORY_TITLE = "📜 <b>История выводов</b>"
    WITHDRAW_HISTORY_EMPTY = "У вас пока нет заявок на вывод."
    BTN_WITHDRAW_HISTORY = "📜 История выводов"
    WITHDRAW_STATUS_PENDING = "⏳ Ожидает"
    WITHDRAW_STATUS_APPROVED = "✅ Выплачено"
    WITHDRAW_STATUS_REJECTED = "❌ Отклонено"

    # ── Daily Report ──
    DAILY_TITLE = "📬 <b>Ежедневный отчёт — {date}</b>"
    DAILY_TODAY = "📅 Сегодня"
    DAILY_WEEK = "📊 За неделю"
    DAILY_BOTS = "🤖 Боты"
    DAILY_TOTALS = "Общие итоги"

    # ── Referral ──
    REFERRAL_TITLE = "🔗 <b>Реферальная программа</b>"
    REFERRAL_YOUR_LINK = (
        "Ваша реферальная ссылка:\n"
        "<code>{link}</code>\n\n"
        "Приглашайте пользователей и получайте бонус с каждой их первой покупки!\n\n"
        "📊 <b>Ставки:</b>\n"
        "• Уровень 1 (прямой): <b>{l1}%</b>\n"
        "• Уровень 2: <b>{l2}%</b>\n"
        "• Уровень 3: <b>{l3}%</b>\n"
        "• Уровень 4: <b>{l4}%</b>"
    )
    BTN_COPY_LINK = "📋 Скопировать ссылку"
    BTN_SHARE_LINK = "📤 Поделиться ссылкой"
    BTN_REFERRAL_STATS = "📊 Моя статистика"
    BTN_REFERRAL_HISTORY = "📜 История начислений"
    BTN_REFERRAL_WITHDRAW = "💸 Вывести бонус"
    BTN_REFERRAL_BACK = "◀️ Назад"

    REFERRAL_STATS_TITLE = "📊 <b>Статистика рефералов</b>"
    REFERRAL_STATS_TEXT = (
        "👥 Приглашено всего: <b>{invited}</b>\n"
        "✅ Подтверждено (первая покупка): <b>{confirmed}</b>\n"
        "💰 Всего заработано (отображаемое): <b>${earned}</b>\n"
        "⏳ На модерации: <b>${pending}</b>"
    )

    REFERRAL_HISTORY_TITLE = "📜 <b>История начислений</b>"
    REFERRAL_HISTORY_EMPTY = "У вас пока нет начислений по реферальной программе."
    REFERRAL_HISTORY_ROW = "• {date}  Ур.{level}  <b>+${amount}</b>  {status}"
    REFERRAL_STATUS_PENDING = "⏳ на модерации"
    REFERRAL_STATUS_APPROVED = "✅ одобрено"
    REFERRAL_STATUS_REJECTED = "❌ отклонено"
    REFERRAL_STATUS_PAID = "💸 выплачено"

    REFERRAL_WITHDRAW_TITLE = "💸 <b>Вывод реферального бонуса</b>"
    REFERRAL_WITHDRAW_BALANCE = "💰 Доступный баланс: <b>${balance}</b>"
    REFERRAL_WITHDRAW_MIN = "Минимальная сумма: <b>${min}</b>"
    REFERRAL_WITHDRAW_NO_FUNDS = "❌ Недостаточно средств."
    REFERRAL_WITHDRAW_ENTER_AMOUNT = "Введите сумму для вывода (в USD):"
    REFERRAL_WITHDRAW_ENTER_REQUISITES = (
        "💳 Введите реквизиты:\n"
        "<i>(BTC-адрес, USDT TRC-20 и т.д.)</i>"
    )
    REFERRAL_WITHDRAW_BAD_AMOUNT = "❌ Некорректная сумма (от ${min} до ${max})."
    REFERRAL_WITHDRAW_CONFIRM = (
        "📋 <b>Подтверждение вывода:</b>\n\n"
        "💰 Сумма: <b>${amount}</b>\n"
        "💳 Реквизиты: <code>{requisites}</code>\n\n"
        "Подтвердить?"
    )
    BTN_CONFIRM_REFERRAL_WITHDRAW = "✅ Подтвердить"
    REFERRAL_WITHDRAW_CREATED = (
        "✅ <b>Заявка принята!</b>\n\n"
        "💰 Сумма: <b>${amount}</b>\n"
        "📋 Статус: ожидает модерации"
    )

    # ── Referral notifications ──
    NOTIF_NEW_REFERRAL = "🎉 <b>Новый реферал!</b>\n\nПользователь зарегистрировался по вашей ссылке."
    NOTIF_REFERRAL_PURCHASE = (
        "💰 <b>Реферал сделал первую покупку!</b>\n\n"
        "Бонус <b>${amount}</b> (уровень {level}) отправлен на модерацию."
    )
    NOTIF_REFERRAL_WITHDRAW_APPROVED = (
        "✅ <b>Вывод одобрен!</b>\n\n"
        "💰 Сумма: <b>${amount}</b>\n"
        "Средства будут переведены в ближайшее время."
    )
    NOTIF_REFERRAL_WITHDRAW_REJECTED = (
        "❌ <b>Вывод отклонён.</b>\n\n"
        "💰 Сумма: <b>${amount}</b>\n"
        "Причина: {reason}"
    )
