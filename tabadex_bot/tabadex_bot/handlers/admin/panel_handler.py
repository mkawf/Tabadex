# tabadex_bot/handlers/admin/panel_handler.py

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from ...locales import get_text
from ...keyboards import get_admin_panel_keyboard
from ...utils.decorators import admin_required

@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main admin panel."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    text = get_text("admin_panel_title", lang)
    keyboard = get_admin_panel_keyboard(lang)
    
    await query.edit_message_text(text, reply_markup=keyboard)

admin_panel_handler = CallbackQueryHandler(admin_panel, pattern="^admin_panel$")