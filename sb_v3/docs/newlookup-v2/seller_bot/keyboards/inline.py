from __future__ import annotations

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from shared.utils.seller_product_meta import bank_item_badge, cc_item_badge


def _seller_mini_app_url(conv_id: int | None = None) -> str | None:
    base_url = (os.getenv("SELLER_MINI_APP_URL") or "").strip()
    if not base_url:
        return None
    if not conv_id:
        return base_url
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["conv_id"] = str(conv_id)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English", callback_data="seller_lang:en")],
        [InlineKeyboardButton(text="Русский", callback_data="seller_lang:ru")],
        [InlineKeyboardButton(text="中文", callback_data="seller_lang:zh")],
        [InlineKeyboardButton(text="Español", callback_data="seller_lang:es")],
    ])


def rules_accept_keyboard(buttons=None) -> InlineKeyboardMarkup:
    buttons = buttons or type("RuleButtons", (), {
        "ACCEPT_RULES": "✅ Accept",
        "DECLINE_RULES": "❌ Decline",
    })
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=buttons.ACCEPT_RULES, callback_data="seller_rules_accept"),
            InlineKeyboardButton(text=buttons.DECLINE_RULES, callback_data="seller_rules_decline"),
        ]
    ])


def seller_main_menu(
    unread_count: int = 0,
    buttons=None,
    actor_role: str | None = None,
    is_on_vacation: bool = False,
) -> InlineKeyboardMarkup:
    buttons = buttons or type("DefaultButtons", (), {
        "MY_BANKS": "🏦 My Banks",
        "UNIVERSAL_UPLOAD": "⬆️ Universal Upload",
        "ADD_BANK": "➕ Add Bank / Enrol",
        "MY_UPLOADS": "🗂 My Uploads",
        "MY_CC": "💳 My CC Items",
        "ADD_CC": "➕ Add CC Item",
        "ADD_NFC": "📱 Add NFC",
        "ADD_OTP": "📲 Add OTP Card",
        "ADD_SELFREG_CC": "💳 Add Selfreg CC",
        "ADD_CHECK": "🖊 Add Check",
        "BRUTE_BANK": "🔓 Brute Bank",
        "MY_ORDERS": "📦 My Orders",
        "MESSAGES": "💬 Messages",
        "MINI_APP": "🖥 Mini App",
        "WITHDRAW": "💸 Withdraw",
        "LEAVE_SYSTEM": "🚪 Leave System",
        "HELPERS": "👥 Helpers",
        "PROFILE": "👤 Profile",
        "VACATION_ON": "🏖 Enable Vacation Mode",
        "VACATION_OFF": "🔔 Disable Vacation Mode",
        "MY_LISTINGS": "📋 My Listings",
    })
    msg_text = f"{buttons.MESSAGES} ({unread_count})" if unread_count > 0 else buttons.MESSAGES
    vacation_text = getattr(buttons, "VACATION_OFF", "🔔 Disable Vacation") if is_on_vacation else getattr(buttons, "VACATION_ON", "🏖 Enable Vacation")
    rows = [
        [InlineKeyboardButton(text=buttons.MY_BANKS, callback_data="seller_my_banks")],
        [InlineKeyboardButton(text=getattr(buttons, "UNIVERSAL_UPLOAD", "⬆️ Universal Upload"), callback_data="seller_upload_product")],
        [InlineKeyboardButton(text=buttons.ADD_BANK, callback_data="seller_add_bank")],
        [InlineKeyboardButton(text=buttons.MY_UPLOADS, callback_data="seller_uploads")],
        [InlineKeyboardButton(text=buttons.MY_CC, callback_data="seller_my_cc")],
        [InlineKeyboardButton(text=buttons.ADD_CC, callback_data="seller_add_cc")],
        [InlineKeyboardButton(text=getattr(buttons, "ADD_NFC", "📱 Add NFC"), callback_data="seller_add_nfc")],
        [InlineKeyboardButton(text=getattr(buttons, "ADD_OTP", "📲 Add OTP Card"), callback_data="seller_add_otp")],
        [InlineKeyboardButton(text=getattr(buttons, "ADD_SELFREG_CC", "💳 Add Selfreg CC"), callback_data="seller_add_selfreg_cc")],
        [InlineKeyboardButton(text=getattr(buttons, "ADD_ENROLL", "🏦 Add Enroll"), callback_data="seller_add_enroll")],
        [InlineKeyboardButton(text=getattr(buttons, "ADD_CHECK", "🖊 Add Check"), callback_data="seller_add_check")],
        [InlineKeyboardButton(text=buttons.BRUTE_BANK, callback_data="seller_brute_bank")],
        [InlineKeyboardButton(text=getattr(buttons, "MY_LISTINGS", "📋 My Listings"), callback_data="seller_my_listings")],
        [InlineKeyboardButton(text=buttons.MY_ORDERS, callback_data="seller_orders")],
        [InlineKeyboardButton(text=msg_text, callback_data="seller_messages")],
        [InlineKeyboardButton(text=vacation_text, callback_data="seller_vacation_toggle")],
    ]
    mini_app_url = _seller_mini_app_url()
    if mini_app_url:
        rows.append([InlineKeyboardButton(text=buttons.MINI_APP, web_app=WebAppInfo(url=mini_app_url))])
    if actor_role in (None, "owner"):
        rows.append([InlineKeyboardButton(text=getattr(buttons, "HELPERS", "👥 Helpers"), callback_data="seller_helpers")])
        rows.append([InlineKeyboardButton(text=getattr(buttons, "ADD_SELLER", "👤 Add Seller"), callback_data="seller_add_seller")])
        rows.append([InlineKeyboardButton(text=getattr(buttons, "BUY_ACCESS", "🔓 Buy Access"), callback_data="seller_buy_access")])
        rows.append([InlineKeyboardButton(text=buttons.WITHDRAW, callback_data="seller_withdraw")])
        rows.append([InlineKeyboardButton(text=getattr(buttons, "LEAVE_SYSTEM", "🚪 Leave System"), callback_data="seller_leave_system")])
    rows.append([InlineKeyboardButton(text=buttons.PROFILE, callback_data="seller_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def seller_bank_list(banks: list) -> InlineKeyboardMarkup:
    buttons = []
    for bank in banks:
        stock_icon = "✅" if bank.is_in_stock else "❌"
        badge = bank_item_badge(getattr(bank, "product_type", "bank"), getattr(bank, "product_subtype", "log"))
        buttons.append([
            InlineKeyboardButton(
                text=f"{stock_icon} {bank.bank_name} [{badge}] | ${bank.seller_price} | qty {bank.stock_count}",
                callback_data=f"seller_bank:{bank.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Add Bank / Enrol", callback_data="seller_add_bank")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def seller_bank_detail(bank_id: int, is_in_stock: bool) -> InlineKeyboardMarkup:
    toggle_text = "❌ Set Out of Stock" if is_in_stock else "✅ Set In Stock"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"seller_toggle:{bank_id}")],
        [InlineKeyboardButton(text="📦 Change Qty", callback_data=f"seller_qty:{bank_id}")],
        [InlineKeyboardButton(text="💰 Change Price", callback_data=f"seller_price:{bank_id}")],
        [InlineKeyboardButton(text="🗑 Delete", callback_data=f"seller_delete:{bank_id}")],
        [InlineKeyboardButton(text="⬅️ Back to My Banks", callback_data="seller_my_banks")]
    ])


def category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 VCC", callback_data="seller_cat:vcc")],
        [InlineKeyboardButton(text="🏦 Personal Bank", callback_data="seller_cat:personal")],
        [InlineKeyboardButton(text="🏢 Business Bank", callback_data="seller_cat:business")],
        [InlineKeyboardButton(text="💸 Crypto", callback_data="seller_cat:crypto")],
        [InlineKeyboardButton(text="🏪 Merchant", callback_data="seller_cat:merchant")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")]
    ])


