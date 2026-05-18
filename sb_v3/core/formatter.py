"""
Formatter v2 — pretty-print SearchBug results for Telegram + export
"""
import csv
import io
import json
from datetime import datetime
from sb_engine import SBResult


# ── People result (shared by phone / address / name / email / number_address) ──

def _fmt_people(r: SBResult, header: str) -> str:
    lines = [header]
    if not r.ok:
        err_map = {
            "NO_ACTIVE_ACCOUNTS": "❌ Нет активных аккаунтов SearchBug",
            "SESSION_EXPIRED":    "❌ Сессия истекла",
            "BLOCKED":            "⛔ Аккаунт заблокирован",
            "NO_TOKENS":          "❌ Недостаточно токенов",
            "TIMEOUT":            "⏱ Таймаут запроса",
        }
        msg = err_map.get(r.error, f"❌ Ошибка: `{r.error}`")
        return lines[0] + "\n" + msg

    if r.parsed.get("message") == "No results found":
        return lines[0] + "\n🔍 Результатов не найдено"

    if r.people:
        lines.append(f"✅ Найдено *{len(r.people)}* записей\n")
        for i, p in enumerate(r.people[:10], 1):
            lines.append(f"*#{i}*")
            if p.get("name"):      lines.append(f"  👤 {p['name']}")
            if p.get("address"):   lines.append(f"  🏠 {p['address']}")
            if p.get("phone"):     lines.append(f"  📱 {p['phone']}")
            if p.get("age"):       lines.append(f"  🎂 Возраст: {p['age']}")
            if p.get("email"):     lines.append(f"  📧 {p['email']}")
            if p.get("relatives"): lines.append(f"  👨‍👩‍👧 {p['relatives'][:80]}")
            if p.get("raw") and not any(p.get(k) for k in ("name","address","phone")):
                lines.append(f"  📄 {p['raw'][:250]}")
            lines.append("")
        if len(r.people) > 10:
            lines.append(f"_...ещё {len(r.people)-10} записей — скачайте файл_")
    elif r.parsed:
        lines.append(f"```\n{json.dumps(r.parsed, indent=2, ensure_ascii=False)[:600]}\n```")

    return "\n".join(lines)


def fmt_phone_result(r: SBResult, query: str) -> str:
    return _fmt_people(r, f"📞 *Phone Lookup* — `{query}`\n")


def fmt_address_result(r: SBResult, query: str) -> str:
    return _fmt_people(r, f"🏠 *Address Lookup* — `{query}`\n")


def fmt_number_address_result(r: SBResult, query: str) -> str:
    return _fmt_people(r, f"🔢 *Number+Address Lookup* — `{query}`\n")


def fmt_name_result(r: SBResult, query: str) -> str:
    return _fmt_people(r, f"👤 *Name Lookup* — `{query}`\n")


def fmt_email_result(r: SBResult, query: str) -> str:
    return _fmt_people(r, f"📧 *Email Lookup* — `{query}`\n")


