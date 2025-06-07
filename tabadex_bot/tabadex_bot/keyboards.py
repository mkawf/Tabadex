# tabadex_bot/keyboards.py
from typing import List, Dict, Any
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from .locales import get_text
from .database.models import User, Order, SavedAddress, Ticket, TicketStatus

# --- Reply Keyboards (دکمه‌های ثابت) ---

def get_main_menu_keyboard(lang: str, is_admin: bool) -> ReplyKeyboardMarkup:
    """کیبورد منوی اصلی با دکمه‌های Reply."""
    keyboard = [
        [KeyboardButton(get_text("exchange_button", lang)), KeyboardButton(get_text("buy_tether_button", lang))],
        [KeyboardButton(get_text("account_button", lang)), KeyboardButton(get_text("support_button", lang))]
    ]
    if is_admin:
        keyboard.append([KeyboardButton(get_text("admin_panel_button", lang))])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_account_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_text("my_orders_button", lang)), KeyboardButton(get_text("saved_addresses_button", lang))],
        [KeyboardButton(get_text("change_language_button", lang)), KeyboardButton(get_text("back_button", lang))]
    ], resize_keyboard=True)

def get_support_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_text("create_new_ticket_button", lang)), KeyboardButton(get_text("view_my_tickets_button", lang))],
        [KeyboardButton(get_text("back_button", lang))]
    ], resize_keyboard=True)

def get_admin_panel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(get_text("admin_user_management", lang))],
        [KeyboardButton(get_text("admin_ticket_management", lang))],
        [KeyboardButton(get_text("admin_statistics", lang)), KeyboardButton(get_text("admin_broadcast", lang))],
        [KeyboardButton(get_text("admin_settings", lang)), KeyboardButton(get_text("back_button", lang))]
    ], resize_keyboard=True)

# --- Inline Keyboards (دکمه‌های شیشه‌ای) ---
def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🇮🇷 فارسی (Persian)", callback_data="set_lang_fa"), InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")]])

def get_cancel_keyboard(lang: str, callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("cancel_button", lang), callback_data=callback_data)]])

def create_currency_keyboard(currencies: list, callback_prefix: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(f"{c['name']} ({c['ticker'].upper()})", callback_data=f"{callback_prefix}_{c['ticker']}") for c in currencies[:9]]
    return InlineKeyboardMarkup([buttons[i:i+3] for i in range(0, len(buttons), 3)])

def get_exchange_preview_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("confirm_rate_button", lang), callback_data="preview_confirm"), InlineKeyboardButton(get_text("cancel_button", lang), callback_data="preview_cancel")]])

def get_orders_keyboard(orders: list, lang: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"#{o.id[:8]}.. | {o.from_amount} {o.from_currency.upper()} ➡️ {o.to_currency.upper()}", callback_data=f"view_order_{o.id}")] for o in orders]
    pagination_row = []
    if page > 1: pagination_row.append(InlineKeyboardButton("« " + get_text("prev_page", lang), callback_data=f"orders_page_{page-1}"))
    if page < total_pages: pagination_row.append(InlineKeyboardButton(get_text("next_page", lang) + " »", callback_data=f"orders_page_{page+1}"))
    if pagination_row: keyboard.append(pagination_row)
    return InlineKeyboardMarkup(keyboard)

def get_back_to_orders_keyboard(lang: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("back_button", lang), callback_data=f"orders_page_{page}")]])
    
def get_addresses_keyboard(addresses: list, lang: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"{addr.name} ({addr.currency_ticker.upper()})", callback_data="noop"), InlineKeyboardButton("🗑️", callback_data=f"delete_address_{addr.id}")] for addr in addresses]
    keyboard.append([InlineKeyboardButton("➕ " + get_text("add_address_button", lang), callback_data="add_address_start")])
    return InlineKeyboardMarkup(keyboard)

def get_support_topics_keyboard(lang: str) -> InlineKeyboardMarkup:
    topics = {"problem_with_order": get_text("topic_order_problem", lang), "deposit_issue": get_text("topic_deposit_issue", lang), "general_question": get_text("topic_general_question", lang), "other": get_text("topic_other", lang)}
    keyboard = [[InlineKeyboardButton(text, callback_data=f"topic_{key}")] for key, text in topics.items()]
    keyboard.append([InlineKeyboardButton(get_text("cancel_button", lang), callback_data="cancel_ticket_creation")])
    return InlineKeyboardMarkup(keyboard)

