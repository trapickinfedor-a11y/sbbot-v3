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

import asyncio, logging, json
from fastapi import FastAPI, Header, HTTPException, Request
from typing import Optional
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sbbot.api")

# Per-search API prices (gross margin already embedded)
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


# ── Public endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0"}


@app.get("/v1/prices")
async def prices(x_api_key: str = Header(...)):
    """Public price list — works with any valid key."""
    await _auth(x_api_key)
    return {
        "prices": API_PRICES,
        "note": "Prices are per search. Batch available at /v1/search/batch (up to 20/query)."
    }


@app.get("/v1/limits")
async def limits(x_api_key: str = Header(...)):
    """Current API key limits and usage."""
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
    """All available subscription tiers."""
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
      "type": "phone|address|background|phone_identify|phone_verify|address_verify|emailrep|ssn_dob|driver_license|credit_report",
      "query": "..."           <- used for phone, address, background, emailrep
      "options": { ... }        <- type-specific params (see docs)
    }

    Response:
    {
      "ok": bool,
      "type": str,
      "price": float,
      "data": { ... }          <- raw engine result
    }
    """
    k = await _auth(x_api_key)
    body = await request.json()
    stype = body.get("type", "")
    query = body.get("query", "")
    opts = body.get("options", {})

    price = API_PRICES.get(stype)
    if not price:
        raise HTTPException(400, f"Unknown search type: '{stype}'. Available: {list(API_PRICES.keys())}")

    # ── Enformion: phone, address, background, phone_identify, phone_verify ──
    if stype in ("phone", "address", "background", "phone_identify", "phone_verify", "address_verify"):
        from sb_engine import pool as enf_pool

        # Build params dict — phone types need {"phone": "..."}
        if stype == "phone":
            params = {"phone": query}
        elif stype == "phone_identify":
            params = {"phone": query}
        elif stype == "phone_verify":
            params = {"phone": query}
        elif stype in ("address", "address_verify"):
            # options may contain first_name, last_name, state, address
            params = {
                "first_name": opts.get("first_name", ""),
                "last_name": opts.get("last_name", ""),
                "state": opts.get("state", ""),
                "address": opts.get("address", ""),
            }
        elif stype == "background":
            params = {
                "first_name": opts.get("first_name", query.split()[0] if query else ""),
                "last_name": " ".join(query.split()[1:]) if len(query.split()) > 1 else "",
                "state": opts.get("state", ""),
            }
        else:
            params = {}

        result = await enf_pool.search(stype, params)
        await db.increment_api_usage(k["id"])
        return {
            "ok": result.ok,
            "type": stype,
            "price": price,
            "data": result.to_dict(),
        }

    # ── Usfull.pro: ssn_dob ────────────────────────────────────────────
    elif stype == "ssn_dob":
        from usfull_engine import usfull_engine as uf
        uf.api_key = await db.get_setting("usfull_api_key") or ""
        if not uf.api_key:
            raise HTTPException(503, "SSN/DOB service not configured (admin: set usfull_api_key)")
        result = await uf.search_ssn_dob(
            first_name=opts.get("first_name", ""),
            last_name=opts.get("last_name", ""),
            dob=opts.get("dob"),
            city=opts.get("city"),
            state=opts.get("state"),
            zip_code=opts.get("zip"),
            phone=opts.get("phone"),
            ssn=opts.get("ssn"),
        )
        await db.increment_api_usage(k["id"])
        return {
            "ok": result.get("ok", False),
            "type": stype,
            "price": price,
            "data": result,
        }

    # ── Usfull.pro: driver_license ─────────────────────────────────────
    elif stype == "driver_license":
        from usfull_engine import usfull_engine as uf
        uf.api_key = await db.get_setting("usfull_api_key") or ""
        if not uf.api_key:
            raise HTTPException(503, "DL service not configured")
        result = await uf.search_driver_license(
            first_name=opts.get("first_name", ""),
            last_name=opts.get("last_name", ""),
            street_address=opts.get("address", ""),
            city=opts.get("city", ""),
            state=opts.get("state", ""),
            zip_code=opts.get("zip", ""),
            dob=opts.get("dob"),
        )
        await db.increment_api_usage(k["id"])
        return {
            "ok": result.get("ok", False),
            "type": stype,
            "price": price,
            "data": result,
        }

    # ── Usfull.pro: credit_report ───────────────────────────────────────
    elif stype == "credit_report":
        from usfull_engine import usfull_engine as uf
        uf.api_key = await db.get_setting("usfull_api_key") or ""
        if not uf.api_key:
            raise HTTPException(503, "Credit report service not configured")
        result = await uf.search_credit_report(
            first_name=opts.get("first_name", ""),
            last_name=opts.get("last_name", ""),
            street_address=opts.get("address", ""),
            city=opts.get("city", ""),
            state=opts.get("state", ""),
            zip_code=opts.get("zip", ""),
            dob=opts.get("dob"),
            ssn=opts.get("ssn"),
        )
        await db.increment_api_usage(k["id"])
        return {
            "ok": result.get("ok", False),
            "type": stype,
            "price": price,
            "data": result,
        }
    # ── Usfull.pro: credit_score ──────────────────────────────────────────
    elif stype == "credit_score":
        from usfull_engine import usfull_engine as uf
        uf.api_key = await db.get_setting("usfull_api_key") or ""
        if not uf.api_key:
            raise HTTPException(503, "Credit score service not configured")
        result = await uf.search_credit_score(
            first_name=opts.get("first_name", ""),
            last_name=opts.get("last_name", ""),
            street_address=opts.get("address", ""),
            city=opts.get("city", ""),
            state=opts.get("state", ""),
            zip_code=opts.get("zip", ""),
            dob=opts.get("dob", ""),
            ssn=opts.get("ssn"),
        )
        await db.increment_api_usage(k["id"])
        return {
            "ok": result.get("ok", False),
            "type": stype,
            "price": price,
            "data": result,
        }

    # ── Enformion: email_verify ───────────────────────────────────────────
    elif stype == "email_verify":
        from sb_engine import pool as enf_pool
        email_addr = opts.get("email", query)
        params = {"email": email_addr}
        result = await enf_pool.search("email_verify", params)
        await db.increment_api_usage(k["id"])
        return {
            "ok": result.ok,
            "type": stype,
            "price": price,
            "data": result.to_dict(),
        }

    # ── EmailRep ────────────────────────────────────────────────────────
    elif stype == "emailrep":
        from sb_engine import pool as enf_pool
        emailrep_key = await db.get_setting("emailrep_key") or ""
        result = await enf_pool.emailrep_lookup(query, emailrep_key)
        await db.increment_api_usage(k["id"])
        return {
            "ok": "error" not in result,
            "type": stype,
            "price": price,
            "data": result,
        }

    else:
        raise HTTPException(400, f"Search type '{stype}' not implemented via API")


# ── Batch Search ──────────────────────────────────────────────────────────

@app.post("/v1/search/batch")
async def batch_search(request: Request, x_api_key: str = Header(...)):
    """
    Batch search (1-20 queries).

    Body:
    {
      "type": "phone|ssn_dob|address|background|emailrep",
      "queries": ["...", "...", ...]
    }

    Response:
    {
      "type": str,
      "price_per_query": float,
      "total_price": float,
      "results": [...]
    }
    """
    k = await _auth(x_api_key)
    body = await request.json()
    stype = body.get("type", "")
    queries = body.get("queries", [])

    if not queries or len(queries) > 20:
        raise HTTPException(400, "queries must be 1-20 items")

    price = API_PRICES.get(stype)
    if not price:
        raise HTTPException(400, f"Unknown type: '{stype}'")

    # Check daily quota
    _, remaining, _ = await db.check_api_rate_limit(k["id"])
    if len(queries) > remaining:
        raise HTTPException(429, f"Daily limit exceeded. Remaining: {remaining}")

    results = []

    if stype == "phone":
        from sb_engine import pool as enf_pool
        for q in queries:
            r = await enf_pool.search("phone", {"phone": q})
            results.append(r.to_dict())

    elif stype == "address":
        from sb_engine import pool as enf_pool
        for q in queries:
            # q can be "FirstName LastName [State]"
            parts = q.split()
            params = {
                "first_name": parts[0] if parts else "",
                "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
            }
            r = await enf_pool.search("address", params)
            results.append(r.to_dict())

    elif stype == "background":
        from sb_engine import pool as enf_pool
        for q in queries:
            parts = q.split()
            params = {
                "first_name": parts[0] if parts else "",
                "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
            }
            r = await enf_pool.search("background", params)
            results.append(r.to_dict())

    elif stype == "ssn_dob":
        from usfull_engine import usfull_engine as uf
        uf.api_key = await db.get_setting("usfull_api_key") or ""
        if not uf.api_key:
            raise HTTPException(503, "SSN service not configured")
        for q in queries:
            # q format: "FirstName LastName [State]"
            parts = q.split()
            r = await uf.search_ssn_dob(
                first_name=parts[0] if parts else "",
                last_name=" ".join(parts[1:]) if len(parts) > 1 else "",
            )
            results.append({"ok": r.get("ok", False), "data": r})

    elif stype == "emailrep":
        from sb_engine import pool as enf_pool
        emailrep_key = await db.get_setting("emailrep_key") or ""
        for q in queries:
            r = await enf_pool.emailrep_lookup(q, emailrep_key)
            results.append({"ok": "error" not in r, "data": r})

    else:
        raise HTTPException(400, f"Batch not supported for '{stype}'")

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
