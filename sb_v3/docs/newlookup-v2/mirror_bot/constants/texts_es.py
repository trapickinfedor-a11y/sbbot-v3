"""
Spanish texts for Mirror Bot.
Fallbacks inherit from English when not overridden.
"""

from mirror_bot.constants.texts_en import BotTexts as EnglishBotTexts


class BotTexts(EnglishBotTexts):
    START_MESSAGE = """⚡ ONE PROJECT: tu acceso rápido al ecosistema ONE.

🚀 Todo en un solo lugar:
🔹 acceso 24/7
🔹 ONE HUB, ONE LOOKUP y ONE BANKS
🔹 control rápido y seguro desde un solo panel"""

    MAIN_MENU_TEXT = "🏠 Menú principal"

    PROFILE_TEXT = """👤 Perfil

🧩 Tu ID: {user_id}
💰 Saldo: {balance} USD
🕓 Registro: {created_at}

🔗 Enlace de referido: {referral_link}
👥 Número de referidos: {referrals_count}

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬
🌐 ENLACE ACTUAL
▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"""

    TOPUP_STEP1 = "🪙 Paso 1 — Elige el sistema de pago"
    TOPUP_STEP2 = """💵 Paso 2 — Introduce el importe

💰 Introduce la cantidad que deseas recargar:
10 — 5000 USD

⚠️ Mínimo: $10 · Máximo: $5000

Después del pago, el sistema lo verificará automáticamente."""
    TOPUP_STEP2_CRYPTOPAY = """💵 Paso 2 — Introduce el importe

💰 Introduce la cantidad que deseas recargar:
10 — 5000 USD

⚠️ Mínimo: $10 · Máximo: $5000

🚨 ¡ATENCIÓN! CryptoBot es un servicio de pago de terceros.
Recargar tu saldo dentro de CryptoBot NO acredita dinero en nuestro sistema.
Después de recargar en CryptoBot, debes pagar la factura que generaremos.

Después del pago, el sistema lo verificará automáticamente."""
    TOPUP_STEP3 = """🔗 Paso 3 — Enlace de pago

Tu enlace de pago ha sido generado.

Pulsa abajo para completar la transacción:"""
    TOPUP_STEP3_CRYPTOPAY = """🔗 Paso 3 — Enlace de pago

💰 Importe: ${amount} USD

⚠️ ¡IMPORTANTE! CryptoBot es un servicio externo.
Después de recargar en CryptoBot, debes pagar la factura usando el enlace de abajo.
El dinero NO llegará a tu saldo hasta que pagues la factura.

ℹ️ Se aplica una comisión de procesamiento.

📌 Criptomonedas aceptadas:
   • USDT (TRC20/ERC20)
   • TON
   • BTC
   • ETH
   • USDC

⏱ La factura expira en 1 hora

Pulsa abajo para completar la transacción:"""
    TOPUP_SUCCESS = """✅ Saldo recargado correctamente por +{amount}$

💼 Tu nuevo saldo se actualizó automáticamente.

🔁 Escribe /menu para volver a la interfaz principal.

⚡ Gracias por usar ONE PROJECT."""
    TOPUP_SUCCESS_SHORT = "✅ ¡Pago exitoso! ${amount} se agregó a tu saldo."
    PAYMENT_AUTO_SUCCESS_TITLE = "✅ <b>¡Pago recibido con éxito!</b>\n\n"
    PAYMENT_AUTO_SUCCESS_AMOUNT = "💵 Acreditado: <b>${amount}</b>\n"
    PAYMENT_AUTO_SUCCESS_BALANCE = "💰 Tu saldo: <b>${balance}</b>\n\n"
    PAYMENT_AUTO_SUCCESS_THANKS = "Gracias por tu recarga 🎉"
    PAYMENT_AUTO_EXPIRED_TITLE = "⏰ <b>El tiempo de pago expiró</b>\n\n"
    PAYMENT_AUTO_EXPIRED_AMOUNT = "El pago de <b>${amount}</b> fue cancelado.\n"
    PAYMENT_AUTO_EXPIRED_CREATE_NEW = "Crea un nuevo pago si quieres recargar tu saldo."
    TOPUP_EXPIRED = """❌ Tu sesión de pago expiró o falló.

Por favor crea un nuevo enlace de pago o contacta a soporte si el dinero fue enviado pero no acreditado.

🧠 Soporte → Crear TICKET"""
    TOPUP_INVALID_AMOUNT = """❌ Importe inválido

⚠️ Mínimo: $10 · Máximo: $5000

Introduce un importe válido:"""
    PAYMENT_WAITING = "⏳ Esperando el pago..."
    PAYMENT_SYSTEM_NOT_CONFIGURED = "❌ El sistema de pago no está configurado"
    PAYMENT_ERROR_CREATING = "❌ Error al crear el pago: {error}"
    PAYMENT_SYSTEM_NOT_CONFIGURED_ALERT = "❌ Sistema de pago no configurado"
    PAYMENT_INVOICE_NOT_FOUND = "❌ Factura no encontrada"
    PAYMENT_CONFIRMED = "✅ ¡Pago confirmado!"
    PAYMENT_CONFIRMED_TEXT = """✅ **¡Pago confirmado!**

Importe: **${amount} {asset}**
Factura ID: `{invoice_id}`
Pagado en: {paid_at}"""
    PAYMENT_EXPIRED = "❌ La factura expiró"
    PAYMENT_CHECK_ERROR = "❌ Error al comprobar el pago"
    PAYMENT_CANCELLED_SUCCESS = "✅ Pago cancelado"
    PAYMENT_CANCELLED_TEXT = "❌ **Pago cancelado**"
    PAYMENT_CANCEL_FAILED = "❌ No se pudo cancelar el pago"
    PAYMENT_CANCEL_ERROR = "❌ Error al cancelar el pago"

    SEND_MONEY_TEXT = """💸 Enviar dinero a otro usuario

Introduce el ID del destinatario:"""
    SEND_MONEY_AMOUNT = """💰 Introduce la cantidad a enviar:

Tu saldo: {balance} USD"""
    SEND_MONEY_AMOUNT_SHORT = "💰 Introduce la cantidad a enviar:\n\nTu saldo: ${balance}"
    SEND_MONEY_SUCCESS = """✅ Envío realizado correctamente: ${amount} al usuario {user_id}

💰 Tu nuevo saldo: ${balance}"""
    SEND_MONEY_SUCCESS_SHORT = "✅ Transferencia realizada\n\n💸 Enviado: ${amount}\n👤 Usuario ID: {recipient_id}\n💰 Tu saldo: ${balance}"
    SEND_MONEY_CONFIRM = "📝 **Confirmar transferencia**\n\n💸 Cantidad: ${amount}\n👤 Usuario ID: {recipient_id}\n\n💰 Tu saldo después: ${balance_after}\n\n¿Confirmar transferencia?"
    SEND_MONEY_INSUFFICIENT = """❌ Saldo insuficiente

💰 Tu saldo: ${balance}
💳 Requerido: ${amount}"""
    SEND_MONEY_INSUFFICIENT_SHORT = "❌ Saldo insuficiente\n\nTu saldo: ${balance}\nSolicitado: ${amount}"

    LANGUAGE_CHANGED = "✅ Idioma cambiado a {language}"
    LANGUAGE_SAVED = "✅ Idioma guardado"
    CHOOSE_YOUR_LANGUAGE = "🌍 Choose your language / Выберите язык / 选择语言 / Elige idioma:"

    REFERRAL_SYSTEM = """🤝 Programa de referidos — hasta +25%

🔗 Tu enlace de referido:
{referral_link}

📊 Sistema de 4 niveles:
1️⃣ Nivel 1 — 10%
2️⃣ Nivel 2 — 7%
3️⃣ Nivel 3 — 5%
4️⃣ Nivel 4 — 3%

👥 Referidos totales: {count}
💵 Ganado total: ${earned} USD

💰 ¡Cada compra en tu cadena te da un bono automáticamente!"""

    ORDER_CONFIRMATION = """✅ Confirmación del pedido

Servicio: {service_name}
💰 Precio: ${price}

📝 ¡Tus datos fueron validados!

¿Confirmar pedido?"""
    ORDER_CREATED = """✅ **¡Pedido creado correctamente!**

🎲 **{product}**
💵 **Precio:** ${price:.2f}
⏱ **ETA:** {eta}
💳 **Saldo:** ${balance:.2f}

Tu pedido fue enviado al equipo de soporte para su procesamiento."""
    ORDER_COMPLETED = """✅ ¡Pedido #{order_id} completado!

Servicio: {service_name}

{result_text}

💰 Tu saldo: ${balance}

Escribe /menu para volver al menú principal."""
    BULK_ORDER_RESULT = """✅ ¡Pedido masivo #{order_id} completado!

Servicio: {service_name}

{items_text}

💰 Reembolso por NOT FOUND: +${refund}
💰 Tu saldo: ${balance}

Escribe /menu para volver al menú principal."""
    INVALID_DATA = """❌ Formato de datos inválido

{error_message}

📝 Ejemplo:
{example}"""
    INSUFFICIENT_BALANCE = """❌ Saldo insuficiente

💰 Tu saldo: ${balance}
💳 Requerido: ${price}

Recarga tu saldo para continuar."""

    RULES_ACCEPT_PROMPT = "📜 Lee y acepta las reglas antes de usar el servicio:"
    RULES_ACCEPTED_SUCCESS = "✅ Reglas aceptadas. Bienvenido al servicio."
    RULES_DECLINED_MESSAGE = "❌ Debes aceptar las reglas para usar el servicio. Envía /start para intentarlo de nuevo."

    AVAILABLE_PRODUCTS = "🛍️ **Productos disponibles**"
    CATEGORY_LABEL = "📂 **Categoría:**"
    STATE_LABEL = "🏛️ **Estado:**"
    TOTAL_LABEL = "📦 **Total:**"
    PRODUCTS_COUNT = "{total} productos"
    PRODUCT_LABEL = "📦 **Producto:**"
    PAID_LABEL = "💰 **Pagado:**"
    NEW_BALANCE_LABEL = "💳 **Nuevo saldo:**"
    FILE_WILL_BE_DELETED = "⚠️ *El archivo se eliminará en 1 hora por seguridad*"
    PURCHASE_SUCCESSFUL = "✅ **¡Compra realizada con éxito!**"
    PURCHASE_COMPLETED = "✅ **¡Compra completada!**"
    FILE_HAS_BEEN_SENT = "📁 **¡Tu archivo fue enviado!**"
    PURCHASE_SUCCESSFUL_SHORT = "¡Compra exitosa! ✅"
    INSUFFICIENT_BALANCE_CAPS = "❌ **Saldo insuficiente**"
    REQUIRED_LABEL_CAPS = "💰 **Requerido:**"
    YOUR_BALANCE_LABEL = "💳 **Tu saldo:**"
    NEED_LABEL = "💸 **Falta:**"
    PURCHASE_FAILED = "❌ **Compra fallida**"
    FILE_DELIVERY_FAILED_SHORT = "❌ **No se pudo entregar el archivo:**"
    FILE_NOT_FOUND_SERVER = "Archivo no encontrado en el servidor"
    BUY_NOW_BUTTON = "💰 Comprar ahora"
    BACK_TO_LIST_BUTTON = "🔙 Volver a la lista"
    BACK_TO_STATES_BUTTON = "🔙 Volver a estados"
    FILE_TYPE_LABEL = "**Tipo de archivo:**"
    DESCRIPTION_LABEL = "📝 **Descripción:**"
    YOUR_ORDER_READY = "✅ **Tu pedido{order_text} está listo!**"
    YOUR_FILE_ATTACHED_BELOW = "📎 Tu archivo está adjunto abajo:"
    VALIDATION_ERROR_SHORT = "❌ Error de validación:"
    TOTAL_WITH_CONFIRM = "💰 Total: ${total}\n\n¿Confirmar?"
    CONFIRM_PURCHASE_QUESTION = "¿Confirmar compra?"
    NO_PRODUCTS_AVAILABLE = "❌ **No hay productos disponibles**"
    INVALID_DATA_FORMAT_SHORT = "❌ Formato de datos inválido"
    ERROR_LOADING_PRODUCTS = "❌ Error al cargar productos"
    ERROR_LOADING_PAGE = "❌ Error al cargar la página"
    ERROR_LOADING_PRODUCT = "❌ Error al cargar el producto"
    ERROR_PROCESSING_PURCHASE = "❌ Error al procesar la compra"
    ERROR_LOADING_STATES = "Error al cargar estados"
    PRODUCT_NOT_FOUND = "❌ Producto no encontrado"
    PURCHASE_FAILED_SHORT = "❌ Compra fallida"
    PURCHASE_PINNED = "📌 Los datos del pedido #{order_id} se fijaron en el chat."
    PURCHASE_ARCHIVED = "📢 Los datos tambien se enviaron a tu canal de archivo."
    PURCHASE_HISTORY_TITLE = "📦 Mis compras"
    PURCHASE_HISTORY_EMPTY = "Todavia no tienes compras."
    PURCHASE_HISTORY_FILTER_CATEGORY = "🗂 Por categorias"
    PURCHASE_HISTORY_FILTER_SELLER = "👨‍💼 Por vendedores"
    PURCHASE_HISTORY_DETAILS = "Detalles"
    PURCHASE_HISTORY_SELECT_CATEGORY = "Elige un filtro por categoria:"
    PURCHASE_HISTORY_SELECT_SELLER = "Elige un filtro por vendedor:"
    HISTORY_FILTER_ALL = "📋 Todas las categorias"
    ARCHIVE_SETUP_INSTRUCTIONS = "📁 Configurar archivo\n\n1. Crea un canal privado.\n2. Agrega este bot como administrador.\n3. Reenvia aqui cualquier mensaje de ese canal."
    ARCHIVE_SETUP_SUCCESS = "✅ Canal de archivo conectado correctamente."
    ARCHIVE_SETUP_INVALID = "❌ Reenvia un mensaje desde un canal para que pueda guardar su ID."
    ARCHIVE_SETUP_BOT_NOT_ADMIN = "❌ Primero agrega este bot como administrador del canal y vuelve a intentarlo."
    PHONE_EXAMPLE_FORMAT = "Ejemplo: +1 (320) 932-0202 o 3209320202"
    INVALID_DATA_FORMAT_WITH_EXAMPLE = "❌ Formato de datos inválido\n\n{issues_text}\n\n📝 Ejemplo:\n{example}"

    PLEASE_START_PROCESS_AGAIN = "⚠️ Por favor inicia el proceso de nuevo"
    VIOLATION_OF_SERVICE_RULES = "Violación de las reglas del servicio"

    SUPPORT_CHOOSE_CATEGORY = """📝 Describe tu problema o pregunta con detalle.

También puedes adjuntar fotos o archivos después de enviar el mensaje."""
    SUPPORT_MESSAGE_TOO_SHORT = "❌ El mensaje es demasiado corto. Describe el problema con más detalle (mínimo 10 caracteres)."
    SUPPORT_TICKET_CREATED = """✅ Tu solicitud #{ticket_id} ha sido creada

Categoría: {category}
Estado: Abierto

Nuestros especialistas te responderán pronto.
Recibirás una notificación cuando llegue una respuesta.

¿Quieres adjuntar archivos o capturas?"""
    SUPPORT_TICKET_NOT_FOUND = "❌ Ticket no encontrado"
    SUPPORT_ACCESS_DENIED = "❌ Acceso denegado"
    SUPPORT_TICKET_CLOSED = "❌ Este ticket ya está cerrado. Crea una nueva solicitud."
    SUPPORT_MESSAGE_EMPTY = "❌ El mensaje no puede estar vacío."
    SUPPORT_MESSAGE_SENT = """✅ Tu mensaje ha sido enviado

Ticket #{ticket_id}
Recibirás una notificación cuando llegue una respuesta."""
    SUPPORT_ATTACH_FILES = """📎 Envía archivos, fotos o documentos.

Cuando termines, pulsa /done"""
    SUPPORT_FILES_ATTACHED = "✅ Archivos adjuntados"
    SUPPORT_FILE_ATTACHED = "✅ Archivo adjuntado. Envía más o pulsa /done"
    MY_TICKETS_MAIN = "📋 Mis tickets"
    MY_TICKETS_OPEN = "🟢 Abiertos:"
    MY_TICKETS_NO_OPEN = "🟢 No hay tickets abiertos"
    MY_TICKETS_CLOSED = "⚪️ Cerrados (últimos 10):"
    TICKET_DETAIL_HEADER = """🎫 Ticket #{ticket_id}

Categoría: {category}
Estado: {status}
Creado: {created_at}

━━━━━━━━━━━━━━━━━"""
    TICKET_SENDER_YOU = "👤 Tú"
    TICKET_SENDER_SUPPORT = "👨‍💼 Soporte"
    TICKET_FILES_COUNT = "📎 Archivos: {count}"
    TICKET_WRITE_REPLY = """✍️ Escribe tu mensaje:

(También puedes enviar una foto o un archivo)"""
    ADMIN_MESSAGE_FROM = "📢 Mensaje del administrador:"
    ADMIN_BROADCAST_FROM = "📢 Comunicado de la administración:"
    SUPPORT_NEW_REPLY = "💬 Nueva respuesta en el ticket #{ticket_id}"
    SUPPORT_REPLY_CATEGORY = "Categoría: {category}"
    SUPPORT_REPLY_SUBJECT = "Asunto: {subject}"
    SUPPORT_REPLY_FROM_SUPPORT = "Respuesta de soporte:"
    SUPPORT_STATUS_CHANGED = "📊 Estado del ticket cambiado #{ticket_id}"
    SUPPORT_NEW_STATUS = "Nuevo estado: {status}"

    SUPPORT_MAIN = """📞 Soporte

Elige el tema de tu solicitud.

Puedes abrir un ticket nuevo o revisar tus tickets existentes."""
