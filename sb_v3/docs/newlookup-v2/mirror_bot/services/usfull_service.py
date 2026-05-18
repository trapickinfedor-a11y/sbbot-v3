"""
HTTP API client for SSN/DL lookup services.

Supports two backends (selected via LOOKUP_API_BASE_URL env var):
  - Self-hosted:  http://lookup_api:8082   (lookup_api/ service in this repo)
  - usfull.info:  https://usfull.pro       (external paid API, default fallback)

Set LOOKUP_API_BASE_URL=http://lookup_api:8082 in .env to use the self-hosted backend.

Endpoints (same interface on both):
  POST /api/search/        — SSN/DOB search
  POST /api/dl/            — Driver License search
  POST /api/cr/            — Credit Report lookup (self-hosted only)
  GET  /api/get_balance/   — Check balance
"""
import logging
import os
from typing import Optional

import httpx

# Override with LOOKUP_API_BASE_URL=http://lookup_api:8082 to use self-hosted server
BASE_URL = os.getenv("LOOKUP_API_BASE_URL", "https://usfull.pro").rstrip("/")
logger = logging.getLogger(__name__)


class UsfullClient:
    """Client for usfull.info API."""

    def __init__(
        self,
        api_key: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.api_key = api_key
        self.username = username
        self.password = password

    def _auth(self):
        if self.username and self.password:
            return (self.username, self.password)
        return None

    # ─── SSN / DOB ────────────────────────────────────────────────────────────

    async def search_ssn(
        self,
        firstname: str,
        lastname: str,
        middlename: Optional[str] = None,
        dob: Optional[str] = None,
        city: Optional[str] = None,
        st: Optional[str] = None,
        zip_code: Optional[str] = None,
        ssn: Optional[str] = None,
    ) -> dict:
        """
        Search by first/last name + optional DOB, address, SSN.
        Передавайте middle name отдельно в middlename, не в firstname.
        Returns: {"results": [...], "count": N, "success": bool}
        """
        payload: dict = {"firstname": firstname, "lastname": lastname}
        if middlename and str(middlename).strip():
            payload["middlename"] = str(middlename).strip()
        if dob:
            payload["dob"] = dob
        if city:
            payload["city"] = city
        if st:
            payload["st"] = st
        if zip_code:
            payload["zip"] = zip_code
        if ssn:
            clean = str(ssn).replace("-", "").replace(" ", "")
            if clean.isdigit():
                payload["ssn"] = int(clean)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/search/",
                json=payload,
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LookupBot/1.0",
                },
                auth=self._auth(),
            )
            resp.raise_for_status()
            data = resp.json()
            data.setdefault("results", [])
            data.setdefault("count", len(data["results"]))
            data["success"] = data["count"] > 0
            return data

    async def search_ssn_from_order_data(self, input_data: dict) -> dict:
        """Extract fields from order input_data and call search_ssn.

        Handles both Pydantic .dict() output (key='zip_code') and
        freeform parser output (key='zip', the model alias).
        DOB is stored as MM/DD/YYYY in SSNLookupData — normalize to YYYYMMDD.
        Note: ssn is what we're *looking for*, not what we provide — it won't
        be in input_data for SSN lookup orders.
        """
        zip_code = input_data.get("zip_code") or input_data.get("zip")
        mn = (input_data.get("middle_name") or input_data.get("middlename") or "").strip()
        return await self.search_ssn(
            firstname=input_data.get("first_name", ""),
            lastname=input_data.get("last_name", ""),
            middlename=mn or None,
            dob=_normalize_dob(input_data.get("dob")),
            city=input_data.get("city"),
            st=input_data.get("state"),
            zip_code=zip_code,
        )

    # ─── Driver License ────────────────────────────────────────────────────────

    async def search_dl(
        self,
        first_name: str,
        last_name: str,
        address: str,
        zipcode: str,
        dob: str,
    ) -> dict:
        """
        Search Driver License by name + address + DOB.
        Returns: {"status": "success"|"error", "license_number": "...", "license_state": "...",
                  "success": bool, "results": [...]}
        """
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "address": address,
            "zipcode": zipcode,
            "dob": dob,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/dl/",
                json=payload,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LookupBot/1.0",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # Self-hosted API returns {"status":"ok","count":N,"results":[...]}
            # External usfull.pro returns {"status":"success","license_number":"...","license_state":"..."}
            if "results" in data and isinstance(data["results"], list):
                data["count"] = data.get("count", len(data["results"]))
                data["success"] = data["count"] > 0
            elif data.get("status") == "success":
                data["results"] = [{
                    "license_number": data.get("license_number"),
                    "license_state": data.get("license_state"),
                }]
                data["count"] = 1
                data["success"] = True
            else:
                data.setdefault("results", [])
                data["count"] = 0
                data["success"] = False
            return data

    async def search_dl_from_order_data(self, input_data: dict) -> dict:
        """Extract fields from order input_data and call search_dl.

        Handles both Pydantic .dict() output (key='zip_code') and
        freeform parser output (key='zip', the model alias).
        """
        street = input_data.get("address", "")
        city = input_data.get("city", "")
        state = input_data.get("state", "")
        address_parts = [p for p in [street, city, state] if p]
        address = ", ".join(address_parts)
        zip_code = input_data.get("zip_code") or input_data.get("zip", "")
        return await self.search_dl(
            first_name=input_data.get("first_name", ""),
            last_name=input_data.get("last_name", ""),
            address=address,
            zipcode=zip_code,
            dob=_normalize_dob(input_data.get("dob")) or input_data.get("dob", ""),
        )

    # ─── Credit Report ─────────────────────────────────────────────────────────

    async def search_cr(
        self,
        ssn: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        dob: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        bureau: str = "any",
    ) -> dict:
        """
        Credit Report lookup.
        bureau: 'transunion' | 'experian' | 'equifax' | 'lexisnexis' | 'wallet' | 'any'
        Returns: {"status": "ok", "count": N, "results": [{credit_score, bureau, report_data, ...}]}
        """
        payload: dict = {"bureau": bureau}
        if ssn:
            payload["ssn"] = str(ssn).replace("-", "").strip()
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if dob:
            payload["dob"] = _normalize_dob(dob) or dob
        if address:
            payload["address"] = address
        if city:
            payload["city"] = city
        if state:
            payload["state"] = state
        if zip_code:
            payload["zip_code"] = zip_code

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BASE_URL}/api/cr/",
                json=payload,
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LookupBot/1.0",
                },
                auth=self._auth(),
            )
            resp.raise_for_status()
            data = resp.json()
            data.setdefault("results", [])
            data.setdefault("count", len(data["results"]))
            data["success"] = data["count"] > 0
            return data

    async def search_cr_from_order_data(self, input_data: dict, bureau: str = "any") -> dict:
        """
        Extract fields from CreditReportData order and call search_cr.

        CreditReportData stores: first_name, last_name, ssn (formatted as XXX-XX-XXXX),
        dob (MM/DD/YYYY), address, city, state, zip_code (or alias 'zip').
        """
        zip_code = input_data.get("zip_code") or input_data.get("zip")
        return await self.search_cr(
            ssn=input_data.get("ssn"),
            first_name=input_data.get("first_name", ""),
            last_name=input_data.get("last_name", ""),
            dob=_normalize_dob(input_data.get("dob")),
            address=input_data.get("address"),
            city=input_data.get("city"),
            state=input_data.get("state"),
            zip_code=zip_code,
            bureau=bureau,
        )

    # ─── CR PDF download ────────────────────────────────────────────────────────

    async def download_cr_pdf(self, record_id: int, dest_path: str) -> bool:
        """Download a CR PDF file from the API and save to dest_path.
        Returns True if the file was saved successfully."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{BASE_URL}/api/cr/download/{record_id}",
                headers={
                    "X-API-KEY": self.api_key,
                    "User-Agent": "LookupBot/1.0",
                },
                auth=self._auth(),
            )
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            import aiofiles
            import os
            os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            return True

    # ─── Balance ───────────────────────────────────────────────────────────────

    async def get_balance(self) -> Optional[float]:
        """Check current API balance."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BASE_URL}/api/get_balance/",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "LookupBot/1.0",
                },
                auth=self._auth(),
            )
            resp.raise_for_status()
            return resp.json().get("balance")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_dob(dob: Optional[str]) -> Optional[str]:
    """Convert various DOB formats to YYYYMMDD for the usfull API."""
    if not dob:
        return None
    dob = dob.strip()
    if len(dob) == 8 and dob.isdigit():
        return dob
    if "/" in dob:
        parts = dob.split("/")
        if len(parts) == 3 and len(parts[2]) == 4:   # MM/DD/YYYY
            return f"{parts[2]}{parts[0].zfill(2)}{parts[1].zfill(2)}"
    if "-" in dob:
        parts = dob.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:   # YYYY-MM-DD
            return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
    if "." in dob:
        parts = dob.split(".")
        if len(parts) == 3 and len(parts[2]) == 4:   # DD.MM.YYYY
            return f"{parts[2]}{parts[1].zfill(2)}{parts[0].zfill(2)}"
    return dob
