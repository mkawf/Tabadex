# tabadex_bot/handlers/exchange_handler.py

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode
from decimal import Decimal, getcontext
from ..config import logger
from ..locales import get_text
from ..utils.swapzone_api import swapzone_api_client
from ..database import crud
from ..database.models import Order, OrderStatus
from ..keyboards import create_currency_keyboard, get_exchange_preview_keyboard, get_cancel_keyboard
from .start_handler import show_main_menu

getcontext().prec = 18

(
    SELECT_FROM,
    ENTER_AMOUNT,
    SELECT_TO,
    CONFIRM_PREVIEW,
    ENTER_ADDRESS,
    AWAIT_SEARCH,
) = range(6)

PERSIAN_CURRENCY_MAP = {
    "بیت کوین": "btc", "اتریوم": "eth", "تتر": "usdt", "دوج کوین": "doge",
    "کاردانو": "ada", "ریپل": "xrp", "سولانا": "sol", "لایت کوین": "ltc", "ترون": "trx",
}

async def start_exchange_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        get_text("exchange_started", lang), reply_markup=ReplyKeyboardRemove()
    )
    try:
        currencies = await swapzone_api_client.get_currencies()
        context.user_data["all_currencies"] = currencies
        keyboard = create_currency_keyboard(currencies, lang, "from")
        await update.message.reply_text(
            get_text("exchange_select_from_currency", lang), reply_markup=keyboard
        )
        context.user_data["current_step"] = "from"
        return SELECT_FROM
    except Exception as e:
        logger.error(f"Failed to start exchange by fetching currencies: {e}")
        await update.message.reply_text(get_text("error_api_connection", lang))
        await show_main_menu(update, context)
        return ConversationHandler.END

async def get_from_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    from_currency_ticker = query.data.split("_")[1]
    context.user_data["from_currency"] = from_currency_ticker
    await query.edit_message_text(
        get_text("exchange_enter_amount_simple", lang).format(
            from_currency=from_currency_ticker.upper()
        )
    )
    return ENTER_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    try:
        amount = float(update.message.text)
        context.user_data["amount"] = str(amount)
        all_currencies = context.user_data.get("all_currencies", [])
        from_currency = context.user_data.get("from_currency")
        to_currencies = [c for c in all_currencies if c.get("ticker") != from_currency]
        keyboard = create_currency_keyboard(to_currencies, lang, "to")
        await update.message.reply_text(
            get_text("exchange_select_to_currency", lang), reply_markup=keyboard
        )
        context.user_data["current_step"] = "to"
        return SELECT_TO
    except (ValueError, TypeError):
        await update.message.reply_text(get_text("error_invalid_amount", lang))
        return ENTER_AMOUNT

async def get_to_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        estimated_amount_raw_str = rate.get("amountEstimated")

        # --- <<< راه‌حل باگ دوم: بررسی وجود نرخ قبل از تبدیل >>> ---
        if estimated_amount_raw_str is None:
            logger.warning(f"No rate available for pair {from_currency}-{to_currency_ticker}")
            await query.edit_message_text(get_text("error_no_rate_found", lang))
            await show_main_menu(update, context)
            return ConversationHandler.END

        min_amount = float(rate.get("min", 0))
        max_amount = float(rate.get("max", float("inf")))
        if not (min_amount <= float(amount) <= max_amount):
            text = get_text("error_amount_out_of_range", lang).format(min_amount=min_amount, max_amount=max_amount)
            await query.edit_message_text(text)
            await show_main_menu(update, context)
            return ConversationHandler.END

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
        logger.error(f"Error in get_to_currency: {e}")
        await query.edit_message_text(get_text("error_getting_rate", lang))
        await show_main_menu(update, context)
        return ConversationHandler.END

