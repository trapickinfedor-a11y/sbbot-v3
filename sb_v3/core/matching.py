"""
matching.py — Address matching module for fullz → Usfull chain.
Scores Enformion persons against fullz input by address similarity,
then stores the best-matched address for precise Usfull queries.
"""
import re
from typing import Optional


# ── Constants ───────────────────────────────────────────────────────

_STREET_ABBREV = {
    # All forms → lowercase short forms (canonical form for comparison)
    "st": "st", "street": "st",
    "ave": "ave", "avenue": "ave",
    "blvd": "blvd", "boulevard": "blvd",
    "rd": "rd", "road": "rd",
    "dr": "dr", "drive": "dr",
    "ln": "ln", "lane": "ln",
    "ct": "ct", "court": "ct",
    "cir": "cir", "circle": "cir",
    "pl": "pl", "place": "pl",
    "hwy": "hwy", "highway": "hwy",
    "pkwy": "pkwy", "parkway": "pkwy",
    "sq": "sq", "square": "sq",
    "trl": "trl", "trail": "trl",
    "way": "way",
    "plz": "plz", "plaza": "plz",
    "ter": "ter", "terrace": "ter",
    "ste": "ste", "suite": "ste",
    "apt": "apt", "apartment": "apt",
    "bldg": "bldg", "building": "bldg",
    # Directionals
    "n": "north", "s": "south", "e": "east", "w": "west",
    "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
}
_ORDINAL_MAP = {
    "1st": "one", "2nd": "two", "3rd": "three", "4th": "four",
    "5th": "five", "6th": "six", "7th": "seven", "8th": "eight",
    "9th": "nine", "10th": "ten", "11th": "eleven", "12th": "twelve",
}
_US_STATES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
    "as", "dc", "gu", "pr", "vi",
}
# Common city names + street names that should NOT be treated as name parts
_NON_NAME_WORDS = {
    # Cities
    "chicago", "houston", "losangeles", "phoenix", "philadelphia",
    "sanantonio", "sandiego", "dallas", "sanjose", "austin",
    "jacksonville", "fortworth", "columbus", "charlotte", "sanfrancisco",
    "indianapolis", "seattle", "denver", "washington", "boston",
    "nashville", "baltimore", "oklahomacity", "portland", "lasvegas",
    "milwaukee", "albuquerque", "tucson", "fresno", "sacramento",
    "atlanta", "kansascity", "coloradosprings", "miami", "omaha",
    "raleigh", "virginiabeach", "oakland", "minneapolis", "tulsa",
    "arlington", "tampa", "neworleans", "wichita", "cleveland",
    "bakersfield", "aurora", "anaheim", "honolulu", "santaana",
    "riverside", "corpuschristi", "lexington", "stockton", "henderson",
    "manhattan", "brooklyn", "queens", "bronx", "jerseycity",
    "springfield", "el", "las", "los", "san", "del", "la",
    # Streets & generic words
    "main", "oak", "elm", "park", "pine", "maple", "cedar", "walnut",
    "birch", "willow", "ash", "spruce", "clark", "liberty", "union",
    "market", "broadway", "central", "north", "south", "east", "west",
    "jefferson", "washington", "lake", "hill", "river", "forest",
    "valley", "sunset", "grove", "heights", "parkway", "bridge",
    "crossing", "station", "square", "plaza", "vista", "santa",
    "highland", "green", "field", "meadow", "spring", "morning",
    "sunrise", "fairview", "lincoln",
    "st", "ave", "blvd", "rd", "dr", "ln", "ct", "cir", "pl",
    "hwy", "pkwy", "trl", "way", "ste", "apt", "bldg",
    "street", "avenue", "boulevard", "road", "drive", "lane",
    "court", "circle", "place", "highway", "parkway", "trail",
    "suite", "apartment", "building",
}


# ── Normalization helpers ────────────────────────────────────────────

def _normalize_street(s: str) -> str:
    """Normalize street: lowercase, remove punctuation, expand abbrevs/ordinals to full words."""
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    words = s.split()
    expanded = []
    for w in words:
        if w in _STREET_ABBREV:
            expanded.append(_STREET_ABBREV[w])
        elif w in _ORDINAL_MAP:
            expanded.append(_ORDINAL_MAP[w])
        else:
            expanded.append(w)
    return " ".join(expanded)


