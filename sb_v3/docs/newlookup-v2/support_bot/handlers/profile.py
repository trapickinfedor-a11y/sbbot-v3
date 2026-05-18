"""
Хэндлеры профиля саппорта
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from support_bot.services.worker_service import WorkerService
from support_bot.keyboards.inline import profile_keyboard, main_menu_keyboard
from support_bot.config import support_bot_config

router = Router(name="profile")


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, session: AsyncSession):
    """Показать профиль саппорта"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    # Получаем статистику за сегодня
    stats_today = await WorkerService.get_worker_stats_today(session, worker.id)
    
    today_done = sum(s.orders_done for s in stats_today)
    today_nf = sum(s.orders_nf for s in stats_today)
    
    # Форматируем категории
    categories_list = []
    for cat in worker.categories:
        cat_name = support_bot_config.CATEGORIES.get(cat, cat)
        categories_list.append(f"   • {cat_name}")
    
    categories_text = "\n".join(categories_list)
    
    text = f"""👤 <b>Your Profile</b>

🆔 <b>Support ID:</b> <code>{worker.id}</code>
👤 <b>Username:</b> @{worker.username or 'N/A'}
📊 <b>Status:</b> {'✅ Active' if worker.is_active else '❌ Inactive'}

━━━━━━━━━━━━━━━━━━
<b>📊 Statistics:</b>
   🎯 Total Orders: {worker.orders_completed}
   ✅ Today Done: {today_done}
   ❌ Today NF: {today_nf}

━━━━━━━━━━━━━━━━━━
<b>📋 Your Categories:</b>
{categories_text}

━━━━━━━━━━━━━━━━━━
<b>📅 Member Since:</b> {worker.created_at.strftime('%Y-%m-%d')}
"""
    
    await callback.message.edit_text(text, reply_markup=profile_keyboard(worker))
    await callback.answer()


@router.callback_query(F.data == "my_categories")
async def show_my_categories(callback: CallbackQuery, session: AsyncSession):
    """Показать категории саппорта"""
    
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    
    if not worker:
        await callback.answer("Access denied", show_alert=True)
        return
    
    categories_list = []
    for cat in worker.categories:
        cat_name = support_bot_config.CATEGORIES.get(cat, cat)
        categories_list.append(f"   • <b>{cat_name}</b> (<code>{cat}</code>)")
    
    categories_text = "\n".join(categories_list)
    
    text = f"""📋 <b>Your Categories</b>

You can process orders from these categories:

{categories_text}

━━━━━━━━━━━━━━━━━━
<b>Total categories:</b> {len(worker.categories)}

To add/remove categories, contact administrator.
"""
    
    await callback.message.edit_text(text, reply_markup=profile_keyboard(worker))
    await callback.answer()

