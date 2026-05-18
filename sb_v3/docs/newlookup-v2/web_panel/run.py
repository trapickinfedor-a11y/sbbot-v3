"""
Запуск веб-панели админа
"""

import sys
import os

# Добавляем корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    import uvicorn
    from web_panel.config import web_panel_config
    is_reload = os.getenv("WEB_PANEL_RELOAD", "").lower() in {"1", "true", "yes"}
    
    print("=" * 50)
    print("Starting Admin Web Panel")
    print("=" * 50)
    print(f"URL: http://{web_panel_config.host}:{web_panel_config.port}")
    print(f"Username: {web_panel_config.admin_username}")
    print("=" * 50)
    print()
    
    uvicorn.run(
        "web_panel.main:app",
        host=web_panel_config.host,
        port=web_panel_config.port,
        reload=is_reload
    )

