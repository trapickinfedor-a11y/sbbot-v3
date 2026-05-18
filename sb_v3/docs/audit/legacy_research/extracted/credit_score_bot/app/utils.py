"""
Вспомогательные утилиты.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

EXPECTED_LINES = 7  # first, last, address, city, state, zip, dob

def parse_bulk_text(text: str) -> List[Dict[str, str]]:
    """
    Парсит большой текстовый блок с профилями.

    Формат одного профиля (7 строк):
    first_name
    last_name
    address
    city
    state
    zip_code
    dob

    Профили разделяются пустыми строками.
    Возвращает список словарей, где каждый словарь - один профиль.
    """
    profiles = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    total_lines = len(lines)
    logger.info(f"Parsing bulk text with {total_lines} non-empty lines.")

    for i in range(0, total_lines, EXPECTED_LINES):
        chunk = lines[i:i + EXPECTED_LINES]
        if len(chunk) == EXPECTED_LINES:
            profile = {
                "first_name": chunk[0],
                "last_name": chunk[1],
                "street": chunk[2],
                "city": chunk[3],
                "state": chunk[4],
                "zip_code": chunk[5],
                "dob": chunk[6],
                # Добавляем дефолтное значение, т.к. его нет в тексте
                "annual_income": "35000" 
            }
            profiles.append(profile)
        else:
            logger.warning(f"Skipping incomplete chunk at line {i+1}. Found {len(chunk)} lines, expected {EXPECTED_LINES}.")

    logger.info(f"Successfully parsed {len(profiles)} profiles.")
    return profiles
