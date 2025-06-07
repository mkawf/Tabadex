# tabadex_bot/handlers/support_handler.py

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import logger, settings
from ..database import crud, models
from ..keyboards import (
    get_support_menu_keyboard,
    get_support_topics_keyboard,
    get_user_tickets_keyboard,
    get_ticket_view_keyboard,
    get_cancel_keyboard
)
from ..locales import get_text

GET_TOPIC, GET_MESSAGE, GET_REPLY = range(30, 33)

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منوی اصلی پشتیبانی را با دکمه‌های ثابت نمایش می‌دهد."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("support_menu_title", lang),
        reply_markup=get_support_menu_keyboard(lang)
    )

async def create_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع مکالمه ایجاد تیکت جدید."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("support_select_topic", lang),
        reply_markup=get_support_topics_keyboard(lang)
    )
    # کیبورد ثابت را به طور موقت حذف می‌کنیم تا با دکمه‌های شیشه‌ای تداخل نکند
    await update.message.reply_text("...", reply_markup=ReplyKeyboardRemove())
    return GET_TOPIC

async def get_ticket_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """موضوع تیکت را دریافت کرده و درخواست متن پیام را می‌کند."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    topic_key = query.data.split("_", 1)[1]
    topic_text = get_text(f"topic_{topic_key}", lang)
    context.user_data['new_ticket_title'] = topic_text
    
    await query.edit_message_text(
        text=get_text("support_enter_message", lang)
    )
    return GET_MESSAGE

async def get_ticket_message_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """پیام کاربر را دریافت، تیکت را ذخیره و به ادمین‌ها به زبان خودشان اطلاع می‌دهد."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    title = context.user_data.pop('new_ticket_title', 'No Title')
    message_text = update.message.text
    
    new_ticket = await crud.create_ticket(session, update.effective_user.id, title, message_text)
    await update.message.reply_text(get_text("support_ticket_created", lang).format(ticket_id=new_ticket.id))
    
    # اطلاع‌رسانی به ادمین‌ها
    for admin_id in settings.ADMIN_ID_SET:
        admin_user = await crud.get_user_by_user_id(session, admin_id)
        admin_lang = admin_user.language_code if admin_user else "fa"
        
        admin_notification_text = get_text("admin_new_ticket_notification", admin_lang).format(
            user_id=update.effective_user.id, ticket_id=new_ticket.id, title=title
        )
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_notification_text)
        except Exception as e:
            logger.error(f"Failed to send new ticket notification to admin {admin_id}: {e}")

    await show_support_menu(update, context)
    return ConversationHandler.END

async def cancel_ticket_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """فرآیند ایجاد تیکت را لغو می‌کند."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    context.user_data.pop('new_ticket_title', None)
    await query.edit_message_text(get_text("add_address_canceled", lang))
    await show_support_menu(update, context)
    return ConversationHandler.END

async def view_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست تیکت‌های کاربر را نمایش می‌دهد."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    tickets = await crud.get_tickets_by_user(session, update.effective_user.id)
    
    if not tickets:
        await update.message.reply_text(get_text("support_no_tickets", lang))
        return

    await update.message.reply_text(
        text=get_text("my_tickets_title", lang),
        reply_markup=get_user_tickets_keyboard(tickets, lang)
    )

async def show_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جزئیات کامل یک تیکت را نمایش می‌دهد."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    ticket_id = int(query.data.split("_")[-1])

    ticket = await crud.get_ticket_with_messages(session, ticket_id, update.effective_user.id)
    if not ticket:
        await query.answer(get_text("error_generic", lang), show_alert=True)
        return

    message_text = f"<b>{get_text('ticket_details_title', lang)} #{ticket.id}</b>\n"
    message_text += f"<i>{get_text('topic_title', lang)}: {ticket.title}</i>\n" + ("-"*20)
    for msg in ticket.messages:
        sender = get_text("you", lang) if not msg.is_admin_response else get_text("support_team", lang)
        message_text += f"\n\n<b>{sender}</b> ({msg.created_at.strftime('%Y-%m-%d %H:%M')}):\n{msg.text}"
    
    keyboard = get_ticket_view_keyboard(lang, ticket.id, ticket.status.name)
    await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """یک تیکت را توسط کاربر می‌بندد."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    ticket_id = int(query.data.split("_")[-1])

    success = await crud.close_ticket_by_user(session, ticket_id, update.effective_user.id)
    if success:
        await query.answer(get_text("support_ticket_closed_success", lang), show_alert=True)
        await show_ticket_details(update, context) # Refresh the view
    else:
        await query.answer(get_text("error_generic", lang), show_alert=True)

# --- Handlers ---

# --- <<< بخش اصلاح شده و حیاتی >>> ---
create_ticket_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(f"^({get_text('create_new_ticket_button', 'fa')}|{get_text('create_new_ticket_button', 'en')})$"), create_ticket_start)],
    states={
        GET_TOPIC: [CallbackQueryHandler(get_ticket_topic, pattern="^topic_")],
        GET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ticket_message_and_save)],
    },
    fallbacks=[CallbackQueryHandler(cancel_ticket_creation, pattern="^cancel_ticket_creation$")],
    per_user=True, per_chat=True
)

support_callback_handler = CallbackQueryHandler(show_ticket_details, pattern="^view_ticket_")
support_close_handler = CallbackQueryHandler(close_ticket, pattern="^close_ticket_")
support_view_list_handler = MessageHandler(filters.Regex(f"^({get_text('view_my_tickets_button', 'fa')}|{get_text('view_my_tickets_button', 'en')})$"), view_my_tickets)