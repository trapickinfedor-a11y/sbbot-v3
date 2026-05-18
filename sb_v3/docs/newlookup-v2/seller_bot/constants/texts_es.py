from seller_bot.constants.texts_en import BotTexts as EnglishBotTexts


class BotTexts(EnglishBotTexts):
    WELCOME_BACK = "👋 Bienvenido de nuevo, <b>{name}</b>!\n\n🏦 Tu panel de vendedor está listo.\n📦 Pedidos totales: {total_orders}\n💰 Ganancia total: ${total_earned:.2f}"
    PENDING_APPROVAL = "⏳ <b>Tu solicitud está pendiente de aprobación.</b>\n\nEspera a que el administrador la revise.\nRecibirás una notificación cuando sea aprobada."
    START_NEW = "🏦 <b>Seller Bot</b>\n\nBienvenido. Este bot te permite vender cuentas bancarias.\n\nPara empezar, envía /register y solicita acceso de vendedor.\nUn administrador revisará tu solicitud."
    ALREADY_REGISTERED = "✅ Ya estás registrado como vendedor."
    ALREADY_PENDING = "⏳ Tu solicitud ya está pendiente de aprobación."
    APPLICATION_SUBMITTED = "✅ <b>Solicitud enviada.</b>\n\nTu solicitud de vendedor fue enviada al administrador.\nRecibirás una notificación cuando sea aprobada."
    MENU_TEXT = "🏦 <b>Panel del vendedor</b>\n\n👤 {name}\n📦 Pedidos: {total_orders}\n💰 Ganado: ${total_earned:.2f}"
    NO_SELLER_ACCESS = "❌ No tienes acceso de vendedor."
    NOT_AUTHORIZED = "❌ No autorizado"
    WITHDRAW_INSUFFICIENT = "Saldo insuficiente"
