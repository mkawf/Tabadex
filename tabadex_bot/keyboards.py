# tabadex_bot/keyboards.py

from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .locales import get_text
from .database.models import User, Order, SavedAddress, Ticket, TicketStatus

# --- General Keyboards ---
def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("🇮🇷 فارسی (Persian)", callback_data="set_lang_fa"), InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")]]
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(get_text("exchange_button", lang), callback_data="main_exchange"), InlineKeyboardButton(get_text("buy_tether_button", lang), callback_data="main_buy_tether")],
        [InlineKeyboardButton(get_text("account_button", lang), callback_data="main_account"), InlineKeyboardButton(get_text("support_button", lang), callback_data="main_support")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(get_text("admin_panel_button", lang), callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def create_currency_keyboard(currencies: List[Dict[str, Any]], callback_prefix: str) -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(f"{c.get('name', 'N/A')} ({c.get('ticker', 'N/A').upper()})", callback_data=f"{callback_prefix}_{c.get('ticker')}") for c in currencies[:9]]
    keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard(lang: str, callback_data: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(get_text("cancel_button", lang), callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

# --- Account Management Keyboards ---
def get_account_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(get_text("my_orders_button", lang), callback_data="account_orders_page_1"), InlineKeyboardButton(get_text("saved_addresses_button", lang), callback_data="account_addresses")],
        [InlineKeyboardButton(get_text("change_language_button", lang), callback_data="account_lang"), InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_orders_keyboard(orders: list[Order], lang: str, current_page: int) -> InlineKeyboardMarkup:
    keyboard = []
    for order in orders:
        text = f"#{order.id[:8]}... | {order.from_amount} {order.from_currency.upper()} -> {order.to_currency.upper()} | {order.status.name.capitalize()}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"view_order_{order.id}")])
    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton("<< " + get_text("prev_page", lang), callback_data=f"account_orders_page_{current_page - 1}"))
    if len(orders) == 5:
        pagination_row.append(InlineKeyboardButton(get_text("next_page", lang) + " >>", callback_data=f"account_orders_page_{current_page + 1}"))
    if pagination_row:
        keyboard.append(pagination_row)
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_account_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_back_to_orders_keyboard(lang: str, page: int) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(get_text("back_button", lang), callback_data=f"account_orders_page_{page}")]]
    return InlineKeyboardMarkup(keyboard)

def get_addresses_keyboard(addresses: list[SavedAddress], lang: str) -> InlineKeyboardMarkup:
    keyboard = []
    for addr in addresses:
        row = [InlineKeyboardButton(f"{addr.name} ({addr.currency_ticker.upper()})", callback_data=f"view_address_{addr.id}"), InlineKeyboardButton("🗑️", callback_data=f"delete_address_{addr.id}")]
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("➕ " + get_text("add_address_button", lang), callback_data="add_address_start")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_account_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_back_to_account_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_account_menu")]]
    return InlineKeyboardMarkup(keyboard)

