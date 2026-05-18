from __future__ import annotations

import io
import json
import re
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.brute_bank_group_key import make_brute_group_key
from shared.database.models import BruteBankGroup, BruteBankItem, SellerBank
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_upload_batch_service import SellerUploadBatchService


def _slugify(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower()).strip("_")


def _build_market_bank_code(base_code: str, product_type: str, product_subtype: str) -> str:
    prefix = f"{product_type}_{product_subtype}"
    return f"{prefix}__{base_code}"[:100]


class SellerUploadPipelineService:
    VALID_BANK_CATEGORIES = {"vcc", "personal", "business", "crypto"}
    VALID_ACCOUNT_TYPES = {"CHECKING", "SAVINGS", "BUSINESS", "MONEY MARKET"}

    @staticmethod
    def parse_price(value: Any) -> Decimal:
        if value is None:
            raise ValueError("Price is required")
        try:
            price = Decimal(str(value).replace("$", "").replace(",", ".").strip())
        except (InvalidOperation, ValueError):
            raise ValueError("Invalid price")
        if price <= 0:
            raise ValueError("Price must be positive")
        return price.quantize(Decimal("0.01"))

    @staticmethod
    def parse_log_details(raw_text: Optional[str]) -> Optional[dict]:
        text = (raw_text or "").strip()
        if not text:
            return None

        account_patterns = [
            ("Checking", r"checking:\s*\$?([\d,]+(?:\.\d+)?)"),
            ("Savings", r"savings:\s*\$?([\d,]+(?:\.\d+)?)"),
            ("CC", r"cc(?:\s+avb)?[:\s]*\$?([\d,]+(?:\.\d+)?)"),
            ("Invest", r"invest(?:ment)?[:\s]*\$?([\d,]+(?:\.\d+)?)"),
            ("Line of credit", r"line of credit[:\s]*\$?([\d,]+(?:\.\d+)?)"),
            ("BUS Checking", r"bus checking[:\s]*\$?([\d,]+(?:\.\d+)?)"),
            ("BUS Savings", r"bus savings[:\s]*\$?([\d,]+(?:\.\d+)?)"),
            ("BUS CC", r"bus cc[:\s]*\$?([\d,]+(?:\.\d+)?)"),
        ]
        accounts: list[dict] = []
        lowered = text.lower()
        for label, pattern in account_patterns:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                balance = match.group(1).replace(",", "")
                accounts.append({"type": label, "balance": float(balance)})

        flag_needles = {
            "has_cvv": ("cvv ✅", "cvv+", "cvv in log"),
            "bt_available": ("bt ✅", "bt+", "balance transfer"),
            "promo_available": ("promo ✅", "promo+"),
            "zelle_enroll": ("zelle enroll", "zelle ✅"),
            "wire_available": ("wire ✅",),
            "billpay_available": ("bill pay: ✅", "billpay ✅", "bill pay ✅"),
            "external_available": ("external transfers: ✅", "external ✅"),
            "safepass_unlocked": ("safepass +🔓", "safepass unlocked"),
            "need_phone_enroll": ("need add mobile phone", "need phone enroll"),
        }
        flags = {key: any(needle in lowered for needle in needles) for key, needles in flag_needles.items()}
        return {
            "raw_text": text,
            "accounts": accounts,
            "flags": flags,
        }

    @staticmethod
    def _infer_card_brand(number: str, item_name: str | None = None) -> str | None:
        digits = re.sub(r"\D", "", number or "")
        if digits.startswith("4"):
            return "Visa"
        if digits[:2] in {"34", "37"}:
            return "Amex"
        if digits.startswith("5"):
            return "Mastercard"
        if digits.startswith("6"):
            return "Discover"
        lowered_name = (item_name or "").lower()
        if "visa" in lowered_name:
            return "Visa"
        if "master" in lowered_name or "mc" in lowered_name:
            return "Mastercard"
        if "amex" in lowered_name:
            return "Amex"
        if "discover" in lowered_name:
            return "Discover"
        return None

    @staticmethod
    def parse_cc_line_flexible(
        text: str,
        product_subtype: str,
        item_name: str | None = None,
        is_non_vbv: bool = False,
    ) -> dict | None:
        """Parse a CC/dump line (pipe-separated).

        Primary world-format (all fields after CVV optional):
          NUMBER | EXP | CVV | TYPE | BRAND | LVL | BANK | COUNTRY | HOLDER | ADDR | STATE | CITY | ZIP | Info | REF | PRICE

        EXP accepts:
          MM/YY, MM/YYYY  — slash-separated inside one field
          MM | YYYY       — two separate fields (legacy)

        Returns None when NUMBER / EXP / CVV are invalid.
        Returns a dict that includes an optional ``seller_price`` key when the
        line contains a PRICE column so the caller can override per-card price.
        """
        if not text or text.strip() == "-":
            return None

        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 3:
            return None

        number = re.sub(r"\D", "", parts[0])
        if len(number) < 12:
            return None

        rest = parts[1:]
        exp_mm_raw = ""
        exp_yyyy_raw = ""
        cvv = ""
        tail: list[str] = []

        if rest and "/" in rest[0]:
            # MM/YY or MM/YYYY in one field → next field is CVV
            exp_chunks = [c.strip() for c in rest[0].split("/", 1)]
            if len(exp_chunks) != 2:
                return None
            exp_mm_raw, exp_yyyy_raw = exp_chunks
            if len(rest) < 2:
                return None
            cvv = rest[1]
            tail = rest[2:]          # TYPE | BRAND | LVL | BANK | COUNTRY | HOLDER | ADDR | STATE | CITY | ZIP | Info | REF | PRICE
        elif len(rest) >= 3:
            # MM | YYYY | CVV | ... (legacy split-expiry)
            exp_mm_raw = rest[0]
            exp_yyyy_raw = rest[1]
            cvv = rest[2]
            tail = rest[3:]
        else:
            return None

        if not exp_mm_raw.isdigit() or not exp_yyyy_raw.isdigit():
            return None
        if not cvv or not re.fullmatch(r"\d{3,4}", cvv):
            return None

        exp_mm = int(exp_mm_raw)
        exp_yyyy = int(exp_yyyy_raw)
        if exp_mm < 1 or exp_mm > 12:
            return None
        if exp_yyyy < 100:
            exp_yyyy += 2000
        if exp_yyyy < 2000 or exp_yyyy > 2100:
            return None

        # ── Named columns after CVV (world-format order) ─────────────────────
        _t = tail + [""] * 16
        card_type = _t[0]   # DEBIT / CREDIT
        brand_raw = _t[1]   # Visa / Mastercard / Amex / Discover
        card_lvl  = _t[2]   # CLASSIC / GOLD / PLATINUM …
        bank      = _t[3]   # bank name
        country   = _t[4]   # US / GB / DE …
        holder    = _t[5]   # full cardholder name
        address   = _t[6]   # street address
        state     = _t[7]
        city      = _t[8]
        zip_code  = _t[9]
        info      = _t[10]  # free-text extra info
        ref       = _t[11]  # source / base reference
        price_raw = _t[12]  # optional per-card price

        # Infer brand from number digits; fall back to explicit BRAND column
        brand = SellerUploadPipelineService._infer_card_brand(number, brand_raw or item_name)

        # fname / lname split for legacy DB columns
        holder_parts = holder.split(" ", 1) if holder else []
        fname = holder_parts[0] if holder_parts else None
        lname = holder_parts[1] if len(holder_parts) > 1 else None

        has_fullz = any([holder, address, state, city, zip_code])

        # Optional per-line price override
        seller_price: Decimal | None = None
        if price_raw:
            try:
                seller_price = Decimal(str(price_raw).replace("$", "").replace(",", ".").strip())
                if seller_price <= 0:
                    seller_price = None
            except Exception:
                seller_price = None

        return {
            "number":     number,
            "exp_mm":     exp_mm,
            "exp_yyyy":   exp_yyyy,
            "cvv":        cvv,
            "fname":      fname or None,
            "lname":      lname or None,
            "address":    address or None,
            "city":       city or None,
            "state":      state or None,
            "zip":        zip_code or None,
            "country":    country or None,
            "card_brand": brand,
            "card_level": card_lvl or item_name or None,
            "bank_name":  bank or None,
            "is_non_vbv": is_non_vbv or (product_subtype == "non_vbv"),
            "has_fullz":  has_fullz,
            "seller_price": seller_price,   # None → use batch price
            "extra_data": {
                "bin":       number[:6] if len(number) >= 6 else number,
                "card":      number,
                "exp":       f"{exp_mm:02d}/{str(exp_yyyy)[-2:]}",
                "cvc":       cvv,
                "card_type": card_type or None,
                "brand":     brand or None,
                "level":     card_lvl or None,
                "bank":      bank or None,
                "country":   country or None,
                "zip":       zip_code or None,
                "state":     state or None,
                "city":      city or None,
                "address":   address or None,
                "holder":    holder or None,
                "info":      info or None,
                "ref":       ref or None,
            },
        }

    @staticmethod
    def _sample_presence_flags(sample: dict, *, include_cookies: bool = False) -> dict[str, bool]:
        flags = {
            "has_login": bool(sample.get("login")),
            "has_password": bool(sample.get("password")),
            "has_routing": bool(sample.get("routing_number")),
            "has_holder_name": bool(sample.get("holder_name")),
        }
        if include_cookies:
            flags["has_cookies"] = bool(sample.get("cookies"))
        return flags

    @staticmethod
    def parse_logs_bulk_text(raw_text: str) -> tuple[list[dict], list[dict]]:
        rows: list[dict] = []
        errors: list[dict] = []
        bank_name: str | None = None
        for idx, raw_line in enumerate(raw_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 4:
                errors.append({"line": idx, "error": "Expected SITE|LOGIN|PASS|COOKIES|..."})
                continue
            site, login, password, cookies = parts[:4]
            if not site:
                errors.append({"line": idx, "error": "SITE is required"})
                continue
            if bank_name is None:
                bank_name = site
            elif site.lower() != bank_name.lower():
                errors.append({"line": idx, "error": "All rows in one upload must use the same SITE"})
                continue
            balance = parts[4] if len(parts) > 4 else None
            state = parts[5] if len(parts) > 5 else None
            routing_number = parts[6] if len(parts) > 6 else None
            holder_name = parts[7] if len(parts) > 7 else None
            extra = "|".join(parts[8:]) if len(parts) > 8 else None
            rows.append({
                "site": site,
                "login": login or None,
                "password": password or None,
                "cookies": cookies or None,
                "balance": balance or None,
                "state": state or None,
                "routing_number": routing_number or None,
                "holder_name": holder_name or None,
                "extra": extra or None,
                "raw_line": line,
            })
        return rows, errors

    @staticmethod
    def parse_selfreg_ba_bulk_text(raw_text: str) -> tuple[list[dict], list[dict]]:
        rows: list[dict] = []
        errors: list[dict] = []
        bank_name: str | None = None
        for idx, raw_line in enumerate(raw_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) < 6:
                errors.append({"line": idx, "error": "Expected BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|..."})
                continue
            row_bank = parts[0]
            if not row_bank:
                errors.append({"line": idx, "error": "BANK is required"})
                continue
            if bank_name is None:
                bank_name = row_bank
            elif row_bank.lower() != bank_name.lower():
                errors.append({"line": idx, "error": "All rows in one upload must use the same BANK"})
                continue
            account_number = parts[3]
            routing_number = parts[4]
            balance = parts[5]
            state = parts[6] if len(parts) > 6 else None
            holder_name = parts[7] if len(parts) > 7 else None
            holder_address = parts[8] if len(parts) > 8 else None
            zip_code = parts[9] if len(parts) > 9 else None
            rows.append({
                "bank_name": row_bank,
                "login": parts[1] or None,
                "password": parts[2] or None,
                "account_number": account_number or None,
                "routing_number": routing_number or None,
                "balance": balance or None,
                "state": state or None,
                "holder_name": holder_name or None,
                "holder_address": holder_address or None,
                "zip": zip_code or None,
                "extra": "|".join(parts[10:]) if len(parts) > 10 else None,
                "raw_line": line,
            })
        return rows, errors

    @staticmethod
    def parse_brute_universal_text(raw_text: str, default_price: Any) -> tuple[dict, dict]:
        rows: list[str] = []
        bank_name: str | None = None
        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) >= 1 and parts[0]:
                if bank_name is None:
                    bank_name = parts[0]
                elif parts[0].lower() != bank_name.lower():
                    raise ValueError("All brute rows in one upload must use the same BANK")
            rows.append(line)
        if not rows or not bank_name:
            raise ValueError("No brute rows found")
        items, errors = SellerUploadPipelineService.parse_brute_bulk_text("\n".join(rows), default_price)
        if not items:
            raise ValueError("No valid brute items found")
        summary = {
            "valid_items": len(items),
            "invalid_items": len(errors),
            "errors": errors[:50],
            "preview_lines": [
                f"Bank: {bank_name}",
                f"Valid items: {len(items)}",
                f"Invalid items: {len(errors)}",
            ],
        }
        return {
            "bank_name": bank_name,
            "bank_code": _slugify(bank_name),
            "upload_mode": "bulk",
            "items": items,
        }, summary

    @staticmethod
    def _parse_boolish(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _normalize_mapping_key(value: str) -> str:
        normalized = str(value or "").strip().lower().replace("→", ":")
        normalized = normalized.replace("?", "").replace("-", "_").replace(" ", "_")
        normalized = re.sub(r"[^a-z0-9_]+", "", normalized)
        return normalized.strip("_")

    @staticmethod
    def parse_text_mapping(raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        if not text:
            raise ValueError("Payload is empty")
        if text.startswith("{"):
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a JSON object")
            return payload

        payload: dict[str, Any] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            separator = ":" if ":" in line else ("→" if "→" in line else None)
            if not separator:
                continue
            key, _, value = line.partition(separator)
            normalized_key = SellerUploadPipelineService._normalize_mapping_key(key)
            if normalized_key:
                payload[normalized_key] = value.strip()
        if not payload:
            raise ValueError("Payload must be JSON or KEY: VALUE lines")
        return payload

    @staticmethod
    def _get_payload_value(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        return default

    @staticmethod
    def _coerce_optional_bool(value: Any) -> bool | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"1", "true", "yes", "y", "on", "da", "oui"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
        return None

    @staticmethod
    def _coerce_optional_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _country_flag(country_code: str | None) -> str:
        code = (country_code or "").strip().upper()
        if len(code) != 2 or not code.isalpha():
            return ""
        return "".join(chr(127397 + ord(char)) for char in code)

    @staticmethod
    def _json_dumps(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def normalize_nfc_payload(
        payload: dict[str, Any],
        *,
        seller_price: Any | None = None,
        data_file_path: str | None = None,
    ) -> dict[str, Any]:
        bank_name = str(
            SellerUploadPipelineService._get_payload_value(payload, "bank_name", "bank", default="")
        ).strip()
        if not bank_name:
            raise ValueError("bank_name is required")
        country = str(
            SellerUploadPipelineService._get_payload_value(payload, "country", default="US")
        ).strip().upper()
        if not country:
            raise ValueError("country is required")
        raw_nfc_type = str(
            SellerUploadPipelineService._get_payload_value(payload, "nfc_type", "type", default="ap")
        ).strip().lower()
        if raw_nfc_type in {"apple_pay", "apple", "ap"}:
            nfc_type = "ap"
        elif raw_nfc_type in {"google_pay", "google", "gp"}:
            nfc_type = "gp"
        elif raw_nfc_type in {"other", "misc"}:
            nfc_type = "other"
        else:
            raise ValueError("nfc_type must be AP, GP, or Other")
        normalized = {
            "bank_name": bank_name,
            "country": country,
            "country_flag": SellerUploadPipelineService._country_flag(country),
            "state": str(payload.get("state") or "").strip() or None,
            "zip": str(payload.get("zip") or "").strip() or None,
            "nfc_type": nfc_type,
        }
        if seller_price is not None:
            normalized["seller_price"] = str(SellerUploadPipelineService.parse_price(seller_price))
        if data_file_path is not None:
            normalized["data_file_path"] = data_file_path
        return normalized

    @staticmethod
    def normalize_otp_payload(payload: dict[str, Any], *, seller_price: Any | None = None) -> dict[str, Any]:
        bank_name = str(
            SellerUploadPipelineService._get_payload_value(payload, "bank_name", "bank", default="")
        ).strip()
        if not bank_name:
            raise ValueError("bank_name is required")
        balance = SellerUploadPipelineService.parse_price(
            SellerUploadPipelineService._get_payload_value(payload, "balance", default=None)
        )
        raw_sms_access = str(
            SellerUploadPipelineService._get_payload_value(payload, "sms_access_type", "sms_access", default="")
        ).strip().lower()
        sms_mapping = {
            "seller_mediated": "seller_mediated",
            "through_seller": "seller_mediated",
            "seller": "seller_mediated",
            "seller_chat": "seller_mediated",
            "account_access": "account_access",
            "account": "account_access",
            "via_account": "account_access",
        }
        sms_access_type = sms_mapping.get(raw_sms_access)
        if not sms_access_type:
            raise ValueError("sms_access_type must be seller_mediated or account_access")
        normalized = {
            "bank_name": bank_name,
            "balance": str(balance),
            "has_fullz": bool(
                SellerUploadPipelineService._coerce_optional_bool(payload.get("has_fullz"))
            ),
            "sms_access_type": sms_access_type,
            "seller_description": str(
                SellerUploadPipelineService._get_payload_value(
                    payload,
                    "seller_description",
                    "description",
                    "additional_description",
                    default="",
                )
            ).strip()
            or None,
        }
        if seller_price is not None:
            normalized["seller_price"] = str(SellerUploadPipelineService.parse_price(seller_price))
        return normalized

    @staticmethod
    def normalize_selfreg_cc_payload(payload: dict[str, Any], *, seller_price: Any | None = None) -> dict[str, Any]:
        bank_name = str(
            SellerUploadPipelineService._get_payload_value(payload, "bank_name", "bank", default="")
        ).strip()
        if not bank_name:
            raise ValueError("bank_name is required")
        has_vcc = SellerUploadPipelineService._coerce_optional_bool(
            SellerUploadPipelineService._get_payload_value(payload, "has_vcc", "vcc", default=None)
        )
        vcc_limit = SellerUploadPipelineService._get_payload_value(payload, "vcc_limit", default=None)
        normalized = {
            "bank_name": bank_name,
            "card_name": str(payload.get("card_name") or payload.get("card_title") or "").strip() or None,
            "credit_limit": (
                str(SellerUploadPipelineService.parse_price(payload.get("credit_limit")))
                if payload.get("credit_limit") not in (None, "")
                else None
            ),
            "vcc_limit": (
                str(SellerUploadPipelineService.parse_price(vcc_limit))
                if has_vcc and vcc_limit not in (None, "")
                else None
            ),
            "state": str(payload.get("state") or "").strip().upper() or None,
            "zip": str(payload.get("zip") or "").strip() or None,
            "has_email": bool(SellerUploadPipelineService._coerce_optional_bool(payload.get("has_email"))),
            "has_phone": bool(SellerUploadPipelineService._coerce_optional_bool(payload.get("has_phone"))),
            "phone_days_remaining": SellerUploadPipelineService._coerce_optional_int(payload.get("phone_days_remaining")),
            "phone_renewable": SellerUploadPipelineService._coerce_optional_bool(payload.get("phone_renewable")),
            "phone_change_allowed": SellerUploadPipelineService._coerce_optional_bool(
                payload.get("phone_change_allowed")
            ),
            "online_access": bool(SellerUploadPipelineService._coerce_optional_bool(payload.get("online_access"))),
        }
        if seller_price is not None:
            normalized["seller_price"] = str(SellerUploadPipelineService.parse_price(seller_price))
        return normalized

    @staticmethod
    def _read_json_from_zip(file_bytes: bytes, expected_name: str) -> tuple[dict, str]:
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                file_names = [name for name in archive.namelist() if not name.endswith("/")]
                json_name = next(
                    (
                        name
                        for name in file_names
                        if name.lower().split("/")[-1] == expected_name.lower()
                    ),
                    None,
                )
                if not json_name:
                    raise ValueError(f"ZIP must contain {expected_name}")
                raw_payload = archive.read(json_name).decode("utf-8", errors="ignore")
        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive") from exc
        except KeyError as exc:
            raise ValueError(f"ZIP archive is missing {expected_name}") from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{expected_name} must contain valid JSON") from exc

        if not isinstance(payload, dict):
            raise ValueError(f"{expected_name} must contain a JSON object")

        return payload, raw_payload

    @staticmethod
    def _read_zip_payload(file_bytes: bytes, expected_names: list[str]) -> tuple[dict, str, list[str]]:
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                file_names = [name for name in archive.namelist() if not name.endswith("/")]
                lowered_names = {PurePosixPath(name).name.lower(): name for name in file_names}
                payload_name = next((lowered_names.get(candidate.lower()) for candidate in expected_names if lowered_names.get(candidate.lower())), None)
                if not payload_name:
                    raise ValueError(f"ZIP must contain one of: {', '.join(expected_names)}")
                raw_payload = archive.read(payload_name).decode("utf-8", errors="ignore")
        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive") from exc
        except KeyError as exc:
            raise ValueError(f"ZIP archive is missing one of: {', '.join(expected_names)}") from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{PurePosixPath(payload_name).name} must contain valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{PurePosixPath(payload_name).name} must contain a JSON object")
        return payload, raw_payload, file_names

    @staticmethod
    def _parse_required_bool(value: Any, field_name: str) -> bool:
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
        raise ValueError(f"{field_name} must be a boolean")

    @staticmethod
    def _parse_required_float(value: Any, field_name: str) -> float:
        if value in (None, ""):
            raise ValueError(f"{field_name} is required")
        try:
            return float(str(value).replace("$", "").replace(",", "").strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a number") from exc

    @staticmethod
    def _parse_required_int(value: Any, field_name: str) -> int:
        if value in (None, ""):
            raise ValueError(f"{field_name} is required")
        try:
            return int(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be an integer") from exc

    @staticmethod
    def parse_enroll_zip(zip_bytes: bytes, price: float) -> dict:
        inspected = SellerUploadPipelineService.inspect_enroll_archive(zip_bytes)
        seller_price = float(SellerUploadPipelineService.parse_price(price))
        return {
            **inspected,
            "price": seller_price,
        }

    @staticmethod
    def inspect_enroll_archive(zip_bytes: bytes) -> dict:
        payload, raw_payload, _ = SellerUploadPipelineService._read_zip_payload(
            zip_bytes,
            ["enroll_data.json", "metadata.json"],
        )

        portal = str(payload.get("portal") or "").strip()
        if not portal:
            raise ValueError("enroll_data.json must include portal")
        balance = SellerUploadPipelineService._parse_required_float(payload.get("balance"), "balance")
        has_ssn = SellerUploadPipelineService._parse_required_bool(payload.get("has_ssn"), "has_ssn")
        has_dob = SellerUploadPipelineService._parse_required_bool(payload.get("has_dob"), "has_dob")
        has_address = SellerUploadPipelineService._parse_required_bool(payload.get("has_address"), "has_address")
        has_docs = SellerUploadPipelineService._parse_required_bool(payload.get("has_docs"), "has_docs")
        online_access = SellerUploadPipelineService._parse_required_bool(payload.get("online_access"), "online_access")
        return {
            "portal": portal,
            "balance": balance,
            "has_ssn": has_ssn,
            "has_dob": has_dob,
            "has_address": has_address,
            "has_docs": has_docs,
            "online_access": online_access,
            "title": f"Enroll | {portal} | ${balance:,.0f}",
            "preview_lines": [
                f"Portal: {portal}",
                f"Balance: ${balance:,.0f}",
                f"SSN: {'yes' if has_ssn else 'no'} | DOB: {'yes' if has_dob else 'no'}",
                f"Address: {'yes' if has_address else 'no'} | Docs: {'yes' if has_docs else 'no'}",
            ],
            "raw_data": raw_payload,
        }

    @staticmethod
    def parse_selfreg_ba_zip(zip_bytes: bytes, price: float) -> dict:
        inspected = SellerUploadPipelineService.inspect_selfreg_ba_archive(zip_bytes)
        seller_price = float(SellerUploadPipelineService.parse_price(price))
        return {
            **inspected,
            "price": seller_price,
        }

    @staticmethod
    def inspect_selfreg_ba_archive(zip_bytes: bytes) -> dict:
        payload, raw_payload, _ = SellerUploadPipelineService._read_zip_payload(
            zip_bytes,
            ["ba_data.json", "metadata.json"],
        )

        bank = str(payload.get("bank") or "").strip()
        if not bank:
            raise ValueError("ba_data.json must include bank")

        state = str(payload.get("state") or "").strip().upper()
        if not state:
            raise ValueError("ba_data.json must include state")

        balance = SellerUploadPipelineService._parse_required_float(
            payload.get("balance"),
            "balance",
        )
        has_phone = SellerUploadPipelineService._parse_required_bool(payload.get("has_phone"), "has_phone")
        phone_days_remaining = SellerUploadPipelineService._parse_required_int(
            payload.get("phone_days_remaining"),
            "phone_days_remaining",
        )
        if phone_days_remaining < 0:
            raise ValueError("phone_days_remaining must be >= 0")

        email_access = SellerUploadPipelineService._parse_required_bool(payload.get("email_access"), "email_access")
        has_ssn = SellerUploadPipelineService._parse_required_bool(payload.get("has_ssn"), "has_ssn")
        has_docs = SellerUploadPipelineService._parse_required_bool(payload.get("has_docs"), "has_docs")
        return {
            "bank": bank,
            "balance": balance,
            "state": state,
            "has_phone": has_phone,
            "phone_days_remaining": phone_days_remaining,
            "email_access": email_access,
            "has_ssn": has_ssn,
            "has_docs": has_docs,
            "title": f"{bank} | ${balance:,.0f} | {state}",
            "preview_lines": [
                f"Bank: {bank}",
                f"Balance: ${balance:,.0f}",
                f"State: {state}",
                f"Phone: {'yes' if has_phone else 'no'} | Email: {'yes' if email_access else 'no'}",
            ],
            "raw_data": raw_payload,
        }

    @staticmethod
    def parse_logs_zip(zip_bytes: bytes, price: float) -> dict:
        inspected = SellerUploadPipelineService.inspect_logs_archive(zip_bytes)
        seller_price = float(SellerUploadPipelineService.parse_price(price))
        return {
            **inspected,
            "price": seller_price,
        }

    @staticmethod
    def inspect_logs_archive(zip_bytes: bytes) -> dict:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
                file_names = [name for name in archive.namelist() if not name.endswith("/")]
                metadata_name = next(
                    (
                        name
                        for name in file_names
                        if name.lower().split("/")[-1] == "metadata.json"
                    ),
                    None,
                )
                if not metadata_name:
                    raise ValueError("ZIP must contain metadata.json")

                raw_payload = archive.read(metadata_name).decode("utf-8", errors="ignore")
                has_cookies = any(
                    name.lower().startswith("cookies/") or "/cookies/" in name.lower()
                    for name in file_names
                )
                has_screenshot = any(
                    name.lower().split("/")[-1] == "screenshot.png"
                    for name in file_names
                )
        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive") from exc
        except KeyError as exc:
            raise ValueError("ZIP archive is missing metadata.json") from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError("metadata.json must contain valid JSON") from exc

        if not isinstance(payload, dict):
            raise ValueError("metadata.json must contain a JSON object")

        bank = str(payload.get("bank") or "").strip()
        if not bank:
            raise ValueError("metadata.json must include bank")

        total_balance = SellerUploadPipelineService._parse_required_float(
            payload.get("total_balance"),
            "total_balance",
        )
        has_cvv = SellerUploadPipelineService._parse_required_bool(payload.get("has_cvv"), "has_cvv")
        bt_available = SellerUploadPipelineService._parse_required_bool(payload.get("bt_available"), "bt_available")
        promo_available = SellerUploadPipelineService._parse_required_bool(payload.get("promo_available"), "promo_available")
        zelle_enroll = SellerUploadPipelineService._parse_required_bool(payload.get("zelle_enroll"), "zelle_enroll")
        wire_available = SellerUploadPipelineService._parse_required_bool(payload.get("wire_available"), "wire_available")
        safepass_unlocked = SellerUploadPipelineService._parse_required_bool(payload.get("safepass_unlocked"), "safepass_unlocked")
        email_valid = SellerUploadPipelineService._parse_required_bool(payload.get("email_valid"), "email_valid")
        return {
            "bank": bank,
            "total_balance": total_balance,
            "has_cvv": has_cvv,
            "bt_available": bt_available,
            "promo_available": promo_available,
            "zelle_enroll": zelle_enroll,
            "wire_available": wire_available,
            "safepass_unlocked": safepass_unlocked,
            "email_valid": email_valid,
            "has_cookies": has_cookies,
            "has_screenshot": has_screenshot,
            "title": f"{bank} | ${total_balance:,.0f}",
            "preview_lines": [
                f"Bank: {bank}",
                f"Total balance: ${total_balance:,.0f}",
                f"Flags: CVV={'yes' if has_cvv else 'no'} | BT={'yes' if bt_available else 'no'} | Promo={'yes' if promo_available else 'no'}",
                f"Cookies: {'yes' if has_cookies else 'no'} | Screenshot: {'yes' if has_screenshot else 'no'}",
            ],
            "raw_data": raw_payload,
        }

    @staticmethod
    def inspect_nfc_archive(file_bytes: bytes) -> dict:
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                file_names = [name for name in archive.namelist() if not name.endswith("/")]
                data_name = next(
                    (
                        name for name in file_names
                        if name.lower().endswith((".apk", ".txt", ".zip"))
                        and PurePosixPath(name).name.lower() != "instruction.txt"
                    ),
                    None,
                )
                instruction_name = next(
                    (name for name in file_names if name.lower().split("/")[-1] == "instruction.txt"),
                    None,
                )
                instruction_text = archive.read(instruction_name).decode("utf-8", errors="ignore") if instruction_name else ""
        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive") from exc
        if not data_name:
            raise ValueError("ZIP must contain a .txt, .zip or .apk data file")
        if not instruction_name:
            raise ValueError("ZIP must contain instruction.txt")
        metadata: dict[str, str] = {}
        for line in instruction_text.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            metadata[key.strip().lower()] = value.strip()
        data_basename = data_name.split("/")[-1].rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
        normalized = SellerUploadPipelineService.normalize_nfc_payload({
            "bank_name": metadata.get("bank_name") or metadata.get("bank") or data_basename or "NFC Upload",
            "country": metadata.get("country") or "US",
            "state": metadata.get("state") or None,
            "zip": metadata.get("zip") or None,
            "nfc_type": metadata.get("nfc_type") or metadata.get("type") or "ap",
        })
        return {
            "data_name": data_name,
            "instruction_name": instruction_name,
            "file_count": len(file_names),
            **normalized,
            "preview_lines": [
                f"Data file: {data_name}",
                f"Instruction: {instruction_name}",
                f"Bank: {normalized['bank_name']}",
                f"Type: {'Apple Pay' if normalized['nfc_type'] == 'ap' else 'Google Pay' if normalized['nfc_type'] == 'gp' else 'Other'}",
                f"Archive files: {len(file_names)}",
            ],
        }

    @staticmethod
    def inspect_check_archive(file_bytes: bytes) -> dict:
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                file_names = [name for name in archive.namelist() if not name.endswith("/")]
                json_name = next(
                    (name for name in file_names if name.lower().split("/")[-1] == "check_data.json"),
                    None,
                )
                scan_name = next(
                    (
                        name for name in file_names
                        if name.lower().split("/")[-1] in {"scan.jpg", "scan.jpeg", "scan.png", "scan.webp"}
                    ),
                    None,
                )
                template_name = next(
                    (
                        name for name in file_names
                        if name.lower().split("/")[-1] in {"template.pdf", "check_template.pdf"}
                    ),
                    None,
                )
                if not json_name:
                    raise ValueError("ZIP must contain check_data.json")
                if not scan_name:
                    raise ValueError("ZIP must contain scan.jpg or another supported scan image")
                raw_payload = archive.read(json_name).decode("utf-8", errors="ignore")
        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP archive") from exc
        except KeyError as exc:
            raise ValueError("ZIP archive is missing check_data.json") from exc

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError("check_data.json must contain valid JSON") from exc

        check_type = str(payload.get("check_type") or "").strip().lower()
        if not check_type:
            raise ValueError("check_data.json must include check_type")
        amount = SellerUploadPipelineService.parse_price(payload.get("amount"))
        has_holder_name = SellerUploadPipelineService._parse_boolish(payload.get("has_holder_name"))
        return {
            "check_type": check_type,
            "amount": str(amount),
            "has_holder_name": has_holder_name,
            "has_address": SellerUploadPipelineService._parse_boolish(payload.get("has_address")),
            "bank_name": (payload.get("bank_name") or "Uploaded Check").strip(),
            "state": ((payload.get("state") or "").strip() or None),
            "zip": ((payload.get("zip") or "").strip() or None),
            "check_date": ((payload.get("check_date") or "").strip() or None),
            "status": ((payload.get("status") or "").strip() or None),
            "seller_description": ((payload.get("seller_description") or "").strip() or None),
            "scan_name": scan_name,
            "template_name": template_name,
            "json_name": json_name,
            "preview_lines": [
                f"Check type: {check_type}",
                f"Amount: ${amount:.2f}",
                f"Holder name: {'yes' if has_holder_name else 'no'}",
                f"Scan: {scan_name}",
                f"Template: {template_name or 'not included'}",
            ],
        }

    @staticmethod
    def validate_bank_payload(payload: dict, seller_id: int) -> tuple[dict, dict]:
        bank_name = (payload.get("bank_name") or "").strip()
        if len(bank_name) < 2:
            raise ValueError("Bank name must be at least 2 characters")
        category = (payload.get("category") or "").strip().lower()
        if category not in SellerUploadPipelineService.VALID_BANK_CATEGORIES:
            raise ValueError("Invalid bank category")
        product_type = (payload.get("product_type") or "bank").strip().lower()
        product_subtype = (payload.get("product_subtype") or "log").strip().lower()
        if product_type not in {"bank", "enrol"}:
            raise ValueError("Invalid product type")
        if product_type == "enrol":
            product_subtype = "selfreg"
        elif product_subtype not in {"log", "selfreg"}:
            raise ValueError("Invalid bank subtype")
        stock_count = int(payload.get("stock_count") or 0)
        if stock_count < 0 or stock_count > 1000:
            raise ValueError("Stock count must be between 0 and 1000")
        seller_price = SellerUploadPipelineService.parse_price(payload.get("seller_price"))
        number_access_available = bool(payload.get("number_access_available", False))
        rental_days_raw = payload.get("rental_days")
        rental_days = int(rental_days_raw) if rental_days_raw not in (None, "", False) else None
        adaptive_report_enabled = bool(payload.get("adaptive_report_enabled", False))
        number_change_allowed = bool(payload.get("number_change_allowed", False))
        auto_unpublish_enabled = bool(payload.get("auto_unpublish_enabled", False))
        listing_duration_days_raw = payload.get("listing_duration_days")
        listing_duration_days = int(listing_duration_days_raw) if listing_duration_days_raw not in (None, "", False) else None
        if number_access_available and (rental_days is None or rental_days <= 0):
            raise ValueError("Rental days are required when number access is enabled")
        if not number_access_available:
            rental_days = None
            adaptive_report_enabled = False
        if auto_unpublish_enabled and (listing_duration_days is None or listing_duration_days <= 0):
            raise ValueError("Listing duration days are required when auto-unpublish is enabled")
        if not auto_unpublish_enabled:
            listing_duration_days = None
        base_code = (payload.get("bank_code") or "").strip().lower()
        if base_code:
            base_code = _slugify(base_code)
        else:
            base_code = f"s{seller_id}_{_slugify(bank_name)}"
        bank_code = _build_market_bank_code(base_code, product_type, product_subtype)
        normalized = {
            "bank_name": bank_name,
            "bank_code": bank_code,
            "base_code": base_code,
            "category": category,
            "product_type": product_type,
            "product_subtype": product_subtype,
            "seller_price": str(seller_price),
            "description": ((payload.get("description") or "").strip() or None),
            "instruction": ((payload.get("instruction") or "").strip() or None),
            "stock_count": stock_count,
            "has_chat": bool(payload.get("has_chat", True)),
            "number_access_available": number_access_available,
            "rental_days": rental_days,
            "adaptive_report_enabled": adaptive_report_enabled,
            "number_change_allowed": number_change_allowed,
            "auto_unpublish_enabled": auto_unpublish_enabled,
            "listing_duration_days": listing_duration_days,
            "state": ((payload.get("state") or "").strip() or None),
            "zip": ((payload.get("zip") or "").strip() or None),
            "portal": ((payload.get("portal") or "").strip() or None),
            "card_type": ((payload.get("card_type") or "").strip() or None),
            "has_ssn": bool(payload.get("has_ssn", False)),
            "has_dob": bool(payload.get("has_dob", False)),
            "has_name": bool(payload.get("has_name", False)),
            "has_address": bool(payload.get("has_address", False)),
            "has_email": bool(payload.get("has_email", False)),
            "has_security_qa": bool(payload.get("has_security_qa", False)),
            "has_docs": bool(payload.get("has_docs", False)),
            "doc_type": ((payload.get("doc_type") or "").strip() or None),
            "phone_area_code": ((payload.get("phone_area_code") or "").strip() or None),
            "details": payload.get("details") or SellerUploadPipelineService.parse_log_details(payload.get("details_text")),
        }
        summary = {
            "preview_lines": [
                f"Bank: {bank_name}",
                f"Product: {product_type}/{product_subtype}",
                f"Category: {category}",
                f"Code: {bank_code}",
                f"Qty: {stock_count}",
                f"Seller price: ${seller_price:.2f}",
                f"Chat: {'enabled' if normalized['has_chat'] else 'disabled'}",
                f"Number access: {'yes' if number_access_available else 'no'}",
                f"Rental days: {rental_days or '-'}",
                f"Number change allowed: {'yes' if number_change_allowed else 'no'}",
                f"Auto-unpublish days: {listing_duration_days or '-'}",
                f"State: {normalized['state'] or '-'}",
                f"ZIP: {normalized['zip'] or '-'}",
            ],
            "valid_items": max(stock_count, 1),
            "invalid_items": 0,
        }
        return normalized, summary

    @staticmethod
    def parse_brute_bulk_text(raw_text: str, default_price: Any = None) -> tuple[list[dict], list[dict]]:
        items: list[dict] = []
        errors: list[dict] = []
        seen = set()
        default_price_value = None
        if default_price not in (None, "", False):
            default_price_value = SellerUploadPipelineService.parse_price(default_price)
        for idx, raw_line in enumerate(raw_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 9:
                errors.append({"line": idx, "error": "Expected BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS"})
                continue
            bank_name = parts[0]
            login = parts[1]
            password = parts[2]
            account_number = parts[3]
            routing_number = parts[4]
            balance_info = parts[5]
            state = parts[6]
            holder_name = parts[7]
            holder_address = parts[8]
            key = (login, password)
            if key in seen:
                errors.append({"line": idx, "error": "Duplicate credentials in batch"})
                continue
            seen.add(key)
            if default_price_value is None:
                errors.append({"line": idx, "error": "Default price is required for brute bulk upload"})
                continue
            items.append({
                "bank_name": bank_name,
                "credentials": {
                    "login": login,
                    "password": password,
                    "extra": "",
                },
                "account_number": account_number or None,
                "routing_number": routing_number or None,
                "balance_info": balance_info or None,
                "price": str(default_price_value),
                "balance_range": None,
                "account_type": None,
                "state": state or None,
                "holder_name": holder_name or None,
                "holder_address": holder_address or None,
            })
        return items, errors

    @staticmethod
    async def validate_brute_payload(payload: dict) -> tuple[dict, dict]:
        bank_name = (payload.get("bank_name") or "").strip()
        bank_code = _slugify((payload.get("bank_code") or "").strip().lower())
        category = (payload.get("category") or "general").strip().lower()
        upload_mode = (payload.get("upload_mode") or "single").strip().lower()
        if len(bank_name) < 2:
            raise ValueError("Bank name must be at least 2 characters")
        if not bank_code:
            raise ValueError("Bank code is required")
        if upload_mode not in {"single", "bulk"}:
            raise ValueError("Invalid upload mode")

        if upload_mode == "single":
            account_type = ((payload.get("account_type") or "").strip().upper() or None)
            if account_type and account_type not in SellerUploadPipelineService.VALID_ACCOUNT_TYPES:
                raise ValueError("Unsupported account type")
            credentials = payload.get("credentials") or {}
            if not credentials or not any((value or "").strip() for value in credentials.values()):
                raise ValueError("Credentials are required")
            price = SellerUploadPipelineService.parse_price(payload.get("price"))
            normalized_items = [{
                "credentials": credentials,
                "balance_info": ((payload.get("balance_info") or "").strip() or None),
                "price": str(price),
                "balance_range": ((payload.get("balance_range") or "").strip() or None),
                "account_type": account_type,
            }]
            error_report = []
        else:
            normalized_items, error_report = SellerUploadPipelineService.parse_brute_bulk_text(
                payload.get("bulk_text") or "",
                payload.get("default_price"),
            )
            if not normalized_items:
                raise ValueError("No valid brute items found")

        attributes = ((payload.get("attributes") or "").strip() or None)
        normalized = {
            "bank_name": bank_name,
            "bank_code": bank_code,
            "category": category,
            "upload_mode": upload_mode,
            "attributes": attributes,
            "items": normalized_items,
        }
        summary = {
            "valid_items": len(normalized_items),
            "invalid_items": len(error_report),
            "errors": error_report[:50],
            "preview_lines": [
                f"Bank: {bank_name}",
                f"Code: {bank_code}",
                f"Mode: {upload_mode}",
                f"Valid items: {len(normalized_items)}",
                f"Invalid items: {len(error_report)}",
            ],
        }
        return normalized, summary

    @staticmethod
    async def create_bank_batch(
        session: AsyncSession,
        *,
        seller_id: int,
        markup_percent: float,
        payload: dict,
        resubmitted_from_batch_id: int | None = None,
    ):
        normalized, summary = SellerUploadPipelineService.validate_bank_payload(payload, seller_id)
        total_items = max(int(normalized["stock_count"]), 1)
        batch = await SellerUploadBatchService.create_batch(
            session,
            seller_id=seller_id,
            item_type="bank",
            upload_mode="bulk" if int(normalized["stock_count"]) > 1 else "single",
            title=normalized["bank_name"],
            total_items=total_items,
            draft_payload=normalized,
            validation_summary=summary,
            submitted=True,
            resubmitted_from_batch_id=resubmitted_from_batch_id,
        )
        base_price = SellerUploadPipelineService.parse_price(normalized["seller_price"])
        auto_unpublish_at = None
        if normalized.get("auto_unpublish_enabled") and normalized.get("listing_duration_days"):
            from datetime import datetime, timedelta, timezone
            auto_unpublish_at = datetime.now(timezone.utc) + timedelta(days=int(normalized["listing_duration_days"]))
        bank = SellerBank(
            seller_id=seller_id,
            upload_batch_id=batch.id,
            bank_name=normalized["bank_name"],
            bank_code=normalized["bank_code"],
            category=normalized["category"],
            product_type=normalized["product_type"],
            product_subtype=normalized["product_subtype"],
            seller_price=base_price,
            base_price=base_price,
            buyer_price=base_price,
            is_in_stock=int(normalized["stock_count"]) > 0,
            stock_count=int(normalized["stock_count"]),
            reserved_count=0,
            description=normalized["description"],
            instruction=normalized["instruction"],
            state=normalized.get("state"),
            zip=normalized.get("zip"),
            portal=normalized.get("portal"),
            card_type=normalized.get("card_type"),
            has_ssn=bool(normalized.get("has_ssn")),
            has_dob=bool(normalized.get("has_dob")),
            has_name=bool(normalized.get("has_name")),
            has_address=bool(normalized.get("has_address")),
            has_email=bool(normalized.get("has_email")),
            has_security_qa=bool(normalized.get("has_security_qa")),
            has_docs=bool(normalized.get("has_docs")),
            doc_type=normalized.get("doc_type"),
            phone_area_code=normalized.get("phone_area_code"),
            details=normalized.get("details"),
            has_chat=bool(normalized["has_chat"]),
            number_access_available=bool(normalized.get("number_access_available")),
            rental_days=normalized.get("rental_days"),
            adaptive_report_enabled=bool(normalized.get("adaptive_report_enabled")),
            number_change_allowed=bool(normalized.get("number_change_allowed")),
            auto_unpublish_enabled=bool(normalized.get("auto_unpublish_enabled")),
            listing_duration_days=normalized.get("listing_duration_days"),
            auto_unpublish_at=auto_unpublish_at,
            is_active=True,
            moderation_status="pending_moderation",
        )
        session.add(bank)
        await session.commit()
        await session.refresh(batch)
        await session.refresh(bank)
        NocoDBService.log_seller_upload(
            seller_id=seller_id,
            category=normalized["category"],
            status="success",
            extra={
                "item_type": "bank",
                "upload_mode": batch.upload_mode,
                "batch_id": batch.id,
                "bank_id": bank.id,
                "product_type": normalized["product_type"],
                "product_subtype": normalized["product_subtype"],
                "stock_count": int(normalized["stock_count"]),
            },
        )
        return batch, bank, summary

    @staticmethod
    async def create_brute_batch(
        session: AsyncSession,
        *,
        seller_id: int,
        payload: dict,
        resubmitted_from_batch_id: int | None = None,
    ):
        normalized, summary = await SellerUploadPipelineService.validate_brute_payload(payload)
        gkey = make_brute_group_key(normalized["bank_code"], normalized.get("attributes"))
        group = await session.scalar(
            select(BruteBankGroup).where(BruteBankGroup.group_key == gkey)
        )
        if not group:
            group = BruteBankGroup(
                group_key=gkey,
                bank_code=normalized["bank_code"],
                bank_name=normalized["bank_name"],
                category=normalized["category"],
                attributes=normalized.get("attributes"),
                position=0,
                is_active=False,
            )
            session.add(group)
            await session.flush()
        effective_category = group.category if group else normalized["category"]
        batch = await SellerUploadBatchService.create_batch(
            session,
            seller_id=seller_id,
            item_type="brute",
            upload_mode=normalized["upload_mode"],
            title=normalized["bank_name"],
            total_items=len(normalized["items"]),
            draft_payload=normalized,
            validation_summary=summary,
            error_report={"errors": summary.get("errors", [])},
            submitted=True,
            resubmitted_from_batch_id=resubmitted_from_batch_id,
        )
        created_items = []
        for row in normalized["items"]:
            item = BruteBankItem(
                seller_id=seller_id,
                upload_batch_id=batch.id,
                group_id=group.id if group else None,
                bank_name=normalized["bank_name"],
                bank_code=normalized["bank_code"],
                category=effective_category,
                product_type="bank",
                product_subtype="brute",
                balance_range=row.get("balance_range"),
                account_type=row.get("account_type"),
                credentials=row["credentials"],
                account_number=row.get("account_number"),
                routing_number=row.get("routing_number"),
                state=row.get("state"),
                holder_name=row.get("holder_name"),
                holder_address=row.get("holder_address"),
                balance_info=row.get("balance_info"),
                price=SellerUploadPipelineService.parse_price(row["price"]),
                base_price=SellerUploadPipelineService.parse_price(row["price"]),
                buyer_price=SellerUploadPipelineService.parse_price(row["price"]),
                moderation_status="pending",
                status="available",
                is_active=False,
            )
            session.add(item)
            created_items.append(item)
        await session.commit()
        await session.refresh(batch)
        NocoDBService.log_seller_upload(
            seller_id=seller_id,
            category=effective_category,
            status="success",
            extra={
                "item_type": "brute",
                "upload_mode": normalized["upload_mode"],
                "batch_id": batch.id,
                "items_count": len(created_items),
                "bank_name": normalized["bank_name"],
                "bank_code": normalized["bank_code"],
                "invalid_items": summary.get("invalid_items", 0),
            },
        )
        return batch, created_items, summary