def _extract_street_number(s: str) -> str:
    """Extract leading number from street address."""
    m = re.match(r"^(\d+)", s.strip())
    return m.group(1) if m else ""


def _normalize_city(s: str) -> str:
    """Normalize city name."""
    if not s:
        return ""
    return re.sub(r"[^\w]", "", s.strip().lower())


def _extract_zip(s: str) -> str:
    """Extract 5-digit ZIP from any string."""
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", s or "")
    return m.group(1) if m else ""


def _zip_prefix(z: str) -> str:
    """Return first 3 digits of ZIP."""
    return z[:3] if z else ""


def _extract_state(s: str) -> str:
    """Extract 2-letter US state abbreviation from any string.

    Uses segments separated by non-alphanumeric chars (spaces, punctuation, digits).
    This naturally prevents "St" in "Street" from being matched as a state,
    while catching the real "IL" after "Chicago".
    Returns the LAST 2-letter segment, which is always the state in standard formats.
    """
    # Split by non-alphanumeric, find all 2-char segments
    segments = re.split(r"\W+", s or "")
    two_letter = [seg for seg in segments if len(seg) == 2 and seg.isalpha()]
    return two_letter[-1].upper() if two_letter else ""


def _extract_city(s: str) -> str:
    """Extract city name (before comma or before state abbreviation)."""
    s = (s or "").strip()
    if "," in s:
        # Take last segment (usually "City ST ZIP")
        seg = s.split(",")[-1].strip()
        # Extract city before state/zip
        parts = seg.split()
        city_parts = []
        for p in parts:
            if re.match(r"^[A-Z]{2}$", p) or re.match(r"^\d{5}", p):
                break
            city_parts.append(p)
        return _normalize_city(" ".join(city_parts))
    else:
        parts = s.split()
        city_parts = []
        for p in parts:
            if re.match(r"^[A-Z]{2}$", p.upper()) or re.match(r"^\d{5}", p):
                break
            city_parts.append(p)
        return _normalize_city(" ".join(city_parts))


def _is_non_name_word(w: str) -> bool:
    """Guess if a word is part of an address/location (not a name)."""
    w_lower = w.lower()
    if w_lower in _US_STATES:
        return True
    if w_lower in _NON_NAME_WORDS:
        return True
    # Numeric address numbers (123, 45A)
    if re.match(r"^\d+[a-z]?$", w, re.IGNORECASE):
        return True
    return False


# ── Similarity scoring ──────────────────────────────────────────────

def _score_street(street1: str, street2: str) -> int:
    """
    Score two street addresses for similarity.
    Returns 0–30 points.
    30 = full match (after normalization)
    15 = partial match (same base, different number OR one is substring)
    5  = word overlap (2+ shared words)
    0  = no match
    """
    if not street1 or not street2:
        return 0

    n1 = _normalize_street(street1)
    n2 = _normalize_street(street2)

    if n1 == n2 and n1:
        return 30

    num1 = _extract_street_number(street1)
    num2 = _extract_street_number(street2)

    base1 = _normalize_street(street1[len(num1):].strip()) if num1 else n1
    base2 = _normalize_street(street2[len(num2):].strip()) if num2 else n2

    if not base1 or not base2:
        return 0

    if base1 == base2:
        if num1 and num2 and num1 == num2:
            return 30
        if num1 and num2:
            return 15  # same base, different number
        return 10

    if base1 in base2 or base2 in base1:
        return 15

    # One base contains the other's words (partial match)
    words1 = set(base1.split())
    words2 = set(base2.split())
    common = words1 & words2
    if common and len(common) >= 2:
        return 5
    if common:
        return 3

    return 0


def _score_zip(zip1: str, zip2: str) -> int:
    """Score ZIP match: 50 for exact 5-digit, 20 for prefix match, 0 otherwise."""
    if not zip1 or not zip2:
        return 0
    if len(zip1) < 5 or len(zip2) < 5:
        return 0
    if zip1 == zip2:
        return 50
    if _zip_prefix(zip1) == _zip_prefix(zip2):
        return 20
    return 0


