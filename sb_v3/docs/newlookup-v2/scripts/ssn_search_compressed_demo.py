#!/usr/bin/env python3
"""
Демо: «сжатые» запросы SSN search — один вызов на уникальный ZIP,
слияние ответов по id, вывод всех уникальных кандидатов.

Подхватывает .env.usfull.local из корня репо (если есть).
Нужны переменные:
  LOOKUP_API_KEY
  LOOKUP_API_BASE_URL (по умолчанию https://usfull.pro)
  LOOKUP_API_BASIC_AUTH=логин:пароль   — для USFULL search

Запуск из корня репозитория:
  export LOOKUP_API_BASIC_AUTH='user:pass'
  python3 scripts/ssn_search_compressed_demo.py

Не коммить пароли. SSN в консоли маскируются.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = REPO_ROOT / ".env.usfull.local"


def load_dotenv_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if key and key not in os.environ:
            os.environ[key] = val


def ssn_present(s: str | None) -> str:
    """В лог не выводим цифры SSN — только факт наличия."""
    if not s:
        return "—"
    d = re.sub(r"\D", "", str(s))
    return "да" if len(d) == 9 else "?"


def usfull_search(
    base: str,
    api_key: str,
    basic: tuple[str, str],
    payload: dict[str, Any],
    timeout: float = 60.0,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/api/search/"
    body = json.dumps(payload).encode("utf-8")
    token = base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode("ascii")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("X-API-KEY", api_key)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "ssn-compressed-demo/1.0")
    req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_zips(zips: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for z in zips:
        d = re.sub(r"\D", "", str(z))[:5]
        if len(d) == 5 and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def compressed_search(
    base: str,
    api_key: str,
    basic: tuple[str, str],
    firstname: str,
    lastname: str,
    st: str,
    zips: list[str],
) -> tuple[dict[int, dict[str, Any]], int]:
    """
    Один HTTP-запрос на каждый уникальный ZIP; результаты мержатся по полю id.
    Возвращает (merged_by_id, num_http_calls).
    """
    merged: dict[int, dict[str, Any]] = {}
    calls = 0
    for zipcode in normalize_zips(zips):
        calls += 1
        payload = {
            "firstname": firstname,
            "lastname": lastname,
            "st": st.upper(),
            "zip": zipcode,
        }
        data = usfull_search(base, api_key, basic, payload)
        for row in data.get("results") or []:
            rid = row.get("id")
            if rid is not None:
                merged[int(rid)] = row
    return merged, calls


def print_candidates(label: str, merged: dict[int, dict[str, Any]], calls: int, zips_used: list[str]) -> None:
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print(f"Уникальных ZIP в запросе: {len(zips_used)} → HTTP-вызовов: {calls}")
    print(f"Уникальных кандидатов после merge по id: {len(merged)}")
    print("-" * 60)
    rows = sorted(merged.values(), key=lambda r: (r.get("zip") or "", r.get("lastname") or ""))
    for r in rows:
        addr = (r.get("address") or "")[:44]
        suf = "…" if len(str(r.get("address") or "")) > 44 else ""
        print(
            f"  id={r.get('id')} | "
            f"{r.get('firstname','')} {r.get('middlename') or ''} {r.get('lastname','')} {r.get('name_suff') or ''} | "
            f"{r.get('city','')}, {r.get('st','')} {r.get('zip','')} | "
            f"{addr}{suf} | "
            f"SSN_есть:{ssn_present(r.get('ssn'))}"
        )


def main() -> int:
    load_dotenv_file(ENV_LOCAL)
    api_key = os.environ.get("LOOKUP_API_KEY", "").strip()
    base = os.environ.get("LOOKUP_API_BASE_URL", "https://usfull.pro").strip()
    auth_raw = os.environ.get("LOOKUP_API_BASIC_AUTH", "").strip()
    if not api_key or ":" not in auth_raw:
        print(
            "Задайте LOOKUP_API_KEY и LOOKUP_API_BASIC_AUTH=user:pass\n"
            f"(можно положить ключ в {ENV_LOCAL})",
            file=sys.stderr,
        )
        return 1
    user, _, pw = auth_raw.partition(":")
    basic = (user, pw)

    # «Что есть сейчас» из твоих fullz: основной zip + zip из других типичных строк по PA
    # (15211, 18954, 18944 — встречались в выдаче Thomas Dickson + PA без zip)
    demo_cases: list[dict[str, Any]] = [
        {
            "label": "Thomas Dickson — сжатие по ZIP (Earp St + возможные старые PA zip)",
            "firstname": "Thomas",
            "lastname": "Dickson",
            "st": "PA",
            "zips": ["19147", "15211", "18954", "18944"],
        },
        {
            "label": "Stephen Rudolph — один целевой ZIP (American St)",
            "firstname": "Stephen",
            "lastname": "Rudolph",
            "st": "PA",
            "zips": ["19147"],
        },
    ]

    for case in demo_cases:
        zips = normalize_zips(case["zips"])
        try:
            merged, calls = compressed_search(
                base,
                api_key,
                basic,
                case["firstname"],
                case["lastname"],
                case["st"],
                zips,
            )
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
            return 1
        except urllib.error.URLError as e:
            print(f"Network error: {e}", file=sys.stderr)
            return 1
        print_candidates(case["label"], merged, calls, zips)

    print(f"\n{'=' * 60}")
    print("Готово. Сравни: один запрос «имя+PA» даёт сотни строк; здесь — только пересечение с выбранными ZIP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
