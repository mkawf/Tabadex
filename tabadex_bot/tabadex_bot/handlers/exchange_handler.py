# tabadex_bot/handlers/exchange_handler.py

from decimal import Decimal, getcontext
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from ..config import logger
from ..locales import get_text
from ..utils.swapzone_api import swapzone_api_client
from ..database import crud
from ..database.models import Order, OrderStatus
from .start_handler import show_main_menu
from ..keyboards import create_currency_keyboard, get_exchange_preview_keyboard, get_cancel_keyboard

getcontext().prec = 18

(
    SELECT_FROM_CURRENCY, ENTER_AMOUNT, SELECT_TO_CURRENCY,
    CONFIRM_PREVIEW, ENTER_RECIPIENT_ADDRESS
) = range(10, 15)

async def start_exchange_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the exchange conversation, called from a MessageHandler."""
    lang = context.user_data.get("lang", "fa")
    
    # Remove the main menu keyboard temporarily
    await update.message.reply_text("...", reply_markup=ReplyKeyboardRemove())
    
    try:
        currencies = await swapzone_api_client.get_currencies()
        currencies = [c for c in currencies if c.get('ticker') and c.get('name')]
        context.user_data['currencies'] = currencies

        keyboard = create_currency_keyboard(currencies, "from")
        await update.message.reply_text(
            text=get_text("exchange_select_from_currency", lang),
            reply_markup=keyboard,
        )
        return SELECT_FROM_CURRENCY
    except Exception as e:
        logger.error(f"Failed to start exchange: {e}")
        await update.message.reply_text(get_text("error_api_connection", lang))
        await show_main_menu(update, context) # Show main menu on failure
        return ConversationHandler.END

async def get_from_currency_and_ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    from_currency_ticker = query.data.split("_")[1]
    context.user_data["from_currency"] = from_currency_ticker
    text = get_text("exchange_enter_amount_simple", lang).format(from_currency=from_currency_ticker.upper())
    await query.edit_message_text(text=text)
    return ENTER_AMOUNT

async def get_amount_and_ask_to_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    lang = context.user_data.get("lang", "fa")
    amount_str = message.text
    try:
        amount = float(amount_str)
        context.user_data["amount"] = str(amount)
        from_currency = context.user_data["from_currency"]
        all_currencies = context.user_data.get('currencies', [])
        to_currencies = [c for c in all_currencies if c['ticker'] != from_currency]
        keyboard = create_currency_keyboard(to_currencies, "to")
        await message.reply_text(text=get_text("exchange_select_to_currency", lang), reply_markup=keyboard)
        return SELECT_TO_CURRENCY
    except (ValueError, TypeError):
        await message.reply_text(get_text("error_invalid_amount", lang))
        return ENTER_AMOUNT

async def get_to_currency_and_show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session = context.db_session
    to_currency_ticker = query.data.split("_")[1]
    context.user_data["to_currency"] = to_currency_ticker
    from_currency = context.user_data["from_currency"]
    amount = context.user_data["amount"]
    await query.edit_message_text(get_text("exchange_fetching_final_rate", lang))
    try:
        rate = await swapzone_api_client.get_rate(from_currency, to_currency_ticker, amount)
        min_amount = float(rate.get("min", 0))
        max_amount = float(rate.get("max", float('inf')))
        if not (min_amount <= float(amount) <= max_amount):
            text = get_text("error_amount_out_of_range", lang).format(min_amount=min_amount, max_amount=max_amount)
            await query.edit_message_text(text)
            await show_main_menu(update, context)
            return ConversationHandler.END
        estimated_amount_raw_str = rate.get("amountEstimated")
        markup_str = await crud.get_setting(session, "markup_percentage", "0.5")
        estimated_amount_raw = Decimal(estimated_amount_raw_str)
        markup_percentage = Decimal(markup_str)
        fee = estimated_amount_raw * (markup_percentage / Decimal(100))
        final_estimated_amount = estimated_amount_raw - fee
        context.user_data["final_estimated_amount"] = str(final_estimated_amount)
        preview_text = get_text("exchange_preview_details", lang).format(
            amount=amount, from_currency=from_currency.upper(),
            estimated_amount=f"{final_estimated_amount:.8f}",
            to_currency=to_currency_ticker.upper()
        )
        keyboard = get_exchange_preview_keyboard(lang)
        await query.edit_message_text(preview_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return CONFIRM_PREVIEW
    except Exception as e:
        logger.error(f"Error in get_to_currency_and_show_preview: {e}")
        await query.edit_message_text(text=get_text("error_getting_rate", lang))
        await show_main_menu(update, context)
        return ConversationHandler.END

async def get_preview_confirmation_and_ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    if query.data != "preview_confirm":
        await query.edit_message_text(get_text("exchange_canceled", lang))
        return await cancel_exchange(update, context)
    to_currency = context.user_data["to_currency"]
    text = get_text("exchange_enter_recipient_address", lang).format(to_currency=to_currency.upper())
    await query.edit_message_text(text)
    return ENTER_RECIPIENT_ADDRESS

async def get_address_and_create_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    lang = context.user_data.get("lang", "fa")
    session = context.db_session
    recipient_address = message.text.strip()
    await message.reply_text(get_text("exchange_creating_transaction", lang))
    try:
        user_data = context.user_data
        tx_data = {
            "from_currency": user_data["from_currency"], "to_currency": user_data["to_currency"],
            "amount": user_data["amount"], "recipient": recipient_address, "refund": None
        }
        created_tx = await swapzone_api_client.create_transaction(**tx_data)
        tx_id = created_tx.get('id')
        deposit_address = created_tx.get('depositAddress')
        new_order = Order(
            id=tx_id, user_id=update.effective_user.id,
            from_currency=tx_data['from_currency'], to_currency=tx_data['to_currency'],
            from_amount=tx_data['amount'],
            to_amount_estimated=user_data.get("final_estimated_amount", "0"),
            deposit_address=deposit_address, recipient_address=recipient_address,
            status=OrderStatus.WAITING,
        )
        session.add(new_order)
        await session.commit()
        deposit_text = get_text("exchange_deposit_info", lang).format(
            amount=tx_data["amount"], from_currency=tx_data["from_currency"].upper(),
            deposit_address=f"<code>{deposit_address}</code>", tx_id=tx_id
        )
        await message.reply_text(deposit_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Failed to create transaction in final step: {e}")
        await message.reply_text(get_text("error_creating_transaction", lang))
    finally:
        keys_to_clear = ['from_currency', 'to_currency', 'amount', 'currencies', 'final_estimated_amount']
        for key in keys_to_clear:
            context.user_data.pop(key, None)
        await show_main_menu(update, context)
    return ConversationHandler.END

async def cancel_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    keys_to_clear = ['from_currency', 'to_currency', 'amount', 'currencies', 'final_estimated_amount']
    for key in keys_to_clear:
        context.user_data.pop(key, None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(get_text("exchange_canceled", lang))
    else:
        await update.effective_message.reply_text(get_text("exchange_canceled", lang))
    await show_main_menu(update, context)
    return ConversationHandler.END

exchange_handler = ConversationHandler(
    entry_points=[CommandHandler('exchange', start_exchange_conv)], # This will be triggered by menu_handler now
    states={
        SELECT_FROM_CURRENCY: [CallbackQueryHandler(get_from_currency_and_ask_amount, pattern="^from_")],
        ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount_and_ask_to_currency)],
        SELECT_TO_CURRENCY: [CallbackQueryHandler(get_to_currency_and_show_preview, pattern="^to_")],
        CONFIRM_PREVIEW: [CallbackQueryHandler(get_preview_confirmation_and_ask_address, pattern="^preview_confirm$")],
        ENTER_RECIPIENT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address_and_create_transaction)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_exchange, pattern="^preview_cancel$"),
        CommandHandler('cancel', cancel_exchange)
    ]
)