def _score_city(city1: str, city2: str) -> int:
    """Score city match: 20 for exact, 0 otherwise."""
    if not city1 or not city2:
        return 0
    n1 = _normalize_city(city1)
    n2 = _normalize_city(city2)
    if n1 == n2 and n1:
        return 20
    return 0


# ── Fullz parsing ───────────────────────────────────────────────────

def parse_fullz(raw: str) -> dict:
    """
    Parse a fullz string into structured fields.
    Handles:
      "John Doe, 123 Main St, Chicago IL 60601"
      "John Doe\\n123 Main St\\nChicago IL 60601"
    Returns: {first_name, last_name, street, city, state, zip_code, raw_input}
    """
    raw_clean = raw.strip()
    result = {
        "first_name": "", "last_name": "",
        "street": "", "city": "", "state": "", "zip_code": "",
        "raw_input": raw_clean,
    }

    state = _extract_state(raw_clean)
    zip_code = _extract_zip(raw_clean)
    result["state"] = state
    result["zip_code"] = zip_code

    # Extract city: comma/multi-line OR pipe-separated layout
    if "," in raw_clean:
        # Comma-separated: take LAST segment ("Chicago IL 60601")
        last_seg = raw_clean.split(",")[-1].strip()
        result["city"] = _extract_city(last_seg)
    elif "\n" in raw_clean:
        # Multi-line: last line is "City ST ZIP"
        last_line = raw_clean.split("\n")[-1].strip()
        result["city"] = _extract_city(last_line)
    elif "|" in raw_clean:
        # Pipe-separated: John|Doe|123 Main St|Chicago|IL|60601
        pipe_parts = [p.strip() for p in raw_clean.split("|")]
        if len(pipe_parts) >= 4:
            result["city"] = _normalize_city(pipe_parts[3])
        # Name from first 2 pipe parts only (skip address, city, state, zip)
        if len(pipe_parts) >= 2:
            name_p = [p for p in pipe_parts[:2] if p and len(p) > 1 and not _is_non_name_word(p)]
            if len(name_p) >= 2:
                result["first_name"] = name_p[0]
                result["last_name"] = " ".join(name_p[1:])
            elif len(name_p) == 1:
                result["first_name"] = name_p[0]
        # Address (3rd field, index 2)
        if len(pipe_parts) >= 3:
            result["street"] = pipe_parts[2]
        return result

    # Extract name: remove states, ZIPs, city names, address words from cleaned text
    cleaned = re.sub(r"\b[A-Z]{2}\b", " ", raw_clean)
    cleaned = re.sub(r"\d{5}(?:-\d{4})?", "", cleaned)
    for cn in ("Chicago", "Houston", "LosAngeles", "LosAngeles", "SanFrancisco",
              "SanAntonio", "SanDiego", "SanJose", "NewYork", "Philadelphia",
              "Phoenix", "OklahomaCity", "FortWorth", "SaltLakeCity", "Springfield",
              "Manhattan", "Brooklyn", "Queens", "Bronx", "JerseyCity",
              "Chicago", "Houston", "Los", "San", "Francisco", "Antonio",
              "Diego", "Phoenix", "Philadelphia", "Indianapolis", "Columbus"):
        cleaned = re.sub(r"\b" + re.escape(cn) + r"\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[,\n|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    words = cleaned.split()
    name_words = [w for w in words if w and len(w) > 1 and not _is_non_name_word(w)]
    if len(name_words) >= 2:
        result["first_name"] = name_words[0]
        result["last_name"] = " ".join(name_words[1:])
    elif len(name_words) == 1:
        result["first_name"] = name_words[0]

    # Extract street from raw input
    result["street"] = _extract_street_from_raw(raw_clean)

    return result


def _extract_street_from_raw(raw: str) -> str:
    """Extract street address from raw fullz string."""
    lines = re.split(r"[,;\n|]", raw)
    for line in lines:
        line = line.strip()
        if re.match(r"^\d+", line) and any(
            ab in line.lower() for ab in
            ("st", "ave", "blvd", "rd", "dr", "ln", "ct", "cir", "pl", "hwy", "pkwy", "trl", "way")
        ):
            cleaned = re.sub(r"\s+[A-Z]{2}\s+\d{5}.*$", "", line)
            cleaned = re.sub(r"\s+\d{5}(?:-\d{4})?$", "", cleaned)
            return cleaned.strip()
    return ""


# ── Address extraction from person ──────────────────────────────────

def get_primary_address(person: dict) -> dict:
    """
    Extract the best available address from a person dict.
    Priority: currentAddress > first in addresses[] > location > address field.
    Returns dict: {street, city, state, zip, raw}
    """
    addr = {"street": "", "city": "", "state": "", "zip": "", "raw": ""}

    current = person.get("currentAddress") or {}
    if current:
        addr["street"] = _safe_str(current.get("addressLine1", ""))
        addr["city"] = _safe_str(current.get("city", ""))
        addr["state"] = _safe_str(current.get("state", ""))
        addr["zip"] = _safe_str(current.get("zipCode", "")) or _safe_str(current.get("zip", ""))
        addr["raw"] = _build_raw(current)
        return addr

    addrs_list = person.get("addresses", [])
    if addrs_list and isinstance(addrs_list, list):
        first = addrs_list[0]
        if isinstance(first, dict):
            addr["street"] = _safe_str(first.get("addressLine1", ""))
            addr["city"] = _safe_str(first.get("city", ""))
            addr["state"] = _safe_str(first.get("state", ""))
            addr["zip"] = _safe_str(first.get("zipCode", "")) or _safe_str(first.get("zip", ""))
            addr["raw"] = _build_raw(first)
            return addr
        elif isinstance(first, str):
            addr["raw"] = first
            addr["street"] = first.split(",")[0].strip() if first else ""
            return addr

    loc = person.get("location", "")
    if loc:
        addr["raw"] = loc
        parts = [p.strip() for p in loc.split(",")]
        if len(parts) >= 2:
            addr["city"] = parts[0]
            addr["state"] = parts[-1][:2].upper()
        elif len(parts) == 1 and len(parts[0]) == 2:
            addr["state"] = parts[0].upper()
        return addr

    ad = person.get("address", "")
    if ad:
        addr["raw"] = ad
        parts = [p.strip() for p in ad.split(",")]
        addr["street"] = parts[0] if parts else ad
        if len(parts) >= 2:
            addr["city"] = parts[1]
        if len(parts) >= 3:
            addr["state"] = parts[2][:2].upper()
        return addr

    return addr


def _safe_str(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _build_raw(addr: dict) -> str:
    parts = []
    for key in ("addressLine1", "addressLine2", "city", "state", "zipCode", "zip"):
        v = _safe_str(addr.get(key))
        if v:
            parts.append(v)
    return ", ".join(parts)


def _extract_phones_from_raw(s: str) -> list:
    """Extract all phone numbers from raw text."""
    import re
    pattern = r'\+?1?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{4}'
    return re.findall(pattern, s or "")


def _extract_emails_from_raw(s: str) -> list:
    """Extract all emails from raw text."""
    import re
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, s or "")


# ── Main scoring function ────────────────────────────────────────────

def score_person(person: dict, fullz: dict) -> int:
    """
    Score a single person against parsed fullz input.
    Returns total score (0–165).
    """
    addr = get_primary_address(person)
    score = 0

    score += _score_zip(fullz.get("zip_code", ""), addr.get("zip", ""))

    if fullz.get("street") and addr.get("street"):
        score += _score_street(fullz["street"], addr["street"])

    score += _score_city(fullz.get("city", ""), addr.get("city", ""))

    fullz_state = fullz.get("state", "")
    addr_state = addr.get("state", "")
    if fullz_state and addr_state and fullz_state.upper() == addr_state.upper():
        score += 15

    # SSN exact match
    fullz_ssn = _extract_ssn(fullz.get("raw_input", ""))
    person_ssn = _safe_str(person.get("ssn", ""))
    if fullz_ssn and person_ssn and fullz_ssn == person_ssn:
        score += 40

    # DOB exact match — normalize person DOB for comparison
    fullz_dob = _extract_dob(fullz.get("raw_input", ""))
    raw_person_dob = _safe_str(person.get("date_of_birth", "")) or _safe_str(person.get("dob", ""))
    person_dob = _normalize_dob(raw_person_dob)
    if fullz_dob and person_dob and fullz_dob == person_dob:
        score += 30

    # Phone cross-match (from fullz input phones)
    phones_from_fullz = _extract_phones_from_raw(fullz.get("raw_input", ""))
    if phones_from_fullz:
        person_phones = extract_all_phones_from_person(person)
        score += _score_phone_match(phones_from_fullz, person_phones)

    # Email cross-match
    emails_from_fullz = _extract_emails_from_raw(fullz.get("raw_input", ""))
    if emails_from_fullz:
        person_emails = person.get("emails", [])
        score += _score_email_match(emails_from_fullz, person_emails)

    return score


def _extract_ssn(s: str) -> str:
    """Extract 9-digit SSN."""
    m = re.search(r"\b(\d{3})[-.]?(\d{2})[-.]?(\d{4})\b", s or "")
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    return ""


def _normalize_dob(dob: str) -> str:
    """Normalize DOB to YYYYMMDD."""
    dob = dob.strip()
    if not dob:
        return ""
    # Already 8 digits
    if len(dob) == 8 and dob.isdigit():
        return dob
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", dob)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    # MM/DD/YYYY or DD.MM.YYYY
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", dob)
    if m:
        return f"{m.group(3)}{int(m.group(1)):02d}{int(m.group(2)):02d}"
    return dob


def _extract_dob(s: str) -> str:
    """Extract DOB in YYYYMMDD."""
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", s or "")
    if m:
        return f"{m.group(3)}{int(m.group(1)):02d}{int(m.group(2)):02d}"
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s or "")
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    m = re.search(r"\b(\d{4})/(\d{2})/(\d{2})\b", s or "")
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    return ""


