# tabadex_bot/handlers/account_handler.py

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from ..locales import get_text
from ..database import crud
from ..keyboards import (
    get_account_menu_keyboard,
    get_orders_keyboard,
    get_back_to_orders_keyboard,
    get_addresses_keyboard,
    get_back_to_account_menu_keyboard,
    get_language_selection_keyboard,
    create_currency_keyboard,  # <-- Import new keyboard
    get_cancel_keyboard      # <-- Import new keyboard
)
from ..utils.swapzone_api import swapzone_api_client
from .start_handler import show_main_menu # To return to main menu after cancel

# States for Add Address Conversation
GET_CURRENCY, GET_ADDRESS, GET_NAME = range(10, 13) # Use a different range to avoid conflicts


# --- Main Account Menu ---

async def show_account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_entry: bool = False):
    """Displays the main account menu. Can be called directly or from a callback."""
    lang = context.user_data.get("lang", "fa")
    text = get_text("account_menu_title", lang)
    keyboard = get_account_menu_keyboard(lang)
    
    if is_entry and update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_message:
         await update.effective_message.reply_text(text, reply_markup=keyboard)


# --- Order Management (No changes here) ---
# ... (کد توابع show_orders_list و show_order_details بدون تغییر باقی می‌ماند)
async def show_orders_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a paginated list of user's orders."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    page = int(query.data.split("_")[-1])
    context.user_data['current_order_page'] = page
    orders = await crud.get_orders_by_user(session, user_id, page=page, limit=5)
    if not orders and page == 1:
        text = get_text("my_orders_empty", lang)
        keyboard = get_back_to_account_menu_keyboard(lang)
    else:
        text = get_text("my_orders_title", lang)
        keyboard = get_orders_keyboard(orders, lang, page)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows detailed information about a single order."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    order_id = query.data.split("_")[-1]
    page = context.user_data.get('current_order_page', 1)
    order = await crud.get_order_by_id_for_user(session, order_id, user_id)
    if not order:
        await query.answer(get_text("error_order_not_found", lang), show_alert=True)
        return
    status_text = get_text(f"order_status_{order.status.name.lower()}", lang)
    text = get_text("order_details_format", lang).format(
        id=order.id, status=status_text, created_at=order.created_at.strftime('%Y-%m-%d %H:%M'),
        from_amount=order.from_amount, from_currency=order.from_currency.upper(),
        to_amount_estimated=order.to_amount_estimated, to_currency=order.to_currency.upper(),
        recipient_address=f"<code>{order.recipient_address}</code>",
        deposit_address=f"<code>{order.deposit_address}</code>"
    )
    keyboard = get_back_to_orders_keyboard(lang, page)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

# --- Address Management ---

async def show_addresses_list(update: Update, context: ContextTypes.DEFAULT_TYPE, is_entry: bool = False):
    """Shows a list of user's saved addresses."""
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    addresses = await crud.get_saved_addresses_by_user(session, user_id)
    text = get_text("saved_addresses_title", lang)
    keyboard = get_addresses_keyboard(addresses, lang)
    
    if is_entry and update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=keyboard)

