"""
validators.py — Input validation and freeform text parsing for SearchBug/Usfull bot.
Adapted from mirror_bot validators with standalone US states data.
"""

import re
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, date

logger = logging.getLogger(__name__)

# ─── US States ───────────────────────────────────────────────────────────────

US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
}

US_STATES_LIST = list(US_STATES.keys())
US_STATES_REVERSE = {v.lower(): k for k, v in US_STATES.items()}

# ─── Regex patterns ───────────────────────────────────────────────────────────

SSN_REGEX    = r'^\d{3}-\d{2}-\d{4}$'
ZIP_REGEX    = r'^\d{5}(-\d{4})?$'
PHONE_REGEX  = r'^\+?1?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{4}$'
DOB_REGEX    = r'^\d{2}/\d{2}/\d{4}$'
DL_REGEX     = r'^[A-Z0-9]{5,20}$'
EMAIL_REGEX  = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'

STREET_TYPES = [
    'street', 'avenue', 'road', 'lane', 'boulevard', 'drive', 'court', 'place',
    'way', 'parkway', 'highway', 'circle', 'terrace', 'trail', 'loop', 'path',
    'alley', 'branch', 'beach', 'st', 'ave', 'av', 'rd', 'ln', 'blvd', 'dr',
    'ct', 'pl', 'pkwy', 'hwy', 'cir', 'ter', 'trl', 'plaza', 'square', 'sq',
    'pike', 'row', 'run', 'walk', 'crossing', 'commons', 'green', 'grove',
    'heights', 'hill', 'hollow', 'landing', 'park', 'point', 'ridge', 'spring',
    'station', 'trace', 'turnpike', 'vista', 'woods',
]

COMMON_CITIES = {
    'new york', 'los angeles', 'chicago', 'houston', 'phoenix', 'philadelphia',
    'san antonio', 'san diego', 'dallas', 'san jose', 'austin', 'jacksonville',
    'fort worth', 'columbus', 'charlotte', 'san francisco', 'indianapolis',
    'seattle', 'denver', 'washington', 'boston', 'el paso', 'nashville',
    'detroit', 'oklahoma city', 'portland', 'las vegas', 'memphis', 'louisville',
    'baltimore', 'milwaukee', 'albuquerque', 'tucson', 'fresno', 'mesa',
    'sacramento', 'atlanta', 'kansas city', 'colorado springs', 'omaha',
    'raleigh', 'miami', 'long beach', 'virginia beach', 'oakland', 'minneapolis',
    'tulsa', 'tampa', 'arlington', 'new orleans', 'wichita', 'cleveland',
    'bakersfield', 'aurora', 'anaheim', 'honolulu', 'santa ana', 'riverside',
    'corpus christi', 'lexington', 'stockton', 'henderson', 'saint paul',
    'st paul', 'cincinnati', 'st louis', 'pittsburgh', 'greensboro', 'lincoln',
    'anchorage', 'plano', 'orlando', 'irvine', 'newark', 'toledo', 'durham',
    'chula vista', 'fort wayne', 'jersey city', 'st petersburg', 'laredo',
    'madison', 'chandler', 'buffalo', 'lubbock', 'scottsdale', 'reno',
    'glendale', 'gilbert', 'winston salem', 'north las vegas', 'norfolk',
    'chesapeake', 'garland', 'irving', 'hialeah', 'fremont', 'boise',
    'richmond', 'baton rouge', 'spokane', 'des moines', 'tacoma', 'san bernardino',
    'modesto', 'fontana', 'moreno valley', 'glendale', 'akron', 'yonkers',
    'huntington beach', 'little rock', 'amarillo', 'mobile', 'grand rapids',
    'salt lake city', 'tallahassee', 'huntsville', 'worcester', 'knoxville',
    'brownsville', 'santa clarita', 'providence', 'garden grove', 'oceanside',
    'chattanooga', 'fort lauderdale', 'rancho cucamonga', 'santa rosa',
    'port arthur', 'tempe', 'cape coral', 'oxnard', 'eugene', 'peoria',
    'salem', 'cary', 'corona', 'springfield', 'fort collins', 'jackson',
    'alexandria', 'hayward', 'lancaster', 'salinas', 'palmdale', 'sunnyvale',
    'pomona', 'escondido', 'kansas city', 'torrance', 'pasadena', 'bridgeport',
    'mcallen', 'syracuse', 'rockford', 'surprise', 'roseville', 'paterson',
    'el monte', 'savannah', 'hollywood', 'clarksville', 'macon', 'lakewood',
    'mesquite', 'dayton', 'orange', 'fullerton', 'killeen', 'warren',
    'west valley city', 'columbia', 'sterling heights', 'new haven', 'miramar',
    'thousand oaks', 'cedar rapids', 'olathe', 'topeka', 'arlington',
    'waco', 'visalia', 'colorado springs', 'concord', 'elizabeth', 'hartford',
    'coral springs', 'roseville', 'abilene', 'beaumont', 'independence',
    'peoria', 'springfield', 'ann arbor', 'berkeley', 'cambridge', 'athens',
    'norman', 'fayetteville', 'columbia', 'lansing', 'inglewood', 'provo',
    'erie', 'denton', 'victorville', 'el cajon', 'west palm beach', 'clearwater',
    'murfreesboro', 'miami gardens', 'round rock', 'waterbury', 'midland',
    'pueblo', 'west jordan', 'high point', 'lowell', 'peoria', 'lansing',
    'clovis', 'pompano beach', 'elgin', 'costa mesa', 'downey', 'miami',
    'burbank', 'antioch', 'richmond', 'west covina', 'norwalk', 'everett',
    'temecula', 'arvada', 'palm bay', 'manchester', 'rochester', 'green bay',
    'billings', 'pueblo', 'murfreesboro', 'las cruces', 'evansville',
    'south bend', 'columbia', 'fargo', 'athens', 'peoria', 'springfield',
}