def _extract_phone_from_raw(s: str) -> str:
    """Extract first phone number (10+ digits) from raw string."""
    # Find sequences of 10+ digits (phone number)
    m = re.search(r"\b(\d{3}[-.]?\d{3}[-.]?\d{4})\b", s or "")
    if m:
        digits = re.sub(r"[^\d]", "", m.group(1))
        return digits
    return ""


def _extract_email_from_raw(s: str) -> str:
    """Extract first email address from raw string."""
    m = re.search(r"[\w.+%+-]+@[\w-]+\.[\w.-]+", s or "")
    return m.group(0) if m else ""


def _normalize_phone_to_10(p: str) -> str:
    """Normalize phone to 10-digit string (strip all non-digits)."""
    digits = re.sub(r"[^\d]", "", p)
    # Drop leading 1 if present (US country code)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[:10]


# phone/email scoring (list-based, added after score_person)


def extract_all_phones_from_person(p: dict) -> list:
    """Extract all unique phone numbers from a person dict."""
    phones = []
    seen = set()
    # From phones list
    for ph_entry in p.get("phones", []):
        if isinstance(ph_entry, dict):
            num = re.sub(r"[^\d]", "", str(ph_entry.get("phone", "")))
        else:
            num = re.sub(r"[^\d]", "", str(ph_entry))
        if num and num not in seen:
            seen.add(num)
            phones.append(num)
    # From singular phone field
    phone = re.sub(r"[^\d]", "", str(p.get("phone", "")))
    if phone and phone not in seen:
        seen.add(phone)
        phones.append(phone)
    return phones


