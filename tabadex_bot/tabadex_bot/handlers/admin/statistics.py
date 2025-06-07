# tabadex_bot/handlers/admin/statistics.py

import asyncio
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CallbackQueryHandler
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.constants import ParseMode

from ...locales import get_text
from ...database import crud
from ...database.models import OrderStatus
from ...keyboards import get_back_to_admin_panel_keyboard
from ...utils.decorators import admin_required

@admin_required
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays bot statistics for the admin."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    
    await update.message.reply_text("⏳ " + get_text("loading_stats", lang), reply_markup=ReplyKeyboardRemove())
    
    since_24h = datetime.utcnow() - timedelta(hours=24)
    
    total_users, new_users_24h, completed_orders, orders_24h = await asyncio.gather(
        crud.get_total_user_count(session),
        crud.get_new_users_count_since(session, since_24h),
        crud.get_orders_count_by_status(session, OrderStatus.COMPLETED),
        crud.get_orders_count_since(session, since_24h)
    )
    
    text = get_text("admin_stats_title", lang) + "\n\n"
    text += f"👤 {get_text('stats_total_users', lang)}: <b>{total_users}</b>\n"
    text += f"📈 {get_text('stats_new_users_24h', lang)}: <b>{new_users_24h}</b>\n\n"
    text += f"✅ {get_text('stats_completed_orders', lang)}: <b>{completed_orders}</b>\n"
    text += f"📊 {get_text('stats_orders_24h', lang)}: <b>{orders_24h}</b>\n"
    
    keyboard = get_back_to_admin_panel_keyboard(lang)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

# No separate handler list needed for this file as it's handled by menu_handler