async def delete_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes a saved address."""
    query = update.callback_query
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    address_id = int(query.data.split("_")[-1])
    success = await crud.delete_saved_address(session, address_id, user_id)
    if success:
        await query.answer(get_text("address_deleted_success", lang), show_alert=True)
    else:
        await query.answer(get_text("error_generic", lang), show_alert=True)
    await show_addresses_list(update, context, is_entry=True)


# --- Add New Address Conversation ---

async def add_address_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the 'add address' conversation. Asks for currency."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")

    try:
        currencies = await swapzone_api_client.get_currencies()
        currencies = [c for c in currencies if c.get('ticker') and c.get('name')]
        context.user_data['currencies_for_address'] = {c['ticker']: c for c in currencies}
        
        keyboard = create_currency_keyboard(currencies, "add_addr_curr")
        keyboard.inline_keyboard.append([InlineKeyboardButton(get_text("cancel_button", lang), callback_data="cancel_add_address")])
        
        await query.edit_message_text(
            text=get_text("add_address_select_currency", lang),
            reply_markup=keyboard
        )
        return GET_CURRENCY
    except Exception as e:
        await query.edit_message_text(get_text("error_api_connection", lang))
        return ConversationHandler.END

async def get_currency_for_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles currency selection and asks for the address string."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    currency_ticker = query.data.split("_")[-1]
    context.user_data['new_address_ticker'] = currency_ticker
    
    await query.edit_message_text(
        text=get_text("add_address_enter_address", lang).format(currency=currency_ticker.upper()),
        reply_markup=get_cancel_keyboard(lang, "cancel_add_address")
    )
    return GET_ADDRESS

async def get_address_for_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles address input and asks for a descriptive name."""
    lang = context.user_data.get("lang", "fa")
    address = update.message.text.strip()
    # Basic validation: can be improved with regex for each currency
    if not address:
        await update.message.reply_text(get_text("error_invalid_address", lang))
        return GET_ADDRESS
        
    context.user_data['new_address_string'] = address
    
    await update.message.reply_text(
        text=get_text("add_address_enter_name", lang),
        reply_markup=get_cancel_keyboard(lang, "cancel_add_address")
    )
    return GET_NAME

async def get_name_and_save_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the name, saves all data to the DB, and ends the conversation."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    user_id = update.effective_user.id
    
    name = update.message.text.strip()
    ticker = context.user_data['new_address_ticker']
    address = context.user_data['new_address_string']
    
    await crud.add_saved_address(session, user_id, name, address, ticker)
    
    await update.message.reply_text(get_text("add_address_success", lang))
    
    # Clean up context
    for key in ['new_address_ticker', 'new_address_string', 'currencies_for_address']:
        context.user_data.pop(key, None)
    
    # Show the updated list
    await show_addresses_list(update, context)
    return ConversationHandler.END

async def cancel_add_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the 'add address' process and returns to the address list."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    await query.edit_message_text(get_text("add_address_canceled", lang))
    
    # Clean up context
    for key in ['new_address_ticker', 'new_address_string', 'currencies_for_address']:
        context.user_data.pop(key, None)
        
    await show_addresses_list(update, context, is_entry=True)
    return ConversationHandler.END


# --- Change Language (No changes here) ---
async def change_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the language selection menu."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    text = get_text("choose_language", lang)
    keyboard = get_language_selection_keyboard()
    keyboard.inline_keyboard.append([InlineKeyboardButton(get_text("back_button", lang), callback_data="back_to_account_menu")])
    await query.edit_message_text(text, reply_markup=keyboard)


# --- Handlers Definition ---
account_menu_handler = CallbackQueryHandler(lambda u, c: show_account_menu(u, c, is_entry=True), pattern="^main_account$|^back_to_account_menu$")
orders_list_handler = CallbackQueryHandler(show_orders_list, pattern="^account_orders_page_")
order_details_handler = CallbackQueryHandler(show_order_details, pattern="^view_order_")
addresses_list_handler = CallbackQueryHandler(lambda u, c: show_addresses_list(u, c, is_entry=True), pattern="^account_addresses$")
delete_address_handler = CallbackQueryHandler(delete_address, pattern="^delete_address_")
change_language_handler = CallbackQueryHandler(change_language_menu, pattern="^account_lang$")

# Conversation handler for adding a new address
add_address_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_address_start, pattern="^add_address_start$")],
    states={
        GET_CURRENCY: [CallbackQueryHandler(get_currency_for_address, pattern="^add_addr_curr_")],
        GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address_for_save)],
        GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_and_save_address)],
    },
    fallbacks=[CallbackQueryHandler(cancel_add_address, pattern="^cancel_add_address$")],
)