from __future__ import annotations

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any, Tuple
import re
import logging
from datetime import datetime, date
from dateutil import parser as date_parser
from nameparser import HumanName
import usaddress
from mirror_bot.constants.states_data import US_STATES_LIST, US_STATES

logger = logging.getLogger(__name__)

US_STATES_REVERSE = {full_name.lower(): code for code, full_name in US_STATES.items()}

SSN_REGEX = r'^\d{3}-\d{2}-\d{4}$'
ZIP_REGEX = r'^\d{5}(-\d{4})?$'
PHONE_REGEX = r'^\+?1?\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{4}$'
DOB_REGEX = r'^\d{2}/\d{2}/\d{4}$'
DL_REGEX = r'^[A-Z0-9]{5,20}$'


# ─── Shared validators (reusable across models) ──────────────────────────

def _validate_state(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if v.upper() not in US_STATES_LIST:
        raise ValueError(f'❌ Invalid state: {v}\n\nUse 2-letter code (CA, NY, TX...)')
    return v.upper()


def _validate_zip(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if not re.match(ZIP_REGEX, v):
        raise ValueError('❌ Invalid ZIP\n\nUse: 12345 or 12345-6789')
    return v


def _validate_address(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if len(v) < 5:
        raise ValueError('❌ Invalid address: too short')
    return v


def _validate_city(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if len(v) < 2:
        raise ValueError('❌ Invalid city: too short')
    return v


def _validate_dob_optional(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if not re.match(DOB_REGEX, v):
        raise ValueError('❌ Invalid DOB format\n\nUse: MM/DD/YYYY (e.g., 01/15/1990)')
    try:
        datetime.strptime(v, '%m/%d/%Y')
    except ValueError:
        raise ValueError('❌ Invalid date\n\nCheck day/month values')
    return v


def _validate_dob_with_normalize(v: Optional[str], required: bool = False) -> Optional[str]:
    if not v:
        if required:
            raise ValueError('❌ Date of birth (DOB) is required\n\nUse: MM/DD/YYYY')
        return v
    normalized, _ = extract_dob(v)
    if normalized:
        v = normalized
    if not re.match(DOB_REGEX, v):
        raise ValueError('❌ Invalid DOB format\n\nUse: MM/DD/YYYY')
    try:
        datetime.strptime(v, '%m/%d/%Y')
    except ValueError:
        raise ValueError('❌ Invalid date\n\nCheck day/month values')
    return v


# ─── Pydantic models ─────────────────────────────────────────────────────

class PhoneSearchData(BaseModel):
    phone: str

    @validator('phone')
    def validate_phone(cls, v):
        cleaned = re.sub(r'[^\d]', '', v)
        if len(cleaned) == 10:
            cleaned = '1' + cleaned
        if len(cleaned) != 11 or not cleaned.startswith('1'):
            raise ValueError('❌ Invalid phone format\n\nUse: +1 (320) 932-0202 or 3209320202')
        return f"+{cleaned}"


class BasePersonData(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = Field(None, min_length=5, max_length=200)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, alias='zip')

    _v_state = validator('state', allow_reuse=True, pre=True)(_validate_state)
    _v_zip = validator('zip_code', allow_reuse=True, pre=True)(_validate_zip)
    _v_addr = validator('address', allow_reuse=True, pre=True)(_validate_address)
    _v_city = validator('city', allow_reuse=True, pre=True)(_validate_city)

    class Config:
        populate_by_name = True


class SSNLookupData(BasePersonData):
    """SSN Lookup — flexible validation, only name required."""
    dob: Optional[str] = None

    _v_dob = validator('dob', allow_reuse=True, pre=True)(_validate_dob_optional)

    class Config:
        populate_by_name = True


class DLLookupData(BasePersonData):
    """DL Lookup — flexible validation, only name required."""
    dob: Optional[str] = None

    _v_dob = validator('dob', allow_reuse=True, pre=True)(_validate_dob_optional)

    class Config:
        populate_by_name = True


class MVRLookupData(BaseModel):
    """MVR Lookup — no validation, accepts any format."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = Field(None, alias='zip')
    dob: Optional[str] = None
    ssn: Optional[str] = None
    dl: Optional[str] = None
    dl_state: Optional[str] = None

    class Config:
        populate_by_name = True


class FullMVRLookupData(MVRLookupData):
    """Full MVR Lookup — same schema as MVR."""
    pass


class CreditScoreLookupData(BasePersonData):
    """Credit Score Lookup — name and DOB required, SSN optional."""
    dob: str = Field(..., description="Date of birth is required")
    ssn: Optional[str] = None

    @validator('ssn')
    def validate_ssn(cls, v):
        if v is None:
            return v
        if not re.match(SSN_REGEX, v):
            raise ValueError('❌ Invalid SSN format\n\nUse: XXX-XX-XXXX or XXXXXXXXX')
        return v

    @validator('dob')
    def validate_dob(cls, v):
        return _validate_dob_with_normalize(v, required=True)

    class Config:
        populate_by_name = True


class BGLookupData(BasePersonData):
    """Background Lookup — flexible validation, only name required."""
    class Config:
        populate_by_name = True


class MMNLookupData(BasePersonData):
    """MMN Lookup — flexible validation, only name required."""
    class Config:
        populate_by_name = True


class EINLookupData(BaseModel):
    """EIN Lookup — no validation, accepts any format."""
    legal_business_name: Optional[str] = Field(None, alias='business_name')
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    class Config:
        populate_by_name = True


class CreditReportData(BasePersonData):
    ssn: str
    dob: str
    address: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., alias='zip')

    @validator('ssn')
    def validate_ssn(cls, v):
        if not v:
            raise ValueError('Missing SSN (9 digits required)')
        cleaned = re.sub(r'[^\d]', '', v)
        if len(cleaned) != 9:
            raise ValueError(f'Invalid SSN - got {len(cleaned)} digits, need exactly 9 digits')
        return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"

    @validator('dob')
    def validate_dob(cls, v):
        return _validate_dob_with_normalize(v, required=True)

    @validator('address')
    def validate_address_required(cls, v):
        if not v or len(v) < 5:
            raise ValueError('Missing or too short address (min 5 characters)')
        return v

    @validator('city')
    def validate_city_required(cls, v):
        if not v or len(v) < 2:
            raise ValueError('Missing or too short city name (min 2 characters)')
        return v

    @validator('state')
    def validate_state_required(cls, v):
        if not v:
            raise ValueError('❌ Missing state')
        return _validate_state(v)

    @validator('zip_code')
    def validate_zip_required(cls, v):
        if not v:
            raise ValueError('❌ Missing ZIP code')
        return _validate_zip(v)


class AddInfoCRData(BaseModel):
    """Add Info CR — no validation, accepts any format."""
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = Field(None, alias='zip')
    employer: Optional[str] = None
    ssn: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[str] = None

    class Config:
        populate_by_name = True


# ============================================
# UNIVERSAL FREEFORM TEXT PARSER
# ============================================

STREET_TYPES = [
    'street', 'avenue', 'road', 'lane', 'boulevard', 'drive', 'court', 'place',
    'way', 'parkway', 'highway', 'circle', 'terrace', 'trail', 'loop', 'path',
    'alley', 'branch', 'beach',
    'st', 'ave', 'av', 'rd', 'ln', 'blvd', 'dr', 'ct', 'pl', 'pkwy', 'hwy',
    'cir', 'ter', 'trl',
    'plaza', 'square', 'sq', 'pike', 'row', 'run', 'walk', 'crossing', 'commons',
    'green', 'grove', 'heights', 'ht', 'hill', 'hollow', 'landing', 'park', 'point',
    'ridge', 'spring', 'station', 'trace', 'turnpike', 'vista', 'woods'
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
    'modesto', 'fontana', 'santa clarita', 'birmingham', 'oxnard', 'fayetteville',
    'moreno valley', 'glendale', 'yonkers', 'huntington beach', 'montgomery',
    'amarillo', 'little rock', 'akron', 'augusta', 'grand rapids', 'mobile',
    'lake worth', 'evansville', 'rocklin', 'perrysburg', 'dickson', 'pensacola',
    'worcester', 'chatham', 'roscommon', 'lavallette', 'brooklyn', 'berea'
}

MONTH_NAMES = {
    'jan': 1, 'january': 1, 'янв': 1, 'январь': 1,
    'feb': 2, 'february': 2, 'фев': 2, 'февраль': 2,
    'mar': 3, 'march': 3, 'мар': 3, 'март': 3,
    'apr': 4, 'april': 4, 'апр': 4, 'апрель': 4,
    'may': 5, 'май': 5,
    'jun': 6, 'june': 6, 'июн': 6, 'июнь': 6,
    'jul': 7, 'july': 7, 'июл': 7, 'июль': 7,
    'aug': 8, 'august': 8, 'авг': 8, 'август': 8,
    'sep': 9, 'september': 9, 'сен': 9, 'сентябрь': 9,
    'oct': 10, 'october': 10, 'окт': 10, 'октябрь': 10,
    'nov': 11, 'november': 11, 'ноя': 11, 'ноябрь': 11,
    'dec': 12, 'december': 12, 'дек': 12, 'декабрь': 12
}

EXCLUDE_WORDS = {
    'apt', 'apartment', 'unit', 'ste', 'suite', 'lot', 'floor', 'fl', 'room', 'rm',
    'jr', 'sr', 'ii', 'iii', 'iv', 'esq',
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december'
}


def _empty_result() -> Dict[str, Any]:
    return {
        "first_name": None, "last_name": None, "address": None,
        "city": None, "state": None, "zip": None, "dob": None,
        "ssn": None, "email": None, "phone": None, "dl": None,
    }


def _normalize_year(year: int) -> int:
    if year < 100:
        return 2000 + year if year <= 50 else 1900 + year
    return year


def _is_valid_date(month: int, day: int, year: int) -> bool:
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= date.today().year):
        return False
    try:
        datetime(year, month, day)
        return True
    except ValueError:
        return False


def clean_text(text: str) -> str:
    text = re.sub(r'[:#;]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def simple_detect_ssn_vs_phone(number: str) -> tuple[str, str]:
    digits = re.sub(r'[^\d]', '', number)
    if len(digits) == 9:
        return 'ssn', f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    elif len(digits) == 10:
        return 'phone', f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        d = digits[1:]
        return 'phone', f"({d[:3]}) {d[3:6]}-{d[6:]}"
    return 'unknown', number


def extract_ssn(text: str, state: str = None) -> tuple[Optional[str], str]:
    number_patterns = [
        r'\bSSN[:\s]*(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
        r'\b(\d{3}[-\s]\d{2}[-\s]\d{4})\b',
        r'\b(\d{3}[-\s]\d{3}[-\s]\d{4})\b',
        r'\b(\d{9,11})\b',
    ]
    for pattern in number_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            number = match.group(1)
            number_type, formatted = simple_detect_ssn_vs_phone(number)
            logger.info("[SSN DEBUG] Number: %s, State: %s, Type: %s, Formatted: %s",
                        number, state, number_type, formatted)
            if number_type == 'ssn':
                ssn_digits = re.sub(r'[^\d]', '', formatted)
                if len(ssn_digits) == 9:
                    area, group, serial = int(ssn_digits[:3]), int(ssn_digits[3:5]), int(ssn_digits[5:])
                    if area == 0 or area == 666 or area >= 900 or group == 0 or serial == 0:
                        continue
                    text = text[:match.start()] + text[match.end():]
                    return formatted, text.strip()
    return None, text


def extract_email(text: str) -> tuple[Optional[str], str]:
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if match:
        return match.group(0), (text[:match.start()] + text[match.end():]).strip()
    return None, text


def extract_phone(text: str) -> tuple[Optional[str], str]:
    for pattern in [
        r'\+?\d{1,3}[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}',
        r'\b\d{10}\b',
        r'\b\d{3}[-\s]\d{3}[-\s]\d{4}\b',
    ]:
        match = re.search(pattern, text)
        if match:
            return match.group(0), (text[:match.start()] + text[match.end():]).strip()
    return None, text


def extract_dl(text: str) -> tuple[Optional[str], str]:
    for pattern in [
        r'\bDL[:\s]*([A-Z0-9]{5,20})\b',
        r'\b(DL\s*NUMBER[:\s]*[A-Z0-9]{5,20})\b',
        r'\b([A-Z]{1,2}\d{6,12})\b',
        r'\b([A-Z0-9]{8,15})\b',
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            dl = match.group(1) if 'DL' in match.group(0).upper() else match.group(0)
            text = text[:match.start()] + text[match.end():]
            return dl.strip().upper(), text.strip()
    return None, text


def remove_common_labels(text: str) -> str:
    text = re.sub(r'\b(name|first\s*name|last\s*name|address|city|state|zip|country|phone|email|ssn|dob|full\s*name|addresses):(?!\s)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(name|first\s*name|last\s*name|address|city|state|zip|country|phone|email|ssn|dob|full\s*name|addresses)\s*:\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(name|first\s*name|last\s*name|address|city|state|zip|country|phone|email|ssn|dob|full\s*name|addresses)\b(?!\s*:)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(your credit score|age|phones|email|null|usa|united states|us)\b', '', text, flags=re.IGNORECASE)
    text = text.replace('|', ' ')
    text = re.sub(r'\s+[\+\-]\s+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_zip(text: str) -> tuple[Optional[str], str]:
    match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', text)
    if match:
        return match.group(1), (text[:match.start()] + text[match.end():]).strip()
    return None, text


def extract_dob(text: str) -> tuple[Optional[str], str]:
    # Named-month patterns: "Sep 12 1965", "12 Sep 1965", "1965 Sep 12"
    month_patterns = [
        (r'\b([a-zA-Zа-яА-Я]{3,})\s+(\d{1,2}),?\s+(\d{4}|\d{2})\b', lambda m: (m[0], m[1], m[2])),
        (r'\b(\d{1,2})\s+([a-zA-Zа-яА-Я]{3,}),?\s+(\d{4}|\d{2})\b', lambda m: (m[1], m[0], m[2])),
        (r'\b(\d{4}|\d{2})\s+([a-zA-Zа-яА-Я]{3,})\s+(\d{1,2})\b', lambda m: (m[1], m[2], m[0])),
    ]
    for pattern, extractor in month_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            month_name, day_s, year_s = extractor(match.groups())
            month_name_lower = month_name.lower()
            if month_name_lower in MONTH_NAMES:
                month = MONTH_NAMES[month_name_lower]
                day, year = int(day_s), _normalize_year(int(year_s))
                if _is_valid_date(month, day, year):
                    text = text[:match.start()] + text[match.end():]
                    return f"{month:02d}/{day:02d}/{year}", text.strip()

    # No-separator dates: "01012000" (8 digits) or "010100" (6 digits)
    no_sep = re.search(r'\b(\d{6}|\d{8})\b', text)
    if no_sep:
        ds = no_sep.group(1)
        if len(ds) == 8:
            candidates = [(ds[:2], ds[2:4], ds[4:8]), (ds[2:4], ds[:2], ds[4:8])]
        else:
            candidates = [(ds[:2], ds[2:4], ds[4:6]), (ds[2:4], ds[:2], ds[4:6])]
        for ms, dd, ys in candidates:
            try:
                m, d, y = int(ms), int(dd), _normalize_year(int(ys))
                if m > 12 and d <= 12:
                    m, d = d, m
                elif m > 12:
                    continue
                if _is_valid_date(m, d, y):
                    text = text[:no_sep.start()] + text[no_sep.end():]
                    return f"{m:02d}/{d:02d}/{y}", text.strip()
            except ValueError:
                continue

    # Dates with separators: /, -, .
    date_patterns = [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2})\b',
        r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b',
        r'\b(\d{1,2}\.\d{1,2}\.\d{2})\b',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            ds = match.group(1)
            try:
                result = _parse_date_with_separators(ds)
                if result:
                    text = text[:match.start()] + text[match.end():]
                    return result, text.strip()
            except (ValueError, IndexError):
                continue
    return None, text


def _parse_date_with_separators(ds: str) -> Optional[str]:
    if '/' in ds or '-' in ds:
        sep = '/' if '/' in ds else '-'
        parts = ds.split(sep)
        if len(parts) != 3:
            return None
        if len(parts[0]) == 4:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            p1, p2, year = int(parts[0]), int(parts[1]), int(parts[2])
            if p1 > 12 and p2 <= 12:
                day, month = p1, p2
            elif p1 <= 12 and p2 > 12:
                month, day = p1, p2
            else:
                month, day = p1, p2
        year = _normalize_year(year)
        if _is_valid_date(month, day, year):
            return f"{month:02d}/{day:02d}/{year}"
    elif '.' in ds:
        parts = ds.split('.')
        if len(parts) != 3:
            return None
        day, month, year = int(parts[0]), int(parts[1]), _normalize_year(int(parts[2]))
        if _is_valid_date(month, day, year):
            return f"{month:02d}/{day:02d}/{year}"
    return None


def extract_address(text: str) -> Tuple[Optional[str], str]:
    try:
        lines = text.replace('|', '\n').split('\n')
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            if re.match(r'^\d+', line):
                try:
                    parsed, _ = usaddress.tag(line)
                    if 'AddressNumber' in parsed and 'StreetName' in parsed:
                        parts = [parsed[k] for k in
                                 ['AddressNumber', 'StreetNamePreDirectional', 'StreetName',
                                  'StreetNamePostType', 'OccupancyType', 'OccupancyIdentifier']
                                 if k in parsed]
                        if parts:
                            addr = ' '.join(parts)
                            text = text.replace(line, '').replace('||', '|').strip('|').strip()
                            return addr, text
                except Exception:
                    pass
    except Exception:
        pass

    street_types_pattern = '|'.join(STREET_TYPES)

    # Short address: number + words + street type
    match = re.search(rf'\b(\d{{1,6}}\s+(?:[A-Za-z0-9]+\s+){{0,3}}(?:{street_types_pattern})\b)', text, re.IGNORECASE)
    if match:
        addr = re.sub(r'\s+', ' ', match.group(1).strip())
        return addr, (text[:match.start()] + text[match.end():]).strip()

    # Long address with apt/unit
    match = re.search(rf'\b(\d{{1,6}}[A-Z]?\s+[A-Za-z0-9\s.,#-]+?(?:{street_types_pattern})\b\.?(?:\s+(?:apt|apartment|unit|ste|suite|#|lot)\s*[A-Za-z0-9-]+)?)', text, re.IGNORECASE)
    if match:
        addr = re.sub(r'\s+', ' ', match.group(1).strip())
        return addr, (text[:match.start()] + text[match.end():]).strip()

    # Flexible: number + words before city/state/zip
    flex = r'\b(\d{1,6}\s+[A-Za-z0-9\s]+?)(?=\s+(?:' + '|'.join(COMMON_CITIES) + r')\b|\s+[A-Z]{2}\s+\d{5}|\s+\d{5})'
    match = re.search(flex, text, re.IGNORECASE)
    if match:
        addr = re.sub(r'\s+', ' ', match.group(1).strip())
        if len(addr.split()) <= 8:
            return addr, (text[:match.start()] + text[match.end():]).strip()

    return None, text


def extract_state(text: str) -> tuple[Optional[str], str]:
    pattern = r'\b(' + '|'.join(US_STATES_LIST) + r')\b'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).upper(), (text[:match.start()] + text[match.end():]).strip()
    for code, full_name in US_STATES.items():
        if re.search(rf'\b{re.escape(full_name)}\b', text, re.IGNORECASE):
            text = re.sub(rf'\b{re.escape(full_name)}\b', '', text, flags=re.IGNORECASE)
            return code, text.strip()
    return None, text


def extract_city(text: str) -> tuple[Optional[str], str]:
    text_lower = text.lower()
    for city in COMMON_CITIES:
        if re.search(rf'\b{re.escape(city)}\b', text_lower):
            match = re.search(rf'\b({re.escape(city)})\b', text, re.IGNORECASE)
            if match:
                city_name = ' '.join(w.capitalize() for w in match.group(1).split())
                text = text[:match.start()] + text[match.end():]
                return city_name, text.strip()

    words = text.split()
    potential_cities = []
    for i in range(len(words)):
        for length in [3, 2, 1]:
            if i + length <= len(words):
                candidate = ' '.join(words[i:i+length])
                candidate_lower = candidate.lower()
                if not re.match(r'^[A-Za-z\s]+$', candidate):
                    continue
                min_len = 4 if length == 1 else 3
                if len(candidate.replace(' ', '')) < min_len:
                    continue
                if candidate_lower in STREET_TYPES or candidate_lower in EXCLUDE_WORDS:
                    continue
                potential_cities.append((i, length, candidate))

    if potential_cities:
        i, length, city = potential_cities[-1]
        remaining = words[:i] + words[i+length:]
        city = ' '.join(w.capitalize() for w in city.split())
        return city, ' '.join(remaining).strip()
    return None, text


def extract_name_from_first_line(text: str) -> Tuple[Optional[str], Optional[str]]:
    text = text.replace('|', '\n')
    lines = text.split('\n')
    first_line = None

    for line in lines:
        if re.search(r'\b(full\s*)?name\s*:', line, re.IGNORECASE):
            first_line = line.strip()
            break
    if not first_line:
        for line in lines:
            if line.strip():
                first_line = line.strip()
                break
    if not first_line:
        return None, None

    first_line = re.sub(r'\b(name|first\s*name|last\s*name|full\s*name|address|city|state|zip|country|phone|email|ssn|dob|addresses):(?!\s)', '', first_line, flags=re.IGNORECASE)
    first_line = re.sub(r'\b(name|first\s*name|last\s*name|full\s*name|address|city|state|zip|country|phone|email|ssn|dob|addresses)\s*:\s*', '', first_line, flags=re.IGNORECASE)
    first_line = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', '', first_line)
    first_line = re.sub(r'\+?\d{1,3}[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}', '', first_line)
    first_line = re.sub(r'\b\d{5,10}\b', '', first_line)

    name_words = []
    for word in first_line.strip().split():
        cleaned = word.strip('.,;:')
        if re.match(r'^[A-Za-z\'-]{2,}$', cleaned):
            name_words.append(cleaned)
        elif len(cleaned) == 1 and cleaned.isupper():
            name_words.append(cleaned)
        elif re.search(r'\d', cleaned) or len(cleaned) < 2:
            break
        if len(name_words) >= 4:
            break

    if len(name_words) >= 2:
        try:
            name = HumanName(' '.join(name_words))
            if name.first and name.last:
                first_full = f"{name.first} {name.middle}" if name.middle else name.first
                return first_full.title(), name.last.capitalize()
        except Exception:
            pass
        if len(name_words) == 3 and len(name_words[1]) == 1:
            return f"{name_words[0]} {name_words[1]}".title(), name_words[2].capitalize()
        if len(name_words) > 2:
            return ' '.join(name_words[:-1]).title(), name_words[-1].capitalize()
        return name_words[0].capitalize(), name_words[-1].capitalize()
    return None, None


def extract_name(text: str) -> Tuple[Optional[str], Optional[str], str]:
    try:
        clean = re.sub(r'[,.|]', ' ', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        name = HumanName(clean)
        first_name = name.first.capitalize() if name.first else None
        last_name = name.last.capitalize() if name.last else None
        if not first_name or not last_name:
            words = [w for w in clean.split() if re.match(r'^[A-Za-z\'-]+$', w) and len(w) >= 2]
            if len(words) >= 2:
                first_name = first_name or words[0].capitalize()
                last_name = last_name or words[-1].capitalize()
        return first_name, last_name, ""
    except Exception:
        return None, None, text


def extract_name_from_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    clean_line = re.sub(r'(?:first\s*name|last\s*name|name)\s*:\s*', '', line, flags=re.IGNORECASE)
    clean_line = re.sub(r'[^\w\s\'-]', ' ', clean_line)
    clean_line = re.sub(r'\s+', ' ', clean_line).strip()

    if re.match(r'^[A-Za-z\s\'-]+$', clean_line) and len(clean_line.split()) >= 2:
        try:
            name = HumanName(clean_line)
            if name.first and name.last:
                first_name = f"{name.first} {name.middle}" if name.middle else name.first
                return first_name.title(), name.last.title()
        except Exception:
            pass
        words = [w for w in clean_line.split() if re.match(r'^[A-Za-z\'-]+$', w)]
        if len(words) >= 2:
            if len(words) == 3 and len(words[1]) == 1:
                return f"{words[0]} {words[1]}".title(), words[2].title()
            return words[0].title(), words[-1].title()
    return None, None


def validate_field(field_name: str, value: Any) -> Optional[str]:
    if value is None:
        return f"Missing {field_name}"
    if field_name in ("first_name", "last_name"):
        if len(value) < 2:
            return f"Invalid {field_name}: too short"
        if not re.match(r"^[A-Za-z\'\-\s]+$", value):
            return f"Invalid {field_name}: must contain only letters"
    elif field_name == "address":
        if len(value) < 5:
            return "Invalid address: too short"
        if not re.search(r'\d', value):
            return "Invalid address: must contain house number"
    elif field_name == "city":
        if len(value) < 2:
            return "Invalid city: too short"
        if not re.match(r"^[A-Za-z\s\.-]+$", value):
            return "Invalid city: must contain only letters"
    elif field_name == "state":
        if value.upper() not in US_STATES_LIST:
            return f"Invalid state: {value}"
    elif field_name == "zip":
        if not re.match(ZIP_REGEX, value):
            return f"Invalid ZIP: {value}"
    elif field_name == "dob":
        try:
            parsed = datetime.strptime(value, '%Y-%m-%d')
            if parsed.year < 1900 or parsed.year > date.today().year:
                return "Invalid DOB: year out of range"
        except Exception:
            return f"Invalid DOB format: {value}"
    return None


# ─── Main freeform parser ────────────────────────────────────────────────

def parse_freeform_text(raw_text: str, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    result = _empty_result()
    result["valid"] = False
    result["errors"] = []

    logger.info("[FREEFORM_PARSER] Input text: '%s'", raw_text)

    if not raw_text or not raw_text.strip():
        result["errors"].append("Empty input")
        return result

    text = raw_text.strip()
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    pipe_count = text.count('|')
    if pipe_count >= 3 or (pipe_count >= 1 and len(lines) == 1):
        result = parse_pipe_format(text)
    elif ':' in text and re.search(r'(?:first\s*name|last\s*name|fname|lname)\s*:', text, re.IGNORECASE):
        result = parse_structured_format(text)
    elif len(lines) >= 2:
        result = parse_multiline_format(lines)
    else:
        result = parse_single_line_format(text)

    result = enhance_parsing_results(result, text)

    if required_fields is None:
        required_fields = ["first_name", "last_name"]

    field_labels = {
        "first_name": "Missing first name", "last_name": "Missing last name",
        "address": "Missing address", "city": "Missing city",
        "state": "Missing state", "zip": "Missing ZIP code", "dob": "Missing date of birth",
    }
    errors = [field_labels.get(f, f"Missing {f}") for f in required_fields if f in result and not result[f]]
    result["errors"] = errors
    result["valid"] = len(errors) == 0
    logger.info("[FREEFORM_PARSER] Final result: %s", result)
    return result


def parse_pipe_format(text: str) -> Dict[str, Any]:
    result = _empty_result()
    lines = text.strip().split('\n')

    if lines and '|' in lines[0]:
        parts = [p.strip() for p in lines[0].split('|')]
        if len(parts) >= 5:
            if parts[0]:
                result["first_name"], result["last_name"] = extract_name_from_line(parts[0])
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
                result["phone"] = ph or parts[6]

    if len(lines) > 1:
        second = lines[1].strip()
        if '-' in second:
            sp = second.split('-')
            if len(sp) == 2:
                ssn, _ = extract_ssn(sp[0].strip())
                if ssn:
                    result["ssn"] = ssn
                dob, _ = extract_dob(sp[1].strip())
                if dob:
                    result["dob"] = dob
        else:
            ssn, _ = extract_ssn(second)
            if ssn:
                result["ssn"] = ssn
            dob, _ = extract_dob(second)
            if dob:
                result["dob"] = dob
    return result


def parse_structured_format(text: str) -> Dict[str, Any]:
    result = _empty_result()
    patterns = {
        "first_name": r'(?:first\s*name|fname)\s*:\s*([^,\n]+)',
        "last_name": r'(?:last\s*name|lname)\s*:\s*([^,\n]+)',
        "address": r'(?:address|addr)\s*:\s*([^,\n]+)',
        "city": r'city\s*:\s*([^,\n]+)',
        "state": r'state\s*:\s*([^,\n]+)',
        "zip": r'(?:zip|postal)\s*:\s*([^,\n]+)',
        "dob": r'(?:dob|date\s*of\s*birth|birth\s*date)\s*:\s*([^,\n]+)',
        "email": r'email\s*:\s*([^,\n]+)',
        "phone": r'phone\s*:\s*([^,\n]+)',
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if field == "dob":
                value, _ = extract_dob(value)
            elif field == "state":
                sc, _ = extract_state(value)
                value = sc or value
            result[field] = value
    return result


def parse_multiline_format(lines: List[str]) -> Dict[str, Any]:
    result = _empty_result()

    if lines:
        first_line = lines[0].strip()
        if ':' not in first_line:
            result["first_name"], result["last_name"] = extract_name_from_line(first_line)
        else:
            for line in lines:
                if ':' not in line and len(line.split()) >= 2:
                    fn, ln = extract_name_from_line(line)
                    if fn and ln:
                        result["first_name"], result["last_name"] = fn, ln
                        break

    if not result["first_name"] or not result["last_name"]:
        fn, ln = extract_name_from_first_line('\n'.join(lines))
        if fn and ln:
            result["first_name"], result["last_name"] = fn, ln

    field_patterns = {
        "address": r'(?:address|addr)\s*:\s*([^,\n]+)',
        "city": r'city\s*:\s*([^,\n]+)',
        "state": r'state\s*:\s*([^,\n]+)',
        "zip": r'(?:zip|postal)\s*:\s*([^,\n]+)',
        "dob": r'(?:dob|date\s*of\s*birth|birth\s*date)\s*:\s*([^,\n]+)',
        "email": r'email\s*:\s*([^,\n]+)',
        "phone": r'phone\s*:\s*([^,\n]+)',
    }

    for line in lines:
        line = line.strip()
        if line == lines[0] and result["first_name"]:
            continue

        if ':' in line:
            for field, pattern in field_patterns.items():
                if not result.get(field):
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if field == "dob":
                            value, _ = extract_dob(value)
                        elif field == "state":
                            sc, _ = extract_state(value)
                            value = sc or value
                        result[field] = value
                        break
        else:
            if not result["dob"]:
                dob, _ = extract_dob(line)
                if dob:
                    result["dob"] = dob
                    continue
            if not result["address"] and re.search(r'\d+.*[A-Za-z]', line):
                addr_parts = parse_address_line(line)
                if addr_parts:
                    result.update({k: v for k, v in addr_parts.items() if v and not result.get(k)})
                    continue
            if not result["city"] and not result["state"] and not result["zip"]:
                m = re.search(r'^([A-Za-z\s]+?)(?:,\s*|\s+)([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$', line.strip())
                if m and m.group(2).upper() in US_STATES_LIST:
                    result["city"] = ' '.join(w.capitalize() for w in m.group(1).strip().split())
                    result["state"] = m.group(2).upper()
                    result["zip"] = m.group(3)
    return result


def parse_single_line_format(text: str) -> Dict[str, Any]:
    result = _empty_result()
    result["first_name"], result["last_name"] = extract_name_from_first_line(text)

    text_cleaned = clean_text(text)
    if not text_cleaned:
        return result
    text_cleaned = remove_common_labels(text_cleaned)

    result["zip"], text_cleaned = extract_zip(text_cleaned)
    result["dob"], text_cleaned = extract_dob(text_cleaned)
    result["address"], text_cleaned = extract_address(text_cleaned)
    result["state"], text_cleaned = extract_state(text_cleaned)
    result["ssn"], text_cleaned = extract_ssn(text_cleaned)
    result["email"], text_cleaned = extract_email(text_cleaned)
    result["phone"], text_cleaned = extract_phone(text_cleaned)
    result["dl"], text_cleaned = extract_dl(text_cleaned)

    if result["first_name"]:
        text_cleaned = re.sub(rf'\b{re.escape(result["first_name"])}\b', '', text_cleaned, flags=re.IGNORECASE)
    if result["last_name"]:
        text_cleaned = re.sub(rf'\b{re.escape(result["last_name"])}\b', '', text_cleaned, flags=re.IGNORECASE)
    text_cleaned = re.sub(r'\s+', ' ', text_cleaned).strip()

    result["city"], text_cleaned = extract_city(text_cleaned)

    if not result["first_name"] or not result["last_name"]:
        fn, ln, _ = extract_name(text_cleaned)
        result["first_name"] = result["first_name"] or fn
        result["last_name"] = result["last_name"] or ln
    return result


def parse_address_line(line: str) -> Dict[str, Any]:
    result = {}
    try:
        parsed = usaddress.tag(line)
        if parsed[1] == 'Street Address':
            d = parsed[0]
            parts = [d[k] for k in ['AddressNumber', 'StreetNamePreDirectional', 'StreetName',
                                     'StreetNamePostType', 'StreetNamePostDirectional',
                                     'OccupancyType', 'OccupancyIdentifier'] if k in d]
            if parts:
                result["address"] = ' '.join(parts)
            if 'PlaceName' in d:
                result["city"] = d['PlaceName']
            if 'StateName' in d:
                sc, _ = extract_state(d['StateName'])
                result["state"] = sc or d['StateName']
            if 'ZipCode' in d:
                result["zip"] = d['ZipCode']
    except Exception:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 2:
            result["address"] = parts[0]
            last_part = parts[-1].strip()
            m = re.search(r'\b([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\b', last_part)
            if m:
                result["state"] = m.group(1)
                result["zip"] = m.group(2)
                city_part = last_part[:m.start()].strip()
                if city_part:
                    result["city"] = city_part
            else:
                sc, remaining = extract_state(last_part)
                if sc:
                    result["state"] = sc
                    zm = re.search(r'\b(\d{5}(?:-\d{4})?)\b', remaining)
                    if zm:
                        result["zip"] = zm.group(1)
            if len(parts) == 3 and not result.get("city"):
                result["city"] = parts[1]
    return result


def enhance_parsing_results(result: Dict[str, Any], original_text: str) -> Dict[str, Any]:
    for field, extractor in [("dob", extract_dob), ("email", extract_email),
                             ("phone", extract_phone), ("ssn", extract_ssn)]:
        if not result.get(field):
            val, _ = extractor(original_text)
            if val:
                result[field] = val
    return result


class DocumentOrderData(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., alias='zip')
    dob: Optional[str] = Field(None, description="Date of birth MM/DD/YYYY")

    _v_state = validator('state', allow_reuse=True, pre=True)(_validate_state)
    _v_zip = validator('zip_code', allow_reuse=True, pre=True)(_validate_zip)

    @validator('dob')
    def validate_dob(cls, v):
        if v and not re.match(DOB_REGEX, v):
            raise ValueError('❌ Invalid DOB format\n\nUse: MM/DD/YYYY')
        return v

    class Config:
        populate_by_name = True
