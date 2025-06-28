# tabadex_bot/handlers/main_menu_handler.py

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from ..locales import get_text
from ..keyboards import get_account_menu_keyboard, get_back_to_main_menu_keyboard
from .start_handler import show_main_menu

async def main_menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes callbacks from the main menu."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    lang = context.user_data.get('lang', 'fa')

    if action == "main_exchange":
        # TODO: Start the exchange ConversationHandler
        await query.edit_message_text("Exchange flow starts here...", reply_markup=get_back_to_main_menu_keyboard(lang))
    
    elif action == "main_buy_tether":
        await query.edit_message_text(get_text("buy_tether_wip", lang), reply_markup=get_back_to_main_menu_keyboard(lang))

    elif action == "main_account":
        text = get_text("account_menu_title", lang)
        keyboard = get_account_menu_keyboard(lang)
        await query.edit_message_text(text, reply_markup=keyboard)

    elif action == "main_support":
        # TODO: Start the support ConversationHandler
        await query.edit_message_text("Support system starts here...", reply_markup=get_back_to_main_menu_keyboard(lang))

    elif action == "back_to_main_menu":
        await show_main_menu(update, context, lang, is_edit=True)

main_menu_handler = CallbackQueryHandler(main_menu_callback_router, pattern=r'^(main_|back_to_main_menu)')

# You will need handlers for account menu actions as well
async def account_menu_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic for My Orders, Saved Addresses, etc.
    pass

account_menu_handler = CallbackQueryHandler(account_menu_callback_router, pattern=r'^account_')