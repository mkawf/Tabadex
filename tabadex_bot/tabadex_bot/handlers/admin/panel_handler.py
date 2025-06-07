# tabadex_bot/handlers/admin/panel_handler.py

from telegram import Update
from telegram.ext import ContextTypes
from ...locales import get_text
from ...keyboards import get_admin_panel_keyboard
from ...utils.decorators import admin_required

@admin_required
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main admin panel with a ReplyKeyboard."""
    lang = context.user_data.get("lang", "fa")
    
    # این تابع از menu_handler فراخوانی می‌شود، بنابراین نوع آپدیت message است
    await update.message.reply_text(
        text=get_text("admin_panel_title", lang),
        reply_markup=get_admin_panel_keyboard(lang)
    )