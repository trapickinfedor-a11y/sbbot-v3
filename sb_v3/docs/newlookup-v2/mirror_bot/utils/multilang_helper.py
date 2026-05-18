"""
Multilingual Helper Utilities
Вспомогательные утилиты для многоязычности
"""

from mirror_bot.constants.language_loader import get_texts, get_buttons

def get_multilang_texts_and_buttons(language: str = "en"):
    """
    Быстрая функция для получения текстов и кнопок для языка
    
    Args:
        language: Код языка (en, ru, zh)
        
    Returns:
        tuple: (texts, buttons)
    """
    texts = get_texts(language)
    buttons = get_buttons(language)
    return texts, buttons

def format_error_message(texts, error_type: str, **kwargs):
    """
    Форматирование сообщений об ошибках
    
    Args:
        texts: Объект с текстами
        error_type: Тип ошибки
        **kwargs: Параметры для форматирования
        
    Returns:
        str: Отформатированное сообщение
    """
    error_messages = {
        "invalid_data": texts.INVALID_DATA_FORMAT,
        "validation_error": texts.VALIDATION_ERROR,
        "please_enter_data": texts.PLEASE_ENTER_DATA,
        "minimum_entries": texts.MINIMUM_ENTRIES_REQUIRED,
        "maximum_entries": texts.MAXIMUM_ENTRIES_ALLOWED,
        "insufficient_balance": texts.INSUFFICIENT_BALANCE,
        "invalid_format": texts.INVALID_FORMAT_TRY_AGAIN,
        "error_in_entry": texts.ERROR_IN_ENTRY
    }
    
    message_template = error_messages.get(error_type, texts.INVALID_DATA)
    return message_template.format(**kwargs)

# Константы для быстрого доступа к примерам
EXAMPLE_MAPPING = {
    "lookup_ssn": "SSN_SINGLE_EXAMPLE",
    "lookup_dl": "DL_SINGLE_EXAMPLE", 
    "lookup_credit": "CS_SINGLE_EXAMPLE",
    "lookup_bg": "BG_SINGLE_EXAMPLE",
    "lookup_mvr": "MVR_SINGLE_EXAMPLE",
    "lookup_fullmvr": "MVR_SINGLE_EXAMPLE",
    "credit_report": "CR_SINGLE_EXAMPLE"
}

BULK_EXAMPLE_MAPPING = {
    "lookup_ssn": "SSN_BULK_EXAMPLE",
    "lookup_dl": "DL_BULK_EXAMPLE",
    "lookup_credit": "CS_BULK_EXAMPLE", 
    "lookup_bg": "BG_BULK_EXAMPLE",
    "lookup_mvr": "MVR_BULK_EXAMPLE",
    "lookup_fullmvr": "MVR_BULK_EXAMPLE",
    "credit_report": "CR_BULK_EXAMPLE"
}

def get_example_for_service(texts, service: str, is_bulk: bool = False):
    """
    Получить пример для сервиса
    
    Args:
        texts: Объект с текстами
        service: Название сервиса
        is_bulk: Bulk пример или single
        
    Returns:
        str: Пример для сервиса
    """
    mapping = BULK_EXAMPLE_MAPPING if is_bulk else EXAMPLE_MAPPING
    example_attr = mapping.get(service, "SSN_SINGLE_EXAMPLE")
    return getattr(texts, example_attr, "No example available")