def get_user_tickets_keyboard(tickets: list, lang: str) -> InlineKeyboardMarkup:
    status_map = {'OPEN': '🔵', 'ANSWERED': '🟢', 'PENDING_USER_REPLY': '🟡', 'CLOSED': '⚫️'}
    keyboard = [[InlineKeyboardButton(f"{status_map.get(t.status.name, '⚪️')} #{t.id} - {t.title}", callback_data=f"view_ticket_{t.id}")] for t in tickets]
    return InlineKeyboardMarkup(keyboard)

def get_ticket_view_keyboard(lang: str, ticket_id: int, status_name: str) -> InlineKeyboardMarkup:
    keyboard = []
    if status_name != 'CLOSED':
        keyboard.append([InlineKeyboardButton("✍️ " + get_text("reply_to_ticket_button", lang), callback_data=f"reply_ticket_{ticket_id}")])
        keyboard.append([InlineKeyboardButton("☑️ " + get_text("close_ticket_button", lang), callback_data=f"close_ticket_{ticket_id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="support_view_list")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_tickets_keyboard(tickets: list, lang: str) -> InlineKeyboardMarkup:
    status_map = {'OPEN': '🔵', 'PENDING_USER_REPLY': '🟡'}
    keyboard = [[InlineKeyboardButton(f"{status_map.get(ticket.status.name, '⚪️')} #{ticket.id} - User: {ticket.user_id}", callback_data=f"admin_view_ticket_{ticket.id}")] for ticket in tickets]
    return InlineKeyboardMarkup(keyboard)

def get_admin_ticket_view_keyboard(lang: str, ticket_id: int, status_name: str) -> InlineKeyboardMarkup:
    keyboard = []
    if status_name != 'CLOSED':
        keyboard.append([InlineKeyboardButton("✍️ " + get_text("admin_reply_button", lang), callback_data=f"admin_reply_start_{ticket_id}")])
        keyboard.append([InlineKeyboardButton("☑️ " + get_text("admin_close_ticket_button", lang), callback_data=f"admin_close_ticket_{ticket_id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_tickets_main")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_user_management_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("📋 " + get_text("admin_view_all_users", lang), callback_data="admin_users_list_1"), InlineKeyboardButton("🔍 " + get_text("admin_search_user", lang), callback_data="admin_search_user_start")]])

def get_admin_users_list_keyboard(users: list, lang: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(f"{'🔴' if user.is_blocked else '🟢'} {user.first_name or 'N/A'} (@{user.username or 'N/A'})", callback_data=f"admin_view_user_{user.user_id}")] for user in users]
    pagination_row = []
    if page > 1: pagination_row.append(InlineKeyboardButton("<<", callback_data=f"admin_users_list_{page - 1}"))
    if page < total_pages: pagination_row.append(InlineKeyboardButton(">>", callback_data=f"admin_users_list_{page + 1}"))
    if pagination_row: keyboard.append(pagination_row)
    return InlineKeyboardMarkup(keyboard)
    
def get_admin_user_details_keyboard(lang: str, user_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    block_text = get_text("admin_unblock_user", lang) if is_blocked else get_text("admin_block_user", lang)
    block_callback = f"admin_unblock_{user_id}" if is_blocked else f"admin_block_{user_id}"
    return InlineKeyboardMarkup([[InlineKeyboardButton(block_text, callback_data=block_callback)], [InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_users_list_1")]])

def get_admin_settings_keyboard(lang: str, markup: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("current_markup", lang).format(markup=markup), callback_data="noop")], [InlineKeyboardButton("✏️ " + get_text("change_markup_button", lang), callback_data="set_markup_start")]])

def get_admin_broadcast_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ " + get_text("admin_broadcast_send", lang), callback_data="confirm_broadcast"), InlineKeyboardButton("❌ " + get_text("cancel_button", lang), callback_data="cancel_broadcast")]])

# --- <<< تابع فراموش شده در اینجا اضافه شده است >>> ---
def get_back_to_admin_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    """A keyboard with a single button to go back to the admin panel."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_panel")]])