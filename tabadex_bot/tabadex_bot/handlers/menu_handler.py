# tabadex_bot/handlers/menu_handler.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from ..config import settings
from ..locales import get_text
from .start_handler import show_main_menu
from .account_handler import show_account_menu
from .support_handler import show_support_menu
from .admin.panel_handler import admin_panel  # <<<--- مسیر صحیح وارد کردن
from .exchange_handler import start_exchange_conv

async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes main menu keyboard presses."""
    lang = context.user_data.get("lang", "fa")
    text = update.message.text

    # --- User Menu ---
    if text == get_text("exchange_button", lang):
        await start_exchange_conv(update, context)
    elif text == get_text("buy_tether_button", lang):
        await update.message.reply_text(get_text("buy_tether_wip", lang))
    elif text == get_text("account_button", lang):
        await show_account_menu(update, context)
    elif text == get_text("support_button", lang):
        await show_support_menu(update, context)

    # --- Admin Menu ---
    elif text == get_text("admin_panel_button", lang):
        if update.effective_user.id in settings.ADMIN_ID_SET:
            await admin_panel(update, context) # <<<--- فراخوانی تابع صحیح
    
    # --- Back Button from submenus ---
    elif text == get_text("back_button", lang):
        await show_main_menu(update, context)

# Filter for all menu buttons to avoid conflicts with other text inputs
def create_main_menu_filter() -> filters.BaseFilter:
    all_menu_buttons = list(set([
        get_text(key, lang)
        for key in [
            "exchange_button", "buy_tether_button", "account_button",
            "support_button", "admin_panel_button", "back_button"
        ]
        for lang in ["fa", "en"]
    ]))
    return filters.Text(all_menu_buttons)

menu_handler = MessageHandler(create_main_menu_filter(), main_menu_router)