# tabadex_bot/handlers/admin/broadcast.py

import asyncio
from telegram import Update, Message
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import Forbidden, TelegramError
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import logger
from ...locales import get_text
from ...database import crud
from ...keyboards import get_admin_broadcast_confirm_keyboard, get_cancel_keyboard
from ...utils.decorators import admin_required
from .panel_handler import admin_panel

# Conversation states
GET_MESSAGE, CONFIRM_BROADCAST = range(50, 52)

async def _do_send_broadcast(
    app: Application,
    admin_id: int,
    message_to_send: Message,
    target_user_ids: list[int],
    lang: str,
):
    """The actual background task for sending messages."""
    success_count = 0
    failure_count = 0
    
    # Send a starting message to the admin
    await app.bot.send_message(
        admin_id,
        get_text("broadcast_started", lang).format(user_count=len(target_user_ids))
    )
    
    for user_id in target_user_ids:
        try:
            # We use copy_message to forward any type of message with formatting
            await app.bot.copy_message(
                chat_id=user_id,
                from_chat_id=message_to_send.chat_id,
                message_id=message_to_send.message_id
            )
            success_count += 1
        except Forbidden:
            # User has blocked the bot
            logger.warning(f"Broadcast failed for user {user_id}: Bot was blocked.")
            failure_count += 1
        except TelegramError as e:
            # Other Telegram errors
            logger.error(f"Broadcast failed for user {user_id}: {e}")
            failure_count += 1
        
        # Rate limit: 20 messages per second
        await asyncio.sleep(0.05)
        
    # Send final report to admin
    await app.bot.send_message(
        admin_id,
        get_text("broadcast_finished", lang).format(
            success_count=success_count,
            failure_count=failure_count
        )
    )

@admin_required
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the broadcast conversation."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    text = get_text("admin_broadcast_prompt", lang)
    keyboard = get_cancel_keyboard(lang, "admin_broadcast_cancel")
    await query.edit_message_text(text, reply_markup=keyboard)
    
    return GET_MESSAGE

@admin_required
async def get_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the message to broadcast and asks for confirmation."""
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    
    # Store the message object to be copied later
    context.user_data['broadcast_message'] = update.message
    
    # Get user count for the confirmation message
    user_ids = await crud.get_all_active_user_ids(session)
    user_count = len(user_ids)
    context.user_data['broadcast_user_ids'] = user_ids
    
    # Show a preview to the admin
    text = get_text("admin_broadcast_confirm_prompt", lang).format(user_count=user_count)
    await update.message.reply_text("👇 " + get_text("preview_title", lang) + " 👇")
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )
    await update.message.reply_text(
        text=text,
        reply_markup=get_admin_broadcast_confirm_keyboard(lang)
    )
    
    return CONFIRM_BROADCAST

@admin_required
async def confirm_and_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirms and starts the background task for sending the broadcast."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    message_to_send = context.user_data.get('broadcast_message')
    user_ids = context.user_data.get('broadcast_user_ids')
    
    if not message_to_send or not user_ids:
        await query.edit_message_text(get_text("error_broadcast_expired", lang))
        return ConversationHandler.END
        
    await query.edit_message_text(get_text("admin_broadcast_sending", lang))
    
    # Start the sending task in the background
    context.application.create_task(
        _do_send_broadcast(
            app=context.application,
            admin_id=update.effective_user.id,
            message_to_send=message_to_send,
            target_user_ids=user_ids,
            lang=lang,
        )
    )
    
    # Clean up context
    context.user_data.pop('broadcast_message', None)
    context.user_data.pop('broadcast_user_ids', None)
    
    return ConversationHandler.END

@admin_required
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the broadcast conversation."""
    query = update.callback_query
    await query.answer()
    
    # Clean up context
    context.user_data.pop('broadcast_message', None)
    context.user_data.pop('broadcast_user_ids', None)
    
    await query.edit_message_text(get_text("admin_broadcast_canceled", lang))
    
    # Go back to admin panel
    await admin_panel(update, context)
    return ConversationHandler.END


# Define the handler
broadcast_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(broadcast_start, pattern="^admin_broadcast_start$")],
    states={
        GET_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, get_broadcast_message)],
        CONFIRM_BROADCAST: [CallbackQueryHandler(confirm_and_send_broadcast, pattern="^admin_broadcast_confirm$")],
    },
    fallbacks=[CallbackQueryHandler(cancel_broadcast, pattern="^admin_broadcast_cancel$")],
)