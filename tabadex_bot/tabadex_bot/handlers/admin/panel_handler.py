# tabadex_bot/handlers/admin/panel_handler.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from ....config import settings
from ....locales import get_text
from ...keyboards import get_admin_panel_keyboard
from .user_management import show_user_management_menu
from .ticket_management import show_admin_tickets_list
from .statistics import show_statistics
from .broadcast import broadcast_start
from .settings_handler import show_settings_menu
from ..start_handler import show_main_menu

@admin_required
async def admin_panel_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes admin panel keyboard presses."""
    lang = context.user_data.get("lang", "fa")
    text = update.message.text
    is_admin = update.effective_user.id in settings.ADMIN_ID_SET

    if not is_admin:
        return

    if text == get_text("admin_user_management", lang):
        await show_user_management_menu(update, context)
    elif text == get_text("admin_ticket_management", lang):
        await show_admin_tickets_list(update, context)
    elif text == get_text("admin_statistics", lang):
        await show_statistics(update, context)
    elif text == get_text("admin_broadcast", lang):
        await broadcast_start(update, context)
    elif text == get_text("admin_settings", lang):
        await show_settings_menu(update, context)
    elif text == get_text("back_button", lang):
        await show_main_menu(update, context)

def create_admin_filter() -> filters.BaseFilter:
    keys = [
        "admin_user_management", "admin_ticket_management", "admin_statistics",
        "admin_broadcast", "admin_settings"
    ]
    texts = list(set([get_text(key, lang) for key in keys for lang in ["fa", "en"]]))
    return filters.Text(texts)

admin_panel_handler = MessageHandler(create_admin_filter(), admin_panel_router)

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main admin panel with a ReplyKeyboard."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("admin_panel_title", lang),
        reply_markup=get_admin_panel_keyboard(lang)
    )