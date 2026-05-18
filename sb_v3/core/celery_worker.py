"""
SBBot v3 — Celery Workers
Run: celery -A celery_worker worker --loglevel=INFO --concurrency=20
"""
import os, sys, asyncio, logging, re
from pathlib import Path

_core = Path(__file__).parent
if str(_core) not in sys.path:
    sys.path.insert(0, str(_core))

from celery import Celery

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
app = Celery("sbbot", broker=BROKER_URL, backend=BROKER_URL)
app.conf.result_expires = 3600
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"

logger = logging.getLogger("celery.workers")


def _digits(s):
    return "".join(c for c in str(s or "") if c.isdigit())


def _phone(v):
    d = _digits(v)
    if len(d) < 7 or len(d) > 15:
        raise ValueError(f"phone must have 7-15 digits, got: {v!r}")
    return d


def _name(v, field):
    s = str(v or "").strip()
    if len(s) < 2:
        raise ValueError(f"{field}: at least 2 chars, got: {v!r}")
    if len(s) > 50:
        raise ValueError(f"{field}: max 50 chars, got: {v!r}")
    return s


def _state(v):
    return (v or "").strip().upper() or ""


def _zip(v):
    d = _digits(v)
    if d and len(d) not in (5, 9):
        raise ValueError(f"zip must be 5 or 9 digits, got: {v!r}")
    return d


def _dob(v):
    s = (v or "").strip()
    for fmt in (r"^\d{2}\.\d{2}\.\d{4}$", r"^\d{2}/\d{2}/\d{4}$",
                r"^\d{4}-\d{2}-\d{2}$", r"^\d{4}/\d{2}/\d{2}$"):
        if re.match(fmt, s):
            return s
    raise ValueError(f"bad dob format: {v!r}")


def _ssn(v):
    d = _digits(v or "")
    if len(d) == 9:
        return str(v).strip()
    if len(d) == 4:
        return d
    raise ValueError(f"ssn must be 9 or 4 digits, got: {v!r}")


def _email(v):
    s = (v or "").strip().lower()
    if "@" not in s:
        raise ValueError(f"bad email: {v!r}")
    return s


def _addr(v):
    s = str(v or "").strip()
    if len(s) < 5:
        raise ValueError(f"addr min 5 chars, got: {v!r}")
    return s


