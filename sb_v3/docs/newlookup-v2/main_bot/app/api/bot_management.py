"""
API endpoints для управления зеркальными ботами
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from shared.security.internal_api import verify_internal_api_request

logger = logging.getLogger(__name__)

app = FastAPI(dependencies=[Depends(verify_internal_api_request)])

# Глобальная ссылка на MirrorBotService (будет установлена из main.py)
mirror_bot_service = None

class BotStatusUpdate(BaseModel):
    bot_id: int
    is_active: bool

@app.post("/bot/toggle")
async def toggle_bot_status(data: BotStatusUpdate):
    """Включить/выключить зеркального бота"""
    if not mirror_bot_service:
        raise HTTPException(status_code=500, detail="Mirror bot service not initialized")
    
    logger.info("toggle_bot_status called: bot_id=%s, is_active=%s", data.bot_id, data.is_active)
    try:
        if data.is_active:
            success = await mirror_bot_service.start_bot_by_id(data.bot_id)
            if success:
                logger.info("Bot %s started successfully", data.bot_id)
                return {"message": f"Bot {data.bot_id} started successfully", "status": "active"}
            else:
                logger.warning("start_bot_by_id returned False for bot %s", data.bot_id)
                raise HTTPException(status_code=400, detail=f"Failed to start bot {data.bot_id}")
        else:
            success = await mirror_bot_service.stop_bot_by_id(data.bot_id)
            if success:
                logger.info("Bot %s stopped successfully", data.bot_id)
                return {"message": f"Bot {data.bot_id} stopped successfully", "status": "inactive"}
            else:
                raise HTTPException(status_code=400, detail=f"Failed to stop bot {data.bot_id}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error toggling bot %s: %s", data.bot_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/bot/status/{bot_id}")
async def get_bot_status(bot_id: int):
    """Получить статус зеркального бота"""
    if not mirror_bot_service:
        raise HTTPException(status_code=500, detail="Mirror bot service not initialized")
    
    try:
        is_running = await mirror_bot_service.is_bot_running(bot_id)
        return {"bot_id": bot_id, "is_running": is_running}
    except Exception as e:
        logger.error(f"Error getting bot status {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

def set_mirror_bot_service(service):
    """Установить ссылку на MirrorBotService"""
    global mirror_bot_service
    mirror_bot_service = service
