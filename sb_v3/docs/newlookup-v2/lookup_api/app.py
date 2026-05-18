"""
Self-hosted Lookup API — SSN / DL / Credit Report search server.

Fully compatible with the usfull.info API interface so that the existing
UsfullClient (mirror_bot/services/usfull_service.py) can point here via
LOOKUP_API_BASE_URL without any code changes.

Endpoints:
  POST /api/create_token/   — issue API key
  GET  /api/get_balance/    — check balance
  POST /api/search/         — SSN / DOB lookup
  POST /api/dl/             — Driver License lookup
  POST /api/cr/             — Credit Report lookup (TransUnion/Experian/Equifax/LexisNexis)

  POST /api/admin/add_balance   — add credits to an account (admin)
  POST /api/admin/import_csv    — bulk-import records from CSV
  GET  /api/admin/users         — list all API accounts
  GET  /api/admin/stats         — DB record counts + billing total
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import logging
import os
import re
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("lookup_api")

# ─── Config ────────────────────────────────────────────────────────────────

DB_PATH = Path(os.getenv("LOOKUP_DB_PATH", "/app/data/lookup.db"))
ADMIN_TOKEN = os.getenv("LOOKUP_ADMIN_TOKEN", "changeme-set-LOOKUP_ADMIN_TOKEN")

# Prices (same as usfull.info)
PRICE_SSN_FOUND   = float(os.getenv("PRICE_SSN_FOUND",   "0.40"))
PRICE_SSN_NOFOUND = float(os.getenv("PRICE_SSN_NOFOUND", "0.01"))
PRICE_DL_FOUND    = float(os.getenv("PRICE_DL_FOUND",    "1.00"))
PRICE_DL_NOFOUND  = float(os.getenv("PRICE_DL_NOFOUND",  "0.00"))
PRICE_CR_FOUND    = float(os.getenv("PRICE_CR_FOUND",    "0.40"))
PRICE_CR_NOFOUND  = float(os.getenv("PRICE_CR_NOFOUND",  "0.01"))


# ─── DB init ───────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _conn()
    conn.executescript("""
        -- API keys / accounts
        CREATE TABLE IF NOT EXISTS api_keys (
            id           INTEGER PRIMARY KEY,
            username     TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            api_key      TEXT NOT NULL UNIQUE,
            balance      REAL NOT NULL DEFAULT 0.0,
            is_active    INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        -- Billing log
        CREATE TABLE IF NOT EXISTS billing_log (
            id          INTEGER PRIMARY KEY,
            api_key_id  INTEGER NOT NULL REFERENCES api_keys(id),
            entry_type  TEXT NOT NULL CHECK(entry_type IN ('debit','credit')),
            amount      REAL NOT NULL,
            service     TEXT,
            description TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_billing_key ON billing_log(api_key_id, created_at);

        -- Persons (SSN records)
        CREATE TABLE IF NOT EXISTS persons (
            id         INTEGER PRIMARY KEY,
            firstname  TEXT,
            lastname   TEXT,
            middlename TEXT,
            ssn        TEXT,
            dob        TEXT,
            address    TEXT,
            city       TEXT,
            st         TEXT,
            zip        TEXT,
            phone      TEXT,
            name_suff  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_persons_ssn  ON persons(ssn);
        CREATE INDEX IF NOT EXISTS idx_persons_dob  ON persons(dob);
        CREATE INDEX IF NOT EXISTS idx_persons_zip  ON persons(zip);
        CREATE INDEX IF NOT EXISTS idx_persons_st   ON persons(st);
        CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(lastname, firstname);

        -- FTS5 for fast name/address search
        CREATE VIRTUAL TABLE IF NOT EXISTS persons_fts USING fts5(
            firstname, lastname, city, address,
            content='persons',
            content_rowid='id'
        );
        CREATE TRIGGER IF NOT EXISTS persons_ai AFTER INSERT ON persons BEGIN
            INSERT INTO persons_fts(rowid, firstname, lastname, city, address)
            VALUES (new.id, new.firstname, new.lastname, new.city, new.address);
        END;
        CREATE TRIGGER IF NOT EXISTS persons_ad AFTER DELETE ON persons BEGIN
            INSERT INTO persons_fts(persons_fts, rowid, firstname, lastname, city, address)
            VALUES ('delete', old.id, old.firstname, old.lastname, old.city, old.address);
        END;

        -- Driver licenses
        CREATE TABLE IF NOT EXISTS licenses (
            id              INTEGER PRIMARY KEY,
            first_name      TEXT,
            last_name       TEXT,
            dob             TEXT,
            address         TEXT,
            city            TEXT,
            state           TEXT,
            zipcode         TEXT,
            license_number  TEXT,
            license_state   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_lic_name ON licenses(last_name, first_name);
        CREATE INDEX IF NOT EXISTS idx_lic_zip  ON licenses(zipcode);
        CREATE INDEX IF NOT EXISTS idx_lic_dob  ON licenses(dob);

        -- Credit report records (TransUnion / Experian / Equifax / LexisNexis / WalletHub)
        CREATE TABLE IF NOT EXISTS cr_records (
            id           INTEGER PRIMARY KEY,
            ssn          TEXT,
            first_name   TEXT,
            last_name    TEXT,
            dob          TEXT,
            address      TEXT,
            city         TEXT,
            state        TEXT,
            zip_code     TEXT,
            bureau       TEXT NOT NULL DEFAULT 'any',
            credit_score INTEGER,
            report_json  TEXT,
            raw_text     TEXT,
            report_file  TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cr_ssn    ON cr_records(ssn);
        CREATE INDEX IF NOT EXISTS idx_cr_bureau ON cr_records(bureau, ssn);
        CREATE INDEX IF NOT EXISTS idx_cr_name   ON cr_records(last_name, first_name, dob);
    """)
    conn.commit()
    conn.close()
    logger.info("DB ready: %s", DB_PATH)


# ─── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    # Refuse to start if the admin token has not been changed from the insecure default.
    _default_token = "changeme-set-LOOKUP_ADMIN_TOKEN"
    if ADMIN_TOKEN == _default_token:
        raise RuntimeError(
            "LOOKUP_ADMIN_TOKEN is still set to the default value. "
            "Set a secure token in your .env file before starting the server."
        )
    init_db()
    yield


app = FastAPI(title="Lookup API", version="1.0.0", lifespan=lifespan)
_cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
_cors_origins = [o.strip() for o in _cors_origins if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Auth helpers ──────────────────────────────────────────────────────────

def _hash_pw(password: str) -> str:
    # PBKDF2 with SHA256 — much stronger than plain SHA256
    return hashlib.pbkdf2_hmac('sha256', password.encode(), b'lookup_api_salt', 100_000).hex()


def _get_key_by_apikey(conn: sqlite3.Connection, api_key: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM api_keys WHERE api_key = ? AND is_active = 1", (api_key,)
    ).fetchone()


def _get_key_by_credentials(
    conn: sqlite3.Connection, username: str, password: str
) -> Optional[sqlite3.Row]:
    row = conn.execute(
        "SELECT * FROM api_keys WHERE username = ? AND is_active = 1", (username,)
    ).fetchone()
    if row and secrets.compare_digest(row["password_hash"], _hash_pw(password)):
        return row
    return None


def _require_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    if not x_api_key:
        raise HTTPException(401, "X-API-KEY header required")
    conn = _conn()
    try:
        row = _get_key_by_apikey(conn, x_api_key)
    finally:
        conn.close()
    if not row:
        raise HTTPException(403, "Invalid or inactive API key")
    return x_api_key


def _require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(403, "Admin token required (X-Admin-Token header)")


# ─── Billing helper ────────────────────────────────────────────────────────

def _bill(
    conn: sqlite3.Connection,
    api_key_id: int,
    amount: float,
    service: str,
    description: str,
) -> float:
    """Deduct *amount* from balance. Returns new balance. Raises 402 if insufficient."""
    row = conn.execute("SELECT balance FROM api_keys WHERE id = ?", (api_key_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "API key not found")
    balance = row["balance"]
    if amount > 0 and balance < amount:
        raise HTTPException(402, f"Insufficient balance: ${balance:.2f} < ${amount:.2f}")
    new_balance = balance - amount
    conn.execute("UPDATE api_keys SET balance = ? WHERE id = ?", (new_balance, api_key_id))
    conn.execute(
        "INSERT INTO billing_log (api_key_id, entry_type, amount, service, description) VALUES (?,?,?,?,?)",
        (api_key_id, "debit", amount, service, description),
    )
    conn.commit()
    return new_balance


# ─── Pydantic models ───────────────────────────────────────────────────────

class CreateTokenRequest(BaseModel):
    username: str
    password: str


class SearchRequest(BaseModel):
    firstname: str
    lastname: str
    middlename: Optional[str] = Field(
        default=None,
        description="Middle name / initial; keep firstname as given name only (no middle here).",
    )
    dob: Optional[str] = None
    city: Optional[str] = None
    st: Optional[str] = None
    zip: Optional[str] = None
    ssn: Optional[str] = None

    @property
    def validated_ssn(self) -> Optional[str]:
        """Return normalized SSN (digits only) or raise ValueError if format invalid."""
        if not self.ssn:
            return None
        digits = re.sub(r"[-\s]", "", self.ssn.strip())
        if not re.fullmatch(r"\d{9}", digits):
            raise ValueError("SSN must be 9 digits (AAA-GG-NNNN format)")
        return digits


class DLRequest(BaseModel):
    first_name: str
    last_name: str
    address: str = ""
    zipcode: str = ""
    dob: Optional[str] = None
    dl_number: Optional[str] = None

    @property
    def validated_dl(self) -> Optional[str]:
        """Return DL number if provided and matches basic alphanumeric pattern."""
        if not self.dl_number:
            return None
        val = self.dl_number.strip().upper()
        if not re.fullmatch(r"[A-Z0-9\-]{4,20}", val):
            raise ValueError("Driver license number must be 4-20 alphanumeric characters")
        return val


class CRRequest(BaseModel):
    """
    Credit Report lookup request.

    Required: ssn OR (first_name + last_name + dob).
    bureau: 'transunion' | 'experian' | 'equifax' | 'lexisnexis' | 'wallet' | 'any'
    """
    ssn: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    bureau: str = "any"


class AddBalanceRequest(BaseModel):
    username: str
    amount: float
    note: Optional[str] = None


# ─── Normalisation ─────────────────────────────────────────────────────────

def _norm_name(s: str) -> str:
    return s.strip().upper() if s else ""


def _norm_dob(dob: Optional[str]) -> Optional[str]:
    """Accept YYYYMMDD, MM/DD/YYYY, MM-DD-YYYY → YYYYMMDD."""
    if not dob:
        return None
    dob = dob.strip()
    if re.fullmatch(r"\d{8}", dob):
        return dob
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(dob, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return dob  # return as-is and let DB handle it


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ─── Endpoints ─────────────────────────────────────────────────────────────

# ── /api/create_token/ ────────────────────────────────────────────────────
@app.post("/api/create_token/")
def create_token(body: CreateTokenRequest):
    """
    Create a new account or return existing API key.
    Mirrors usfull.info POST /api/create_token/
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE username = ?", (body.username,)
        ).fetchone()

        if row:
            # Verify password
            if row["password_hash"] != _hash_pw(body.password):
                raise HTTPException(403, "Wrong password for existing user")
            return {
                "status": "ok",
                "api_key": row["api_key"],
                "balance": row["balance"],
                "message": "Existing user",
            }

        # Create new account
        api_key = secrets.token_hex(32)
        conn.execute(
            "INSERT INTO api_keys (username, password_hash, api_key) VALUES (?,?,?)",
            (body.username, _hash_pw(body.password), api_key),
        )
        conn.commit()
        return {
            "status": "ok",
            "api_key": api_key,
            "balance": 0.0,
            "message": "Account created",
        }
    finally:
        conn.close()


# ── /api/get_balance/ ─────────────────────────────────────────────────────
@app.get("/api/get_balance/")
def get_balance(api_key: str = Depends(_require_api_key)):
    conn = _conn()
    try:
        row = _get_key_by_apikey(conn, api_key)
        return {
            "status": "ok",
            "balance": round(row["balance"], 4),
            "username": row["username"],
        }
    finally:
        conn.close()


# ── /api/search/ ──────────────────────────────────────────────────────────
@app.post("/api/search/")
def search_ssn(body: SearchRequest, api_key: str = Depends(_require_api_key)):
    """
    SSN / DOB lookup by name (+ optional filters).
    Mirrors usfull.info POST /api/search/
    """
    conn = _conn()
    try:
        key_row = _get_key_by_apikey(conn, api_key)
        api_key_id = key_row["id"]

        fn = _norm_name(body.firstname)
        ln = _norm_name(body.lastname)
        mn_raw = body.middlename.strip() if body.middlename else ""
        dob = _norm_dob(body.dob)
        city = body.city.strip().upper() if body.city else None
        st = body.st.strip().upper() if body.st else None
        zip_ = body.zip.strip() if body.zip else None
        # Validate and normalize SSN
        if body.ssn:
            try:
                ssn_q = body.validated_ssn
            except ValueError as e:
                raise HTTPException(422, str(e))
        else:
            ssn_q = None

        # Direct SSN lookup
        if ssn_q:
            rows = conn.execute(
                "SELECT * FROM persons WHERE ssn = ? LIMIT 50", (ssn_q,)
            ).fetchall()
        else:
            # Middle name: либо отдельное поле middlename (предпочтительно), либо слова во firstname (legacy).
            if mn_raw:
                fn_words = [w for w in fn.split() if w]
                mn_words = [w for w in _norm_name(mn_raw).split() if w]
                fn_first = fn_words[0] if fn_words else fn
                fts_tokens = [f'"{w}"' for w in fn_words + mn_words + [ln] if w]
            else:
                fn_parts = fn.split()
                fn_first = fn_parts[0] if fn_parts else fn
                fts_tokens = [f'"{w}"' for w in fn_parts + [ln] if w]
            fts_q = " ".join(fts_tokens)
            try:
                fts_rows = conn.execute(
                    "SELECT rowid FROM persons_fts WHERE persons_fts MATCH ? ORDER BY rank LIMIT 500",
                    (fts_q,),
                ).fetchall()
            except sqlite3.OperationalError:
                fts_rows = []

            # Fallback: try exact match on first word of firstname + lastname
            if not fts_rows:
                fts_rows = conn.execute(
                    "SELECT id as rowid FROM persons WHERE upper(firstname) LIKE ? AND upper(lastname)=? LIMIT 500",
                    (f"{fn_first}%", ln),
                ).fetchall()

            if not fts_rows:
                _bill(conn, api_key_id, PRICE_SSN_NOFOUND, "ssn_search", f"no result: {fn} {ln}")
                return {"status": "ok", "count": 0, "results": []}

            ids = tuple(r["rowid"] for r in fts_rows)
            placeholders = ",".join("?" * len(ids))
            params: list[Any] = list(ids)
            where_extra = ""

            if dob:
                where_extra += " AND dob = ?"
                params.append(dob)
            if st:
                where_extra += " AND upper(st) = ?"
                params.append(st)
            if zip_:
                where_extra += " AND zip = ?"
                params.append(zip_)
            if city:
                where_extra += " AND upper(city) LIKE ?"
                params.append(f"%{city}%")
            if mn_raw:
                mn_norm = _norm_name(mn_raw)
                if len(mn_norm) == 1:
                    # инициал: C → C, CHARLES, …
                    where_extra += (
                        " AND (upper(substr(trim(ifnull(middlename,'')), 1, 1)) = ? "
                        "OR upper(trim(ifnull(middlename,''))) = ?)"
                    )
                    params.extend([mn_norm, mn_norm])
                else:
                    where_extra += " AND upper(trim(ifnull(middlename,''))) LIKE ?"
                    params.append(f"{mn_norm}%")

            rows = conn.execute(
                f"SELECT * FROM persons WHERE id IN ({placeholders}){where_extra} LIMIT 1000",
                params,
            ).fetchall()

        if not rows:
            _bill(conn, api_key_id, PRICE_SSN_NOFOUND, "ssn_search", f"no result: {fn} {ln}")
            return {"status": "ok", "count": 0, "results": []}

        _bill(conn, api_key_id, PRICE_SSN_FOUND, "ssn_search", f"found {len(rows)}: {fn} {ln}")
        results = [_row_to_dict(r) for r in rows]
        return {"status": "ok", "count": len(results), "results": results}

    finally:
        conn.close()


# ── /api/dl/ ──────────────────────────────────────────────────────────────
@app.post("/api/dl/")
def search_dl(body: DLRequest, api_key: str = Depends(_require_api_key)):
    """
    Driver license lookup.
    Mirrors usfull.info POST /api/dl/
    """
    conn = _conn()
    try:
        key_row = _get_key_by_apikey(conn, api_key)
        api_key_id = key_row["id"]

        fn = _norm_name(body.first_name)
        ln = _norm_name(body.last_name)
        dob = _norm_dob(body.dob)
        zip_ = body.zipcode.strip() if body.zipcode else ""

        # Bot parser may include middle name in first_name (e.g. "BROOKE HANNAH")
        # DB stores just "BROOKE" — use LIKE prefix match
        fn_first = fn.split()[0] if fn else fn

        # Strict: name + zip + dob (if all available)
        rows = []
        if dob and zip_:
            rows = conn.execute(
                """SELECT * FROM licenses
                   WHERE upper(last_name) = ?
                     AND upper(first_name) LIKE ?
                     AND zipcode = ?
                     AND dob = ?
                   LIMIT 50""",
                (ln, f"{fn_first}%", zip_, dob),
            ).fetchall()

        # Retry: name + dob (no zip)
        if not rows and dob:
            rows = conn.execute(
                """SELECT * FROM licenses
                   WHERE upper(last_name) = ?
                     AND upper(first_name) LIKE ?
                     AND dob = ?
                   LIMIT 50""",
                (ln, f"{fn_first}%", dob),
            ).fetchall()

        # Retry: name + zip (no dob)
        if not rows and zip_:
            rows = conn.execute(
                """SELECT * FROM licenses
                   WHERE upper(last_name) = ?
                     AND upper(first_name) LIKE ?
                     AND zipcode = ?
                   LIMIT 50""",
                (ln, f"{fn_first}%", zip_),
            ).fetchall()

        # Last resort: name only
        if not rows:
            rows = conn.execute(
                """SELECT * FROM licenses
                   WHERE upper(last_name) = ?
                     AND upper(first_name) LIKE ?
                   LIMIT 50""",
                (ln, f"{fn_first}%"),
            ).fetchall()

        if not rows:
            _bill(conn, api_key_id, PRICE_DL_NOFOUND, "dl_search", f"no result: {fn} {ln}")
            return {"status": "ok", "count": 0, "results": []}

        _bill(conn, api_key_id, PRICE_DL_FOUND, "dl_search", f"found {len(rows)}: {fn} {ln}")
        results = [_row_to_dict(r) for r in rows]
        return {"status": "ok", "count": len(results), "results": results}

    finally:
        conn.close()


# ── /api/cr/ ──────────────────────────────────────────────────────────────
@app.post("/api/cr/")
def search_cr(body: CRRequest, api_key: str = Depends(_require_api_key)):
    """
    Credit Report lookup by SSN (primary) or name+DOB (fallback).
    bureau: transunion | experian | equifax | lexisnexis | wallet | any
    """
    conn = _conn()
    try:
        key_row = _get_key_by_apikey(conn, api_key)
        api_key_id = key_row["id"]

        bureau = body.bureau.lower().strip() if body.bureau else "any"
        ssn_q  = re.sub(r"[^\d]", "", body.ssn or "")
        fn     = _norm_name(body.first_name or "")
        ln     = _norm_name(body.last_name or "")
        dob    = _norm_dob(body.dob)

        if not ssn_q and not (fn and ln):
            raise HTTPException(400, "Provide ssn OR first_name+last_name")

        params: list[Any] = []
        where_clauses: list[str] = []

        # Primary: SSN match
        if ssn_q:
            # Normalise stored SSN (may be stored with or without dashes)
            where_clauses.append(
                "(ssn = ? OR ssn = ? OR ssn = ?)"
            )
            fmt_ssn = f"{ssn_q[:3]}-{ssn_q[3:5]}-{ssn_q[5:]}" if len(ssn_q) == 9 else ssn_q
            params += [ssn_q, fmt_ssn, fmt_ssn.replace("-", "")]
        else:
            where_clauses.append("upper(last_name) = ?")
            params.append(ln)
            fn_first = fn.split()[0] if fn else fn
            where_clauses.append("upper(first_name) LIKE ?")
            params.append(f"{fn_first}%")
            if dob:
                where_clauses.append("dob = ?")
                params.append(dob)

        # Bureau filter
        if bureau and bureau != "any":
            where_clauses.append("(lower(bureau) = ? OR bureau = 'any')")
            params.append(bureau)

        sql = "SELECT * FROM cr_records WHERE " + " AND ".join(where_clauses) + " ORDER BY id LIMIT 20"
        rows = conn.execute(sql, params).fetchall()

        if not rows:
            _bill(conn, api_key_id, PRICE_CR_NOFOUND, "cr_search",
                  f"no result: ssn={ssn_q or 'N/A'} bureau={bureau}")
            return {"status": "ok", "count": 0, "results": []}

        _bill(conn, api_key_id, PRICE_CR_FOUND, "cr_search",
              f"found {len(rows)}: ssn={ssn_q or fn+' '+ln} bureau={bureau}")

        results = []
        for r in rows:
            rec = _row_to_dict(r)
            if rec.get("report_json"):
                try:
                    import json as _json
                    rec["report_data"] = _json.loads(rec["report_json"])
                except Exception:
                    rec["report_data"] = {}
            else:
                rec["report_data"] = {}
            # Signal whether a PDF file is available for download
            pdf_path = rec.get("report_file") or ""
            rec["has_pdf"] = bool(pdf_path and Path(pdf_path).exists())
            rec["pdf_download_url"] = f"/api/cr/download/{rec['id']}" if rec["has_pdf"] else None
            results.append(rec)

        return {"status": "ok", "count": len(results), "results": results}

    finally:
        conn.close()


# ── /api/cr/download/<id> ─────────────────────────────────────────────────
@app.get("/api/cr/download/{record_id}")
def download_cr_pdf(record_id: int, api_key: str = Depends(_require_api_key)):
    """Download the PDF file for a credit report record."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT report_file, first_name, last_name, bureau FROM cr_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Record not found")
        pdf_path = row["report_file"]
        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(404, "PDF file not available for this record")
        fn = (row["first_name"] or "").strip()
        ln = (row["last_name"] or "").strip()
        bureau = (row["bureau"] or "report").strip()
        filename = f"CR_{fn}_{ln}_{bureau}.pdf".replace(" ", "_")
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename,
        )
    finally:
        conn.close()


# ── /api/cr/upload_pdf ────────────────────────────────────────────────────
@app.post("/api/cr/upload_pdf")
async def upload_cr_pdf(
    record_id: int,
    file: UploadFile = File(...),
    _: None = Depends(_require_admin),
):
    """Upload a PDF file and attach it to an existing cr_records entry."""
    content = await file.read()

    def _do_upload():
        conn = _conn()
        try:
            row = conn.execute("SELECT id FROM cr_records WHERE id = ?", (record_id,)).fetchone()
            if not row:
                return None
            pdf_dir = DB_PATH.parent / "cr_pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            dest = pdf_dir / f"cr_{record_id}.pdf"
            dest.write_bytes(content)
            conn.execute("UPDATE cr_records SET report_file = ? WHERE id = ?", (str(dest), record_id))
            conn.commit()
            return str(dest)
        finally:
            conn.close()

    loop = asyncio.get_event_loop()
    dest_path = await loop.run_in_executor(None, _do_upload)
    if dest_path is None:
        raise HTTPException(404, f"CR record {record_id} not found")
    return {"status": "ok", "record_id": record_id, "file_path": dest_path, "size_bytes": len(content)}


# ─── Admin endpoints ───────────────────────────────────────────────────────

@app.post("/api/admin/add_balance")
def admin_add_balance(
    body: AddBalanceRequest,
    _: None = Depends(_require_admin),
):
    """Add balance to a user account."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE username = ?", (body.username,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"User '{body.username}' not found")
        new_bal = row["balance"] + body.amount
        conn.execute("UPDATE api_keys SET balance = ? WHERE id = ?", (new_bal, row["id"]))
        conn.execute(
            "INSERT INTO billing_log (api_key_id, entry_type, amount, service, description) VALUES (?,?,?,?,?)",
            (row["id"], "credit", body.amount, "admin", body.note or "manual top-up"),
        )
        conn.commit()
        return {"status": "ok", "username": body.username, "new_balance": round(new_bal, 4)}
    finally:
        conn.close()


@app.get("/api/admin/users")
def admin_list_users(_: None = Depends(_require_admin)):
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, username, api_key, balance, is_active, created_at FROM api_keys ORDER BY id"
        ).fetchall()
        return {"status": "ok", "users": [_row_to_dict(r) for r in rows]}
    finally:
        conn.close()


@app.get("/api/admin/stats")
def admin_stats(_: None = Depends(_require_admin)):
    conn = _conn()
    try:
        persons_count  = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
        licenses_count = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
        cr_count       = conn.execute("SELECT COUNT(*) FROM cr_records").fetchone()[0]
        billing_total  = conn.execute(
            "SELECT SUM(amount) FROM billing_log WHERE entry_type='debit'"
        ).fetchone()[0] or 0
        return {
            "status": "ok",
            "persons_records": persons_count,
            "license_records": licenses_count,
            "cr_records": cr_count,
            "total_billed": round(billing_total, 4),
        }
    finally:
        conn.close()


@app.post("/api/admin/import_csv")
async def admin_import_csv(
    table: str,  # 'persons', 'licenses', or 'cr_records'
    file: UploadFile = File(...),
    _: None = Depends(_require_admin),
):
    """
    Bulk-import CSV into persons, licenses, or cr_records table.
    For large files use the CLI importer (importer.py) instead.
    """
    if table not in ("persons", "licenses", "cr_records"):
        raise HTTPException(400, "table must be 'persons', 'licenses', or 'cr_records'")

    content = await file.read()
    text = content.decode("utf-8", errors="replace")

    def _do_import():
        reader = csv.DictReader(io.StringIO(text))
        conn = _conn()
        inserted = 0
        try:
            if table == "persons":
                for batch_start in _batched(reader, 1000):
                    for row in batch_start:
                        row = {k.lower().strip(): v.strip() for k, v in row.items() if k}
                        conn.execute(
                            """INSERT INTO persons
                               (firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                row.get("firstname") or row.get("first_name") or row.get("fname", ""),
                                row.get("lastname")  or row.get("last_name")  or row.get("lname", ""),
                                row.get("middlename") or row.get("middle_name") or row.get("mname", ""),
                                row.get("ssn", ""),
                                _norm_dob(row.get("dob") or row.get("date_of_birth")),
                                row.get("address", ""),
                                row.get("city", ""),
                                row.get("st") or row.get("state", ""),
                                row.get("zip") or row.get("zipcode") or row.get("zip_code", ""),
                                row.get("phone", ""),
                                row.get("name_suff") or row.get("suffix", ""),
                            ),
                        )
                        inserted += 1
            elif table == "licenses":
                for row in reader:
                    row = {k.lower().strip(): v.strip() for k, v in row.items() if k}
                    conn.execute(
                        """INSERT INTO licenses
                           (first_name,last_name,dob,address,city,state,zipcode,license_number,license_state)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            row.get("first_name") or row.get("firstname", ""),
                            row.get("last_name")  or row.get("lastname",  ""),
                            _norm_dob(row.get("dob") or row.get("date_of_birth")),
                            row.get("address", ""),
                            row.get("city", ""),
                            row.get("state") or row.get("st", ""),
                            row.get("zipcode") or row.get("zip") or row.get("zip_code", ""),
                            row.get("license_number") or row.get("dl_number", ""),
                            row.get("license_state") or row.get("dl_state", ""),
                        ),
                    )
                    inserted += 1
            else:  # cr_records
                import json as _json
                for row in reader:
                    row = {k.lower().strip(): v.strip() for k, v in row.items() if k}
                    report_json_val = row.get("report_json") or row.get("report_data") or ""
                    score_raw = row.get("credit_score") or row.get("score", "")
                    try:
                        score_int = int(score_raw) if score_raw else None
                    except ValueError:
                        score_int = None
                    conn.execute(
                        """INSERT INTO cr_records
                           (ssn,first_name,last_name,dob,address,city,state,zip_code,bureau,credit_score,report_json,raw_text)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            row.get("ssn", ""),
                            row.get("first_name") or row.get("firstname", ""),
                            row.get("last_name")  or row.get("lastname",  ""),
                            _norm_dob(row.get("dob") or row.get("date_of_birth")),
                            row.get("address", ""),
                            row.get("city", ""),
                            row.get("state") or row.get("st", ""),
                            row.get("zip_code") or row.get("zip") or row.get("zipcode", ""),
                            (row.get("bureau") or "any").lower(),
                            score_int,
                            report_json_val,
                            row.get("raw_text", ""),
                        ),
                    )
                    inserted += 1

            conn.commit()
        finally:
            conn.close()
        return inserted

    loop = asyncio.get_event_loop()
    inserted = await loop.run_in_executor(None, _do_import)
    return {"status": "ok", "table": table, "inserted": inserted}


def _batched(iterable, n):
    """Yield batches of n items from iterable."""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


# ─── Healthcheck ───────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


# ─── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("LOOKUP_API_PORT", "8082"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