# ─── Field extractors ─────────────────────────────────────────────────────────

def extract_ssn(text: str) -> Tuple[Optional[str], str]:
    """Extract SSN (XXX-XX-XXXX or 9 digits)."""
    # With dashes
    m = re.search(r'\b(\d{3}-\d{2}-\d{4})\b', text)
    if m:
        ssn = m.group(1)
        text = text[:m.start()] + text[m.end():]
        return ssn, text.strip()
    # 9 digits (not part of phone/zip)
    m = re.search(r'(?<!\d)(\d{9})(?!\d)', text)
    if m:
        digits = m.group(1)
        ssn = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        text = text[:m.start()] + text[m.end():]
        return ssn, text.strip()
    return None, text


def extract_phone(text: str) -> Tuple[Optional[str], str]:
    """Extract US phone number."""
    patterns = [
        r'\+?1?\s?\((\d{3})\)\s?(\d{3})[-\s]?(\d{4})',
        r'\+?1?[-\s]?(\d{3})[-\s](\d{3})[-\s](\d{4})',
        r'(\d{10})',
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            phone = m.group(0)
            text = text[:m.start()] + text[m.end():]
            return phone, text.strip()
    return None, text


def extract_zip(text: str) -> Tuple[Optional[str], str]:
    """Extract ZIP code (5 or 9 digits)."""
    m = re.search(r'\b(\d{5}(?:-\d{4})?)\b', text)
    if m:
        zip_code = m.group(1)
        text = text[:m.start()] + text[m.end():]
        return zip_code, text.strip()
    return None, text


def extract_state(text: str) -> Tuple[Optional[str], str]:
    """Extract US state code."""
    # 2-letter code
    m = re.search(r'\b([A-Z]{2})\b', text)
    if m and m.group(1) in US_STATES_LIST:
        state = m.group(1)
        text = text[:m.start()] + text[m.end():]
        return state, text.strip()
    # Full name
    for full_name, code in US_STATES_REVERSE.items():
        if full_name in text.lower():
            text = re.sub(re.escape(full_name), '', text, flags=re.IGNORECASE)
            return code, text.strip()
    return None, text


def extract_dob(text: str) -> Tuple[Optional[str], str]:
    """Extract date of birth in various formats, normalize to MM/DD/YYYY."""
    month_names = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
        'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
        'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
    }

    # Month name patterns: "Sep 12 1965", "12 Sep 1965"
    month_patterns = [
        r'\b([a-zA-Z]{3,})\s+(\d{1,2}),?\s+(\d{4}|\d{2})\b',
        r'\b(\d{1,2})\s+([a-zA-Z]{3,}),?\s+(\d{4}|\d{2})\b',
    ]
    for i, pattern in enumerate(month_patterns):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            if i == 0:
                month_name, day, year = m.groups()
            else:
                day, month_name, year = m.groups()
            mn = month_name.lower()
            if mn in month_names:
                month = month_names[mn]
                day, year = int(day), int(year)
                if year < 100:
                    year = 2000 + year if year <= 50 else 1900 + year
                if 1 <= day <= 31 and 1900 <= year <= date.today().year:
                    try:
                        datetime(year, month, day)
                        text = text[:m.start()] + text[m.end():]
                        return f"{month:02d}/{day:02d}/{year}", text.strip()
                    except ValueError:
                        pass

    # Date with separators
    date_patterns = [
        (r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b', 'mdy'),
        (r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b', 'ymd'),
        (r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', 'dmy'),
        (r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})\b', 'mdy2'),
    ]
    for pattern, fmt in date_patterns:
        m = re.search(pattern, text)
        if m:
            p1, p2, p3 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if fmt == 'ymd':
                year, month, day = p1, p2, p3
            elif fmt == 'dmy':
                day, month, year = p1, p2, p3
            elif fmt == 'mdy2':
                month, day = p1, p2
                year = 2000 + p3 if p3 <= 50 else 1900 + p3
            else:  # mdy
                if p1 > 12 and p2 <= 12:
                    day, month, year = p1, p2, p3
                else:
                    month, day, year = p1, p2, p3
            if fmt == 'mdy2':
                pass  # already handled
            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= date.today().year:
                try:
                    datetime(year, month, day)
                    text = text[:m.start()] + text[m.end():]
                    return f"{month:02d}/{day:02d}/{year}", text.strip()
                except ValueError:
                    pass

    # 8-digit MMDDYYYY or YYYYMMDD
    m = re.search(r'(?<!\d)(\d{8})(?!\d)', text)
    if m:
        ds = m.group(1)
        # Try MMDDYYYY
        try:
            month, day, year = int(ds[:2]), int(ds[2:4]), int(ds[4:])
            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= date.today().year:
                datetime(year, month, day)
                text = text[:m.start()] + text[m.end():]
                return f"{month:02d}/{day:02d}/{year}", text.strip()
        except ValueError:
            pass
        # Try YYYYMMDD
        try:
            year, month, day = int(ds[:4]), int(ds[4:6]), int(ds[6:])
            if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= date.today().year:
                datetime(year, month, day)
                text = text[:m.start()] + text[m.end():]
                return f"{month:02d}/{day:02d}/{year}", text.strip()
        except ValueError:
            pass

    return None, text


def extract_address(text: str) -> Tuple[Optional[str], str]:
    """Extract street address."""
    # Pattern: number + street name + type
    street_type_pattern = '|'.join(re.escape(t) for t in STREET_TYPES)
    pattern = rf'\b(\d+\s+[A-Za-z0-9\s\.]+?(?:{street_type_pattern})\.?(?:\s+(?:apt|suite|ste|unit|#)\s*\w+)?)\b'
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        addr = m.group(1).strip()
        text = text[:m.start()] + text[m.end():]
        return addr, text.strip()
    return None, text


def extract_name_from_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract first and last name from a line."""
    line = re.sub(r'[,.|]', ' ', line)
    line = re.sub(r'\s+', ' ', line).strip()
    words = [w for w in line.split() if re.match(r'^[A-Za-z\'\-]+$', w) and len(w) >= 2]
    if len(words) >= 2:
        if len(words) == 3:
            return f"{words[0]} {words[1]}".title(), words[2].capitalize()
        elif len(words) > 3:
            return ' '.join(words[:-1]).title(), words[-1].capitalize()
        else:
            return words[0].capitalize(), words[1].capitalize()
    elif len(words) == 1:
        return words[0].capitalize(), None
    return None, None


def remove_labels(text: str) -> str:
    """Remove common field labels from text."""
    text = re.sub(
        r'\b(name|first\s*name|last\s*name|address|city|state|zip|country|phone|email|ssn|dob|full\s*name|addresses)\s*:?\s*',
        '', text, flags=re.IGNORECASE
    )
    text = text.replace('|', ' ')
    text = re.sub(r'\s+[\+\-]\s+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ─── Main parser ─────────────────────────────────────────────────────────────

def parse_freeform(raw_text: str, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Parse freeform text into structured fields.
    Supports formats:
      - "John Smith NY 10001"
      - "John Smith\n123 Main St, New York, NY 10001\nDOB: 01/15/1985"
      - "First Name: John, Last Name: Smith, ..."
      - "John|Smith|123 Main St|New York|NY|10001"

    Returns dict with: first_name, last_name, address, city, state, zip,
                       dob, ssn, phone, email, dl, valid, errors
    """
    result: Dict[str, Any] = {
        "first_name": None, "last_name": None, "address": None,
        "city": None, "state": None, "zip": None, "dob": None,
        "ssn": None, "phone": None, "email": None, "dl": None,
        "valid": False, "errors": [],
    }

    if not raw_text or not raw_text.strip():
        result["errors"].append("Empty input")
        return result

    text = raw_text.strip()
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Strategy 0: Pipe format
    if text.count('|') >= 3:
        result = _parse_pipe(text)
    # Strategy 1: Structured key:value
    elif ':' in text and re.search(r'(?:first\s*name|last\s*name|fname|lname)\s*:', text, re.IGNORECASE):
        result = _parse_structured(text)
    # Strategy 2: Multiline
    elif len(lines) >= 2:
        result = _parse_multiline(lines)
    # Strategy 3: Single line
    else:
        result = _parse_single_line(text)

    # Enhance: extract anything missed
    result = _enhance(result, text)

    # Validate required fields
    if required_fields is None:
        required_fields = ["first_name", "last_name"]

    errors = []
    for field in required_fields:
        if field in result and not result.get(field):
            errors.append(f"Missing {field.replace('_', ' ')}")
    result["errors"] = errors
    result["valid"] = len(errors) == 0
    return result


def _parse_pipe(text: str) -> Dict:
    """Parse pipe-separated format: Name|Address|City|State|ZIP|..."""
    result: Dict[str, Any] = {
        "first_name": None, "last_name": None, "address": None,
        "city": None, "state": None, "zip": None, "dob": None,
        "ssn": None, "phone": None, "email": None, "dl": None,
    }
    lines = text.strip().split('\n')
    if lines and '|' in lines[0]:
        parts = [p.strip() for p in lines[0].split('|')]
        if len(parts) >= 1 and parts[0]:
            fn, ln = extract_name_from_line(parts[0])
            result["first_name"] = fn
            result["last_name"] = ln
        if len(parts) > 1 and parts[1]:
            result["address"] = parts[1]
        if len(parts) > 2 and parts[2]:
            result["city"] = parts[2]
        if len(parts) > 3 and parts[3]:
            sc, _ = extract_state(parts[3])
            result["state"] = sc or parts[3]
        if len(parts) > 4 and parts[4]:
            zc, _ = extract_zip(parts[4])
            result["zip"] = zc or parts[4]
        if len(parts) > 6 and parts[6]:
            ph, _ = extract_phone(parts[6])
            result["phone"] = ph
        # Check remaining lines for DOB/SSN
        for line in lines[1:]:
            if not result["dob"]:
                dob, _ = extract_dob(line)
                result["dob"] = dob
            if not result["ssn"]:
                ssn, _ = extract_ssn(line)
                result["ssn"] = ssn
    return result


def _parse_structured(text: str) -> Dict:
    """Parse key: value format."""
    result: Dict[str, Any] = {
        "first_name": None, "last_name": None, "address": None,
        "city": None, "state": None, "zip": None, "dob": None,
        "ssn": None, "phone": None, "email": None, "dl": None,
    }
    patterns = {
        "first_name": r'(?:first\s*name|fname)\s*:\s*([^\n,;]+)',
        "last_name":  r'(?:last\s*name|lname)\s*:\s*([^\n,;]+)',
        "address":    r'(?:address|addr)\s*:\s*([^\n,;]+)',
        "city":       r'city\s*:\s*([^\n,;]+)',
        "state":      r'state\s*:\s*([^\n,;]+)',
        "zip":        r'zip(?:\s*code)?\s*:\s*([^\n,;]+)',
        "dob":        r'(?:dob|date\s*of\s*birth|birth)\s*:\s*([^\n,;]+)',
        "ssn":        r'ssn\s*:\s*([^\n,;]+)',
        "phone":      r'phone\s*:\s*([^\n,;]+)',
        "email":      r'email\s*:\s*([^\n,;]+)',
    }
    for field, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if field == "state":
                sc, _ = extract_state(val)
                result[field] = sc or val.upper()[:2]
            elif field == "zip":
                zc, _ = extract_zip(val)
                result[field] = zc or val
            elif field == "dob":
                dob, _ = extract_dob(val)
                result[field] = dob or val
            elif field == "ssn":
                ssn, _ = extract_ssn(val)
                result[field] = ssn or val
            elif field == "phone":
                ph, _ = extract_phone(val)
                result[field] = ph or val
            else:
                result[field] = val.strip()
    return result


def _parse_multiline(lines: List[str]) -> Dict:
    """Parse multiline format: name on line 1, address on line 2, etc."""
    result: Dict[str, Any] = {
        "first_name": None, "last_name": None, "address": None,
        "city": None, "state": None, "zip": None, "dob": None,
        "ssn": None, "phone": None, "email": None, "dl": None,
    }
    remaining_lines = list(lines)

    # Line 1: name
    if remaining_lines:
        fn, ln = extract_name_from_line(remaining_lines[0])
        result["first_name"] = fn
        result["last_name"] = ln
        remaining_lines.pop(0)

    # Remaining lines: address, city/state/zip, dob, ssn
    for line in remaining_lines:
        line_clean = remove_labels(line)

        # Try DOB
        if not result["dob"]:
            dob, rest = extract_dob(line_clean)
            if dob:
                result["dob"] = dob
                line_clean = rest

        # Try SSN
        if not result["ssn"]:
            ssn, rest = extract_ssn(line_clean)
            if ssn:
                result["ssn"] = ssn
                line_clean = rest

        # Try phone
        if not result["phone"]:
            ph, rest = extract_phone(line_clean)
            if ph:
                result["phone"] = ph
                line_clean = rest

        # Try email
        if not result["email"]:
            em = re.search(EMAIL_REGEX, line_clean, re.IGNORECASE)
            if em:
                result["email"] = em.group(0)
                line_clean = line_clean[:em.start()] + line_clean[em.end():]

        # Try ZIP
        if not result["zip"]:
            zc, rest = extract_zip(line_clean)
            if zc:
                result["zip"] = zc
                line_clean = rest

        # Try state
        if not result["state"]:
            sc, rest = extract_state(line_clean.upper())
            if sc:
                result["state"] = sc
                line_clean = rest

        # Try address
        if not result["address"]:
            addr, rest = extract_address(line_clean)
            if addr:
                result["address"] = addr
                line_clean = rest

        # Try city
        if not result["city"]:
            for city in COMMON_CITIES:
                if city in line_clean.lower():
                    result["city"] = city.title()
                    line_clean = re.sub(re.escape(city), '', line_clean, flags=re.IGNORECASE)
                    break

    return result


def _parse_single_line(text: str) -> Dict:
    """Parse single line: 'John Smith NY 10001' or 'John Smith, 123 Main St, NY'."""
    result: Dict[str, Any] = {
        "first_name": None, "last_name": None, "address": None,
        "city": None, "state": None, "zip": None, "dob": None,
        "ssn": None, "phone": None, "email": None, "dl": None,
    }
    working = remove_labels(text)

    # Extract structured fields first
    dob, working = extract_dob(working)
    result["dob"] = dob

    ssn, working = extract_ssn(working)
    result["ssn"] = ssn

    ph, working = extract_phone(working)
    result["phone"] = ph

    em = re.search(EMAIL_REGEX, working, re.IGNORECASE)
    if em:
        result["email"] = em.group(0)
        working = working[:em.start()] + working[em.end():]

    zc, working = extract_zip(working)
    result["zip"] = zc

    addr, working = extract_address(working)
    result["address"] = addr

    sc, working = extract_state(working.upper())
    result["state"] = sc

    # City
    for city in COMMON_CITIES:
        if city in working.lower():
            result["city"] = city.title()
            working = re.sub(re.escape(city), '', working, flags=re.IGNORECASE)
            break

    # Name from what's left
    fn, ln = extract_name_from_line(working)
    result["first_name"] = fn
    result["last_name"] = ln

    return result


def _enhance(result: Dict, original_text: str) -> Dict:
    """Try to fill in missing fields from original text."""
    text = original_text

    if not result.get("dob"):
        dob, _ = extract_dob(text)
        result["dob"] = dob

    if not result.get("ssn"):
        ssn, _ = extract_ssn(text)
        result["ssn"] = ssn

    if not result.get("phone"):
        ph, _ = extract_phone(text)
        result["phone"] = ph

    if not result.get("zip"):
        zc, _ = extract_zip(text)
        result["zip"] = zc

    if not result.get("state"):
        sc, _ = extract_state(text.upper())
        result["state"] = sc

    if not result.get("email"):
        em = re.search(EMAIL_REGEX, text, re.IGNORECASE)
        if em:
            result["email"] = em.group(0)

    return result


# ─── Individual field validators ─────────────────────────────────────────────

def validate_phone(phone: str) -> Tuple[bool, str, str]:
    """
    Validate and normalize US phone number.
    Returns: (is_valid, normalized_phone, error_message)
    """
    cleaned = re.sub(r'[^\d]', '', phone)
    if len(cleaned) == 10:
        cleaned = '1' + cleaned
    if len(cleaned) != 11 or not cleaned.startswith('1'):
        return False, phone, "❌ Invalid phone format\n\nUse: +1 (320) 932-0202 or 3209320202"
    return True, f"+{cleaned}", ""


def validate_ssn(ssn: str) -> Tuple[bool, str, str]:
    """Validate and normalize SSN."""
    cleaned = re.sub(r'[^\d]', '', ssn)
    if len(cleaned) != 9:
        return False, ssn, "❌ Invalid SSN format\n\nUse: XXX-XX-XXXX or 9 digits"
    normalized = f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"
    return True, normalized, ""


def validate_state(state: str) -> Tuple[bool, str, str]:
    """Validate US state code."""
    code = state.upper().strip()
    if code in US_STATES_LIST:
        return True, code, ""
    # Try full name
    full_lower = state.lower().strip()
    if full_lower in US_STATES_REVERSE:
        return True, US_STATES_REVERSE[full_lower], ""
    return False, state, f"❌ Invalid state: {state}\n\nUse 2-letter code (CA, NY, TX...)"


def validate_zip(zip_code: str) -> Tuple[bool, str, str]:
    """Validate ZIP code."""
    if re.match(ZIP_REGEX, zip_code.strip()):
        return True, zip_code.strip(), ""
    return False, zip_code, "❌ Invalid ZIP\n\nUse: 12345 or 12345-6789"


def validate_dob(dob: str) -> Tuple[bool, str, str]:
    """Validate and normalize DOB to MM/DD/YYYY."""
    normalized, _ = extract_dob(dob)
    if normalized:
        return True, normalized, ""
    return False, dob, "❌ Invalid DOB format\n\nUse: MM/DD/YYYY (e.g., 01/15/1990)"


def validate_email(email: str) -> Tuple[bool, str, str]:
    """Validate email address."""
    if re.match(EMAIL_REGEX, email.strip(), re.IGNORECASE):
        return True, email.strip().lower(), ""
    return False, email, "❌ Invalid email format"


# ─── Batch phone validator ────────────────────────────────────────────────────

def parse_phone_list(text: str) -> Tuple[List[str], List[str]]:
    """
    Parse a list of phone numbers from multiline text.
    Returns: (valid_phones, errors)
    Supports 10-20 phones per batch.
    """
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    valid = []
    errors = []
    for line in lines:
        # Remove common separators
        line = re.sub(r'[,;]', '', line).strip()
        ok, normalized, err = validate_phone(line)
        if ok:
            valid.append(normalized)
        else:
            errors.append(f"{line}: {err}")
    return valid, errors


def parse_person_list(text: str) -> Tuple[List[Dict], List[str]]:
    """
    Parse a list of persons from multiline text.
    Each person on a new line or separated by blank lines.
    Returns: (parsed_persons, errors)
    """
    # Split by blank lines (groups) or by single lines
    blocks = re.split(r'\n\s*\n', text.strip())
    if len(blocks) == 1:
        # Single line per person
        blocks = text.strip().split('\n')

    persons = []
    errors = []
    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue
        parsed = parse_freeform(block)
        parsed["_line"] = i + 1
        if not parsed.get("first_name") or not parsed.get("last_name"):
            errors.append(f"Line {i+1}: could not extract name from '{block[:50]}'")
        else:
            persons.append(parsed)
    return persons, errors


# ─── Format helpers ───────────────────────────────────────────────────────────

def format_ssn_display(ssn: str) -> str:
    """Format SSN for display: XXX-XX-XXXX."""
    cleaned = re.sub(r'[^\d]', '', ssn)
    if len(cleaned) == 9:
        return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"
    return ssn


def format_phone_display(phone: str) -> str:
    """Format phone for display: +1 (XXX) XXX-XXXX."""
    cleaned = re.sub(r'[^\d]', '', phone)
    if len(cleaned) == 11 and cleaned.startswith('1'):
        cleaned = cleaned[1:]
    if len(cleaned) == 10:
        return f"+1 ({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    return phone