def _run_async(coro):
    """Run coroutine in new event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Tasks ────────────────────────────────────────────────────────────────

@app.task(bind=True, name="sbbot.search.phone")
def task_phone(self, api_key_id, query, opts):
    import database as _db
    from sb_engine import pool as _pool
    r = _run_async(_pool.search("phone", {"phone": _phone(query)}))
    _run_async(_db.increment_api_usage(api_key_id))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.phone_identify")
def task_phone_identify(self, api_key_id, query, opts):
    from sb_engine import pool as _pool
    r = _run_async(_pool.search("phone_identify", {"phone": _phone(query)}))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.phone_verify")
def task_phone_verify(self, api_key_id, query, opts):
    from sb_engine import pool as _pool
    r = _run_async(_pool.search("phone_verify", {"phone": _phone(query)}))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.address")
def task_address(self, api_key_id, query, opts):
    import database as _db
    from sb_engine import pool as _pool
    o = opts or {}
    params = {
        "first_name": o.get("first_name") or "",
        "last_name": o.get("last_name") or "",
        "state": _state(o.get("state", "")),
        "address": o.get("address") or "",
    }
    r = _run_async(_pool.search("address", params))
    _run_async(_db.increment_api_usage(api_key_id))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.address_verify")
def task_address_verify(self, api_key_id, query, opts):
    from sb_engine import pool as _pool
    o = opts or {}
    params = {
        "first_name": _name(o.get("first_name") or "", "first_name"),
        "last_name": _name(o.get("last_name") or "", "last_name"),
        "state": _state(o.get("state", "")),
        "address": _addr(o.get("address", "")),
    }
    r = _run_async(_pool.search("address_verify", params))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.background")
def task_background(self, api_key_id, query, opts):
    from sb_engine import pool as _pool
    o = opts or {}
    params = {
        "first_name": o.get("first_name") or "",
        "last_name": o.get("last_name") or "",
        "state": _state(o.get("state", "")),
    }
    r = _run_async(_pool.search("background", params))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.email_verify")
def task_email_verify(self, api_key_id, query, opts):
    from sb_engine import pool as _pool
    email = (opts or {}).get("email") or query
    r = _run_async(_pool.search("email_verify", {"email": _email(email)}))
    return {"ok": r.ok, "data": r.to_dict()}


@app.task(bind=True, name="sbbot.search.emailrep")
def task_emailrep(self, api_key_id, query, opts):
    from sb_engine import pool as _pool
    email = (opts or {}).get("query") or query or ""
    r = _run_async(_pool.emailrep_lookup(_email(email), ""))
    return {"ok": "error" not in r, "data": r}


@app.task(bind=True, name="sbbot.search.ssn_dob")
def task_ssn_dob(self, api_key_id, query, opts):
    import database as _db
    from usfull_engine import usfull_engine as _uf
    o = opts or {}
    _uf.api_key = os.environ.get("USFULL_API_KEY", "")
    r = _run_async(_uf.search_ssn_dob(
        first_name=_name(o.get("first_name") or "", "first_name"),
        last_name=_name(o.get("last_name") or "", "last_name"),
        dob=_dob(o.get("dob", "")),
        city=(o.get("city") or "").strip(),
        state=_state(o.get("state", "")),
        zip_code=_zip(o.get("zip", "")),
        phone=o.get("phone") or "",
        ssn=_ssn(o.get("ssn", "")),
    ))
    _run_async(_db.increment_api_usage(api_key_id))
    return {"ok": r.get("ok", False), "data": r}


@app.task(bind=True, name="sbbot.search.driver_license")
def task_driver_license(self, api_key_id, query, opts):
    from usfull_engine import usfull_engine as _uf
    o = opts or {}
    _uf.api_key = os.environ.get("USFULL_API_KEY", "")
    r = _run_async(_uf.search_driver_license(
        first_name=_name(o.get("first_name") or "", "first_name"),
        last_name=_name(o.get("last_name") or "", "last_name"),
        street_address=o.get("address") or "",
        city=(o.get("city") or "").strip(),
        state=_state(o.get("state", "")),
        zip_code=_zip(o.get("zip", "")),
        dob=_dob(o.get("dob", "")),
    ))
    return {"ok": r.get("ok", False), "data": r}


@app.task(bind=True, name="sbbot.search.credit_report")
def task_credit_report(self, api_key_id, query, opts):
    from usfull_engine import usfull_engine as _uf
    o = opts or {}
    _uf.api_key = os.environ.get("USFULL_API_KEY", "")
    r = _run_async(_uf.search_credit_report(
        first_name=_name(o.get("first_name") or "", "first_name"),
        last_name=_name(o.get("last_name") or "", "last_name"),
        street_address=o.get("address") or "",
        city=(o.get("city") or "").strip(),
        state=_state(o.get("state", "")),
        zip_code=_zip(o.get("zip", "")),
        dob=_dob(o.get("dob", "")),
        ssn=_ssn(o.get("ssn", "")),
    ))
    return {"ok": r.get("ok", False), "data": r}


@app.task(bind=True, name="sbbot.search.credit_score")
def task_credit_score(self, api_key_id, query, opts):
    from usfull_engine import usfull_engine as _uf
    o = opts or {}
    _uf.api_key = os.environ.get("USFULL_API_KEY", "")
    r = _run_async(_uf.search_credit_score(
        first_name=_name(o.get("first_name") or "", "first_name"),
        last_name=_name(o.get("last_name") or "", "last_name"),
        street_address=o.get("address") or "",
        city=(o.get("city") or "").strip(),
        state=_state(o.get("state", "")),
        zip_code=_zip(o.get("zip", "")),
        dob=_dob(o.get("dob", "")),
        ssn=o.get("ssn") or "",
    ))
    return {"ok": r.get("ok", False), "data": r}


# ── Task registry ─────────────────────────────────────────────────────

TASK_MAP = {
    "phone": task_phone,
    "phone_identify": task_phone_identify,
    "phone_verify": task_phone_verify,
    "address": task_address,
    "address_verify": task_address_verify,
    "background": task_background,
    "email_verify": task_email_verify,
    "emailrep": task_emailrep,
    "ssn_dob": task_ssn_dob,
    "driver_license": task_driver_license,
    "credit_report": task_credit_report,
    "credit_score": task_credit_score,
}
