"""
Функции для форматирования сообщений.
"""

def format_summary_message(data: dict) -> str:
    """Форматирует сводное сообщение с данными для подтверждения."""
    summary = (
        f"<b>📊 Пожалуйста, проверьте введенные данные:</b>\n\n"
        f"- <b>Имя:</b> {data.get('first_name', '—')}\n"
        f"- <b>Фамилия:</b> {data.get('last_name', '—')}\n"
        f"- <b>Адрес:</b> {data.get('street', '—')}, {data.get('city', '—')}, {data.get('state', '—')} {data.get('zip_code', '—')}\n"
        f"- <b>Дата рождения:</b> {data.get('dob', '—')}\n"
        f"- <b>Годовой доход:</b> ${data.get('annual_income', '0')}\n\n"
        f"Всё верно?"
    )
    return summary
