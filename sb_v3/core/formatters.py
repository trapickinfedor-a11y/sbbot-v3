"""
formatters.py — Wraps formatter.py + Enformion-specific formatters.
This is the unified formatting module used by bot.py.
"""
import csv
import io
import json
from datetime import datetime

# Re-export everything from the original formatter
from formatter import (
    _fmt_people,
    fmt_phone_result, fmt_phone_identify, fmt_phone_verify,
    fmt_address_result, fmt_address_verify, fmt_number_address_result,
    fmt_name_result, fmt_email_result, fmt_email_verify,
    fmt_background, fmt_emailrep,
    fmt_batch_summary, export_csv, export_txt, export_json,
)
from sb_engine import SBResult


def fmt_enformion_result(r: SBResult, query: str) -> str:
    """
    Generic Enformion result formatter.
    Works for both ReversePhoneSearch and PersonSearch responses.
    Shows all available fields: phones, emails, dob, ssn, akas, addresses, relatives, carrier.
    """
    search_type = r.search_type
    icon = "📞" if "phone" in search_type else "🏠" if "ad" in search_type else "🔍"

    if not r.ok:
        err_map = {
            "NO_ACTIVE_ACCOUNTS": "❌ Нет активных аккаунтов Enformion",
            "SESSION_EXPIRED":    "❌ Сессия истекла",
            "BLOCKED":            "⛔ Аккаунт заблокирован",
            "NO_TOKENS":          "❌ Недостаточно токенов",
            "TIMEOUT":            "⏱ Таймаут запроса",
            "EMAIL_SEARCH_UNSUPPORTED": "❌ Email поиск не поддерживается напрямую. Используйте /email_verify для проверки email.",
            "CIRCUIT_OPEN":       "🔧 Circuit breaker открыт, попробуйте позже",
        }
        msg = err_map.get(r.error, f"❌ Ошибка: `{r.error}`")
        return f"{icon} *Результат*\n" + msg

    if r.parsed.get("message") == "No results found":
        return f"{icon} *Результат*\n\n🔍 Результатов не найдено"

    if r.people:
        lines = [f"{icon} *Результат* — найдено *{len(r.people)}* записей\n"]
        for i, p in enumerate(r.people[:10], 1):
            lines.append(f"*#{i}*")
            name = p.get("name", "")
            if name:
                lines.append(f"  👤 {name}")
            age = p.get("age", 0)
            dob = p.get("date_of_birth", "")
            if age:
                lines.append(f"  🎂 Возраст: {age}" + (f" (DOB: {dob})" if dob else ""))
            elif dob:
                lines.append(f"  🎂 DOB: {dob}")
            # All phones
            phones = p.get("phones", [])
            if phones:
                for ph in phones[:5]:
                    parts = [f"  📱 {ph.get('phone', '')}"]
                    if ph.get("phoneType"):
                        parts.append(f"    Тип: {ph['phoneType']}")
                    if ph.get("carrier"):
                        parts.append(f"    Оператор: {ph['carrier']}")
                    lines.append("\n".join(parts))
            elif p.get("phone"):
                lines.append(f"  📱 {p['phone']}")
            # Carrier / phone type at person level
            if p.get("carrier") and not phones:
                lines.append(f"  📶 Оператор: {p['carrier']}")
            if p.get("phone_type") and not phones:
                lines.append(f"  📡 Тип номера: {p['phone_type']}")
            # Location
            loc = p.get("location", "")
            if loc:
                lines.append(f"  📍 {loc}")
            # Address
            addr = p.get("address", "")
            if addr:
                lines.append(f"  🏠 {addr}")
            if not addr and p.get("addresses"):
                for a in p["addresses"][:3]:
                    lines.append(f"  🏠 {a}")
            # Historical addresses
            hist = p.get("addresses", [])
            if len(hist) > 1:
                lines.append(f"  📜 История адресов ({len(hist)}):")
                for a in hist[1:4]:
                    lines.append(f"    • {a}")
            # Emails
            emails = p.get("emails", [])
            if emails:
                lines.append(f"  📧 {', '.join(emails[:3])}")
            elif p.get("email"):
                lines.append(f"  📧 {p['email']}")
            # SSN
            ssn = p.get("ssn", "")
            if ssn:
                lines.append(f"  🔢 SSN: {ssn}")
            # AKAs
            akas = p.get("akas", [])
            if akas:
                lines.append(f"  👤 AKA: {', '.join(akas[:3])}")
            # VOIP
            voip = p.get("voip")
            if voip is not None:
                lines.append(f"  📡 VOIP: {'Да' if voip else 'Нет'}")
            # Connected to
            conn = p.get("connected_to", "")
            if conn:
                lines.append(f"  🔗 Связан с: {conn}")
            # Relatives
            rel = p.get("relatives", "")
            if rel:
                lines.append(f"  👨‍👩‍👧 {rel[:120]}")
            lines.append("")
        if len(r.people) > 10:
            lines.append(f"_...ещё {len(r.people)-10} записей — скачайте файл для полного экспорта_")
    elif r.parsed:
        lines = [f"{icon} *Результат*\n\n"]
        raw = r.parsed.get("raw", "")
        if raw:
            lines.append(f"```\n{raw[:800]}\n```")
        else:
            lines.append(f"```\n{json.dumps(r.parsed, indent=2, ensure_ascii=False)[:800]}\n```")

    return "\n".join(lines)


