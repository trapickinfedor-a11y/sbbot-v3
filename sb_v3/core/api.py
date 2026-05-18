"""
SBBot v3 — Public REST API (FastAPI)
Run: uvicorn api:app --host 0.0.0.0 --port 8081
Auth: X-API-Key header
"""
import os, sys
from pathlib import Path
_core = Path(__file__).parent
if str(_core) not in sys.path:
    sys.path.insert(0, str(_core))

import asyncio, logging, json, re
from fastapi import FastAPI, Header, HTTPException, Request
from typing import Optional, Dict, Any
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sbbot.api")


# ── Per-search API prices ───────────────────────────────────────────────────────
API_PRICES = {
    "phone":           3.00,
    "address":         1.20,
    "background":       3.50,
    "phone_identify":   1.00,
    "phone_verify":     1.00,
    "address_verify":   0.80,
    "email_verify":     0.60,
    "emailrep":        0.40,
    "ssn_dob":         1.50,
    "driver_license":   3.00,
    "credit_report":    6.00,
    "credit_score":     4.00,
}


# ── Validators ────────────────────────────────────────────────────────────────

class ValidationError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(400, detail)


def _digits_only(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def validate_phone(value: str) -> str:
    """Extract and validate phone: 7-15 digits after stripping non-digits."""
    if not value:
        raise ValidationError("phone: required field is empty")
    digits = _digits_only(value)
    if len(digits) < 7:
        raise ValidationError(f"phone: must have at least 7 digits. Got: '{value}'")
    if len(digits) > 15:
        raise ValidationError(f"phone: must have at most 15 digits. Got: '{value}'")
    return digits


def validate_name(value: str, field: str, required: bool = True) -> str:
    """First/last name: 2-50 letters, spaces, hyphens, apostrophes."""
    if not value:
        if required:
            raise ValidationError(f"{field}: required field is empty")
        return ""
    stripped = value.strip()
    if len(stripped) < 2:
        raise ValidationError(f"{field}: must be at least 2 characters. Got: '{value}'")
    if len(stripped) > 50:
        raise ValidationError(f"{field}: must be at most 50 characters. Got: '{value}'")
    # Letters, spaces, hyphens, apostrophes, periods
    if not re.match(r"^[\w\s\-\'.]+$", stripped, re.UNICODE):
        raise ValidationError(f"{field}: contains invalid characters. Only letters, spaces, hyphens allowed. Got: '{value}'")
    return stripped


def validate_state(value: Optional[str]) -> str:
    """US state code: 2 uppercase letters or empty."""
    if not value:
        return ""
    stripped = value.strip().upper()
    if stripped and not re.match(r"^[A-Z]{2}$", stripped):
        raise ValidationError(f"state: must be 2-letter US state code (e.g., CA, NY). Got: '{value}'")
    return stripped


def validate_zip(value: Optional[str]) -> str:
    """US ZIP: 5 or 9 digits."""
    if not value:
        return ""
    stripped = value.strip()
    digits = _digits_only(stripped)
    if len(digits) not in (5, 9):
        raise ValidationError(f"zip: must be 5 or 9 digits. Got: '{value}'")
    return digits


def validate_dob(value: Optional[str]) -> str:
    """DOB: accept MM.DD.YYYY, DD.MM.YYYY, YYYY-MM-DD, MM/DD/YYYY, YYYY/MM/DD."""
    if not value:
        return ""
    stripped = value.strip()
    # Try all known formats
    for fmt in (
        r"^\d{2}\.\d{2}\.\d{4}$",
        r"^\d{2}/\d{2}/\d{4}$",
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{4}/\d{2}/\d{2}$",
    ):
        if re.match(fmt, stripped):
            # Basic sanity: year 1900-2010, month 1-12, day 1-31
            parts = re.split(r"[/\-.]", stripped)
            if len(parts) == 3:
                if len(parts[0]) == 4:  # YYYY first
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                if not (1900 <= year <= 2010):
                    raise ValidationError(f"dob: year must be 1900-2010. Got: '{value}'")
                if not (1 <= month <= 12):
                    raise ValidationError(f"dob: invalid month. Got: '{value}'")
                if not (1 <= day <= 31):
                    raise ValidationError(f"dob: invalid day. Got: '{value}'")
            return stripped
    raise ValidationError(
        f"dob: invalid format. Use MM.DD.YYYY, DD.MM.YYYY, YYYY-MM-DD, MM/DD/YYYY, or YYYY/MM/DD. Got: '{value}'"
    )


def validate_ssn(value: Optional[str]) -> str:
    """SSN: XXX-XX-XXXX or last 4 digits."""
    if not value:
        return ""
    stripped = value.strip()
    digits = _digits_only(stripped)
    if len(digits) == 9:
        # Full SSN format check
        if not re.match(r"^\d{3}-\d{2}-\d{4}$", stripped):
            raise ValidationError(f"ssn: must be format XXX-XX-XXXX with dashes. Got: '{value}'")
        return stripped
    if len(digits) == 4:
        return digits  # last 4
    raise ValidationError(f"ssn: must be 9 digits (XXX-XX-XXXX) or last 4 digits. Got: '{value}'")


def validate_email(value: str, required: bool = True) -> str:
    """Email: RFC 5321 basic validation."""
    if not value:
        if required:
            raise ValidationError("email: required field is empty")
        return ""
    stripped = value.strip().lower()
    # Basic pattern
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", stripped):
        raise ValidationError(f"email: invalid format. Got: '{value}'")
    if len(stripped) > 254:
        raise ValidationError(f"email: too long (max 254 chars). Got: '{value}'")
    local, domain = stripped.split("@", 1)
    if len(local) > 64:
        raise ValidationError(f"email: local part too long (max 64 chars). Got: '{value}'")
    return stripped


def validate_address(value: Optional[str]) -> str:
    """Street address: 5-200 characters."""
    if not value:
        return ""
    stripped = value.strip()
    if len(stripped) < 5:
        raise ValidationError(f"address: must be at least 5 characters. Got: '{value}'")
    if len(stripped) > 200:
        raise ValidationError(f"address: must be at most 200 characters. Got: '{value}'")
    return stripped


def validate_city(value: Optional[str]) -> str:
    """City: 2-100 characters."""
    if not value:
        return ""
    stripped = value.strip()
    if len(stripped) < 2:
        raise ValidationError(f"city: must be at least 2 characters. Got: '{value}'")
    if len(stripped) > 100:
        raise ValidationError(f"city: must be at most 100 characters. Got: '{value}'")
    return stripped


def validate_search_type(stype: str) -> None:
    """Check search type is known."""
    if stype not in API_PRICES:
        available = list(API_PRICES.keys())
        raise ValidationError(
            f"Unknown search type: '{stype}'. Available: {available}"
        )


# ── Search-specific validators ────────────────────────────────────────────────

def validate_phone_search(opts: Dict[str, Any], query: str) -> Dict[str, Any]:
    phone = query or opts.get("phone", "")
    return {"phone": validate_phone(str(phone))}


def validate_phone_identify(opts: Dict[str, Any], query: str) -> Dict[str, Any]:
    phone = query or opts.get("phone", "")
    return {"phone": validate_phone(str(phone))}


def validate_phone_verify(opts: Dict[str, Any], query: str) -> Dict[str, Any]:
    phone = query or opts.get("phone", "")
    return {"phone": validate_phone(str(phone))}


def validate_address_search(opts: Dict[str, Any]) -> Dict[str, Any]:
    fn = opts.get("first_name", "")
    ln = opts.get("last_name", "")
    st = opts.get("state", "")
    addr = opts.get("address", "")
    # If only address is provided (no name), try parsing it
    if fn or ln:
        validate_name(fn, "first_name")
        validate_name(ln, "last_name")
    return {
        "first_name": validate_name(fn, "first_name", required=bool(fn)),
        "last_name": validate_name(ln, "last_name", required=bool(ln)),
        "state": validate_state(st),
        "address": validate_address(addr) if addr else "",
    }


def validate_address_verify(opts: Dict[str, Any]) -> Dict[str, Any]:
    fn = opts.get("first_name", "")
    ln = opts.get("last_name", "")
    st = opts.get("state", "")
    addr = opts.get("address", "")
    validate_name(fn, "first_name")
    validate_name(ln, "last_name")
    return {
        "first_name": fn.strip(),
        "last_name": ln.strip(),
        "state": validate_state(st),
        "address": validate_address(addr),
    }


def validate_background(opts: Dict[str, Any], query: str) -> Dict[str, Any]:
    fn = opts.get("first_name", "").strip() or (query.split()[0] if query else "")
    ln = opts.get("last_name", "").strip() or (" ".join(query.split()[1:]) if len(query.split()) > 1 else "")
    st = opts.get("state", "")
    if not fn:
        raise ValidationError("first_name: required for background search")
    return {
        "first_name": validate_name(fn, "first_name"),
        "last_name": validate_name(ln, "last_name"),
        "state": validate_state(st),
    }


def validate_email_verify(opts: Dict[str, Any], query: str) -> Dict[str, Any]:
    email = opts.get("email", "") or query
    return {"email": validate_email(str(email))}


def validate_emailrep(opts: Dict[str, Any], query: str) -> str:
    email = query or opts.get("query", "") or opts.get("email", "")
    return validate_email(str(email), required=True)


def validate_ssn_dob(opts: Dict[str, Any]) -> Dict[str, Any]:
    fn = opts.get("first_name", "")
    ln = opts.get("last_name", "")
    dob = opts.get("dob", "")
    city = opts.get("city", "")
    st = opts.get("state", "")
    zipcode = opts.get("zip", "")
    phone_val = opts.get("phone", "")
    ssn_val = opts.get("ssn", "")
    if not fn:
        raise ValidationError("first_name: required for ssn_dob search")
    if not ln:
        raise ValidationError("last_name: required for ssn_dob search")
    return {
        "first_name": validate_name(fn, "first_name"),
        "last_name": validate_name(ln, "last_name"),
        "dob": validate_dob(dob),
        "city": validate_city(city),
        "state": validate_state(st),
        "zip_code": validate_zip(zipcode),
        "phone": validate_phone(phone_val) if phone_val else "",
        "ssn": validate_ssn(ssn_val),
    }


def validate_driver_license(opts: Dict[str, Any]) -> Dict[str, Any]:
    fn = opts.get("first_name", "")
    ln = opts.get("last_name", "")
    st = opts.get("state", "")
    addr = opts.get("address", "")
    city_val = opts.get("city", "")
    zipcode = opts.get("zip", "")
    dob = opts.get("dob", "")
    if not fn:
        raise ValidationError("first_name: required for driver_license search")
    if not ln:
        raise ValidationError("last_name: required for driver_license search")
    st = validate_state(st)
    if not st:
        raise ValidationError("state: required for driver_license search")
    # Need either address+city+zip OR state
    if addr or city_val or zipcode:
        return {
            "first_name": validate_name(fn, "first_name"),
            "last_name": validate_name(ln, "last_name"),
            "street_address": validate_address(addr),
            "city": validate_city(city_val),
            "state": st,
            "zip_code": validate_zip(zipcode),
            "dob": validate_dob(dob),
        }
    return {
        "first_name": validate_name(fn, "first_name"),
        "last_name": validate_name(ln, "last_name"),
        "street_address": "",
        "city": "",
        "state": st,
        "zip_code": "",
        "dob": validate_dob(dob),
    }


def validate_credit_report(opts: Dict[str, Any]) -> Dict[str, Any]:
    fn = opts.get("first_name", "")
    ln = opts.get("last_name", "")
    st = opts.get("state", "")
    addr = opts.get("address", "")
    city_val = opts.get("city", "")
    zipcode = opts.get("zip", "")
    dob = opts.get("dob", "")
    ssn_val = opts.get("ssn", "")
    if not fn:
        raise ValidationError("first_name: required for credit_report search")
    if not ln:
        raise ValidationError("last_name: required for credit_report search")
    if not st:
        raise ValidationError("state: required for credit_report search")
    if not dob:
        raise ValidationError("dob: required for credit_report search")
    if not ssn_val:
        raise ValidationError("ssn: required for credit_report search")
    return {
        "first_name": validate_name(fn, "first_name"),
        "last_name": validate_name(ln, "last_name"),
        "street_address": validate_address(addr) if addr else "",
        "city": validate_city(city_val),
        "state": validate_state(st),
        "zip_code": validate_zip(zipcode),
        "dob": validate_dob(dob),
        "ssn": validate_ssn(ssn_val),
    }


def validate_credit_score(opts: Dict[str, Any]) -> Dict[str, Any]:
    # Same as credit_report
    return validate_credit_report(opts)


# ── Auth ─────────────────────────────────────────────────────────────────────

async def _auth(x_api_key: str = Header(...)) -> dict:
    if not x_api_key:
        raise HTTPException(401, "X-API-Key required")
    key_info = await db.get_api_key_by_key(x_api_key)
    if not key_info:
        raise HTTPException(401, "Invalid API key")
    allowed, _, _ = await db.check_api_rate_limit(key_info["id"])
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded — try again in 60 seconds")
    return key_info


# ── Lifespan ────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    logger.info("[API] Started on :8081")
    yield
    logger.info("[API] Shutdown")


app = FastAPI(title="SBBot API", version="3.0", lifespan=lifespan)


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0"}


@app.get("/v1/prices")
async def prices(x_api_key: str = Header(...)):
    await _auth(x_api_key)
    return {
        "prices": API_PRICES,
        "note": "Prices per search. Batch up to 20 at /v1/search/batch."
    }


@app.get("/v1/limits")
async def limits(x_api_key: str = Header(...)):
    k = await _auth(x_api_key)
    _, remaining, rate = await db.check_api_rate_limit(k["id"])
    return {
        "tier": k.get("tier", "starter"),
        "daily_limit": k.get("daily_limit", 100),
        "remaining_today": remaining,
        "rate_limit_per_min": rate,
        "total_requests": k.get("total_requests", 0),
        "searches_today": k.get("searches_today", 0),
    }


@app.get("/v1/tiers")
async def tiers(x_api_key: str = Header(...)):
    await _auth(x_api_key)
    tiers_list = ["starter", "pro", "enterprise", "unlimited"]
    result = {}
    for t in tiers_list:
        s = await db.get_api_tier_settings(t)
        result[t] = {
            "cost_monthly": s.get("cost", 0),
            "daily_limit": int(s.get("daily", 100)),
            "rate_limit_per_min": int(s.get("rate", 10)),
        }
    return result


# ── Search ────────────────────────────────────────────────────────────────

@app.post("/v1/search")
async def search(request: Request, x_api_key: str = Header(...)):
    """
    Perform a single search.

    Body:
    {
      "type": "phone|...",
      "query": "...",
      "options": {...}
    }
    """
    k = await _auth(x_api_key)
    body = await request.json()
    stype = body.get("type", "")
    query = body.get("query", "")
    opts = body.get("options", {}) or {}

    validate_search_type(stype)
    price = API_PRICES[stype]

    try:
        # ── Enformion: phone types ──
        if stype == "phone":
            params = validate_phone_search(opts, query)

        elif stype == "phone_identify":
            params = validate_phone_identify(opts, query)

        elif stype == "phone_verify":
            params = validate_phone_verify(opts, query)

        # ── Enformion: address/name types ──
        elif stype == "address":
            params = validate_address_search(opts)

        elif stype == "address_verify":
            params = validate_address_verify(opts)

        elif stype == "background":
            params = validate_background(opts, query)

        elif stype == "email_verify":
            params = validate_email_verify(opts, query)

        # ── EmailRep ──
        elif stype == "emailrep":
            email = validate_emailrep(opts, query)
            from sb_engine import pool as enf_pool
            result = await enf_pool.emailrep_lookup(email, await db.get_setting("emailrep_key") or "")
            await db.increment_api_usage(k["id"])
            return {
                "ok": "error" not in result,
                "type": stype,
                "price": price,
                "data": result,
            }

        # ── Usfull.pro: SSN/DOB ──
        elif stype == "ssn_dob":
            from usfull_engine import usfull_engine as uf
            uf.api_key = await db.get_setting("usfull_api_key") or ""
            if not uf.api_key:
                raise HTTPException(503, "SSN/DOB service not configured (admin: set usfull_api_key)")
            params = validate_ssn_dob(opts)

        # ── Usfull.pro: Driver License ──
        elif stype == "driver_license":
            from usfull_engine import usfull_engine as uf
            uf.api_key = await db.get_setting("usfull_api_key") or ""
            if not uf.api_key:
                raise HTTPException(503, "DL service not configured")
            params = validate_driver_license(opts)

        # ── Usfull.pro: Credit Report ──
        elif stype == "credit_report":
            from usfull_engine import usfull_engine as uf
            uf.api_key = await db.get_setting("usfull_api_key") or ""
            if not uf.api_key:
                raise HTTPException(503, "Credit report service not configured")
            params = validate_credit_report(opts)

        # ── Usfull.pro: Credit Score ──
        elif stype == "credit_score":
            from usfull_engine import usfull_engine as uf
            uf.api_key = await db.get_setting("usfull_api_key") or ""
            if not uf.api_key:
                raise HTTPException(503, "Credit score service not configured")
            params = validate_credit_score(opts)

        else:
            raise HTTPException(400, f"Search type '{stype}' not implemented via API")

        # Route to Enformion engine
        from sb_engine import pool as enf_pool
        result = await enf_pool.search(stype, params)

    except ValidationError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[API] search error: {stype}")
        raise HTTPException(500, f"Internal error: {str(e)}")

    await db.increment_api_usage(k["id"])
    return {
        "ok": result.ok,
        "type": stype,
        "price": price,
        "data": result.to_dict(),
    }


# ── Batch Search ──────────────────────────────────────────────────────────

@app.post("/v1/search/batch")
async def batch_search(request: Request, x_api_key: str = Header(...)):
    """
    Batch search (1-20 queries).

    Body:
    {
      "type": "phone|ssn_dob|address|background|emailrep",
      "queries": ["...", ...]
    }
    """
    k = await _auth(x_api_key)
    body = await request.json()
    stype = body.get("type", "")
    queries = body.get("queries", [])

    if not queries:
        raise HTTPException(400, "queries: at least 1 item required")
    if len(queries) > 20:
        raise HTTPException(400, "queries: maximum 20 items per batch")

    validate_search_type(stype)
    price = API_PRICES[stype]

    _, remaining, _ = await db.check_api_rate_limit(k["id"])
    if len(queries) > remaining:
        raise HTTPException(429, f"Daily limit exceeded. Remaining: {remaining}")

    results = []

    try:
        if stype == "phone":
            from sb_engine import pool as enf_pool
            for q in queries:
                validated = validate_phone(str(q))
                r = await enf_pool.search("phone", {"phone": validated})
                results.append(r.to_dict())

        elif stype == "address":
            from sb_engine import pool as enf_pool
            for q in queries:
                parts = str(q).split()
                params = {
                    "first_name": parts[0] if parts else "",
                    "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
                    "state": "",
                    "address": "",
                }
                if params["first_name"]:
                    params["first_name"] = validate_name(params["first_name"], "first_name")
                if params["last_name"]:
                    params["last_name"] = validate_name(params["last_name"], "last_name")
                r = await enf_pool.search("address", params)
                results.append(r.to_dict())

        elif stype == "background":
            from sb_engine import pool as enf_pool
            for q in queries:
                parts = str(q).split()
                params = {
                    "first_name": parts[0] if parts else "",
                    "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
                    "state": "",
                }
                if not params["first_name"]:
                    raise ValidationError("first_name: required for background search")
                params["first_name"] = validate_name(params["first_name"], "first_name")
                if params["last_name"]:
                    params["last_name"] = validate_name(params["last_name"], "last_name")
                r = await enf_pool.search("background", params)
                results.append(r.to_dict())

        elif stype == "ssn_dob":
            from usfull_engine import usfull_engine as uf
            uf.api_key = await db.get_setting("usfull_api_key") or ""
            if not uf.api_key:
                raise HTTPException(503, "SSN service not configured")
            for q in queries:
                parts = str(q).split()
                opts = {"first_name": parts[0] if parts else "", "last_name": " ".join(parts[1:]) if len(parts) > 1 else ""}
                validated = validate_ssn_dob(opts)
                r = await uf.search_ssn_dob(
                    first_name=validated["first_name"],
                    last_name=validated["last_name"],
                    dob=validated["dob"],
                    city=validated["city"],
                    state=validated["state"],
                    zip_code=validated["zip_code"],
                    phone=validated["phone"],
                    ssn=validated["ssn"],
                )
                results.append({"ok": r.get("ok", False), "data": r})

        elif stype == "emailrep":
            from sb_engine import pool as enf_pool
            for q in queries:
                email = validate_emailrep({}, str(q))
                r = await enf_pool.emailrep_lookup(email, await db.get_setting("emailrep_key") or "")
                results.append({"ok": "error" not in r, "data": r})

        else:
            raise HTTPException(400, f"Batch not supported for '{stype}'. Available: phone, address, background, ssn_dob, emailrep")

    except ValidationError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[API] batch error: {stype}")
        raise HTTPException(500, f"Internal error: {str(e)}")

    await db.increment_api_usage(k["id"], len(queries))
    return {
        "type": stype,
        "price_per_query": price,
        "total_price": round(price * len(queries), 4),
        "count": len(queries),
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