def bank_product_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Bank", callback_data="seller_product_type:bank")],
        [InlineKeyboardButton(text="🪪 Enrol", callback_data="seller_product_type:enrol")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def bank_product_subtype_keyboard(product_type: str) -> InlineKeyboardMarkup:
    if product_type == "enrol":
        rows = [[InlineKeyboardButton(text="🪪 Selfreg", callback_data="seller_product_subtype:selfreg")]]
    else:
        rows = [
            [InlineKeyboardButton(text="📝 Log", callback_data="seller_product_subtype:log")],
            [InlineKeyboardButton(text="🧾 Selfreg", callback_data="seller_product_subtype:selfreg")],
            [InlineKeyboardButton(text="🔓 Brute", callback_data="seller_product_subtype:brute")],
        ]
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def add_mode_keyboard() -> InlineKeyboardMarkup:
    """Add to existing type vs Request new vs Create new type"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Add to existing type", callback_data="seller_add_mode:existing")],
        [InlineKeyboardButton(text="📝 Request new bank", callback_data="seller_add_mode:request")],
        [InlineKeyboardButton(text="🆕 Create new type", callback_data="seller_add_mode:new")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")]
    ])


def bank_type_keyboard(bank_types: list, category: str) -> InlineKeyboardMarkup:
    """Bank types for Add to existing - paginated if many"""
    buttons = []
    for bt in bank_types[:15]:  # max 15 to fit
        buttons.append([
            InlineKeyboardButton(text=bt["name"], callback_data=f"seller_bank_type:{category}:{bt['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_add_bank")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def support_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 With Seller Chat", callback_data="seller_support_mode:chat")],
        [InlineKeyboardButton(text="🚫 No Support Chat", callback_data="seller_support_mode:nochat")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def bank_number_access_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Number Access Included", callback_data="seller_bank_number_access:yes")],
        [InlineKeyboardButton(text="❌ No Number Access", callback_data="seller_bank_number_access:no")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def bank_number_change_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Number Change Allowed", callback_data="seller_bank_number_change:yes")],
        [InlineKeyboardButton(text="🚫 Number Change Not Allowed", callback_data="seller_bank_number_change:no")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def bank_auto_unpublish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Auto Unpublish by Days", callback_data="seller_bank_auto_unpublish:yes")],
        [InlineKeyboardButton(text="♾ Keep Active", callback_data="seller_bank_auto_unpublish:no")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def cc_category_keyboard(categories: list) -> InlineKeyboardMarkup:
    """CC categories for Add CC"""
    buttons = [[InlineKeyboardButton(text=c["name"], callback_data=f"seller_cc_cat:{c['code']}")] for c in categories]
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cc_non_vbv_keyboard() -> InlineKeyboardMarkup:
    """Ask seller: is this batch NON-VBV?"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Yes — NON-VBV", callback_data="seller_cc_non_vbv:yes")],
        [InlineKeyboardButton(text="💳 No — Regular", callback_data="seller_cc_non_vbv:no")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def cc_type_keyboard(cc_types: list, category_code: str) -> InlineKeyboardMarkup:
    """CC types for Add to existing"""
    buttons = [[InlineKeyboardButton(text=t["name"], callback_data=f"seller_cc_type:{category_code}:{t['id']}")] for t in cc_types[:15]]
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_add_cc")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def seller_cc_list(items: list) -> InlineKeyboardMarkup:
    """List of seller CC items"""
    buttons = []
    for item in items:
        status = "✅" if item.moderation_status == "approved" else "⏳" if item.moderation_status == "pending_moderation" else "❌"
        badge = cc_item_badge(getattr(item, "product_subtype", "with_fullz"))
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {item.item_name} [{badge}] | ${item.seller_price}",
                callback_data=f"seller_cc_item:{item.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="➕ Add CC Item", callback_data="seller_add_cc")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_delete_keyboard(bank_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, delete", callback_data=f"seller_confirm_del:{bank_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"seller_bank:{bank_id}")
        ]
    ])


