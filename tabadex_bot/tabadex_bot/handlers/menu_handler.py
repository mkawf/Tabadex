# tabadex_bot/handlers/menu_handler.py

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from ..config import settings
from ..locales import get_text
from .start_handler import show_main_menu
from .account_handler import show_account_menu, handle_orders_list, handle_saved_addresses, handle_change_language
from .support_handler import show_support_menu, create_ticket_start, view_my_tickets
from .admin.panel_handler import admin_panel  # <<<--- مسیر و نام صحیح وارد شده است
from .admin.user_management import show_user_management_menu
from .admin.ticket_management import show_admin_tickets_list
from .admin.statistics import show_statistics
from .admin.broadcast import broadcast_start
from .admin.settings_handler import show_settings_menu
from .exchange_handler import start_exchange_conv

async def main_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    مسیریاب مرکزی برای تمام دکمه‌های کیبورد پایین صفحه (ReplyKeyboard).
    """
    lang = context.user_data.get("lang", "fa")
    text = update.message.text
    user_id = update.effective_user.id
    is_admin = user_id in settings.ADMIN_ID_SET

    # --- User Menu ---
    if text == get_text("exchange_button", lang):
        await start_exchange_conv(update, context)
    elif text == get_text("buy_tether_button", lang):
        await update.message.reply_text(get_text("buy_tether_wip", lang))
    elif text == get_text("account_button", lang):
        await show_account_menu(update, context)
    elif text == get_text("support_button", lang):
        await show_support_menu(update, context)
    elif text == get_text("admin_panel_button", lang) and is_admin:
        await admin_panel(update, context) # <<<--- تابع صحیح فراخوانی شده است
    
    # --- Account Menu Buttons ---
    elif text == get_text("my_orders_button", lang):
        await handle_orders_list(update, context)
    elif text == get_text("saved_addresses_button", lang):
        await handle_saved_addresses(update, context)
    elif text == get_text("change_language_button", lang):
        await handle_change_language(update, context)

    # --- Support Menu Buttons ---
    elif text == get_text("create_new_ticket_button", lang):
        # این دکمه باید یک ConversationHandler را شروع کند
        # این منطق در فایل main.py مدیریت می‌شود و اینجا نیازی به کد نیست
        pass # The ConversationHandler will catch this
    elif text == get_text("view_my_tickets_button", lang):
        await view_my_tickets(update, context)
        
    # --- Admin Panel Buttons ---
    elif is_admin:
        if text == get_text("admin_user_management", lang):
            await show_user_management_menu(update, context)
        elif text == get_text("admin_ticket_management", lang):
            await show_admin_tickets_list(update, context)
        elif text == get_text("admin_statistics", lang):
            await show_statistics(update, context)
        elif text == get_text("admin_broadcast", lang):
            # این دکمه نیز یک ConversationHandler را شروع می‌کند
            pass # The ConversationHandler will catch this
        elif text == get_text("admin_settings", lang):
            await show_settings_menu(update, context)
            
    # --- Back Button (Universal) ---
    if text == get_text("back_button", lang):
        await show_main_menu(update, context)

def create_text_filter() -> filters.BaseFilter:
    """Creates a filter for all possible button texts in all languages."""
    keys = [
        "exchange_button", "buy_tether_button", "account_button", "support_button",
        "admin_panel_button", "back_button", "my_orders_button", "saved_addresses_button",
        "change_language_button", "create_new_ticket_button", "view_my_tickets_button",
        "admin_user_management", "admin_ticket_management", "admin_statistics",
        "admin_broadcast", "admin_settings"
    ]
    texts = list(set([get_text(key, lang) for key in keys for lang in ["fa", "en"]]))
    return filters.Text(texts)

menu_handler = MessageHandler(create_text_filter(), main_router)