# --- Support Keyboards ---
def get_support_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("💬 " + get_text("create_new_ticket_button", lang), callback_data="support_create_start")],
        [InlineKeyboardButton("🎟️ " + get_text("view_my_tickets_button", lang), callback_data="support_view_list")],
        [InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_support_topics_keyboard(lang: str) -> InlineKeyboardMarkup:
    topics = {"problem_with_order": get_text("topic_order_problem", lang), "deposit_issue": get_text("topic_deposit_issue", lang), "general_question": get_text("topic_general_question", lang), "other": get_text("topic_other", lang)}
    keyboard = [[InlineKeyboardButton(text, callback_data=f"support_create_topic_{key}")] for key, text in topics.items()]
    keyboard.append([InlineKeyboardButton(get_text("cancel_button", lang), callback_data="support_cancel_creation")])
    return InlineKeyboardMarkup(keyboard)

def get_user_tickets_keyboard(tickets: list[Ticket], lang: str) -> InlineKeyboardMarkup:
    keyboard = []
    for ticket in tickets:
        status_icon = {TicketStatus.OPEN: "🔵", TicketStatus.ANSWERED: "🟢", TicketStatus.PENDING_USER_REPLY: "🟡", TicketStatus.CLOSED: "⚫️"}.get(ticket.status, "⚪️")
        text = f"{status_icon} #{ticket.id} - {ticket.title}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"support_view_ticket_{ticket.id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="support_main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_ticket_view_keyboard(lang: str, ticket_id: int, status: TicketStatus) -> InlineKeyboardMarkup:
    keyboard = []
    if status != TicketStatus.CLOSED:
        keyboard.append([InlineKeyboardButton("✍️ " + get_text("reply_to_ticket_button", lang), callback_data=f"support_reply_start_{ticket_id}"), InlineKeyboardButton("☑️ " + get_text("close_ticket_button", lang), callback_data=f"support_close_{ticket_id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="support_view_list")])
    return InlineKeyboardMarkup(keyboard)

# --- Admin Keyboards ---
def get_admin_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    """The main keyboard for the admin panel."""
    keyboard = [
        [InlineKeyboardButton("👥 " + get_text("admin_user_management", lang), callback_data="admin_users_main")],
        [InlineKeyboardButton("🎫 " + get_text("admin_ticket_management", lang), callback_data="admin_tickets_main")],
        [InlineKeyboardButton("📊 " + get_text("admin_statistics", lang), callback_data="admin_stats")],
        [InlineKeyboardButton("📢 " + get_text("admin_broadcast", lang), callback_data="admin_broadcast_start")],
        [InlineKeyboardButton("⚙️ " + get_text("admin_settings", lang), callback_data="admin_settings_main")],
        [InlineKeyboardButton(get_text("back_to_main_menu", lang), callback_data="back_to_main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_admin_panel_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_panel")]]
    return InlineKeyboardMarkup(keyboard)

def get_admin_settings_keyboard(lang: str, current_markup: str) -> InlineKeyboardMarkup:
    """Displays the current settings and provides actions."""
    text = get_text("current_markup", lang).format(markup=current_markup)
    keyboard = [
        [InlineKeyboardButton(text, callback_data="noop")], # No operation, just for display
        [InlineKeyboardButton("✏️ " + get_text("change_markup_button", lang), callback_data="admin_set_markup_start")],
        [InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_broadcast_confirm_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✅ " + get_text("admin_broadcast_send", lang), callback_data="admin_broadcast_confirm")],
        [InlineKeyboardButton("❌ " + get_text("cancel_button", lang), callback_data="admin_broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_tickets_keyboard(tickets: list[Ticket], lang: str) -> InlineKeyboardMarkup:
    keyboard = []
    for ticket in tickets:
        status_icon = "🟡" if ticket.status == TicketStatus.PENDING_USER_REPLY else "🔵"
        text = f"{status_icon} #{ticket.id} - User: {ticket.user_id} - {ticket.title}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"admin_view_ticket_{ticket.id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_ticket_view_keyboard(lang: str, ticket_id: int, status: TicketStatus) -> InlineKeyboardMarkup:
    keyboard = []
    if status != TicketStatus.CLOSED:
        keyboard.append([InlineKeyboardButton("✍️ " + get_text("admin_reply_button", lang), callback_data=f"admin_reply_start_{ticket_id}"), InlineKeyboardButton("☑️ " + get_text("admin_close_ticket_button", lang), callback_data=f"admin_close_ticket_{ticket_id}")])
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_tickets_main")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_user_management_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📋 " + get_text("admin_view_all_users", lang), callback_data="admin_users_list_1")],
        [InlineKeyboardButton("🔍 " + get_text("admin_search_user", lang), callback_data="admin_search_user_start")],
        [InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_users_list_keyboard(users: list[User], lang: str, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    keyboard = []
    for user in users:
        status_icon = "🔴" if user.is_blocked else "🟢"
        text = f"{status_icon} {user.first_name or 'No Name'} (@{user.username or 'N/A'}) - ID: {user.user_id}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"admin_view_user_{user.user_id}")])
    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton("<<", callback_data=f"admin_users_list_{current_page - 1}"))
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton(">>", callback_data=f"admin_users_list_{current_page + 1}"))
    if pagination_row:
        keyboard.append(pagination_row)
    keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_users_main")])
    return InlineKeyboardMarkup(keyboard)
    
def get_admin_user_details_keyboard(lang: str, user_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    if is_blocked:
        block_text = "✅ " + get_text("admin_unblock_user", lang)
        block_callback = f"admin_unblock_{user_id}"
    else:
        block_text = "🚫 " + get_text("admin_block_user", lang)
        block_callback = f"admin_block_{user_id}"
    keyboard = [[InlineKeyboardButton(block_text, callback_data=block_callback)], [InlineKeyboardButton(get_text("back_button", lang), callback_data="admin_users_list_1")]]
    return InlineKeyboardMarkup(keyboard)