def extract_state_from_location(loc: str) -> str:
    """Extract 2-letter state from 'City, ST' or 'City, ST ZIP' string."""
    if not loc:
        return ""
    parts = [p.strip() for p in (loc or "").split(",")]
    if len(parts) >= 2:
        # Last part could be "ST ZIP" or just "ST"
        last = parts[-1].strip()
        # Check last 2 chars as state abbrev
        if len(last) == 2 and last.isalpha():
            return last.upper()
        # Last 2 chars of last segment
        s = last[-2:].upper()
        if s.isalpha() and s in _US_STATES:
            return s
        # Find state in any segment
        for seg in parts:
            seg = seg.strip()
            if len(seg) == 2 and seg.isalpha() and seg.lower() in _US_STATES:
                return seg.upper()
            if len(seg) >= 2:
                s = seg[-2:].upper()
                if s.isalpha() and s.lower() in _US_STATES:
                    return s
    return ""


def _score_name_similarity(name1: str, name2: str) -> float:
    """Return similarity ratio 0.0–1.0 between two names (basic word overlap)."""
    if not name1 or not name2:
        return 0.0
    w1 = set(name1.lower().split())
    w2 = set(name2.lower().split())
    if not w1 or not w2:
        return 0.0
    overlap = len(w1 & w2)
    total = max(len(w1), len(w2))
    return overlap / total if total else 0.0


