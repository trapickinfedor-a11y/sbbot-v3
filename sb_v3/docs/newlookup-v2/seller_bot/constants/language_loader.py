from seller_bot.constants.texts_en import BotTexts as TextsEn
from seller_bot.constants.texts_ru import BotTexts as TextsRu
from seller_bot.constants.texts_zh import BotTexts as TextsZh
from seller_bot.constants.texts_es import BotTexts as TextsEs
from seller_bot.constants.buttons_en import ButtonTexts as ButtonsEn
from seller_bot.constants.buttons_ru import ButtonTexts as ButtonsRu
from seller_bot.constants.buttons_zh import ButtonTexts as ButtonsZh
from seller_bot.constants.buttons_es import ButtonTexts as ButtonsEs


def get_texts(language: str):
    return {
        "en": TextsEn,
        "ru": TextsRu,
        "zh": TextsZh,
        "es": TextsEs,
    }.get(language or "en", TextsEn)


def get_buttons(language: str):
    return {
        "en": ButtonsEn,
        "ru": ButtonsRu,
        "zh": ButtonsZh,
        "es": ButtonsEs,
    }.get(language or "en", ButtonsEn)
