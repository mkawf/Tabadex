# tabadex_bot/handlers/admin/settings_handler.py

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...locales import get_text
from ...database import crud
from ...keyboards import get_admin_settings_keyboard, get_cancel_keyboard, get_admin_panel_keyboard
from ...utils.decorators import admin_required

GET_MARKUP = range(60, 61)

@admin_required
async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main settings menu."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    
    current_markup = await crud.get_setting(session, "markup_percentage", "0.5")
    
    text = get_text("admin_settings_title", lang)
    keyboard = get_admin_settings_keyboard(lang, current_markup)
    await update.message.reply_text(text, reply_markup=keyboard)

@admin_required
async def set_markup_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to set a new markup."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")

    text = get_text("enter_new_markup", lang)
    keyboard = get_cancel_keyboard(lang, "cancel_set_markup")
    await query.edit_message_text(text, reply_markup=keyboard)
    return GET_MARKUP

async def get_new_markup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives, validates, and saves the new markup value."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    new_markup_str = update.message.text.strip()
    
    try:
        new_markup = float(new_markup_str)
        if not (0 <= new_markup < 100):
            raise ValueError("Markup must be between 0 and 100")
            
        await crud.set_setting(session, "markup_percentage", str(new_markup))
        
        await update.message.reply_text(
            get_text("markup_updated_success", lang).format(markup=new_markup)
        )
        
    except (ValueError, TypeError):
        await update.message.reply_text(get_text("error_invalid_markup", lang))

    finally:
        await show_settings_menu(update, context)
        return ConversationHandler.END

async def cancel_set_markup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the markup setting process."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Cancelled.")
    await show_settings_menu(update, context)
    return ConversationHandler.END

# Handlers
set_markup_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(set_markup_start, pattern="^admin_set_markup_start$")],
    states={GET_MARKUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_markup)]},
    fallbacks=[CallbackQueryHandler(cancel_set_markup, pattern="^cancel_set_markup$")]
)

admin_settings_handlers = [
    MessageHandler(filters.Regex(f"^({get_text('admin_settings', 'fa')}|{get_text('admin_settings', 'en')})$"), show_settings_menu)
]