from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from mirror_bot.constants.buttons_en import ButtonTexts


def language_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура выбора языка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=buttons.LANG_RUSSIAN, callback_data="lang_ru"),
            InlineKeyboardButton(text=buttons.LANG_ENGLISH, callback_data="lang_en")
        ],
        [
            InlineKeyboardButton(text=buttons.LANG_CHINESE, callback_data="lang_zh"),
            InlineKeyboardButton(text=buttons.LANG_SPANISH, callback_data="lang_es")
        ]
    ])


def rules_accept_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура принятия правил"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.ACCEPT_RULES, callback_data="rules_accept")],
        [InlineKeyboardButton(text=buttons.DECLINE_RULES, callback_data="rules_decline")]
    ])


def profile_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    my_cc_text = getattr(buttons, "MY_CC_ORDERS", "💳 My CC Orders")
    coupon_text = getattr(buttons, "APPLY_COUPON", "🎟 Apply Coupon")
    my_purchases_text = getattr(buttons, "MY_PURCHASES", "📦 My Purchases")
    setup_archive_text = getattr(buttons, "SETUP_ARCHIVE", "📁 Setup Archive")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.MY_BANK_ORDERS, callback_data="buyer_my_orders")],
        [InlineKeyboardButton(text=my_purchases_text, callback_data="product_purchase_history")],
        [InlineKeyboardButton(text=my_cc_text, callback_data="buyer_my_cc_orders")],
        [InlineKeyboardButton(text=buttons.SEND_MONEY, callback_data="send_money")],
        [InlineKeyboardButton(text=coupon_text, callback_data="apply_coupon")],
        [InlineKeyboardButton(text=buttons.REFERRAL_SYSTEM, callback_data="ref_system")],
        [InlineKeyboardButton(text=setup_archive_text, callback_data="setup_archive")],
        [InlineKeyboardButton(text=buttons.VIEW_RULES, callback_data="view_rules")],
        [InlineKeyboardButton(text=buttons.CHOOSE_LANGUAGE, callback_data="choose_lang")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])


def topup_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.PAY_VIA_CRYPTOBOT, callback_data="pay_cryptopay")],
        [InlineKeyboardButton(text=buttons.PAY_VIA_CRYPTOMUS, callback_data="pay_cryptomus")],
        [InlineKeyboardButton(text=buttons.BACK_TO_MENU, callback_data="back_main")]
    ])


def payment_link_keyboard(url: str, buttons) -> InlineKeyboardMarkup:
    """Клавиатура с ссылкой на оплату"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.OPEN_PAYMENT_LINK, url=url)],
        [InlineKeyboardButton(text=buttons.REFRESH_STATUS, callback_data="check_payment")],
        [InlineKeyboardButton(text=buttons.BACK_TO_MENU, callback_data="back_main")]
    ])


def reorder_keyboard(service_name: str, user_language: str = "en") -> InlineKeyboardMarkup:
    """Кнопка 'Заказать ещё' после завершения заказа"""
    from mirror_bot.constants.language_loader import get_buttons
    buttons = get_buttons(user_language)

    SERVICE_TO_CATEGORY = {
        "lookup_ssn": "lookup", "lookup_dl": "lookup", "lookup_mvr": "lookup",
        "lookup_fullmvr": "lookup", "lookup_credit": "lookup", "lookup_bg": "lookup",
        "lookup_mmn": "lookup", "lookup_ein": "lookup",
        "phone_name": "lookup", "phone_ssn": "lookup", "phone_full": "lookup",
        "cr_transunion": "credit", "cr_experian": "credit", "cr_equifax": "credit",
        "cr_lexisnexis": "credit", "cr_wallet": "credit",
        "fullz": "fullz", "fullz_cs": "fullz", "fullz_business": "fullz",
        "fullz_700plus": "fullz", "fullz_800plus": "fullz",
        "fullz_under18": "fullz", "fullz_immigrant": "fullz", "fullz_zero_bank": "fullz",
        "personal_random": "fullz",
        "dl_front_back": "documents", "dl_selfie": "documents", "dl_kyc": "documents",
        "passport": "documents", "business_docs": "documents",
        "accounts_background": "accounts", "accounts_lookup": "accounts",
        "addinfo_cr": "addinfo", "addinfo_bg": "addinfo",
        "addinfo_employer": "addinfo", "addinfo_unfreeze": "addinfo",
    }

    category = SERVICE_TO_CATEGORY.get(service_name)
    if not category:
        for prefix in ("lookup_", "phone_", "cr_", "fullz", "dl_", "passport",
                        "business_docs", "accounts_", "addinfo_", "sms_", "data_"):
            if service_name.startswith(prefix):
                if prefix in ("sms_", "data_"):
                    category = "esim"
                elif prefix in ("lookup_", "phone_"):
                    category = "lookup"
                elif prefix == "cr_":
                    category = "credit"
                elif prefix.startswith("fullz"):
                    category = "fullz"
                elif prefix in ("dl_", "passport", "business_docs"):
                    category = "documents"
                elif prefix == "accounts_":
                    category = "accounts"
                elif prefix == "addinfo_":
                    category = "addinfo"
                break
        if service_name.startswith("bank_") or service_name.startswith("vcc_") or \
           service_name.startswith("pers_") or service_name.startswith("biz_") or \
           service_name.startswith("crypto_"):
            category = "banks"
        # eSIM: каталог из БД + configurator + старые префиксы sms_/data_
        if service_name.startswith(
            ("gv_", "esim_cfg_", "esim_sms_", "esim_data_", "sms_", "data_")
        ):
            category = "esim"

    if not category:
        category = "lookup"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.REORDER, callback_data=f"reorder:{category}")]
    ])


def cs_retry_keyboard(order_id: int, user_language: str = "en", bulk_item_number: int = None) -> InlineKeyboardMarkup:
    """Кнопка повторного запуска CS automation."""
    from mirror_bot.constants.language_loader import get_buttons

    buttons = get_buttons(user_language)
    callback_data = (
        f"cs_retry_item:{order_id}:{bulk_item_number}"
        if bulk_item_number is not None
        else f"cs_retry_order:{order_id}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.REORDER, callback_data=callback_data)]
    ])


def get_payment_keyboard(payment_url: str, invoice_id: str, method: str, buttons) -> InlineKeyboardMarkup:
    """
    Клавиатура для оплаты (универсальная для CryptoPay и Cryptomus)
    
    Args:
        payment_url: URL для оплаты
        invoice_id: ID инвойса
        method: Метод оплаты ("cryptopay" или "cryptomus")
        buttons: Объект с переводами кнопок
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.PAY_INVOICE, url=payment_url)],
        [InlineKeyboardButton(text=buttons.CHECK_STATUS, callback_data=f"check_payment:{method}:{invoice_id}")],
        [InlineKeyboardButton(text=buttons.CANCEL, callback_data=f"cancel_payment:{method}:{invoice_id}")]
    ])


