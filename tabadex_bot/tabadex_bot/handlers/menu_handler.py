# tabadex_bot/handlers/menu_handler.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from ..config import settings
from ..locales import get_text
from .start_handler import show_main_menu
from .account_handler import show_account_menu, handle_account_menu_buttons
from .support_handler import show_support_menu, handle_support_menu_buttons
from .admin.panel_handler import show_admin_panel, handle_admin_panel_buttons
from .exchange_handler import start_exchange_conv

async def main_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    text = update.message.text

    # Route to main features
    if text == get_text("exchange_button", lang):
        await start_exchange_conv(update, context)
    elif text == get_text("buy_tether_button", lang):
        await update.message.reply_text(get_text("buy_tether_wip", lang))
    elif text == get_text("account_button", lang):
        await show_account_menu(update, context)
    elif text == get_text("support_button", lang):
        await show_support_menu(update, context)
    elif text == get_text("admin_panel_button", lang) and update.effective_user.id in settings.ADMIN_ID_SET:
        await show_admin_panel(update, context)
    
    # Route to submenu features
    elif await handle_account_menu_buttons(update, context):
        return
    elif await handle_support_menu_buttons(update, context):
        return
    elif await handle_admin_panel_buttons(update, context):
        return

    # Back button from any submenu
    elif text == get_text("back_button", lang):
        await show_main_menu(update, context)

def create_text_filter(keys: list) -> filters.BaseFilter:
    texts = list(set([get_text(key, lang) for key in keys for lang in ["fa", "en"]]))
    return filters.Text(texts)

menu_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, main_router)