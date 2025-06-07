# tabadex_bot/handlers/admin/settings_handler.py

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...locales import get_text
from ...database import crud
from ...keyboards import get_admin_settings_keyboard, get_cancel_keyboard
from ...utils.decorators import admin_required
from .panel_handler import admin_panel

# Conversation states for setting markup
GET_MARKUP = range(60, 61)

@admin_required
async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main settings menu."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    
    current_markup = await crud.get_setting(session, "markup_percentage", "0.5") # Default to 0.5%
    
    text = get_text("admin_settings_title", lang)
    keyboard = get_admin_settings_keyboard(lang, current_markup)
    await query.edit_message_text(text, reply_markup=keyboard)


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
        
        # Go back to the settings menu
        await settings_menu(update, context)
        return ConversationHandler.END
        
    except (ValueError, TypeError):
        await update.message.reply_text(get_text("error_invalid_markup", lang))
        return GET_MARKUP # Ask again

async def cancel_set_markup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the markup setting process."""
    await settings_menu(update, context)
    return ConversationHandler.END

# --- Handler Definitions ---
settings_menu_handler = CallbackQueryHandler(settings_menu, pattern="^admin_settings_main$")

set_markup_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(set_markup_start, pattern="^admin_set_markup_start$")],
    states={GET_MARKUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_markup)]},
    fallbacks=[CallbackQueryHandler(cancel_set_markup, pattern="^cancel_set_markup$")],
    map_to_parent={"cancel_set_markup": "admin_settings_main"} # Go back to menu on cancel
)