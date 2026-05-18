#!/usr/bin/env python3
"""
Seller System Health Check Script
Проверяет готовность всех компонентов к запуску
"""
import sys
import os
from pathlib import Path

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status='info'):
    """Печать статуса с цветом"""
    if status == 'ok':
        print(f"{GREEN}✅ {message}{RESET}")
    elif status == 'error':
        print(f"{RED}❌ {message}{RESET}")
    elif status == 'warning':
        print(f"{YELLOW}⚠️  {message}{RESET}")
    else:
        print(f"{BLUE}ℹ️  {message}{RESET}")

def check_env_file():
    """Проверка .env файла"""
    print("\n" + "="*60)
    print("1. Проверка .env файла")
    print("="*60)
    
    env_path = Path('.env')
    if not env_path.exists():
        print_status(".env файл не найден", 'error')
        return False
    
    print_status(".env файл существует", 'ok')
    
    # Проверка обязательных переменных
    required_vars = [
        'SELLER_BOT_TOKEN',
        'DATABASE_URL',
        'SELLER_MINI_APP_URL'
    ]
    
    with open(env_path) as f:
        content = f.read()
    
    missing = []
    for var in required_vars:
        if var not in content:
            missing.append(var)
            print_status(f"{var} отсутствует", 'error')
        else:
            # Проверка, что не пустое значение
            for line in content.split('\n'):
                if line.startswith(var):
                    value = line.split('=', 1)[1].strip() if '=' in line else ''
                    if value and not value.startswith('change_me') and not value.startswith('replace'):
                        print_status(f"{var} настроен", 'ok')
                    else:
                        print_status(f"{var} требует настройки", 'warning')
                    break
    
    return len(missing) == 0

def check_seller_bot_structure():
    """Проверка структуры Seller Bot"""
    print("\n" + "="*60)
    print("2. Проверка структуры Seller Bot")
    print("="*60)
    
    required_files = [
        'seller_bot/bot.py',
        'seller_bot/config.py',
        'seller_bot/run.py',
        'seller_bot/handlers/start.py',
        'seller_bot/handlers/orders.py',
        'seller_bot/handlers/chat.py',
        'seller_bot/services/weekly_report_service.py',
        'seller_bot/services/auto_payout_service.py',
        'seller_bot/middlewares/seller_auth.py',
        'seller_bot/keyboards/inline.py',
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print_status(f"{file_path}", 'ok')
        else:
            print_status(f"{file_path} отсутствует", 'error')
            all_exist = False
    
    return all_exist

def check_web_panel_structure():
    """Проверка структуры Web Panel"""
    print("\n" + "="*60)
    print("3. Проверка структуры Web Panel")
    print("="*60)
    
    required_files = [
        'web_panel/main.py',
        'web_panel/api/seller_mini_app.py',
        'web_panel/templates/seller_mini_app.html',
        'web_panel/static/seller_mini_app.css',
        'web_panel/static/seller_mini_app.js',
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            print_status(f"{file_path} ({size} bytes)", 'ok')
        else:
            print_status(f"{file_path} отсутствует", 'error')
            all_exist = False
    
    return all_exist

def check_shared_services():
    """Проверка shared services"""
    print("\n" + "="*60)
    print("4. Проверка Shared Services")
    print("="*60)
    
    required_files = [
        'shared/database/models.py',
        'shared/services/seller_actor_service.py',
        'shared/services/seller_deposit_service.py',
        'shared/services/seller_dispute_service.py',
        'shared/services/seller_finance_service.py',
        'shared/services/seller_order_delivery_service.py',
        'shared/utils/chat_filter.py',
        'shared/utils/telegram_auth.py',
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print_status(f"{file_path}", 'ok')
        else:
            print_status(f"{file_path} отсутствует", 'error')
            all_exist = False
    
    return all_exist

def check_imports():
    """Проверка импортов Python"""
    print("\n" + "="*60)
    print("5. Проверка импортов Python")
    print("="*60)
    
    # Добавляем текущую директорию в путь
    sys.path.insert(0, str(Path.cwd()))
    
    imports_to_check = [
        ('aiogram', 'Aiogram 3.x'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('fastapi', 'FastAPI'),
        ('pydantic', 'Pydantic'),
    ]
    
    all_ok = True
    for module, name in imports_to_check:
        try:
            __import__(module)
            print_status(f"{name} установлен", 'ok')
        except ImportError:
            print_status(f"{name} не установлен", 'error')
            all_ok = False
    
    return all_ok

def check_documentation():
    """Проверка документации"""
    print("\n" + "="*60)
    print("6. Проверка документации")
    print("="*60)
    
    docs = [
        'SELLER_ARCHITECTURE.md',
        'SELLER_IMPLEMENTATION_PLAN.md',
        'QUICK_START_SELLER.md',
        'SELLER_STATUS_REPORT.md',
    ]
    
    for doc in docs:
        if Path(doc).exists():
            print_status(f"{doc}", 'ok')
        else:
            print_status(f"{doc} отсутствует", 'warning')
    
    return True

def count_code_lines():
    """Подсчёт строк кода"""
    print("\n" + "="*60)
    print("7. Статистика кода")
    print("="*60)
    
    components = {
        'Seller Bot': 'seller_bot/**/*.py',
        'Web Panel API': 'web_panel/api/seller_mini_app.py',
        'Mini App HTML': 'web_panel/templates/seller_mini_app.html',
        'Mini App CSS': 'web_panel/static/seller_mini_app.css',
        'Mini App JS': 'web_panel/static/seller_mini_app.js',
    }
    
    total = 0
    for name, pattern in components.items():
        count = 0
        if '**' in pattern:
            # Рекурсивный поиск
            base = pattern.split('/**')[0]
            for py_file in Path(base).rglob('*.py'):
                with open(py_file) as f:
                    count += len(f.readlines())
        else:
            # Один файл
            if Path(pattern).exists():
                with open(pattern) as f:
                    count += len(f.readlines())
        
        if count > 0:
            print_status(f"{name}: {count} строк", 'ok')
            total += count
    
    print_status(f"ИТОГО: {total} строк кода", 'ok')
    return True

def print_summary(results):
    """Печать итогового отчёта"""
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЁТ")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for check, result in results.items():
        status = 'ok' if result else 'error'
        print_status(check, status)
    
    print("\n" + "-"*60)
    if passed == total:
        print_status(f"Все проверки пройдены ({passed}/{total})", 'ok')
        print_status("Система готова к запуску! 🚀", 'ok')
        print("\nСледующий шаг:")
        print("  docker-compose up -d postgres redis web_panel seller_bot")
    else:
        print_status(f"Пройдено проверок: {passed}/{total}", 'warning')
        print_status("Требуется доработка", 'warning')

def main():
    """Главная функция"""
    print(f"\n{BLUE}{'='*60}")
    print("🔍 Seller System Health Check")
    print(f"{'='*60}{RESET}\n")
    
    results = {
        '.env файл': check_env_file(),
        'Seller Bot структура': check_seller_bot_structure(),
        'Web Panel структура': check_web_panel_structure(),
        'Shared Services': check_shared_services(),
        'Python импорты': check_imports(),
        'Документация': check_documentation(),
        'Статистика кода': count_code_lines(),
    }
    
    print_summary(results)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Прервано пользователем{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Ошибка: {e}{RESET}")
        sys.exit(1)