def get_cryptomus_payment_keyboard(payment_url: str, order_id: str, uuid: str, buttons) -> InlineKeyboardMarkup:
    """Клавиатура для оплаты через Cryptomus"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.PAY_WITH_CRYPTO, url=payment_url)],
        [InlineKeyboardButton(text=buttons.CHECK_STATUS, callback_data=f"check_payment:cryptomus:{order_id}:{uuid}")],
        [InlineKeyboardButton(text=buttons.BACK_TO_MENU, callback_data="back_main")]
    ])


def confirm_keyboard(buttons, suffix="") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения
    
    Args:
        buttons: Объект с текстами кнопок
        suffix: Суффикс для callback_data (например, "_ssn", "_phone", "_others")
    """
    confirm_callback = f"confirm_yes{suffix}"
    cancel_callback = f"confirm_no{suffix}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CONFIRM, callback_data=confirm_callback)],
        [InlineKeyboardButton(text=buttons.CANCEL, callback_data=cancel_callback)]
    ])


def order_type_keyboard(service: str, buttons) -> InlineKeyboardMarkup:
    """Клавиатура выбора: Single или Bulk заказ"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.SINGLE_ORDER, callback_data=f"{service}_single")],
        [InlineKeyboardButton(text=buttons.BULK_ORDER_BUTTON, callback_data=f"{service}_bulk")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_lookup" if service.startswith("lookup") else "back_main")]
    ])


def lookup_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура lookup сервисов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=buttons.LOOKUP_SSN_DOB, callback_data="lookup_ssn"),
            InlineKeyboardButton(text=buttons.LOOKUP_CREDIT_SCORE, callback_data="lookup_credit")
        ],
        [
            InlineKeyboardButton(text=buttons.LOOKUP_DL, callback_data="lookup_dl"),
            InlineKeyboardButton(text=buttons.LOOKUP_MVR, callback_data="lookup_mvr"),
            InlineKeyboardButton(text=buttons.LOOKUP_FULL_MVR, callback_data="lookup_fullmvr")
        ],
        [InlineKeyboardButton(text=buttons.LOOKUP_PHONE_SEARCH, callback_data="lookup_phone")],
        [
            InlineKeyboardButton(text=buttons.LOOKUP_BACKGROUND, callback_data="lookup_bg"),
            InlineKeyboardButton(text=buttons.LOOKUP_MMN, callback_data="lookup_mmn"),
            InlineKeyboardButton(text=buttons.LOOKUP_EIN, callback_data="lookup_ein")
        ],
        [InlineKeyboardButton(text=getattr(buttons, "LOOKUP_BANK_ACCOUNTS", "🏦 Bank Account Lookup"), callback_data="lookup_ba")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])


def phone_search_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура поиска по телефону"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.PHONE_NAME_LOOKUP, callback_data="phone_name")],
        [InlineKeyboardButton(text=buttons.PHONE_NAME_DOB_SSN, callback_data="phone_ssn")],
        [InlineKeyboardButton(text=buttons.PHONE_FULL_LOOKUP, callback_data="phone_full")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_lookup")]
    ])


def credit_reports_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура кредитных отчетов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CR_TRANSUNION, callback_data="cr_transunion")],
        [InlineKeyboardButton(text=buttons.CR_EXPERIAN, callback_data="cr_experian")],
        [InlineKeyboardButton(text=buttons.CR_EQUIFAX, callback_data="cr_equifax")],
        [InlineKeyboardButton(text=buttons.CR_LEXISNEXIS, callback_data="cr_lexisnexis")],
        [InlineKeyboardButton(text=buttons.CR_WALLETHUB, callback_data="cr_wallet")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])


def bulk_confirmation_keyboard(buttons, suffix="") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения bulk заказа
    
    Args:
        buttons: Объект с текстами кнопок
        suffix: Суффикс для callback_data (например, "_ssn", "_phone", "_others")
    """
    confirm_callback = f"bulk_confirm{suffix}"
    edit_callback = f"bulk_edit{suffix}" if suffix else "bulk_edit"
    cancel_callback = f"bulk_cancel{suffix}"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CONFIRM_ALL, callback_data=confirm_callback)],
        [InlineKeyboardButton(text=buttons.EDIT, callback_data=edit_callback)],
        [InlineKeyboardButton(text=buttons.CANCEL, callback_data=cancel_callback)]
    ])


