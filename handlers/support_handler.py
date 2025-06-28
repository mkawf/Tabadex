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
    """Displays the support menu using ReplyKeyboard."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("support_menu_title", lang),
        reply_markup=get_support_menu_keyboard(lang)
    )

async def create_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the new ticket conversation."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("support_select_topic", lang),
        reply_markup=get_support_topics_keyboard(lang)
    )
    await update.message.reply_text("...", reply_markup=ReplyKeyboardRemove())
    return GET_TOPIC

async def get_ticket_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles topic selection and asks for the message."""
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
    """Saves the new ticket and notifies admins."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    title = context.user_data.pop('new_ticket_title', 'No Title')
    message_text = update.message.text
    
    new_ticket = await crud.create_ticket(session, update.effective_user.id, title, message_text)
    await update.message.reply_text(get_text("support_ticket_created", lang).format(ticket_id=new_ticket.id))
    
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
    """Cancels the ticket creation process."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    context.user_data.pop('new_ticket_title', None)
    await query.edit_message_text(get_text("add_address_canceled", lang))
    await show_support_menu(update.callback_query.message, context)
    return ConversationHandler.END

async def view_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a list of the user's tickets."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    tickets = await crud.get_tickets_by_user(session, update.effective_user.id)
    
    if not tickets:
        await update.message.reply_text(get_text("support_no_tickets", lang))
        return

    await update.message.reply_text(text=".", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        text=get_text("my_tickets_title", lang),
        reply_markup=get_user_tickets_keyboard(tickets, lang)
    )

async def show_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the full conversation of a single ticket."""
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
    """Closes a ticket by the user."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    ticket_id = int(query.data.split("_")[-1])

    success = await crud.close_ticket_by_user(session, ticket_id, update.effective_user.id)
    if success:
        await query.answer(get_text("support_ticket_closed_success", lang), show_alert=True)
        await show_ticket_details(update, context)
    else:
        await query.answer(get_text("error_generic", lang), show_alert=True)

async def reply_to_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the reply process."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    ticket_id = int(query.data.split("_")[-1])
    context.user_data['reply_ticket_id'] = ticket_id

    await query.edit_message_text(
        text=get_text("reply_prompt", lang),
        reply_markup=get_cancel_keyboard(lang, f"cancel_reply_{ticket_id}")
    )
    return GET_REPLY

async def get_reply_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the user's reply to the database."""
    session: AsyncSession = context.db_session
    user_id = update.effective_user.id
    ticket_id = context.user_data.pop('reply_ticket_id')
    reply_text = update.message.text

    await crud.add_reply_to_ticket(session, ticket_id, user_id, reply_text, is_admin=False)
    
    class MockQuery:
        def __init__(self, t_id, message):
            self.data = f"view_ticket_{t_id}"
            self.message = message
        async def answer(self): pass
        async def edit_message_text(self, *args, **kwargs):
            await self.message.reply_text(*args, **kwargs)

    mock_update = Update(update.update_id, message=update.message, callback_query=MockQuery(ticket_id, update.message))
    await show_ticket_details(mock_update, context)

    return ConversationHandler.END

async def cancel_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop('reply_ticket_id', None)
    await show_ticket_details(update, context)
    return ConversationHandler.END

async def back_to_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for the back button from the ticket list."""
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    await show_support_menu(query.message, context)

# --- Handlers ---
create_ticket_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(f"^({get_text('create_new_ticket_button', 'fa')}|{get_text('create_new_ticket_button', 'en')})$"), create_ticket_start)],
    states={
        GET_TOPIC: [CallbackQueryHandler(get_ticket_topic, pattern="^topic_")],
        GET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ticket_message_and_save)],
    },
    fallbacks=[CallbackQueryHandler(cancel_ticket_creation, pattern="^cancel_ticket_creation$")],
    per_message=True
)
reply_ticket_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(reply_to_ticket_start, pattern=r"^reply_ticket_")],
    states={GET_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_reply_and_save)]},
    fallbacks=[CallbackQueryHandler(cancel_reply, pattern=r"^cancel_reply_")],
    per_message=True
)
support_handlers = [
    MessageHandler(filters.Regex(f"^({get_text('view_my_tickets_button', 'fa')}|{get_text('view_my_tickets_button', 'en')})$"), view_my_tickets),
    CallbackQueryHandler(show_ticket_details, pattern="^view_ticket_"),
    CallbackQueryHandler(close_ticket, pattern="^close_ticket_"),
    CallbackQueryHandler(back_to_support_menu, pattern="^back_to_support_menu$"),
]