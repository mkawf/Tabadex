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
from ..database.models import OrderStatus
from ..keyboards import create_currency_keyboard, create_network_keyboard, get_exchange_preview_keyboard
from .start_handler import show_main_menu

getcontext().prec = 18

(
    SELECT_FROM_CURRENCY, SELECT_FROM_NETWORK, ENTER_AMOUNT,
    SELECT_TO_CURRENCY, SELECT_TO_NETWORK, CONFIRM_PREVIEW,
    ENTER_ADDRESS, AWAIT_SEARCH
) = range(8)

TOP_9_CURRENCIES = ['btc', 'eth', 'usdt', 'bnb', 'sol', 'xrp', 'usdc', 'ada', 'doge']
PERSIAN_CURRENCY_MAP = {"بیت کوین": "btc", "اتریوم": "eth", "تتر": "usdt", "دوج کوین": "doge", "کاردانو": "ada", "ریپل": "xrp", "سولانا": "sol", "لایت کوین": "ltc", "ترون": "trx"}

async def start_exchange_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        get_text("exchange_started", lang), reply_markup=ReplyKeyboardRemove()
    )
    try:
        all_currencies = await swapzone_api_client.get_currencies()
        context.user_data['all_currencies'] = {c['ticker']: c for c in all_currencies}
        top_currencies = [context.user_data['all_currencies'][ticker] for ticker in TOP_9_CURRENCIES if ticker in context.user_data['all_currencies']]
        keyboard = create_currency_keyboard(top_currencies, lang, "from")
        await update.message.reply_text(
            get_text("exchange_select_from_currency", lang), reply_markup=keyboard
        )
        context.user_data['current_step'] = "from"
        return SELECT_FROM_CURRENCY
    except Exception as e:
        logger.error(f"Failed to start exchange: {e}")
        await update.message.reply_text(get_text("error_api_connection", lang))
        await show_main_menu(update, context)
        return ConversationHandler.END

async def get_from_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    lang = context.user_data.get("lang", "fa")
    context.user_data["from_currency"] = query.data.split("_")[1]
    all_currencies = list(context.user_data.get("all_currencies", {}).values())
    top_currencies = [c for c in all_currencies if c['ticker'] in TOP_9_CURRENCIES]
    keyboard = create_currency_keyboard(top_currencies, lang, "to")
    await query.edit_message_text(get_text("exchange_select_to_currency", lang), reply_markup=keyboard)
    return SELECT_TO_CURRENCY

async def get_to_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    lang = context.user_data.get("lang", "fa")
    context.user_data["to_currency"] = query.data.split("_")[1]
    from_currency_info = context.user_data['all_currencies'][context.user_data["from_currency"]]
    networks = from_currency_info.get('networks', [])
    if len(networks) == 1:
        context.user_data["from_network"] = networks[0]
        return await ask_to_network(update, context)
    keyboard = create_network_keyboard(networks, "from_net")
    await query.edit_message_text(get_text("select_network_prompt", lang).format(currency=from_currency_info['ticker'].upper()), reply_markup=keyboard)
    return SELECT_FROM_NETWORK
    
async def get_from_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    context.user_data["from_network"] = query.data.split("_")[-1]
    return await ask_to_network(update, context)

async def ask_to_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    to_currency_info = context.user_data['all_currencies'][context.user_data["to_currency"]]
    networks = to_currency_info.get('networks', [])
    if len(networks) == 1:
        context.user_data["to_network"] = networks[0]
        await update.callback_query.edit_message_text(get_text("exchange_enter_amount_simple", lang).format(from_currency=context.user_data['from_currency'].upper()))
        return ENTER_AMOUNT
    keyboard = create_network_keyboard(networks, "to_net")
    await update.callback_query.edit_message_text(get_text("select_network_prompt", lang).format(currency=to_currency_info['ticker'].upper()), reply_markup=keyboard)
    return SELECT_TO_NETWORK

