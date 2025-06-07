# tabadex_bot/keyboards.py
from typing import List, Dict, Any
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from .locales import get_text
from .database.models import TicketStatus

# --- Reply Keyboards (دکمه‌های ثابت) ---
def get_main_menu_keyboard(lang: str, is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(get_text("exchange_button", lang)), KeyboardButton(get_text("buy_tether_button", lang))],[KeyboardButton(get_text("account_button", lang)), KeyboardButton(get_text("support_button", lang))]]
    if is_admin: keyboard.append([KeyboardButton(get_text("admin_panel_button", lang))])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_language_selection_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["🇮🇷 فارسی (Persian)", "🇬🇧 English"]], resize_keyboard=True, one_time_keyboard=True)

def get_account_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(get_text("my_orders_button", lang)), KeyboardButton(get_text("saved_addresses_button", lang))],[KeyboardButton(get_text("change_language_button", lang)), KeyboardButton(get_text("back_button", lang))]], resize_keyboard=True)

def get_support_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(get_text("create_new_ticket_button", lang)), KeyboardButton(get_text("view_my_tickets_button", lang))],[KeyboardButton(get_text("back_button", lang))]], resize_keyboard=True)

def get_admin_panel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(get_text("admin_user_management", lang)), KeyboardButton(get_text("admin_ticket_management", lang))],[KeyboardButton(get_text("admin_statistics", lang)), KeyboardButton(get_text("admin_broadcast", lang))],[KeyboardButton(get_text("admin_settings", lang)), KeyboardButton(get_text("back_button", lang))]], resize_keyboard=True)

# --- Inline Keyboards (دکمه‌های شیشه‌ای) ---
def get_cancel_keyboard(lang: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("cancel_button", lang), callback_data=callback_data)]])

def create_currency_keyboard(top_currencies: list, lang: str, callback_prefix: str, show_extra_buttons: bool = True) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(f"{c['name']} ({c['ticker'].upper()})", callback_data=f"{callback_prefix}_{c['ticker']}") for c in top_currencies]
    keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    if show_extra_buttons:
        keyboard.append([
            InlineKeyboardButton("🔍 " + get_text("search_currency_button", lang), callback_data="exchange_search"),
            InlineKeyboardButton("📜 " + get_text("view_all_currencies_button", lang), callback_data="exchange_view_all")
        ])
    return InlineKeyboardMarkup(keyboard)

def create_network_keyboard(networks: list, lang: str, callback_prefix: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(net.upper(), callback_data=f"{callback_prefix}_{net}") for net in networks]
    return InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])

def get_exchange_preview_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("confirm_rate_button", lang), callback_data="preview_confirm"), InlineKeyboardButton(get_text("cancel_button", lang), callback_data="preview_cancel")]])

def get_orders_keyboard(orders: list, lang: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"#{o.id[:8]}.. | {o.from_amount} {o.from_currency.upper()} ➡️ {o.to_currency.upper()}", callback_data=f"view_order_{o.id}")] for o in orders]
    pagination_row = []
    if page > 1: pagination_row.append(InlineKeyboardButton("«", callback_data=f"orders_page_{page-1}"))
    if page < total_pages: pagination_row.append(InlineKeyboardButton("»", callback_data=f"orders_page_{page+1}"))
    if pagination_row: keyboard.append(pagination_row)
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_account_menu")])
    return InlineKeyboardMarkup(keyboard)
    
def get_addresses_keyboard(addresses: list, lang: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"{addr.name} ({addr.currency_ticker.upper()})", callback_data="noop"), InlineKeyboardButton("🗑️", callback_data=f"delete_address_{addr.id}")] for addr in addresses]
    keyboard.append([InlineKeyboardButton("➕ " + get_text("add_address_button", lang), callback_data="add_address_start")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_account_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_support_topics_keyboard(lang: str) -> InlineKeyboardMarkup:
    topics = {"problem_with_order": get_text("topic_order_problem"), "deposit_issue": get_text("topic_deposit_issue"), "general_question": get_text("topic_general_question"), "other": get_text("topic_other")}
    keyboard = [[InlineKeyboardButton(text, callback_data=f"topic_{key}")] for key, text in topics.items()]
    keyboard.append([InlineKeyboardButton(get_text("cancel_button", lang), callback_data="cancel_ticket_creation")])
    return InlineKeyboardMarkup(keyboard)

def get_user_tickets_keyboard(tickets: list, lang: str) -> InlineKeyboardMarkup:
    status_map = {'OPEN': '🔵', 'ANSWERED': '🟢', 'PENDING_USER_REPLY': '🟡', 'CLOSED': '⚫️'}
    keyboard = [[InlineKeyboardButton(f"{status_map.get(t.status.name, '⚪️')} #{t.id} - {t.title}", callback_data=f"view_ticket_{t.id}")] for t in tickets]
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_support_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_ticket_view_keyboard(lang: str, ticket_id: int, status_name: str) -> InlineKeyboardMarkup:
    keyboard = []
    if status_name != 'CLOSED':
        keyboard.append([InlineKeyboardButton("✍️ " + get_text("reply_to_ticket_button", lang), callback_data=f"reply_ticket_{ticket_id}")])
        keyboard.append([InlineKeyboardButton("☑️ " + get_text("close_ticket_button", lang), callback_data=f"close_ticket_{ticket_id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_ticket_list")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_settings_keyboard(lang: str, markup: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(get_text("current_markup", lang).format(markup=markup), callback_data="noop")],[InlineKeyboardButton("✏️ " + get_text("change_markup_button", lang), callback_data="set_markup_start")]]
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_admin_panel")])
    return InlineKeyboardMarkup(keyboard)