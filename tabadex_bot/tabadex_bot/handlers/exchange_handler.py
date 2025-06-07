# tabadex_bot/handlers/exchange_handler.py
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes)
from telegram.constants import ParseMode
from decimal import Decimal, getcontext
from ..config import logger
from ..locales import get_text
from ..utils.swapzone_api import swapzone_api_client
from ..database import crud
from ..keyboards import create_currency_keyboard, create_network_keyboard, get_exchange_preview_keyboard
from .start_handler import show_main_menu

getcontext().prec = 18

(SELECT_FROM, SELECT_TO, SELECT_FROM_NETWORK, SELECT_TO_NETWORK, ENTER_AMOUNT, CONFIRM_PREVIEW, ENTER_ADDRESS, AWAIT_SEARCH) = range(8)
PERSIAN_CURRENCY_MAP = {"بیت کوین": "btc", "اتریوم": "eth", "تتر": "usdt", "دوج کوین": "doge", "کاردانو": "ada", "ریپل": "xrp", "سولانا": "sol", "لایت کوین": "ltc", "ترون": "trx"}

async def start_exchange_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(get_text("exchange_started", lang), reply_markup=ReplyKeyboardRemove())
    try:
        all_currencies = await swapzone_api_client.get_currencies()
        context.user_data['all_currencies'] = {c['ticker']: c for c in all_currencies}
        top_currencies = list(context.user_data['all_currencies'].values())[:9]
        keyboard = create_currency_keyboard(top_currencies, lang, "from")
        await update.message.reply_text(get_text("exchange_select_from_currency", lang), reply_markup=keyboard)
        return SELECT_FROM
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
    top_currencies = all_currencies[:9]
    keyboard = create_currency_keyboard(top_currencies, lang, "to")
    await query.edit_message_text(get_text("exchange_select_to_currency", lang), reply_markup=keyboard)
    return SELECT_TO

async def get_to_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    lang = context.user_data.get("lang", "fa")
    context.user_data["to_currency"] = query.data.split("_")[1]
    from_currency_info = context.user_data['all_currencies'][context.user_data["from_currency"]]
    networks = from_currency_info.get('networks', [])
    if len(networks) == 1:
        context.user_data["from_network"] = networks[0]
        return await ask_to_network(update, context)
    keyboard = create_network_keyboard(networks, lang, "from_net")
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
    keyboard = create_network_keyboard(networks, lang, "to_net")
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
    # We now have all data, proceed to show preview
    await show_preview(update, context)
    return CONFIRM_PREVIEW
    
async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    message = update.message
    if update.callback_query:
        message = update.callback_query.message
    
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

# ... (و سایر توابع که در ریپازیتوری نهایی اصلاح شده‌اند)