async def get_to_network(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    lang = context.user_data.get("lang", "fa")
    context.user_data["to_network"] = query.data.split("_")[-1]
    await query.edit_message_text(get_text("exchange_enter_amount_simple", lang).format(from_currency=context.user_data['from_currency'].upper()))
    return ENTER_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    context.user_data["amount"] = update.message.text
    await show_preview(update, context)
    return CONFIRM_PREVIEW

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    message = update.message
    await message.reply_text(get_text("exchange_fetching_final_rate", lang))
    try:
        rate_data = await swapzone_api_client.get_rate(
            from_currency=context.user_data["from_currency"], from_network=context.user_data["from_network"],
            to_currency=context.user_data["to_currency"], to_network=context.user_data["to_network"],
            amount=context.user_data["amount"]
        )
        estimated_amount_str = rate_data.get("amountEstimated")
        if not estimated_amount_str:
            await message.reply_text(get_text("error_no_rate_found", lang))
            return await cancel_exchange(update, context)
        markup_str = await crud.get_setting(context.db_session, "markup_percentage", "0.5")
        final_amount = Decimal(estimated_amount_str) * (Decimal(100) - Decimal(markup_str)) / Decimal(100)
        context.user_data["final_estimated_amount"] = str(final_amount)
        preview_text = get_text("exchange_preview_details", lang).format(
            amount=context.user_data["amount"], from_currency=context.user_data["from_currency"].upper(),
            estimated_amount=f"{final_amount:.8f}", to_currency=context.user_data["to_currency"].upper()
        )
        await message.reply_text(preview_text, reply_markup=get_exchange_preview_keyboard(lang), parse_mode=ParseMode.HTML)
        return CONFIRM_PREVIEW
    except Exception as e:
        logger.error(f"Error in show_preview: {e}")
        await message.reply_text(get_text("error_getting_rate", lang))
        return await cancel_exchange(update, context)

async def get_preview_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data != "preview_confirm":
        return await cancel_exchange(update, context)
    lang = context.user_data.get("lang", "fa")
    to_currency = context.user_data["to_currency"]
    await query.edit_message_text(get_text("exchange_enter_recipient_address", lang).format(to_currency=to_currency.upper()))
    return ENTER_ADDRESS

async def get_address_and_create_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    session = context.db_session
    recipient_address = update.message.text.strip()
    await update.message.reply_text(get_text("exchange_creating_transaction", lang))
    try:
        tx_data = {
            "from": context.user_data["from_currency"], "fromNetwork": context.user_data["from_network"],
            "to": context.user_data["to_currency"], "toNetwork": context.user_data["to_network"],
            "amount": context.user_data["amount"], "recipient": recipient_address,
            "refundAddress": recipient_address
        }
        created_tx = await swapzone_api_client.create_transaction(**tx_data)
        new_order = await crud.create_order(
            session=session, tx_id=created_tx['id'], user_id=update.effective_user.id,
            from_currency=tx_data['from'], from_network=tx_data['fromNetwork'],
            to_currency=tx_data['to'], to_network=tx_data['toNetwork'],
            from_amount=tx_data['amount'], to_amount_estimated=context.user_data.get("final_estimated_amount", "0"),
            deposit_address=created_tx['depositAddress'], recipient_address=recipient_address
        )
        deposit_text = get_text("exchange_deposit_info", lang).format(
            amount=tx_data["amount"], from_currency=tx_data["from"].upper(),
            deposit_address=f"<code>{new_order.deposit_address}</code>", tx_id=new_order.id
        )
        await update.message.reply_text(deposit_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Failed to create transaction in final step: {e}")
        await update.message.reply_text(get_text("error_creating_transaction", lang))
    finally:
        for key in ["from_currency", "from_network", "to_currency", "to_network", "amount", "all_currencies", "final_estimated_amount"]:
            context.user_data.pop(key, None)
        await show_main_menu(update, context)
    return ConversationHandler.END

async def cancel_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(get_text("exchange_canceled", lang))
    else:
        await update.message.reply_text(get_text("exchange_canceled", lang))
    for key in ["from_currency", "from_network", "to_currency", "to_network", "amount", "all_currencies", "final_estimated_amount"]:
        context.user_data.pop(key, None)
    await show_main_menu(update, context)
    return ConversationHandler.END

# --- <<< بخش اصلاح شده و حیاتی >>> ---
# تعریف متغیر exchange_handler برای export کردن به main.py
exchange_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.Regex(f"^({get_text('exchange_button', 'fa')}|{get_text('exchange_button', 'en')})$"),
            start_exchange_conv
        )
    ],
    states={
        SELECT_FROM_CURRENCY: [CallbackQueryHandler(get_from_currency, pattern="^from_")],
        SELECT_FROM_NETWORK: [CallbackQueryHandler(get_from_network, pattern="^from_net_")],
        ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
        SELECT_TO_CURRENCY: [CallbackQueryHandler(get_to_currency, pattern="^to_")],
        SELECT_TO_NETWORK: [CallbackQueryHandler(get_to_network, pattern="^to_net_")],
        CONFIRM_PREVIEW: [CallbackQueryHandler(get_preview_confirmation, pattern="^preview_confirm$")],
        ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address_and_create_transaction)],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_exchange, pattern="^preview_cancel$"),
        CommandHandler('cancel', cancel_exchange)
    ],
)
