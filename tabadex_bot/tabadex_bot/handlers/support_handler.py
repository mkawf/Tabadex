# tabadex_bot/handlers/support_handler.py

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
from ..database import crud, models
from ..keyboards import (
    get_support_main_menu_keyboard,
    get_support_topics_keyboard,
    get_user_tickets_keyboard,
    get_ticket_view_keyboard,
    get_cancel_keyboard,
)

# Conversation states for creating a new ticket
GET_TOPIC, GET_MESSAGE = range(20, 22)
# Conversation state for replying to a ticket
GET_REPLY_MESSAGE = range(22, 23)


# --- Main Support Menu ---
async def support_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the main support menu."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    text = get_text("support_menu_title", lang)
    keyboard = get_support_main_menu_keyboard(lang)
    await query.edit_message_text(text, reply_markup=keyboard)


# --- View Tickets Flow ---
async def show_user_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a list of the user's tickets."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session

    tickets = await crud.get_tickets_by_user(session, user_id)

    if not tickets:
        text = get_text("support_no_tickets", lang)
    else:
        text = get_text("my_tickets_title", lang)
    
    keyboard = get_user_tickets_keyboard(tickets, lang)
    await query.edit_message_text(text, reply_markup=keyboard)


async def show_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_id: int = 0):
    """Shows the full conversation of a single ticket."""
    query = update.callback_query
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    
    # Can be called from a callback or after a reply
    if query:
        await query.answer()
        ticket_id = int(query.data.split("_")[-1])

    ticket = await crud.get_ticket_with_messages(session, ticket_id, user_id)
    if not ticket:
        await query.answer(get_text("error_generic", lang), show_alert=True)
        return

    message_text = f"<b>{get_text('ticket_details_title', lang)} #{ticket.id}</b>\n"
    message_text += f"<i>{get_text('topic_title', lang)}: {ticket.title}</i>\n"
    message_text += "---"
    for msg in ticket.messages:
        sender = "You" if not msg.is_admin_response else "Support"
        message_text += f"\n\n<b>{sender}</b> ({msg.created_at.strftime('%Y-%m-%d %H:%M')}):\n{msg.text}"
    
    keyboard = get_ticket_view_keyboard(lang, ticket.id, ticket.status)
    
    if query:
        await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else: # If called after a reply (no query)
        await context.bot.send_message(user_id, message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


# --- Create Ticket Conversation ---
async def create_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts creating a new ticket, asks for a topic."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    text = get_text("support_select_topic", lang)
    keyboard = get_support_topics_keyboard(lang)
    await query.edit_message_text(text, reply_markup=keyboard)
    return GET_TOPIC

async def get_ticket_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gets the topic and asks for the user's message."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    topic_key = "_".join(query.data.split("_")[3:])
    topic_text = get_text(f"topic_{topic_key}", lang)
    context.user_data['new_ticket_title'] = topic_text
    
    text = get_text("support_enter_message", lang)
    keyboard = get_cancel_keyboard(lang, "support_cancel_creation")
    await query.edit_message_text(text, reply_markup=keyboard)
    return GET_MESSAGE

async def get_ticket_message_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the new ticket to the database."""
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    
    title = context.user_data.pop('new_ticket_title')
    message = update.message.text
    
    new_ticket = await crud.create_ticket(session, user_id, title, message)
    
    text = get_text("support_ticket_created", lang).format(ticket_id=new_ticket.id)
    await update.message.reply_text(text)
    
    # TODO: Notify admins about the new ticket
    
    await show_user_tickets(update, context) # Show the list with the new ticket
    return ConversationHandler.END

async def cancel_ticket_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the ticket creation process."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop('new_ticket_title', None)
    await support_main_menu(update, context) # Go back to support menu
    return ConversationHandler.END


# --- Reply To Ticket Conversation ---
async def reply_to_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the reply process."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    ticket_id = int(query.data.split("_")[-1])
    context.user_data['reply_ticket_id'] = ticket_id

    text = get_text("reply_prompt", lang)
    keyboard = get_cancel_keyboard(lang, f"support_cancel_reply_{ticket_id}")
    await query.edit_message_text(text, reply_markup=keyboard)
    return GET_REPLY_MESSAGE

async def get_reply_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the user's reply to the database."""
    session: AsyncSession = context.db_session
    user_id = update.effective_user.id
    ticket_id = context.user_data.pop('reply_ticket_id')
    reply_text = update.message.text

    await crud.add_reply_to_ticket(session, ticket_id, user_id, reply_text, is_admin=False)
    
    # Show the updated ticket details
    await show_ticket_details(update, context, ticket_id=ticket_id)
    return ConversationHandler.END

async def cancel_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the reply process."""
    query = update.callback_query
    context.user_data.pop('reply_ticket_id', None)
    await show_ticket_details(update, context) # Go back to the ticket view
    return ConversationHandler.END

# --- Other Handlers ---
async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows a user to close their own ticket."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    ticket_id = int(query.data.split("_")[-1])

    success = await crud.close_ticket_by_user(session, ticket_id, user_id)
    if success:
        await query.answer(get_text("support_ticket_closed_success", lang), show_alert=True)
        await show_ticket_details(update, context)
    else:
        await query.answer(get_text("error_generic", lang), show_alert=True)


# --- Handler Definitions ---

# Main entry point for the /support command or callback
support_menu_handler = CallbackQueryHandler(support_main_menu, pattern="^main_support$|^support_main_menu$")

# Handlers for viewing tickets
view_tickets_handler = CallbackQueryHandler(show_user_tickets, pattern="^support_view_list$")
view_ticket_details_handler = CallbackQueryHandler(show_ticket_details, pattern="^support_view_ticket_")
close_ticket_handler = CallbackQueryHandler(close_ticket, pattern="^support_close_")

# Conversation for creating a new ticket
create_ticket_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_ticket_start, pattern="^support_create_start$")],
    states={
        GET_TOPIC: [CallbackQueryHandler(get_ticket_topic, pattern="^support_create_topic_")],
        GET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ticket_message_and_save)],
    },
    fallbacks=[CallbackQueryHandler(cancel_ticket_creation, pattern="^support_cancel_creation$")],
)

# Conversation for replying to an existing ticket
reply_ticket_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(reply_to_ticket_start, pattern="^support_reply_start_")],
    states={
        GET_REPLY_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_reply_and_save)],
    },
    fallbacks=[CallbackQueryHandler(cancel_reply, pattern="^support_cancel_reply_")],
)