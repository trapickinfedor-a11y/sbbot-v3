from __future__ import annotations

from decimal import Decimal


def _bool_badge(value) -> str:
    return "yes" if bool(value) else "no"


def _flag(country_code) -> str:
    code = str(country_code or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(127397 + ord(char)) for char in code)


def _money(value) -> str:
    amount = Decimal(str(value or 0))
    return f"${amount:,.2f}".rstrip("0").rstrip(".")


def _yes_no_emoji(value) -> str:
    return "✅" if bool(value) else "❌"


def _price_value(item) -> float:
    value = (
        getattr(item, "price", None)
        or getattr(item, "seller_price", None)
        or getattr(item, "buyer_price", None)
        or 0
    )
    return float(value or 0)


def render_cc_description(item) -> str:
    extra = getattr(item, "extra_data", None) or {}
    card_brand = getattr(item, "card_brand", None) or extra.get("brand") or "CC"
    card_level = extra.get("level") or getattr(item, "card_level", None) or getattr(item, "item_name", None) or ""
    card_type  = extra.get("card_type") or ""   # DEBIT / CREDIT
    bank_name  = getattr(item, "bank_name", None) or extra.get("bank") or "—"
    country    = getattr(item, "country", None) or extra.get("country") or "—"
    state      = getattr(item, "state", None) or extra.get("state") or "—"
    city       = getattr(item, "city", None) or extra.get("city") or "—"
    zip_code   = getattr(item, "zip", None) or extra.get("zip") or "—"
    address    = getattr(item, "address", None) or extra.get("address") or "—"
    number     = getattr(item, "number", None) or ""
    bin_val    = extra.get("bin") or (number[:6] if len(number) >= 6 else number) or "—"
    exp        = extra.get("exp") or "—"
    holder     = extra.get("holder") or ""
    if not holder:
        fname = getattr(item, "fname", None) or ""
        lname = getattr(item, "lname", None) or ""
        holder = " ".join(p for p in [fname, lname] if p) or "—"
    phone  = extra.get("phone") or "—"
    email  = extra.get("email") or "—"
    ssn    = extra.get("ssn") or "—"
    dob    = extra.get("dob") or "—"
    dl     = extra.get("dl") or "—"
    non_vbv = _yes_no_emoji(getattr(item, "is_non_vbv", False))
    country_with_flag = f"{_flag(country)} {country}".strip()
    type_level = " ".join(p for p in [card_type, card_level] if p) or card_brand

    lines = [
        f"💳 <b>{card_brand}</b> {bin_val} — {bank_name}",
        f"━━━━━━━━━━━━━━━━━━━",
        f"BIN: {bin_val} | Exp: {exp}",
        f"Type: {type_level} | NON-VBV: {non_vbv}",
        f"Country: {country_with_flag} | State: {state} | ZIP: {zip_code}",
    ]
    if address != "—":
        lines.append(f"Address: {address}, {city}")
    if holder != "—":
        lines.append(f"Holder: {holder}")
    if phone != "—":
        lines.append(f"Phone: {phone}")
    if email != "—":
        lines.append(f"Email: {email}")
    if ssn != "—":
        lines.append(f"SSN: {ssn}")
    if dob != "—":
        lines.append(f"DOB: {dob}")
    info = extra.get("info") or ""
    ref  = extra.get("ref") or ""
    if info:
        lines.append(f"Info: {info}")
    if ref:
        lines.append(f"Ref: {ref}")
    lines.append("━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def render_brute_description(item) -> str:
    return (
        f"🔓 {getattr(item, 'bank_name', 'Bank')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Balance: {getattr(item, 'balance_info', None) or '—'}\n"
        f"State: {getattr(item, 'state', None) or '—'}\n"
        f"Login: {_bool_badge((getattr(item, 'credentials', {}) or {}).get('login'))} | "
        f"Routing: {_bool_badge(getattr(item, 'routing_number', None))} | "
        f"Name: {_bool_badge(getattr(item, 'holder_name', None))}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )


def render_bank_description(bank) -> str:
    details = getattr(bank, "details", None) or {}
    details_format = details.get("format")
    sample = details.get("sample", {}) or {}
    if details_format == "logs":
        return (
            f"📋 {getattr(bank, 'bank_name', 'Logs')}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Balance: {sample.get('balance') or '—'}\n"
            f"State: {sample.get('state') or getattr(bank, 'state', None) or '—'}\n"
            f"Login: {_bool_badge(sample.get('login'))} | Cookies: {_bool_badge(sample.get('cookies'))}\n"
            f"Routing: {_bool_badge(sample.get('routing_number'))} | Name: {_bool_badge(sample.get('holder_name'))}\n"
            f"Qty: {details.get('rows_count') or getattr(bank, 'stock_count', 0) or 1}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
    if details_format == "selfreg_ba":
        return (
            f"🏦 {getattr(bank, 'bank_name', 'Selfreg BA')}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Balance: {sample.get('balance') or '—'}\n"
            f"State: {sample.get('state') or getattr(bank, 'state', None) or '—'} | ZIP: {sample.get('zip') or getattr(bank, 'zip', None) or '—'}\n"
            f"Login: {_bool_badge(sample.get('login'))} | Routing: {_bool_badge(sample.get('routing_number'))} | Name: {_bool_badge(sample.get('holder_name'))}\n"
            f"Account: {_bool_badge(sample.get('account_number'))} | Address: {_bool_badge(sample.get('holder_address'))}\n"
            f"Qty: {details.get('rows_count') or getattr(bank, 'stock_count', 0) or 1}\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
    parts = [
        f"🏦 {getattr(bank, 'bank_name', 'Bank')}",
        "━━━━━━━━━━━━━━━━━━━",
    ]
    if getattr(bank, "portal", None):
        parts.append(f"Portal: {bank.portal}")
    if getattr(bank, "card_type", None):
        parts.append(f"Card Type: {bank.card_type}")
    if getattr(bank, "state", None) or getattr(bank, "zip", None):
        parts.append(f"State: {getattr(bank, 'state', '—')} | ZIP: {getattr(bank, 'zip', '—')}")
    if getattr(bank, "details", None):
        details = bank.details or {}
        for account in details.get("accounts", []):
            parts.append(f"{account.get('type', 'Account')}: ${account.get('balance', 0)}")
        flags = details.get("flags", {})
        if flags:
            parts.append("Flags: " + ", ".join(f"{key}={'✅' if value else '❌'}" for key, value in flags.items()))
    else:
        parts.append(f"Description: {getattr(bank, 'description', None) or '—'}")
    parts.append("━━━━━━━━━━━━━━━━━━━")
    return "\n".join(parts)


def render_nfc_description(item) -> str:
    nfc_type = "Apple Pay" if getattr(item, "nfc_type", "") == "ap" else "Google Pay"
    country = getattr(item, "country", None) or "—"
    country_with_flag = f"{_flag(country)} {country}".strip()
    return (
        f"📱 {nfc_type} — {getattr(item, 'bank_name', 'Bank')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Country: {country_with_flag}\n"
        f"State: {getattr(item, 'state', None) or '—'} | ZIP: {getattr(item, 'zip', None) or '—'}\n"
        f"Archive: {_bool_badge(getattr(item, 'data_file_path', None))}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )


def render_otp_description(item) -> str:
    description = getattr(item, "description", None) or getattr(item, "seller_description", None)
    return (
        f"📲 OTP | {getattr(item, 'bank_name', 'Bank')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Balance: {_money(getattr(item, 'balance', 0))}\n"
        f"Fullz: {_yes_no_emoji(getattr(item, 'has_fullz', False))}\n"
        f"SMS access: {getattr(item, 'sms_access_type', None) or '—'}\n"
        f"Notes: {description or '—'}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )


def render_enroll_description(item) -> str:
    portal = getattr(item, "portal", None) or getattr(item, "bank_name", None) or "N/A"
    balance = getattr(item, "balance", None) or 0
    lines = [
        f"🔐 <b>Enroll</b> | {portal} | <b>{_money(balance)}</b>",
        "",
        f"📋 SSN: {_bool_badge(getattr(item, 'has_ssn', False))}  |  DOB: {_bool_badge(getattr(item, 'has_dob', False))}",
        f"🏠 Address: {_bool_badge(getattr(item, 'has_address', False))}  |  Docs: {_bool_badge(getattr(item, 'has_docs', False))}",
        f"🌐 Online Access: {_bool_badge(getattr(item, 'online_access', False))}",
        "",
        f"💰 Price: <b>${_price_value(item):.2f}</b>",
    ]
    return "\n".join(lines)


def render_selfreg_ba_description(item) -> str:
    phone_days = getattr(item, "phone_days_remaining", None)
    phone_info = f"✅ Active — {phone_days} days left" if phone_days else "❌"
    bank = getattr(item, "bank", None) or getattr(item, "bank_name", None) or "N/A"
    balance = getattr(item, "balance", None) or 0
    lines = [
        f"🏦 <b>{bank} Bank — Selfreg Account</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"Balance: {_money(balance)} | State: {getattr(item, 'state', None) or 'N/A'} | ZIP: {getattr(item, 'zip', None) or '—'}",
        "━━━━━━━━━━━━━━━━━━━",
        "",
        f"📱 Phone: {phone_info}",
        f"📧 Email: {_yes_no_emoji(getattr(item, 'email_access', False) or getattr(item, 'has_email', False))}",
        f"SSN: {_yes_no_emoji(getattr(item, 'has_ssn', False))} | Docs: {_yes_no_emoji(getattr(item, 'has_docs', False))}",
        "",
        "━━━━━━━━━━━━━━━━━━━",
        f"💰 Price: <b>{_money(_price_value(item))}</b>",
    ]
    return "\n".join(lines)


def render_logs_description(item) -> str:
    flags = []
    if getattr(item, "has_cvv", False):
        flags.append("CVV")
    if getattr(item, "bt_available", False):
        flags.append("BT")
    if getattr(item, "promo_available", False):
        flags.append("Promo")
    if getattr(item, "zelle_enroll", False):
        flags.append("Zelle")
    if getattr(item, "wire_available", False):
        flags.append("Wire")
    if getattr(item, "safepass_unlocked", False):
        flags.append("SafePass")

    bank = getattr(item, "bank", None) or getattr(item, "bank_name", None) or "N/A"
    total_balance = getattr(item, "total_balance", None) or getattr(item, "balance", None) or 0
    lines = [
        f"📋 <b>{bank} — Bank Log</b>",
        "━━━━━━━━━━━━━━━━━━━",
        f"💰 Total balance: {_money(total_balance)}",
        "",
        f"🏷 Flags: {' | '.join(flags) if flags else 'None'}",
        f"📧 Email Valid: {_yes_no_emoji(getattr(item, 'email_valid', False))}",
        f"🍪 Cookies: {_yes_no_emoji(getattr(item, 'has_cookies', False))}  |  Screenshot: {_yes_no_emoji(getattr(item, 'has_screenshot', False))}",
        "",
        "━━━━━━━━━━━━━━━━━━━",
        f"💰 Price: <b>{_money(_price_value(item))}</b>",
    ]
    return "\n".join(lines)


def render_selfreg_cc_description(item) -> str:
    card_name = getattr(item, "card_name", None) or "Selfreg CC"
    vcc_limit = getattr(item, "vcc_limit", None)
    return (
        f"💳 {getattr(item, 'bank_name', 'Selfreg CC')} — {card_name}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Credit Limit: {_money(getattr(item, 'credit_limit', 0) or 0)}\n"
        f"VCC Limit: {_money(vcc_limit) if vcc_limit is not None else '—'} | "
        f"State: {getattr(item, 'state', None) or '—'} | ZIP: {getattr(item, 'zip', None) or '—'}\n"
        f"Email: {_yes_no_emoji(getattr(item, 'has_email', False))} | "
        f"Phone: {_yes_no_emoji(getattr(item, 'has_phone', False))} | "
        f"Online Access: {_yes_no_emoji(getattr(item, 'online_access', False))}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )


def render_check_description(item) -> str:
    status = getattr(item, "status", None) or getattr(item, "seller_status", None) or "—"
    return (
        f"🖊 {getattr(item, 'bank_name', 'Check')} {str(getattr(item, 'check_type', '')).title()} Check\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Amount: {_money(getattr(item, 'amount', 0) or 0)}\n"
        f"State: {getattr(item, 'state', None) or '—'} | ZIP: {getattr(item, 'zip', None) or '—'}\n"
        f"Holder: {_yes_no_emoji(getattr(item, 'has_holder_name', False))} | Address: {_yes_no_emoji(getattr(item, 'has_address', False))}\n"
        f"Status: {status}\n"
        f"Scan: {_bool_badge(getattr(item, 'scan_file_path', None))} | Template: {_bool_badge(getattr(item, 'template_file_path', None))}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