def _same_address(addr1: dict, addr2: dict) -> bool:
    """Check if two addresses are the same (same street + city or same SSN)."""
    s1 = _normalize_street(addr1.get("street", ""))
    s2 = _normalize_street(addr2.get("street", ""))
    c1 = _normalize_city(addr1.get("city", ""))
    c2 = _normalize_city(addr2.get("city", ""))
    if s1 and s1 == s2 and c1 and c1 == c2:
        return True
    return False


def deduplicate_persons(persons: list) -> list:
    """
    Merge persons with the same SSN or same name+address (>=80% name similarity).
    Keeps the person with most populated fields.
    Returns deduplicated list (original order preserved, best copy kept first).
    """
    if not persons:
        return persons

    result: list = []
    for p in persons:
        # Count filled fields (exclude internal _* fields)
        def field_count(person: dict) -> int:
            return sum(
                1 for k, v in person.items()
                if not k.startswith("_") and v and str(v).strip()
            )

        # Check for duplicate
        is_dup = False
        best_idx = -1
        p_ssn = _safe_str(p.get("ssn", "")).replace("-", "").replace(".", "")
        p_name = p.get("name", "")
        p_addr = get_primary_address(p)

        for i, existing in enumerate(result):
            ex_ssn = _safe_str(existing.get("ssn", "")).replace("-", "").replace(".", "")
            ex_name = existing.get("name", "")
            ex_addr = get_primary_address(existing)

            # Same SSN
            if p_ssn and ex_ssn and p_ssn == ex_ssn:
                if field_count(p) > field_count(existing):
                    result[i] = p
                is_dup = True
                break

            # Same name + address
            if p_name and ex_name:
                sim = _score_name_similarity(p_name, ex_name)
                if sim >= 0.8 and _same_address(p_addr, ex_addr):
                    if field_count(p) > field_count(existing):
                        result[i] = p
                    is_dup = True
                    break

        if not is_dup:
            result.append(p)

    return result


def confidence_tier(score: int) -> str:
    if score >= 100:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"


def confidence_icon(score: int) -> str:
    if score >= 100:
        return "🟢"
    if score >= 60:
        return "🟡"
    return "🔴"


# ── Match fullz to persons ──────────────────────────────────────────

def match_fullz(persons: list, fullz_raw: str) -> list:
    """
    Score and rank all persons against fullz input.
    Adds _score, _confidence, _confidence_icon, _matched_addr to each person.
    Returns sorted list (highest score first).
    """
    fullz = parse_fullz(fullz_raw)

    scored = []
    for p in persons:
        s = score_person(p, fullz)
        addr = get_primary_address(p)
        tier = confidence_tier(s)
        icon = confidence_icon(s)

        scored_p = dict(p)
        scored_p["_score"] = s
        scored_p["_confidence"] = tier
        scored_p["_confidence_icon"] = icon
        scored_p["_matched_addr"] = addr
        scored.append(scored_p)

    scored.sort(key=lambda x: x["_score"], reverse=True)

    # Deduplicate: merge persons with same SSN or same name+address
    scored = deduplicate_persons(scored)

    return scored


def best_match(persons: list, fullz_raw: str) -> Optional[dict]:
    """Return the best-matching person, or None if none score >= 60."""
    matched = match_fullz(persons, fullz_raw)
    for p in matched:
        if p["_score"] >= 60:
            return p
    return matched[0] if matched else None


