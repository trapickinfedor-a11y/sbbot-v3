"""Textos en español para Marketer Bot"""


class MarketerTexts:

    CHOOSE_LANGUAGE = "🌍 Elige idioma / Choose language"

    # ── Welcome & Rules ──
    WELCOME_INTRO = (
        "👋 <b>¡Bienvenido a Marketer Bot!</b>\n\n"
        "Aquí puedes crear hasta <b>10 bots clones</b>, "
        "atraer usuarios y ganar un porcentaje de cada compra que realicen.\n\n"
        "<b>📋 Cómo funciona:</b>\n"
        "1. Crea un bot con @BotFather\n"
        "2. Agrega su token en \"Mis bots\"\n"
        "3. Atrae usuarios a tus bots\n"
        "4. Gana comisión por cada compra\n\n"
        "<b>💰 Programa de niveles:</b>\n"
        "🥉 <b>Inicio</b> — 7% (0–499 usuarios)\n"
        "🥈 <b>Avanzado</b> — 9% (500–4.999 usuarios)\n"
        "🥇 <b>Élite</b> — 12% (5.000+ usuarios)\n\n"
        "Tu porcentaje se basa en el <b>total de usuarios</b> "
        "en todos tus bots. ¡Cuantos más atraigas, mayor será tu tasa!"
    )
    RULES_TEXT = (
        "📜 <b>Reglas del programa de afiliados:</b>\n\n"
        "1. Está prohibido el spam y los usuarios falsos\n"
        "2. Los esquemas fraudulentos están prohibidos\n"
        "3. No presentar el bot como un servicio oficial\n"
        "4. Los bots con infracciones serán eliminados sin aviso\n"
        "5. La administración se reserva el derecho de cambiar los términos\n"
        "6. Máximo 10 bots por marketer\n"
        "7. Retiros — por solicitud al administrador\n\n"
        "Al hacer clic en \"Acepto\", confirmas que estás de acuerdo con las reglas."
    )
    BTN_ACCEPT_RULES = "✅ Acepto las Reglas"

    # ── Dashboard ──
    DASHBOARD_TITLE = "📊 <b>Panel del marketer</b>"
    TIER_LEVEL = "Nivel"
    TIER_MAX = "¡Nivel máximo!"
    TIER_NEXT = 'Para <b>{name}</b> ({percent}%): <b>{left}</b> usuarios más'
    TOTAL_USERS = "👥 Total de usuarios"
    BOTS_COUNT = "🤖 Bots"
    ORDERS_COUNT = "🛒 Pedidos"
    TOTAL_EARNED = "💰 Total ganado"
    TODAY = "📅 Hoy"
    LAST_30D = "📊 Últimos 30 días"
    REGISTRATIONS = "📝 Registros"
    BUYERS = "👥 Compradores"
    SALES = "🛒 Ventas"
    EARNED = "💰 Ganado"
    REG_SHORT = "📝 Reg"
    TIERS_LABEL = "Niveles"

    # ── Buttons ──
    BTN_MY_BOTS = "🤖 Mis bots"
    BTN_ANALYTICS = "📈 Analíticas"
    BTN_REFERRAL_MENU = "🔗 Referidos"
    BTN_LOGS = "📋 Registro de actividad"
    BTN_REFRESH = "🔄 Actualizar"
    BTN_BACK = "◀️ Atrás"
    BTN_BACK_MAIN = "◀️ Inicio"
    BTN_BACK_BOTS = "◀️ Mis bots"
    BTN_CREATE_BOT = "➕ Crear nuevo bot"
    BTN_EDIT_WELCOME = "✏️ Bienvenida"
    BTN_TOGGLE_OFF = "⏸ Desactivar"
    BTN_TOGGLE_ON = "▶️ Activar"
    BTN_DELETE = "🗑 Eliminar"
    BTN_CANCEL = "❌ Cancelar"
    BTN_BY_BOTS = "🤖 Por bot"
    BTN_TRENDS_7 = "📉 Tendencia 7d"
    BTN_TRENDS_14 = "📉 Tendencia 14d"
    BTN_TRENDS_30 = "📉 Tendencia 30d"
    BTN_LANGUAGE = "🌐 Idioma"

    # ── Periods ──
    PERIOD_DAY = "Hoy"
    PERIOD_WEEK = "Semana"
    PERIOD_MONTH = "Mes"
    PERIOD_ALL = "Todo"

    # ── My Bots ──
    MY_BOTS_TITLE = "🤖 <b>Mis bots</b>"
    BOT_ACTIVE = "✅ Activo"
    BOT_INACTIVE = "❌ Desactivado"
    BOT_USERS = "👥 Usuarios"
    BOT_ORDERS = "🛒 Pedidos"
    BOT_EARNED = "💰 Ganado"
    BOT_RATE = "📊 Tasa actual"
    BOT_WELCOME = "💬 Mensaje de bienvenida"
    BOT_WELCOME_DEFAULT = "predeterminado"
    USERS_SHORT = "usuarios"
    NO_BOTS_YET = "Aún no tienes bots.\n¡Crea un bot con @BotFather y agrégalo aquí!"
    TIER_UNTIL = "📈 Para {percent}%: <b>{left}</b> usuarios más"
    BOT_LIMIT = "Límite de bots: {max}"
    BOT_CREATED = '🎉 <b>¡Bot @{username} agregado!</b>\n\n📊 Nivel actual: {icon} {tier} — {percent}%\n👥 Total de usuarios: {total}\n\n¡Atrae usuarios a tus bots y sube de nivel!'
    BOT_ACTIVATED = "activado ✅"
    BOT_DEACTIVATED = "desactivado ❌"
    BOT_DELETED = "Bot eliminado"
    WELCOME_UPDATED = "✅ ¡Mensaje de bienvenida actualizado!"
    NOT_FOUND = "No encontrado"

    # ── Create bot FSM ──
    CREATE_BOT_TITLE = "🤖 <b>Crear nuevo bot</b>"
    CREATE_STEP1 = (
        "<b>Paso 1:</b> Crea un bot en @BotFather:\n"
        "1. Abre @BotFather\n"
        "2. Envía /newbot\n"
        "3. Establece nombre y username\n"
        "4. Copia el token y envíalo aquí\n\n"
        "<i>Ejemplo: 1234567890:AAxxxxxx...</i>"
    )
    CREATE_BAD_TOKEN = "❌ Formato de token inválido. Intenta de nuevo o presiona Cancelar."
    CREATE_DUPLICATE = "❌ Este token ya está registrado."
    CREATE_INVALID = "❌ Token inválido. Verifica e intenta de nuevo."
    CREATE_FOUND = (
        '✅ ¡Bot <b>@{username}</b> encontrado y añadido!\n\n'
        '⚠️ <b>No olvides:</b> configura un avatar en @BotFather '
        '(/setuserpic), agrega una descripción (/setdescription) '
        'y texto de perfil (/setabouttext) — ¡esto genera confianza!'
    )
    ENTER_WELCOME = "✏️ Ingresa el nuevo mensaje de bienvenida:"
    FIRST_START = "Primero envía /start"

    # ── Analytics ──
    ANALYTICS_TITLE = "📈 <b>Analíticas — {period}</b>"
    TREND_LABEL = "(tendencia)"
    CHART_TITLE = "Esta semana"
    TOPUP_AMOUNT = "💵 Monto de recarga"
    EFFICIENCY = "Métricas de eficiencia"
    CONVERSION = "📊 Conversión (reg→comprador)"
    AVG_CHECK = "🧾 Ticket promedio"
    AVG_DAILY = "📅 Promedio/día"
    AVG_REG = "reg."
    BOTS_STATS_TITLE = "📊 <b>Estadísticas por bot</b>"
    BOTS_TOTAL = "Total"
    LAST_ACTIVITY = "Últ.act"
    TREND_TITLE = "📉 <b>Tendencias ({days}d)</b>"
    TREND_HEADER = "<i>Ganado | Reg | Ventas</i>"
    NO_DATA = "Sin datos."

    # ── Logs ──
    LOGS_TITLE = "📋 <b>Registro de actividad</b>"
    LOGS_TITLE_COUNT = "📋 <b>Registro de actividad</b> (últimos {n})"
    LOGS_EMPTY = "Sin registros aún."
    LOG_REGISTRATION = "🆕 Registro"
    LOG_EARNING = "💰 Ingreso"
    LOG_TIER_UPGRADE = "📈 Subida de nivel"
    LOG_BOT_CREATED = "🤖 Bot creado"
    LOG_BOT_DELETED = "🗑 Bot eliminado"

    # ── Help ──
    HELP_TEXT = (
        "📖 <b>Ayuda Marketer Bot</b>\n\n"
        "<b>Comandos:</b>\n"
        "/start — Panel del marketer\n"
        "/bots — Mis bots\n"
        "/logs — Registro de actividad\n"
        "/help — Esta ayuda\n\n"
        "<b>Cómo funciona:</b>\n"
        "1. Crea un bot en @BotFather\n"
        "2. Agrega su token en \"Mis bots\"\n"
        "3. Atrae usuarios a tus bots\n"
        "4. Gana % de cada compra\n\n"
        "<b>Programa de niveles:</b>\n"
        "🥉 Inicio — 7% (hasta 500 usuarios)\n"
        "🥈 Avanzado — 9% (desde 500 usuarios)\n"
        "🥇 Élite — 12% (desde 5.000 usuarios)\n\n"
        "<b>📈 Analíticas:</b>\n"
        "• Estadísticas por día / semana / mes / siempre\n"
        "• Conversión, ticket promedio, promedios diarios\n"
        "• Tendencias de 7 / 14 / 30 días\n"
        "• Desglose detallado por bot\n\n"
        "<b>📬 Reporte diario:</b>\n"
        "Cada día a las 21:00 (MSK) el bot envía un resumen completo.\n\n"
        "Puedes crear hasta 10 bots."
    )

    # ── Withdrawal ──
    BTN_WITHDRAW = "💸 Retirar fondos"
    WITHDRAW_TITLE = "💸 <b>Retiro de fondos</b>"
    WITHDRAW_BALANCE = "💰 Tu saldo: <b>${balance}</b>"
    WITHDRAW_MIN = "Monto mínimo de retiro: <b>${min}</b>"
    WITHDRAW_NO_FUNDS = "❌ Fondos insuficientes para el retiro."
    WITHDRAW_ENTER_AMOUNT = "Ingresa el monto a retirar (en $):"
    WITHDRAW_BAD_AMOUNT = "❌ Monto inválido. Ingresa un número entre ${min} y ${max}."
    WITHDRAW_CHOOSE_WALLET = "💳 Elige el tipo de wallet para recibir:"
    BTN_WALLET_BTC = "₿ BTC"
    BTN_WALLET_USDT = "₮ USDT"
    WITHDRAW_ENTER_ADDRESS_BTC = "📤 Ingresa tu dirección de wallet <b>BTC</b>:"
    WITHDRAW_ENTER_ADDRESS_USDT = "📤 Ingresa tu dirección de wallet <b>USDT TRC-20</b>:"
    WITHDRAW_ENTER_REQUISITES = (
        "💳 Ingresa los datos de pago:\n"
        "<i>(billetera USDT TRC-20, número de tarjeta, etc.)</i>"
    )
    WITHDRAW_CONFIRM = (
        "📋 <b>Confirma tu solicitud:</b>\n\n"
        "💰 Monto: <b>${amount}</b>\n"
        "💳 Datos: <code>{requisites}</code>\n\n"
        "¿Confirmar?"
    )
    BTN_CONFIRM_WITHDRAW = "✅ Confirmar"
    WITHDRAW_CREATED = (
        "✅ <b>¡Solicitud de retiro creada!</b>\n\n"
        "💰 Monto: <b>${amount}</b>\n"
        "📋 Estado: pendiente de revisión\n\n"
        "El administrador procesará tu solicitud pronto."
    )
    WITHDRAW_HISTORY_TITLE = "📜 <b>Historial de retiros</b>"
    WITHDRAW_HISTORY_EMPTY = "Aún no tienes solicitudes de retiro."
    BTN_WITHDRAW_HISTORY = "📜 Historial de retiros"
    WITHDRAW_STATUS_PENDING = "⏳ Pendiente"
    WITHDRAW_STATUS_APPROVED = "✅ Pagado"
    WITHDRAW_STATUS_REJECTED = "❌ Rechazado"

    # ── Daily Report ──
    DAILY_TITLE = "📬 <b>Reporte diario — {date}</b>"
    DAILY_TODAY = "📅 Hoy"
    DAILY_WEEK = "📊 Esta semana"
    DAILY_BOTS = "🤖 Bots"
    DAILY_TOTALS = "Totales"

    # ── Referral ──
    REFERRAL_TITLE = "🔗 <b>Programa de referidos</b>"
    REFERRAL_YOUR_LINK = (
        "Tu enlace de referido:\n"
        "<code>{link}</code>\n\n"
        "¡Invita usuarios y gana un bono de cada una de sus primeras compras!\n\n"
        "📊 <b>Tasas:</b>\n"
        "• Nivel 1 (directo): <b>{l1}%</b>\n"
        "• Nivel 2: <b>{l2}%</b>\n"
        "• Nivel 3: <b>{l3}%</b>\n"
        "• Nivel 4: <b>{l4}%</b>"
    )
    BTN_COPY_LINK = "📋 Copiar enlace"
    BTN_SHARE_LINK = "📤 Compartir enlace"
    BTN_REFERRAL_STATS = "📊 Mis estadísticas"
    BTN_REFERRAL_HISTORY = "📜 Historial de ganancias"
    BTN_REFERRAL_WITHDRAW = "💸 Retirar bono"
    BTN_REFERRAL_BACK = "◀️ Atrás"

    REFERRAL_STATS_TITLE = "📊 <b>Estadísticas de referidos</b>"
    REFERRAL_STATS_TEXT = (
        "👥 Total invitados: <b>{invited}</b>\n"
        "✅ Confirmados (primera compra): <b>{confirmed}</b>\n"
        "💰 Total ganado (mostrado): <b>${earned}</b>\n"
        "⏳ En moderación: <b>${pending}</b>"
    )

    REFERRAL_HISTORY_TITLE = "📜 <b>Historial de ganancias</b>"
    REFERRAL_HISTORY_EMPTY = "Aún no tienes ganancias por referidos."
    REFERRAL_HISTORY_ROW = "• {date}  Nv.{level}  <b>+${amount}</b>  {status}"
    REFERRAL_STATUS_PENDING = "⏳ pendiente"
    REFERRAL_STATUS_APPROVED = "✅ aprobado"
    REFERRAL_STATUS_REJECTED = "❌ rechazado"
    REFERRAL_STATUS_PAID = "💸 pagado"

    REFERRAL_WITHDRAW_TITLE = "💸 <b>Retirar bono de referidos</b>"
    REFERRAL_WITHDRAW_BALANCE = "💰 Saldo disponible: <b>${balance}</b>"
    REFERRAL_WITHDRAW_MIN = "Monto mínimo: <b>${min}</b>"
    REFERRAL_WITHDRAW_NO_FUNDS = "❌ Fondos insuficientes."
    REFERRAL_WITHDRAW_ENTER_AMOUNT = "Ingresa el monto a retirar (en USD):"
    REFERRAL_WITHDRAW_ENTER_REQUISITES = (
        "💳 Ingresa los datos de pago:\n"
        "<i>(dirección BTC, USDT TRC-20, etc.)</i>"
    )
    REFERRAL_WITHDRAW_BAD_AMOUNT = "❌ Monto inválido (de ${min} a ${max})."
    REFERRAL_WITHDRAW_CONFIRM = (
        "📋 <b>Confirmar retiro:</b>\n\n"
        "💰 Monto: <b>${amount}</b>\n"
        "💳 Datos: <code>{requisites}</code>\n\n"
        "¿Confirmar?"
    )
    BTN_CONFIRM_REFERRAL_WITHDRAW = "✅ Confirmar"
    REFERRAL_WITHDRAW_CREATED = (
        "✅ <b>¡Solicitud enviada!</b>\n\n"
        "💰 Monto: <b>${amount}</b>\n"
        "📋 Estado: en espera de moderación"
    )

    # ── Referral notifications ──
    NOTIF_NEW_REFERRAL = "🎉 <b>¡Nuevo referido!</b>\n\nUn usuario se registró a través de tu enlace."
    NOTIF_REFERRAL_PURCHASE = (
        "💰 <b>¡Tu referido realizó su primera compra!</b>\n\n"
        "Bono <b>${amount}</b> (nivel {level}) enviado a moderación."
    )
    NOTIF_REFERRAL_WITHDRAW_APPROVED = (
        "✅ <b>¡Retiro aprobado!</b>\n\n"
        "💰 Monto: <b>${amount}</b>\n"
        "Los fondos serán transferidos en breve."
    )
    NOTIF_REFERRAL_WITHDRAW_REJECTED = (
        "❌ <b>Retiro rechazado.</b>\n\n"
        "💰 Monto: <b>${amount}</b>\n"
        "Motivo: {reason}"
    )
