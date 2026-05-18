"""
Language loader for Mirror Bot
Универсальный загрузчик языков
"""

from typing import Dict, Any
import importlib

class LanguageLoader:
    """Загрузчик языковых файлов"""
    
    _texts_cache: Dict[str, Any] = {}
    _buttons_cache: Dict[str, Any] = {}
    
    SUPPORTED_LANGUAGES = ['en', 'ru', 'zh', 'es']
    DEFAULT_LANGUAGE = 'en'
    
    @classmethod
    def get_texts(cls, language: str = None) -> Any:
        """
        Получить тексты для указанного языка
        
        Args:
            language: Код языка (en, ru, zh)
            
        Returns:
            BotTexts класс для указанного языка
        """
        if not language or language not in cls.SUPPORTED_LANGUAGES:
            language = cls.DEFAULT_LANGUAGE
            
        if language not in cls._texts_cache:
            try:
                module = importlib.import_module(f'mirror_bot.constants.texts_{language}')
                cls._texts_cache[language] = module.BotTexts
            except ImportError:
                # Fallback to default language
                module = importlib.import_module(f'mirror_bot.constants.texts_{cls.DEFAULT_LANGUAGE}')
                cls._texts_cache[language] = module.BotTexts
                
        return cls._texts_cache[language]
    
    @classmethod
    def get_buttons(cls, language: str = None) -> Any:
        """
        Получить кнопки для указанного языка
        
        Args:
            language: Код языка (en, ru, zh)
            
        Returns:
            ButtonTexts класс для указанного языка
        """
        if not language or language not in cls.SUPPORTED_LANGUAGES:
            language = cls.DEFAULT_LANGUAGE
            
        if language not in cls._buttons_cache:
            try:
                module = importlib.import_module(f'mirror_bot.constants.buttons_{language}')
                cls._buttons_cache[language] = module.ButtonTexts
            except ImportError:
                # Fallback to default language
                module = importlib.import_module(f'mirror_bot.constants.buttons_{cls.DEFAULT_LANGUAGE}')
                cls._buttons_cache[language] = module.ButtonTexts
                
        return cls._buttons_cache[language]
    
    @classmethod
    def clear_cache(cls):
        """Очистить кэш языков"""
        cls._texts_cache.clear()
        cls._buttons_cache.clear()


# Удобные функции для быстрого доступа
def get_texts(language: str = None):
    """Получить тексты для языка"""
    return LanguageLoader.get_texts(language)

def get_buttons(language: str = None):
    """Получить кнопки для языка"""
    return LanguageLoader.get_buttons(language)

def get_user_language_from_context(context: dict) -> str:
    """
    Извлечь язык пользователя из контекста
    
    Args:
        context: Контекст с данными пользователя
        
    Returns:
        Код языка пользователя или язык по умолчанию
    """
    return context.get('user_language', LanguageLoader.DEFAULT_LANGUAGE)
