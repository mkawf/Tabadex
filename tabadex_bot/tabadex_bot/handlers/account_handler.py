# tabadex_bot/handlers/account_handler.py

import math
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import logger
from ..database import crud
from ..keyboards import (
    get_account_menu_keyboard, get_language_selection_keyboard,
    get_orders_keyboard, get_back_to_orders_keyboard,
    get_addresses_keyboard, create_currency_keyboard, get_cancel_keyboard
)
from ..locales import get_text
from .start_handler import show_main_menu
from ..utils.swapzone_api import swapzone_api_client

ORDERS_PER_PAGE = 5
GET_CURRENCY, GET_ADDRESS, GET_NAME = range(20, 23)

async def show_account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the account menu using ReplyKeyboard."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("account_menu_title", lang),
        reply_markup=get_account_menu_keyboard(lang)
    )

async def handle_orders_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'My Orders' button press and shows the first page."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        get_text("my_orders_title_loading", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await show_orders_page(update, context, page_number=1)

async def show_orders_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page_number: int):
    """Displays a specific page of the user's orders."""
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    
    total_orders = await crud.get_orders_count_by_user(session, user_id)
    if total_orders == 0:
        await update.effective_message.reply_text(get_text("my_orders_empty", lang))
        await show_account_menu(update, context)
        return

    total_pages = math.ceil(total_orders / ORDERS_PER_PAGE)
    orders = await crud.get_orders_by_user(session, user_id, page=page_number, limit=ORDERS_PER_PAGE)

    text = get_text("my_orders_title", lang).format(page=page_number, total_pages=total_pages)
    keyboard = get_orders_keyboard(orders, lang, page_number, total_pages)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.effective_message.reply_text(text, reply_markup=keyboard)


async def orders_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles pagination button clicks for orders."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[-1])
    context.user_data["current_order_page"] = page
    await show_orders_page(update, context, page_number=page)

async def show_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows detailed information about a single order."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    order_id = query.data.split("_")[-1]
    order = await crud.get_order_by_id_for_user(session, order_id, update.effective_user.id)
    
    if not order:
        await query.answer(get_text("error_order_not_found", lang), show_alert=True)
        return
    
    page = context.user_data.get("current_order_page", 1)
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


async def handle_saved_addresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    addresses = await crud.get_saved_addresses_by_user(session, update.effective_user.id)
    
    await update.message.reply_text(
        get_text("saved_addresses_title", lang),
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        get_text("saved_addresses_list", lang),
        reply_markup=get_addresses_keyboard(addresses, lang)
    )

async def delete_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    address_id = int(query.data.split("_")[-1])
    
    success = await crud.delete_saved_address(session, address_id, user_id)
    if success:
        await query.answer(get_text("address_deleted_success", lang), show_alert=True)
        addresses = await crud.get_saved_addresses_by_user(session, user_id)
        keyboard = get_addresses_keyboard(addresses, lang)
        await query.edit_message_text(get_text("saved_addresses_list", lang), reply_markup=keyboard)
    else:
        await query.answer(get_text("error_generic", lang), show_alert=True)

async def add_address_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    try:
        currencies = await swapzone_api_client.get_currencies()
        currencies = [c for c in currencies if c.get('ticker') and c.get('name')]
        keyboard = create_currency_keyboard(currencies, "add_addr_curr")
        await query.edit_message_text(
            text=get_text("add_address_select_currency", lang),
            reply_markup=keyboard
        )
        return GET_CURRENCY
    except Exception as e:
        logger.error(f"Error starting add_address: {e}")
        await query.edit_message_text(get_text("error_api_connection", lang))
        return ConversationHandler.END

async def get_currency_for_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    lang = context.user_data.get("lang", "fa")
    address = update.message.text.strip()
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
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    user_id = update.effective_user.id
    name = update.message.text.strip()
    ticker = context.user_data['new_address_ticker']
    address = context.user_data['new_address_string']
    
    await crud.add_saved_address(session, user_id, name, address, ticker)
    await update.message.reply_text(get_text("add_address_success", lang))
    
    for key in ['new_address_ticker', 'new_address_string']:
        context.user_data.pop(key, None)
    
    await show_account_menu(update, context)
    return ConversationHandler.END

async def cancel_add_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    for key in ['new_address_ticker', 'new_address_string']:
        context.user_data.pop(key, None)
        
    await query.edit_message_text(get_text("add_address_canceled", lang))
    # After cancelling, we should show the saved addresses list again
    # But since we don't have the message object to edit, we'll just send a new one
    await show_account_menu(update, context) # This will show the account menu keyboard
    return ConversationHandler.END

async def handle_change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        get_text("choose_language"),
        reply_markup=get_language_selection_keyboard()
    )

add_address_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_address_start, pattern="^add_address_start$")],
    states={
        GET_CURRENCY: [CallbackQueryHandler(get_currency_for_address, pattern="^add_addr_curr_")],
        GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address_for_save)],
        GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_and_save_address)],
    },
    fallbacks=[CallbackQueryHandler(cancel_add_address, pattern="^cancel_add_address$")],
    per_user=True, per_chat=True
)

# --- <<< بخش اصلاح شده و حیاتی >>> ---
# تعریف لیستی از هندلرهای کلیک برای export کردن به main.py
account_callback_handlers = [
    CallbackQueryHandler(orders_page_callback, pattern="^orders_page_"),
    CallbackQueryHandler(show_order_details, pattern="^view_order_"),
    CallbackQueryHandler(delete_address, pattern="^delete_address_"),
]