from typing import Dict, List
import re
from mirror_bot.services.validator import parse_freeform_text


class DataParser:
    
    @staticmethod
    def smart_parse_address_data(text: str, require_dob: bool = False) -> Dict:
        """
        Универсальный парсер данных в любом формате.
        Использует продвинутый парсер parse_freeform_text из validator.py
        """
        text = text.strip()
        
        # Используем продвинутый парсер из validator.py
        parsed = parse_freeform_text(text, required_fields=None)
        
        # DOB уже в правильном формате MM/DD/YYYY из parse_freeform_text
        dob_formatted = parsed.get('dob')
        
        # Формируем результат в нужном формате
        result = {
            "first": parsed.get('first_name'),
            "last": parsed.get('last_name'),
            "address": parsed.get('address'),
            "city": parsed.get('city'),
            "state": parsed.get('state'),
            "zip": parsed.get('zip'),
            "dob": dob_formatted,
            "ssn": parsed.get('ssn'),
            "dl": parsed.get('dl'),  # Добавляем DL
            "issues": parsed.get('errors', [])
        }
        
        # Дополнительная проверка для require_dob
        if require_dob and not result['dob']:
            if "Missing dob" not in result['issues']:
                result['issues'].append("Missing DOB (Date of Birth)")
        
        return result
    
    @staticmethod
    def parse_key_value_format(text: str) -> Dict[str, str]:
        lines = text.strip().split('\n')
        data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key_normalized = key.strip().lower().replace(' ', '_')
                data[key_normalized] = value.strip()
        
        return data
    
    @staticmethod
    def parse_bulk_entries(text: str, separator: str = None) -> List[str]:
        """
        Parse bulk entries with auto-detection of separator.
        Supports: 
        - * (asterisk on separate line)
        - \n\n (double newline / empty line)
        - Smart detection for single newlines (if double newline fails)
        """
        text = text.strip()
        
        # Auto-detect separator
        if separator is None:
            # 1. Check if asterisk is used as separator
            if '\n*\n' in text or text.startswith('*\n') or text.endswith('\n*'):
                separator = '*'
            # 2. Check for double newline (empty lines)
            elif '\n\n' in text:
                separator = '\n\n'
            # 3. Fallback: try to detect entries by pattern (NAME on first line)
            else:
                separator = 'smart'
        
        # Split by separator
        if separator == '*':
            # Split by asterisk and clean up
            entries = [e.strip() for e in text.split('*') if e.strip()]
        elif separator == '\n\n':
            entries = [e.strip() for e in text.split('\n\n') if e.strip()]
        elif separator == 'smart':
            # Smart parsing: group lines into entries
            # Heuristic: if 3+ consecutive lines with address pattern, group them
            entries = DataParser._smart_split_entries(text)
        else:
            entries = [e.strip() for e in text.split(separator) if e.strip()]
        
        return entries
    
    @staticmethod
    def _smart_split_entries(text: str) -> List[str]:
        """
        Smart split when no clear separator is found.
        Groups lines into entries based on patterns.
        """
        import re
        lines = text.split('\n')
        entries = []
        current_entry = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                # Empty line - finish current entry
                if current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = []
                continue
            
            # Check if this looks like a NAME line (start of new entry)
            # Name typically: 2-4 words, all caps or title case, no numbers at start
            # ИСКЛЮЧАЕМ строки с DOB, датами, SSN и другими данными
            is_name_line = (
                not re.match(r'^\d', line) and  # Doesn't start with digit
                len(line.split()) >= 2 and      # At least 2 words
                len(line.split()) <= 5 and      # Not more than 5 words
                not any(word.lower() in line.lower() for word in ['street', 'avenue', 'road', 'st', 'ave', 'rd', 'blvd', 'drive', 'ln', 'way']) and
                not any(word.lower() in line.lower() for word in ['dob', 'ssn', 'phone', 'email', 'credit', 'score', 'address', 'city', 'state', 'zip', 'country']) and  # Исключаем строки с данными
                not re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line) and  # Исключаем даты
                not re.search(r'\d{3}[-\s]?\d{2}[-\s]?\d{4}', line) and     # Исключаем SSN
                not re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{4}', line) and     # Исключаем телефоны
                not re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line) and  # Исключаем email
                ':' not in line  # Исключаем строки с двоеточием (структурированные данные)
            )
            
            # Более строгие условия для начала новой записи:
            # 1. Должно быть минимум 6 строк в текущей записи (полная запись)
            # 2. И следующая строка должна выглядеть как имя
            # 3. И предыдущая запись должна содержать ключевые данные (адрес/город/штат)
            if (is_name_line and 
                len(current_entry) >= 6 and  # Увеличиваем с 4 до 6
                any(keyword in '\n'.join(current_entry).lower() for keyword in ['address', 'city', 'state', 'street', 'ave', 'rd', 'blvd'])):
                entries.append('\n'.join(current_entry))
                current_entry = [line]
            else:
                current_entry.append(line)
        
        # Add last entry
        if current_entry:
            entries.append('\n'.join(current_entry))
        
        return entries
    
    @staticmethod
    def format_example(fields: Dict[str, str]) -> str:
        return '\n'.join([f"{key.replace('_', ' ').title()}: {value}" for key, value in fields.items()])