def fmt_background(r: SBResult, query: str) -> str:
    lines = [f"🔍 *Background Check* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    if r.parsed.get("message") == "No results found":
        return lines[0] + "🔍 Результатов не найдено"
    if r.people:
        lines.append(f"✅ Найдено *{len(r.people)}* записей\n")
        for i, p in enumerate(r.people[:5], 1):
            lines.append(f"*#{i}*")
            for k, v in p.items():
                if v and k != "raw":
                    lines.append(f"  • {k.title()}: {str(v)[:100]}")
            if p.get("raw") and not any(p.get(k) for k in ("name","address","phone")):
                lines.append(f"  📄 {p['raw'][:300]}")
            lines.append("")
    return "\n".join(lines)


# ── Phone identify / verify ────────────────────────────────────────────────────

def fmt_phone_identify(r: SBResult, query: str) -> str:
    lines = [f"📡 *Phone Identify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    # Phone identify returns results in r.people, not r.parsed
    if r.people:
        for i, p in enumerate(r.people[:5], 1):
            lines.append(f"*#{i}*")
            phone_type = p.get("phone_type", "") or p.get("phoneType", "")
            carrier = p.get("carrier", "")
            loc = p.get("location", "")
            voip = p.get("voip")
            phone_num = p.get("phone", "")
            if phone_num:
                lines.append(f"  📱 {phone_num}")
            if phone_type:
                icon = "📱" if phone_type.lower() == "mobile" else "📞"
                lines.append(f"  {icon} Тип: *{phone_type}*")
            if carrier:
                lines.append(f"  📶 Оператор: {carrier}")
            if loc:
                lines.append(f"  📍 {loc}")
            if voip is not None:
                lines.append(f"  📡 VOIP: {'Да' if voip else 'Нет'}")
            if p.get("name"):
                lines.append(f"  👤 {p['name']}")
            lines.append("")
        return "\n".join(lines)
    # Fallback to parsed raw
    p = r.parsed
    if p.get("message") == "No results found":
        return lines[0] + "🔍 Номер не идентифицирован"
    if p.get("phone_type"): lines.append(f"📱 Тип: *{p['phone_type']}*")
    if p.get("carrier"):    lines.append(f"📶 Оператор: {p['carrier']}")
    if p.get("location"):   lines.append(f"📍 Город: {p['location']}")
    if p.get("state"):      lines.append(f"🗺 Штат: {p['state']}")
    if not any(p.get(k) for k in ("phone_type", "carrier", "location")):
        lines.append(f"```\n{p.get('raw','')[:400]}\n```")
    return "\n".join(lines)


def fmt_phone_verify(r: SBResult, query: str) -> str:
    lines = [f"✅ *Phone Verify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    p = r.parsed
    if "valid" in p:
        icon = "✅" if p["valid"] else "❌"
        lines.append(f"{icon} Номер {'АКТИВЕН' if p['valid'] else 'НЕАКТИВЕН / НЕДЕЙСТВИТЕЛЕН'}")
    else:
        lines.append(f"```\n{p.get('raw','')[:400]}\n```")
    return "\n".join(lines)


# ── Address verify ─────────────────────────────────────────────────────────────

def fmt_address_verify(r: SBResult, query: str) -> str:
    lines = [f"📍 *Address Verify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    p = r.parsed
    if "valid" in p:
        icon = "✅" if p["valid"] else "❌"
        lines.append(f"{icon} Адрес {'ДЕЙСТВИТЕЛЕН (USPS)' if p['valid'] else 'НЕ НАЙДЕН В USPS'}")
    if p.get("standardized"):
        lines.append(f"📮 Стандартизированный: `{p['standardized']}`")
    if not any(p.get(k) for k in ("valid", "standardized")):
        lines.append(f"```\n{p.get('raw','')[:400]}\n```")
    return "\n".join(lines)


# ── Email verify ───────────────────────────────────────────────────────────────

def fmt_email_verify(r: SBResult, query: str) -> str:
    lines = [f"📧 *Email Verify* — `{query}`\n"]
    if not r.ok:
        return lines[0] + f"❌ `{r.error}`"
    p = r.parsed
    if "valid" in p:
        icon = "✅" if p["valid"] else "❌"
        lines.append(f"{icon} Email {'СУЩЕСТВУЕТ' if p['valid'] else 'НЕ СУЩЕСТВУЕТ'}")
    return "\n".join(lines)


# ── EmailRep ───────────────────────────────────────────────────────────────────

def fmt_emailrep(data: dict, email: str) -> str:
    if data.get("error"):
        return f"📧 *EmailRep* — `{email}`\n❌ {data['error']}"
    lines = [f"📧 *EmailRep* — `{email}`\n"]
    rep = data.get("reputation", "unknown")
    icon = {"high": "🟢", "medium": "🟡", "low": "🔴", "none": "⚫"}.get(rep, "⚪")
    lines.append(f"{icon} Репутация: *{rep.upper()}*")
    lines.append(f"📊 Подозрительный: {'⚠️ ДА' if data.get('suspicious') else '✅ НЕТ'}")
    refs = data.get("references", 0)
    lines.append(f"🔗 Упоминаний: {refs}")
    details = data.get("details", {})
    if details:
        lines.append("")
        if details.get("email_provider"):
            lines.append(f"📮 Провайдер: {details['email_provider']}")
        if details.get("disposable") is not None:
            lines.append(f"🗑 Одноразовый: {'Да' if details['disposable'] else 'Нет'}")
        if details.get("free_provider") is not None:
            lines.append(f"🆓 Бесплатный: {'Да' if details['free_provider'] else 'Нет'}")
        if details.get("deliverable") is not None:
            lines.append(f"📬 Доставляемый: {'Да' if details['deliverable'] else 'Нет'}")
        if details.get("spam") is not None:
            lines.append(f"🚫 Спам: {'Да' if details['spam'] else 'Нет'}")
        if details.get("blacklisted") is not None:
            lines.append(f"⛔ В чёрном списке: {'Да' if details['blacklisted'] else 'Нет'}")
        if details.get("domain_reputation"):
            lines.append(f"🌐 Репутация домена: {details['domain_reputation']}")
        profiles = details.get("profiles", [])
        if profiles:
            lines.append(f"👤 Профили: {', '.join(profiles[:5])}")
    return "\n".join(lines)


# ── Batch summary ──────────────────────────────────────────────────────────────

def fmt_batch_summary(results: list, search_type: str) -> str:
    total = len(results)
    ok = sum(1 for r in results if r.get("ok"))
    found = sum(
        1 for r in results
        if r.get("ok") and (
            r.get("people") or
            r.get("parsed", {}).get("valid") is not None
        )
    )
    errors = total - ok
    type_label = {
        "phone":          "📞 Phone Lookup",
        "address":        "🏠 Address Lookup",
        "number_address": "🔢 Number+Address",
        "name":           "👤 Name Lookup",
        "email":          "📧 Email Lookup",
        "background":     "🔍 Background Check",
        "phone_identify": "📡 Phone Identify",
        "phone_verify":   "✅ Phone Verify",
        "address_verify": "📍 Address Verify",
        "email_verify":   "📧 Email Verify",
    }.get(search_type, search_type.replace("_", " ").title())

    lines = [
        f"📊 *Batch завершён* — {type_label}",
        "",
        f"✅ Обработано: {ok}/{total}",
        f"🎯 С результатами: {found}",
        f"❌ Ошибок: {errors}",
        "",
        "📁 Скачайте полные результаты ↓",
    ]
    return "\n".join(lines)


# ── Export ─────────────────────────────────────────────────────────────────────

def export_csv(results: list[dict], search_type: str) -> io.BytesIO:
    buf = io.StringIO()
    rows = []
    for r in results:
        base = {
            "query":   json.dumps(r.get("query", {}), ensure_ascii=False),
            "ok":      r.get("ok"),
            "error":   r.get("error", ""),
            "type":    r.get("type", search_type),
            "account": r.get("account", ""),
        }
        people = r.get("people", [])
        parsed = r.get("parsed", {})
        if people:
            for p in people:
                row = dict(base)
                row.update({k: str(v) for k, v in p.items()})
                rows.append(row)
        else:
            row = dict(base)
            row.update({k: str(v) for k, v in parsed.items() if k != "raw"})
            rows.append(row)

    if not rows:
        rows = [{"message": "No results"}]

    all_keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in all_keys:
                all_keys.append(k)

    writer = csv.DictWriter(buf, fieldnames=all_keys, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return io.BytesIO(buf.getvalue().encode("utf-8-sig"))


def export_txt(results: list[dict], search_type: str) -> io.BytesIO:
    lines = [
        f"SearchBug Results — {search_type.replace('_', ' ').title()}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total: {len(results)}",
        "=" * 60,
        "",
    ]
    for i, r in enumerate(results, 1):
        q = r.get("query", {})
        query_str = " | ".join(f"{k}={v}" for k, v in q.items() if v)
        lines.append(f"[{i}] Query: {query_str}")
        lines.append(f"     Status: {'OK' if r.get('ok') else 'ERROR: ' + r.get('error', '')}")
        people = r.get("people", [])
        if people:
            lines.append(f"     Records: {len(people)}")
            for p in people[:5]:
                parts = []
                for k in ("name", "address", "phone", "age", "email"):
                    if p.get(k):
                        parts.append(f"{k}={p[k]}")
                if p.get("raw") and not parts:
                    parts.append(p["raw"][:150])
                lines.append(f"       → {' | '.join(parts)}")
        else:
            parsed = r.get("parsed", {})
            if parsed and parsed.get("message") != "No results found":
                for k, v in parsed.items():
                    if k != "raw":
                        lines.append(f"     {k}: {v}")
        lines.append("")
    return io.BytesIO("\n".join(lines).encode("utf-8"))


def export_json(results: list[dict]) -> io.BytesIO:
    return io.BytesIO(
        json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8")
    )