async def get_preview_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    if query.data != "preview_confirm":
        return await cancel_exchange(update, context)
    to_currency = context.user_data["to_currency"]
    text = get_text("exchange_enter_recipient_address", lang).format(to_currency=to_currency.upper())
    await query.edit_message_text(text)
    return ENTER_ADDRESS

async def get_address_and_create_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    session = context.db_session
    recipient_address = update.message.text.strip()
    await update.message.reply_text(get_text("exchange_creating_transaction", lang))
    try:
        tx_data = {"from_currency": context.user_data["from_currency"], "to_currency": context.user_data["to_currency"], "amount": context.user_data["amount"], "recipient": recipient_address}
        created_tx = await swapzone_api_client.create_transaction(**tx_data)
        new_order = await crud.create_order(
            session=session, tx_id=created_tx['id'], user_id=update.effective_user.id,
            from_currency=tx_data['from_currency'], to_currency=tx_data['to_currency'],
            from_amount=tx_data['amount'], to_amount_estimated=context.user_data.get("final_estimated_amount", "0"),
            deposit_address=created_tx['depositAddress'], recipient_address=recipient_address
        )
        deposit_text = get_text("exchange_deposit_info", lang).format(
            amount=tx_data["amount"], from_currency=tx_data["from_currency"].upper(),
            deposit_address=f"<code>{new_order.deposit_address}</code>", tx_id=new_order.id
        )
        await update.message.reply_text(deposit_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Failed to create transaction in final step: {e}")
        await update.message.reply_text(get_text("error_creating_transaction", lang))
    finally:
        for key in ["from_currency", "to_currency", "amount", "all_currencies", "final_estimated_amount", "current_step"]:
            context.user_data.pop(key, None)
        await show_main_menu(update, context)
    return ConversationHandler.END

async def prompt_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    await query.edit_message_text(get_text("search_prompt", lang))
    return AWAIT_SEARCH

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    search_term = update.message.text.lower().strip()
    all_currencies = context.user_data.get("all_currencies", [])
    persian_ticker = PERSIAN_CURRENCY_MAP.get(search_term, search_term)

    # --- <<< راه‌حل باگ اول: استفاده از .get() برای جلوگیری از KeyError >>> ---
    results = [
        c for c in all_currencies 
        if (persian_ticker in c.get('ticker', '').lower()) or \
           (search_term in c.get('name', '').lower())
    ]
    
    if not results:
        await update.message.reply_text(get_text("no_currency_found", lang))
        return AWAIT_SEARCH

    current_step = context.user_data.get("current_step", "from")
    keyboard = create_currency_keyboard(results, lang, current_step, show_extra_buttons=False)
    await update.message.reply_text(get_text("search_results_title", lang), reply_markup=keyboard)
    return SELECT_FROM if current_step == "from" else SELECT_TO

async def cancel_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(get_text("exchange_canceled", lang))
    else:
        await update.message.reply_text(get_text("exchange_canceled", lang))
    for key in ["from_currency", "to_currency", "amount", "all_currencies", "final_estimated_amount", "current_step"]:
        context.user_data.pop(key, None)
    await show_main_menu(update, context)
    return ConversationHandler.END

exchange_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(f"^({get_text('exchange_button', 'fa')}|{get_text('exchange_button', 'en')})$"), start_exchange_conv)],
    states={
        SELECT_FROM: [
            CallbackQueryHandler(get_from_currency, pattern="^from_"),
            CallbackQueryHandler(prompt_search, pattern="^exchange_search$")
        ],
        ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        SELECT_TO: [
            CallbackQueryHandler(get_to_currency, pattern="^to_"),
            CallbackQueryHandler(prompt_search, pattern="^exchange_search$")
        ],
        CONFIRM_PREVIEW: [CallbackQueryHandler(get_preview_confirmation, pattern="^preview_confirm$")],
        ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address_and_create_transaction)],
        AWAIT_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_exchange, pattern="^preview_cancel$"),
        CommandHandler('cancel', cancel_exchange)
    ],
)