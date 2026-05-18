"""
CLI data importer for the Lookup API database.

Usage:
  python importer.py persons  /path/to/ssn_data.csv   --db /app/data/lookup.db
  python importer.py licenses /path/to/dl_data.csv    --db /app/data/lookup.db
  python importer.py persons  /path/to/data.tsv  --sep tab
  python importer.py rebuild-fts                       --db /app/data/lookup.db

Supported column name aliases (case-insensitive):
  Persons:  firstname/first_name/fname, lastname/last_name/lname,
            middlename/middle_name/mname, ssn, dob/date_of_birth,
            address, city, st/state, zip/zipcode/zip_code, phone, suffix
  Licenses: first_name/firstname, last_name/lastname, dob/date_of_birth,
            address, city, state/st, zipcode/zip/zip_code,
            license_number/dl_number, license_state/dl_state
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("importer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BATCH_SIZE = 5_000

# ─── DOB normalisation ────────────────────────────────────────────────────

def _norm_dob(dob: str | None) -> str | None:
    if not dob:
        return None
    dob = dob.strip()
    if re.fullmatch(r"\d{8}", dob):
        return dob
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(dob, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return dob


# ─── Column aliases ───────────────────────────────────────────────────────

def _pick(row: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v:
            return v.strip()
    return default


def _normalise_header(row: dict) -> dict:
    return {k.lower().strip(): v for k, v in row.items() if k}


# ─── Import persons (SSN table) ───────────────────────────────────────────

def import_persons(conn: sqlite3.Connection, path: Path, sep: str = ",") -> int:
    inserted = 0
    skipped = 0
    t0 = time.time()

    with path.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        batch: list[tuple] = []

        for raw in reader:
            row = _normalise_header(raw)
            fn   = _pick(row, "firstname", "first_name", "fname")
            ln   = _pick(row, "lastname", "last_name", "lname")
            mn   = _pick(row, "middlename", "middle_name", "mname")
            ssn  = _pick(row, "ssn")
            dob  = _norm_dob(_pick(row, "dob", "date_of_birth") or None)
            addr = _pick(row, "address", "addr")
            city = _pick(row, "city")
            st   = _pick(row, "st", "state")
            zip_ = _pick(row, "zip", "zipcode", "zip_code")
            phone = _pick(row, "phone", "telephone")
            suff = _pick(row, "name_suff", "suffix", "suff")

            if not fn and not ln and not ssn:
                skipped += 1
                continue

            batch.append((fn, ln, mn, ssn, dob, addr, city, st, zip_, phone, suff))

            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT INTO persons (firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                conn.commit()
                inserted += len(batch)
                elapsed = time.time() - t0
                logger.info("  ...%d rows imported (%.1fs)", inserted, elapsed)
                batch = []

        if batch:
            conn.executemany(
                "INSERT INTO persons (firstname,lastname,middlename,ssn,dob,address,city,st,zip,phone,name_suff) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )
            conn.commit()
            inserted += len(batch)

    logger.info("Persons: inserted=%d skipped=%d in %.1fs", inserted, skipped, time.time() - t0)
    return inserted


# ─── Import licenses (DL table) ───────────────────────────────────────────

def import_licenses(conn: sqlite3.Connection, path: Path, sep: str = ",") -> int:
    inserted = 0
    skipped = 0
    t0 = time.time()

    with path.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        batch: list[tuple] = []

        for raw in reader:
            row = _normalise_header(raw)
            fn       = _pick(row, "first_name", "firstname", "fname")
            ln       = _pick(row, "last_name", "lastname", "lname")
            dob      = _norm_dob(_pick(row, "dob", "date_of_birth") or None)
            addr     = _pick(row, "address", "addr")
            city     = _pick(row, "city")
            state    = _pick(row, "state", "st")
            zip_     = _pick(row, "zipcode", "zip", "zip_code")
            lic_num  = _pick(row, "license_number", "dl_number", "license_no", "dl_no")
            lic_st   = _pick(row, "license_state", "dl_state")

            if not fn and not ln:
                skipped += 1
                continue

            batch.append((fn, ln, dob, addr, city, state, zip_, lic_num, lic_st))

            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT INTO licenses (first_name,last_name,dob,address,city,state,zipcode,license_number,license_state) VALUES (?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                conn.commit()
                inserted += len(batch)
                elapsed = time.time() - t0
                logger.info("  ...%d rows imported (%.1fs)", inserted, elapsed)
                batch = []

        if batch:
            conn.executemany(
                "INSERT INTO licenses (first_name,last_name,dob,address,city,state,zipcode,license_number,license_state) VALUES (?,?,?,?,?,?,?,?,?)",
                batch,
            )
            conn.commit()
            inserted += len(batch)

    logger.info("Licenses: inserted=%d skipped=%d in %.1fs", inserted, skipped, time.time() - t0)
    return inserted


# ─── Rebuild FTS index ────────────────────────────────────────────────────

def rebuild_fts(conn: sqlite3.Connection) -> None:
    logger.info("Rebuilding FTS index (this may take a while)...")
    t0 = time.time()
    conn.execute("DELETE FROM persons_fts")
    conn.execute(
        "INSERT INTO persons_fts(rowid, firstname, lastname, city, address) SELECT id, firstname, lastname, city, address FROM persons"
    )
    conn.execute("INSERT INTO persons_fts(persons_fts) VALUES ('optimize')")
    conn.commit()
    logger.info("FTS rebuilt in %.1fs", time.time() - t0)


# ─── CLI ──────────────────────────────────────────────────────────────────

def import_cr_records(conn: sqlite3.Connection, path: Path, sep: str = ",") -> int:
    """
    Import Credit Report records from CSV.

    Expected columns (case-insensitive aliases supported):
      ssn, first_name/firstname, last_name/lastname,
      dob/date_of_birth, address, city, state/st, zip_code/zip/zipcode,
      bureau (transunion|experian|equifax|lexisnexis|wallet|any),
      credit_score/score, report_json/report_data, raw_text
    """
    import json as _json

    inserted = 0
    skipped = 0
    t0 = time.time()

    with path.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        batch: list[tuple] = []

        for raw in reader:
            row = _normalise_header(raw)
            ssn      = _pick(row, "ssn")
            fn       = _pick(row, "first_name", "firstname", "fname")
            ln       = _pick(row, "last_name", "lastname", "lname")
            dob      = _norm_dob(_pick(row, "dob", "date_of_birth") or None)
            addr     = _pick(row, "address", "addr")
            city     = _pick(row, "city")
            state    = _pick(row, "state", "st")
            zip_     = _pick(row, "zip_code", "zip", "zipcode")
            bureau   = (_pick(row, "bureau") or "any").lower()
            score_raw = _pick(row, "credit_score", "score")
            report_json = _pick(row, "report_json", "report_data")
            raw_text = _pick(row, "raw_text", "text", "report_text")

            if not ssn and not fn and not ln:
                skipped += 1
                continue

            try:
                score_int = int(score_raw) if score_raw else None
            except ValueError:
                score_int = None

            report_file = _pick(row, "report_file", "pdf_path", "file_path")

            batch.append((ssn, fn, ln, dob, addr, city, state, zip_, bureau, score_int, report_json, raw_text, report_file))

            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT INTO cr_records (ssn,first_name,last_name,dob,address,city,state,zip_code,bureau,credit_score,report_json,raw_text,report_file) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                conn.commit()
                inserted += len(batch)
                logger.info("  ...%d CR rows imported (%.1fs)", inserted, time.time() - t0)
                batch = []

        if batch:
            conn.executemany(
                "INSERT INTO cr_records (ssn,first_name,last_name,dob,address,city,state,zip_code,bureau,credit_score,report_json,raw_text,report_file) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )
            conn.commit()
            inserted += len(batch)

    logger.info("CR records: inserted=%d skipped=%d in %.1fs", inserted, skipped, time.time() - t0)
    return inserted


def link_pdfs(conn: sqlite3.Connection, pdf_dir: Path, pattern: str = "ssn") -> int:
    """
    Link PDF files to cr_records by matching filenames to SSN or name.

    Supported patterns:
      ssn:  filename contains 9-digit SSN (e.g. "CR_016724463.pdf" or "016-72-4463_equifax.pdf")
      name: filename contains "FirstName_LastName" (e.g. "Kyle_Linseman_equifax.pdf")
    """
    import re as _re

    linked = 0
    pdf_files = list(pdf_dir.glob("*.pdf"))
    logger.info("Found %d PDF files in %s", len(pdf_files), pdf_dir)

    for pdf in pdf_files:
        stem = pdf.stem
        digits = _re.sub(r"[^\d]", "", stem)

        if pattern == "ssn" and len(digits) >= 9:
            ssn_candidate = digits[:9]
            row = conn.execute(
                "SELECT id FROM cr_records WHERE ssn = ? OR ssn = ? LIMIT 1",
                (ssn_candidate, f"{ssn_candidate[:3]}-{ssn_candidate[3:5]}-{ssn_candidate[5:]}"),
            ).fetchone()
            if row:
                conn.execute("UPDATE cr_records SET report_file = ? WHERE id = ?", (str(pdf.resolve()), row[0]))
                linked += 1
                logger.info("  Linked %s → record #%d", pdf.name, row[0])
        elif pattern == "name":
            parts = _re.split(r"[_\-\s]+", stem)
            name_parts = [p for p in parts if p.isalpha() and len(p) >= 2]
            if len(name_parts) >= 2:
                fn, ln = name_parts[0].upper(), name_parts[1].upper()
                row = conn.execute(
                    "SELECT id FROM cr_records WHERE upper(first_name) LIKE ? AND upper(last_name) = ? LIMIT 1",
                    (f"{fn}%", ln),
                ).fetchone()
                if row:
                    conn.execute("UPDATE cr_records SET report_file = ? WHERE id = ?", (str(pdf.resolve()), row[0]))
                    linked += 1
                    logger.info("  Linked %s → record #%d", pdf.name, row[0])

    conn.commit()
    logger.info("Linked %d PDF files to CR records", linked)
    return linked


def main() -> None:
    parser = argparse.ArgumentParser(description="Lookup API — data importer")
    parser.add_argument(
        "command",
        choices=["persons", "licenses", "cr_records", "rebuild-fts", "link-pdfs"],
        help="What to import / do",
    )
    parser.add_argument("file", nargs="?", help="CSV/TSV file path or PDF directory (for link-pdfs)")
    parser.add_argument("--db", default="/app/data/lookup.db", help="SQLite DB path")
    parser.add_argument("--sep", default=",", help="CSV delimiter (use 'tab' for \\t)")
    parser.add_argument("--match", default="ssn", choices=["ssn", "name"], help="PDF matching strategy for link-pdfs")
    args = parser.parse_args()

    sep = "\t" if args.sep.lower() in ("tab", "\\t", "\t") else args.sep

    db_path = Path(args.db)
    if not db_path.exists():
        logger.error("DB not found: %s  (start the API first so it initialises the DB)", db_path)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")

    try:
        if args.command == "rebuild-fts":
            rebuild_fts(conn)
        elif args.command == "link-pdfs":
            if not args.file:
                parser.error("PDF directory path required for link-pdfs")
            pdf_dir = Path(args.file)
            if not pdf_dir.is_dir():
                logger.error("Not a directory: %s", pdf_dir)
                sys.exit(1)
            n = link_pdfs(conn, pdf_dir, pattern=args.match)
            logger.info("Done. Linked: %d", n)
        else:
            if not args.file:
                parser.error("file argument required for import commands")
            csv_path = Path(args.file)
            if not csv_path.exists():
                logger.error("File not found: %s", csv_path)
                sys.exit(1)

            if args.command == "persons":
                n = import_persons(conn, csv_path, sep)
            elif args.command == "licenses":
                n = import_licenses(conn, csv_path, sep)
            else:
                n = import_cr_records(conn, csv_path, sep)

            logger.info("Done. Total inserted: %d", n)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
