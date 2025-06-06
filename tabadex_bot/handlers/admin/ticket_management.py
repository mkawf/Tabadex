# tabadex_bot/handlers/admin/ticket_management.py

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

from ...locales import get_text
from ...database import crud, models
from ...keyboards import get_admin_tickets_keyboard, get_admin_ticket_view_keyboard, get_cancel_keyboard
from ...utils.decorators import admin_required
from .panel_handler import admin_panel

# Conversation state for replying to a ticket
ADMIN_GET_REPLY = range(30, 31)

@admin_required
async def show_admin_tickets_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a list of open tickets for admins."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session

    # Fetch tickets that need attention (answered by user or new)
    tickets = await crud.get_all_tickets_by_status(session, [models.TicketStatus.PENDING_USER_REPLY, models.TicketStatus.OPEN])
    
    if not tickets:
        text = get_text("admin_no_open_tickets", lang)
    else:
        text = get_text("admin_tickets_title", lang)
    
    keyboard = get_admin_tickets_keyboard(tickets, lang)
    await query.edit_message_text(text, reply_markup=keyboard)


@admin_required
async def show_admin_ticket_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the full conversation of a ticket to an admin."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    ticket_id = int(query.data.split("_")[-1])

    ticket = await crud.get_ticket_by_id_for_admin(session, ticket_id)
    if not ticket:
        await query.answer(get_text("error_generic", lang), show_alert=True)
        return

    message_text = f"<b>Ticket #{ticket.id} - User: {ticket.user_id}</b>\n"
    message_text += f"<i>Topic: {ticket.title}</i>\n---"
    for msg in ticket.messages:
        sender = f"Admin ({msg.sender_id})" if msg.is_admin_response else f"User ({msg.sender_id})"
        message_text += f"\n\n<b>{sender}</b> ({msg.created_at.strftime('%Y-%m-%d %H:%M')}):\n{msg.text}"
    
    keyboard = get_admin_ticket_view_keyboard(lang, ticket.id, ticket.status)
    await query.edit_message_text(message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


@admin_required
async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the admin reply process."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    ticket_id = int(query.data.split("_")[-1])
    context.user_data['admin_reply_ticket_id'] = ticket_id

    text = get_text("admin_reply_prompt", lang)
    keyboard = get_cancel_keyboard(lang, f"admin_cancel_reply_{ticket_id}")
    await query.edit_message_text(text, reply_markup=keyboard)
    return ADMIN_GET_REPLY

async def get_admin_reply_and_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the admin's reply and notifies the user."""
    session: AsyncSession = context.db_session
    admin_id = update.effective_user.id
    lang = context.user_data.get("lang", "fa")
    ticket_id = context.user_data.pop('admin_reply_ticket_id')
    reply_text = update.message.text

    ticket = await crud.get_ticket_by_id_for_admin(session, ticket_id)
    if not ticket:
        await update.message.reply_text("Error: Ticket not found.")
        return ConversationHandler.END

    await crud.add_reply_to_ticket(session, ticket_id, admin_id, reply_text, is_admin=True)
    await update.message.reply_text(get_text("admin_reply_sent_success", lang))
    
    # Notify the user
    user_lang = ticket.user.language_code
    notification_text = get_text("user_notification_new_reply", user_lang).format(ticket_id=ticket_id)
    # You might want to add a keyboard to this notification
    try:
        await context.bot.send_message(chat_id=ticket.user_id, text=notification_text)
    except Exception as e:
        logger.error(f"Failed to send notification to user {ticket.user_id}: {e}")

    # Return admin to the ticket list
    await show_admin_tickets_list(update, context)
    return ConversationHandler.END

async def admin_cancel_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the admin reply process."""
    # This function needs to be implemented. For now, it just ends.
    await update.callback_query.edit_message_text("Canceled.")
    return ConversationHandler.END

@admin_required
async def admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows an admin to close any ticket."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    ticket_id = int(query.data.split("_")[-1])

    success = await crud.close_ticket_by_admin(session, ticket_id)
    if success:
        await query.answer("Ticket closed!", show_alert=True)
        # Refresh ticket list for admin
        await show_admin_tickets_list(update, context)
    else:
        await query.answer("Error closing ticket.", show_alert=True)


# --- Handler Definitions ---
admin_tickets_list_handler = CallbackQueryHandler(show_admin_tickets_list, pattern="^admin_tickets_main$")
admin_view_ticket_handler = CallbackQueryHandler(show_admin_ticket_details, pattern="^admin_view_ticket_")
admin_close_ticket_handler = CallbackQueryHandler(admin_close_ticket, pattern="^admin_close_ticket_")

admin_reply_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_reply_start, pattern="^admin_reply_start_")],
    states={
        ADMIN_GET_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_admin_reply_and_save)],
    },
    fallbacks=[CallbackQueryHandler(admin_cancel_reply, pattern="^admin_cancel_reply_")],
)