def seller_order_keyboard(order_id: int, has_chat: bool = True) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Complete Order", callback_data=f"seller_complete:{order_id}")],
    ]
    if has_chat:
        buttons.append([InlineKeyboardButton(text="💬 Chat with Buyer", callback_data=f"seller_chat:{order_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def seller_orders_list(orders: list) -> InlineKeyboardMarkup:
    buttons = []
    status_icon = {
        "approved": "🟡",
        "in_progress": "🔵",
        "completed": "✅",
        "rejected": "❌",
        "cancelled": "⚪",
        "pending_admin": "⏳"
    }
    status_short = {
        "approved": "Wait",
        "in_progress": "Work",
        "completed": "Done",
        "rejected": "Rej",
        "cancelled": "Canc",
        "pending_admin": "Pending"
    }
    for order in orders:
        icon = status_icon.get(order.status, "❓")
        short = status_short.get(order.status, order.status[:4])
        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} #{order.id} | ${order.price_for_seller:.0f} | {short}",
                callback_data=f"seller_order:{order.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_approval_keyboard(seller_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_seller:{seller_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_seller:{seller_id}")
        ]
    ])


def admin_order_approval_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_order:{order_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_order:{order_id}")
        ]
    ])


def chat_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ End Chat", callback_data=f"seller_end_chat:{order_id}")]
    ])


def seller_helpers_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Helper", callback_data="seller_helper_add")],
        [InlineKeyboardButton(text="👥 Active Helpers", callback_data="seller_helpers_active")],
        [InlineKeyboardButton(text="🕓 Pending Invites", callback_data="seller_helpers_pending")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")],
    ])


def seller_helper_role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Upload Helper", callback_data="seller_helper_role:upload_helper")],
        [InlineKeyboardButton(text="💬 Support Helper", callback_data="seller_helper_role:support_helper")],
        [InlineKeyboardButton(text="🧩 Manager Helper", callback_data="seller_helper_role:manager_helper")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_helpers")],
    ])


def seller_helpers_list_keyboard(helpers: list, list_type: str = "active") -> InlineKeyboardMarkup:
    rows = []
    for helper in helpers:
        label = helper.display_name or helper.username or str(helper.telegram_id)
        rows.append([
            InlineKeyboardButton(
                text=f"{label} | {helper.role} | {helper.status}",
                callback_data=f"seller_helper:{helper.id}",
            )
        ])
    back_target = "seller_helpers_pending" if list_type == "pending" else "seller_helpers"
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=back_target)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def seller_helper_detail_keyboard(helper_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧩 Change Role", callback_data=f"seller_helper_change_role:{helper_id}")],
        [InlineKeyboardButton(text="⛔ Block", callback_data=f"seller_helper_block:{helper_id}")],
        [InlineKeyboardButton(text="🗑 Remove", callback_data=f"seller_helper_remove:{helper_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_helpers_active")],
    ])


def seller_helper_accept_keyboard(helper_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Accept Invite", callback_data=f"seller_helper_accept:{helper_id}")],
    ])