def esim_main_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура главного меню eSIM"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.ESIM_SMS, callback_data="esim_sms")],
        [InlineKeyboardButton(text=buttons.ESIM_DATA, callback_data="esim_data")],
        [InlineKeyboardButton(text=getattr(buttons, "ESIM_CONFIGURATOR", "⚙️ eSIM with CS/CR"), callback_data="esim_configurator")],
        [InlineKeyboardButton(text=getattr(buttons, "ESIM_GV", "📞 Google Voice"), callback_data="esim_gv")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])




# ============ SUPPORT KEYBOARDS ============

def support_categories_keyboard(buttons) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории обращения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.SUPPORT_PAYMENT, callback_data="support_category_payment")],
        [InlineKeyboardButton(text=buttons.SUPPORT_PRODUCT, callback_data="support_category_product")],
        [InlineKeyboardButton(text=buttons.SUPPORT_GENERAL, callback_data="support_category_general")],
        [InlineKeyboardButton(text=buttons.SUPPORT_PARTNERSHIP, callback_data="support_category_partnership")],
        [InlineKeyboardButton(text=buttons.MY_TICKETS, callback_data="my_tickets")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
    ])


def my_tickets_keyboard(open_tickets: list, closed_tickets: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком тикетов"""
    from mirror_bot.constants.language_loader import get_buttons
    temp_buttons = get_buttons('ru')  # Support tickets обычно на русском
    
    buttons = []
    
    # Открытые тикеты
    for ticket in open_tickets[:5]:  # Показываем только первые 5
        buttons.append([
            InlineKeyboardButton(
                text=f"🟢 #{ticket.id} - {ticket.subject[:25]}...",
                callback_data=f"ticket_{ticket.id}"
            )
        ])
    
    # Закрытые тикеты
    for ticket in closed_tickets[:5]:  # Показываем только первые 5
        buttons.append([
            InlineKeyboardButton(
                text=f"⚪️ #{ticket.id} - {ticket.subject[:25]}...",
                callback_data=f"ticket_{ticket.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text=temp_buttons.BACK_SUPPORT, callback_data="support")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ticket_detail_keyboard(
    ticket_id: int,
    can_reply: bool = True,
    has_files_option: bool = False,
    is_viewing: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра тикета"""
    from mirror_bot.constants.language_loader import get_buttons
    temp_buttons = get_buttons('ru')  # Support tickets обычно на русском
    
    buttons = []
    
    if can_reply:
        buttons.append([
            InlineKeyboardButton(text=temp_buttons.TICKET_REPLY, callback_data=f"reply_ticket_{ticket_id}")
        ])
    
    if has_files_option:
        buttons.append([
            InlineKeyboardButton(text=temp_buttons.TICKET_ATTACH_FILES, callback_data=f"attach_files_{ticket_id}")
        ])
    
    if is_viewing:
        buttons.append([InlineKeyboardButton(text=temp_buttons.TICKET_BACK_TO_TICKETS, callback_data="my_tickets")])
    else:
        buttons.append([InlineKeyboardButton(text=temp_buttons.BACK_SUPPORT, callback_data="support")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_support_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню поддержки"""
    from mirror_bot.constants.language_loader import get_buttons
    temp_buttons = get_buttons('ru')  # Support tickets обычно на русском
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=temp_buttons.BACK_TO_SUPPORT, callback_data="back_to_support")]
    ])



def bulk_order_keyboard(buttons, bulk_price=None) -> InlineKeyboardMarkup:
    """Кнопка для bulk заказа (цена не отображается на кнопке)"""
    # Всегда используем только текст без цены
    button_text = buttons.BULK_ORDER_BUTTON
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, callback_data="bulk_order")]
    ])
