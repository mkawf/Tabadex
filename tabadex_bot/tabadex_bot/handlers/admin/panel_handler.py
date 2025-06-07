# tabadex_bot/handlers/admin/panel_handler.py

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CallbackQueryHandler

from ...locales import get_text
from ...keyboards import get_admin_panel_keyboard
from ...utils.decorators import admin_required

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
    # After showing the inline message, also show the main admin keyboard
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=".",
        reply_markup=get_admin_panel_keyboard(lang)
    )


admin_panel_callback_handler = CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$")