# tabadex_bot/handlers/admin/panel_handler.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from ...config import settings
from ...locales import get_text
from ...keyboards import get_admin_panel_keyboard
from ...utils.decorators import admin_required

@admin_required
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main admin panel with a ReplyKeyboard."""
    lang = context.user_data.get("lang", "fa")
    
    # This function can be called by a MessageHandler or a CallbackQuery
    # We need to determine how to reply.
    
    text = get_text("admin_panel_title", lang)
    keyboard = get_admin_panel_keyboard(lang)
    
    if update.callback_query:
        await update.callback_query.answer()
        # If we came from an inline keyboard, we might want to edit the message
        # and then send the new ReplyKeyboard.
        await update.callback_query.edit_message_text(text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=".",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard
        )

# --- <<< بخش اصلاح شده و حیاتی >>> ---
# این هندلر برای دکمه‌های شیشه‌ای "بازگشت به پنل ادمین" استفاده می‌شود
admin_panel_callback_handler = CallbackQueryHandler(show_admin_panel, pattern="^admin_panel$")

# این هندلر برای دکمه ثابت "پنل ادمین" در منوی اصلی استفاده می‌شود
admin_panel_entry_handler = MessageHandler(
    filters.Regex(f"^({get_text('admin_panel_button', 'fa')}|{get_text('admin_panel_button', 'en')})$"),
    show_admin_panel
)