def _score_phone_match(fullz_phones: list, person_phones: list) -> int:
    """Score 25 points if any fullz phone matches any person phone (normalized to 10 digits)."""
    if not fullz_phones or not person_phones:
        return 0
    def to_10digit(p):
        digits = "".join(c for c in str(p) if c.isdigit())
        return digits[-10:] if len(digits) >= 10 else digits
    fullz_set = {to_10digit(p) for p in fullz_phones if to_10digit(p)}
    person_set = {to_10digit(p) for p in person_phones if to_10digit(p)}
    if fullz_set & person_set:
        return 25
    return 0


def _score_email_match(fullz_emails: list, person_emails: list) -> int:
    """Score 20 points if any fullz email matches any person email."""
    if not fullz_emails or not person_emails:
        return 0
    fullz_set = {str(e).lower().strip() for e in fullz_emails if e}
    person_set = {str(e).lower().strip() for e in person_emails if e}
    if fullz_set & person_set:
        return 20
    return 0


def extract_state_from_location(loc: str) -> str:
    """Extract 2-letter state from 'City, ST' or 'City, ST ZIP' string."""
    if not loc:
        return ""
    # Find the last comma-separated segment
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        state_part = parts[-1].strip()
        # Could be "NY 10001" or just "NY"
        import re
        m = re.search(r'\b([A-Z]{2})\b', state_part)
        if m:
            return m.group(1)
        # Try second-to-last
        if len(parts) >= 2:
            m = re.search(r'\b([A-Z]{2})\b', parts[-2].strip())
            if m:
                return m.group(1)
    return ""


def extract_all_phones_from_person(p: dict) -> list:
    """Extract all unique phone numbers from a person dict."""
    phones = []
    # From phones list
    for ph in p.get("phones", []):
        if isinstance(ph, dict):
            phone = ph.get("phone", "")
        else:
            phone = str(ph)
        if phone:
            phones.append(phone)
    # From phone field
    if p.get("phone"):
        phones.append(p["phone"])
    # Deduplicate
    seen = set()
    result = []
    for ph in phones:
        norm = "".join(c for c in ph if c.isdigit())[-10:]
        if norm and norm not in seen:
            seen.add(norm)
            result.append(ph)
    return result


def _jaro_winkler(s1: str, s2: str) -> float:
    """Jaro-Winkler similarity 0.0-1.0."""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    match_dist = max(len1, len2) // 2 - 1
    if match_dist < 0:
        match_dist = 0
    s1_m = [False] * len1
    s2_m = [False] * len2
    matches = 0
    transpositions = 0
    for i in range(len1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if s2_m[j] or s1[i] != s2[j]:
                continue
            s1_m[i] = True
            s2_m[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    for i in range(len1):
        if not s1_m[i]:
            continue
        while not s2_m[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    jaro = (matches/len1 + matches/len2 + (matches - transpositions/2)/matches) / 3
    prefix = 0
    for i in range(min(4, len1, len2)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
    return jaro + prefix * 0.1 * (1 - jaro)


def _count_filled_fields(p: dict) -> int:
    count = 0
    for k in ("name", "first_name", "last_name", "ssn", "date_of_birth", "phone",
              "address", "addresses", "emails", "akas", "relatives", "age"):
        if p.get(k):
            count += 1
    return count


def deduplicate_persons(persons: list) -> list:
    """Merge duplicate persons (same SSN or 90%+ name similarity + same state)."""
    if not persons:
        return []
    result = []
    for p in persons:
        is_dup = False
        for existing in result:
            # SSN match
            if p.get("ssn") and existing.get("ssn") and p["ssn"] == existing["ssn"]:
                if _count_filled_fields(existing) < _count_filled_fields(p):
                    result.remove(existing)
                    result.append(p)
                is_dup = True
                break
            # Name + state fuzzy match
            p_name = (p.get("first_name", "") + p.get("last_name", "")).lower().replace(" ", "")
            e_name = (existing.get("first_name", "") + existing.get("last_name", "")).lower().replace(" ", "")
            p_state = extract_state_from_location(p.get("location", ""))
            e_state = extract_state_from_location(existing.get("location", ""))
            if p_name and e_name and _jaro_winkler(p_name, e_name) > 0.88 and p_state == e_state:
                if _count_filled_fields(existing) < _count_filled_fields(p):
                    result.remove(existing)
                    result.append(p)
                is_dup = True
                break
        if not is_dup:
            result.append(p)
    return result