def fmt_phone_identify(r: SBResult, query: str) -> str:
    """Phone identify via dedicated IdentifyPhoneType endpoint."""
    lines = [f"📡 *Phone Identify* — `{query}`\n"]
    if not r.ok:
        err_map = {
            "NO_ACTIVE_ACCOUNTS": "❌ Нет активных аккаунтов",
            "BLOCKED": "⛔ Аккаунт заблокирован",
            "NO_TOKENS": "❌ Недостаточно токенов",
            "TIMEOUT": "⏱ Таймаут",
            "CIRCUIT_OPEN": "🔧 Сервис временно недоступен",
        }
        msg = err_map.get(r.error, f"❌ `{r.error}`")
        return lines[0] + msg

    # Try people first (Enformion returns people for phone_identify)
    if r.people:
        for i, p in enumerate(r.people[:5], 1):
            lines.append(f"*#{i}*")
            # Phone details
            phones = p.get("phones", [])
            if phones:
                for ph in phones[:3]:
                    phone_str = ph.get("phone", "") if isinstance(ph, dict) else str(ph)
                    lines.append(f"  📱 {phone_str}")
                    if isinstance(ph, dict):
                        if ph.get("phoneType"):
                            icon = "📱" if ph["phoneType"].lower() == "mobile" else "📞"
                            lines.append(f"    {icon} Тип: *{ph['phoneType']}*")
                        if ph.get("carrier"):
                            lines.append(f"    📶 Оператор: {ph['carrier']}")
                        if ph.get("location"):
                            lines.append(f"    📍 {ph['location']}")
            elif p.get("phone"):
                lines.append(f"  📱 {p['phone']}")
            if p.get("carrier") and not phones:
                lines.append(f"  📶 Оператор: {p['carrier']}")
            if p.get("phone_type") and not phones:
                lines.append(f"  📡 Тип номера: {p['phone_type']}")
            loc = p.get("location", "")
            if loc:
                lines.append(f"  📍 {loc}")
            voip = p.get("voip")
            if voip is not None:
                lines.append(f"  📡 VOIP: {'Да' if voip else 'Нет'}")
            if p.get("name"):
                lines.append(f"  👤 {p['name']}")
            lines.append("")
        return "\n".join(lines)

    # Fallback to parsed raw
    if r.parsed:
        if r.parsed.get("message") == "No results found":
            return lines[0] + "🔍 Номер не идентифицирован"
        raw = r.parsed.get("raw", "")
        if raw:
            lines.append(f"```\n{raw[:600]}\n```")
    return "\n".join(lines)


def fmt_phone_verify(r: SBResult, query: str) -> str:
    """Phone verify via dedicated VerifyPhone endpoint."""
    lines = [f"✅ *Phone Verify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    if r.people:
        names = [p.get("name", "") for p in r.people[:3] if p.get("name")]
        if names:
            lines.append(f"✅ Номер АКТИВЕН — связан с: {', '.join(names)}")
        else:
            lines.append(f"✅ Номер АКТИВЕН — найдено {len(r.people)} записей")
        # Show phone details
        for p in r.people[:3]:
            phone = p.get("phone", "")
            loc = p.get("location", "")
            if phone:
                lines.append(f"  📱 {phone}" + (f" — {loc}" if loc else ""))
    else:
        lines.append("❌ Номер НЕАКТИВЕН или не найден")
    return "\n".join(lines)


def fmt_address_verify(r: SBResult, query: str) -> str:
    """Address verify via PersonSearch."""
    lines = [f"📍 *Address Verify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    if r.people:
        addrs = []
        for p in r.people:
            for a in p.get("addresses", []):
                if a not in addrs:
                    addrs.append(a)
        if addrs:
            lines.append(f"✅ Найдено адресов: {len(addrs)}\n")
            for i, a in enumerate(addrs[:5], 1):
                lines.append(f"  {i}. {a}")
        else:
            names = [p.get("name", "") for p in r.people[:3] if p.get("name")]
            lines.append(f"✅ Найдено {len(r.people)} записей\n")
            if names:
                lines.append(f"Связанные имена: {', '.join(names)}")
        # Show DOB / SSN if available
        for p in r.people[:2]:
            dob = p.get("date_of_birth", "")
            ssn = p.get("ssn", "")
            if dob:
                lines.append(f"  🎂 DOB: {dob}")
            if ssn:
                lines.append(f"  🔢 SSN: {ssn}")
    else:
        lines.append("❌ Не найдено")
    return "\n".join(lines)


def fmt_email_verify(r: SBResult, query: str) -> str:
    """Email verify via Enformion/PersonSearch."""
    lines = [f"📧 *Email Verify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    if r.people:
        lines.append(f"✅ Найдено {len(r.people)} связанных записей\n")
        for i, p in enumerate(r.people[:5], 1):
            name = p.get("name", "Unknown")
            age = p.get("age", 0)
            dob = p.get("date_of_birth", "")
            phones = p.get("phones", [])
            phone_str = phones[0].get("phone", "") if phones else p.get("phone", "")
            parts = [f"  {i}. {name}"]
            if age:
                parts.append(f"(Age {age})")
            elif dob:
                parts.append(f"(DOB: {dob})")
            if phone_str:
                parts.append(f"📱{phone_str}")
            lines.append(" ".join(parts))
    else:
        lines.append("❌ Не найдено")
    return "\n".join(lines)
