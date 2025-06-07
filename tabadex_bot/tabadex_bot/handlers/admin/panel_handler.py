# tabadex_bot/handlers/admin/panel_handler.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from ...config import settings  # <<<--- مسیر صحیح وارد کردن (دو نقطه)
from ...locales import get_text
from ...keyboards import get_admin_panel_keyboard
from ...utils.decorators import admin_required
from .user_management import show_user_management_menu
from .ticket_management import show_admin_tickets_list
from .statistics import show_statistics
from .broadcast import broadcast_start
from .settings_handler import show_settings_menu
from ..start_handler import show_main_menu

@admin_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main admin panel with a ReplyKeyboard."""
    lang = context.user_data.get("lang", "fa")
    
    await update.message.reply_text(
        text=get_text("admin_panel_title", lang),
        reply_markup=get_admin_panel_keyboard(lang)
    )

@admin_required
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles returning to the admin panel from an inline keyboard."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    await query.edit_message_text(
        text=get_text("admin_panel_title", lang)
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=".",
        reply_markup=get_admin_panel_keyboard(lang)
    )

admin_panel_callback_handler = CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$")