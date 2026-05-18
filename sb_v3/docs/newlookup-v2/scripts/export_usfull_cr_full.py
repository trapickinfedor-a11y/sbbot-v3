#!/usr/bin/env python3
"""Сохранить полные ответы POST /api/cr/ в data/usfull_cr_full_search_report.json.

Параметры запросов (без коммита SSN в git): положите файл

  data/cr_export_inputs.json

формат:
{
  "sean_piwowar": { "first_name":"...", "last_name":"...", "street_address":"...",
    "city":"...", "state":"...", "zip_code":"...", "dob":"MM/DD/YYYY", "ssn":"9digits" },
  ...
}

Ключи — любые строки (станут именами блоков в отчёте).

  export LOOKUP_API_KEY='...'
  python3 scripts/export_usfull_cr_full.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT = REPO / "data" / "cr_export_inputs.json"
OUT = REPO / "data" / "usfull_cr_full_search_report.json"


def main() -> int:
    if not INPUT.is_file():
        print(f"Create {INPUT} with CR request objects (see script docstring).", file=sys.stderr)
        return 1

    cases: dict[str, dict] = json.loads(INPUT.read_text(encoding="utf-8"))
    if not isinstance(cases, dict) or not cases:
        print("cr_export_inputs.json must be a non-empty object", file=sys.stderr)
        return 1

    base = os.environ.get("LOOKUP_API_BASE_URL", "https://usfull.pro").rstrip("/")
    key = os.environ.get("LOOKUP_API_KEY", "").strip()
    if not key:
        load = REPO / ".env.usfull.local"
        if load.is_file():
            for line in load.read_text().splitlines():
                if line.startswith("LOOKUP_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        print("Set LOOKUP_API_KEY", file=sys.stderr)
        return 1

    out: dict = {}
    for label, payload in cases.items():
        if not isinstance(payload, dict):
            continue
        req = urllib.request.Request(
            f"{base}/api/cr/",
            data=json.dumps(payload).encode(),
            method="POST",
        )
        req.add_header("X-API-Key", key)
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "export-usfull-cr/1.0")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors="replace")
            print(f"{label}: HTTP {e.code} {err[:500]}", file=sys.stderr)
            return 1
        out[str(label)] = {"request": payload, "response": body}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote", OUT, OUT.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
