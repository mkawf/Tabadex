# tabadex_bot/handlers/admin/broadcast.py

import asyncio
from telegram import Update, Message, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import logger
from ...locales import get_text
from ...database import crud
from ...keyboards import get_admin_broadcast_confirm_keyboard, get_cancel_keyboard
from ...utils.decorators import admin_required
# from .panel_handler import admin_panel  # <<<--- این خط حذف می‌شود تا چرخه شکسته شود

# Conversation states
GET_MESSAGE, CONFIRM_BROADCAST = range(50, 52)

@admin_required
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the broadcast conversation."""
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        get_text("admin_broadcast_prompt", lang),
        reply_markup=get_cancel_keyboard(lang, "admin_broadcast_cancel")
    )
    await update.message.reply_text("...", reply_markup=ReplyKeyboardRemove())
    return GET_MESSAGE

# ... (تمام توابع دیگر این فایل مانند _do_send_broadcast, get_broadcast_message و ... بدون تغییر باقی می‌مانند)
async def _do_send_broadcast(app: Application, admin_id: int, message_to_send: Message, target_user_ids: list[int], lang: str):
    success_count, failure_count = 0, 0
    await app.bot.send_message(admin_id, get_text("broadcast_started", lang).format(user_count=len(target_user_ids)))
    for user_id in target_user_ids:
        try:
            await app.bot.copy_message(chat_id=user_id, from_chat_id=message_to_send.chat_id, message_id=message_to_send.message_id)
            success_count += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for user {user_id}: {e}")
            failure_count += 1
        await asyncio.sleep(0.05)
    await app.bot.send_message(admin_id, get_text("broadcast_finished", lang).format(success_count=success_count, failure_count=failure_count))

async def get_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    context.user_data['broadcast_message'] = update.message
    user_ids = await crud.get_all_active_user_ids(session)
    context.user_data['broadcast_user_ids'] = user_ids
    text = get_text("admin_broadcast_confirm_prompt", lang).format(user_count=len(user_ids))
    await update.message.reply_text("👇 " + get_text("preview_title", lang) + " 👇")
    await context.bot.copy_message(chat_id=update.effective_chat.id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
    await update.message.reply_text(text=text, reply_markup=get_admin_broadcast_confirm_keyboard(lang))
    return CONFIRM_BROADCAST

async def confirm_and_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    message_to_send = context.user_data.get('broadcast_message')
    user_ids = context.user_data.get('broadcast_user_ids')
    if not message_to_send or not user_ids:
        await query.edit_message_text(get_text("error_broadcast_expired", lang))
        return ConversationHandler.END
    await query.edit_message_text(get_text("admin_broadcast_sending", lang))
    context.application.create_task(_do_send_broadcast(app=context.application, admin_id=update.effective_user.id, message_to_send=message_to_send, target_user_ids=user_ids, lang=lang))
    context.user_data.pop('broadcast_message', None)
    context.user_data.pop('broadcast_user_ids', None)
    return ConversationHandler.END

@admin_required
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the broadcast conversation."""
    # --- <<< تغییر اصلی و حیاتی اینجاست >>> ---
    # واردات محلی برای شکستن چرخه
    from .panel_handler import show_admin_panel
    
    query = update.callback_query
    await query.answer()
    context.user_data.pop('broadcast_message', None)
    context.user_data.pop('broadcast_user_ids', None)
    await query.edit_message_text(get_text("admin_broadcast_canceled", lang=context.user_data.get("lang", "fa")))
    
    # بازگشت به منوی ادمین
    await show_admin_panel(update.callback_query, context) # Use callback_query here
    return ConversationHandler.END

# Handlers
broadcast_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(f"^({get_text('admin_broadcast', 'fa')}|{get_text('admin_broadcast', 'en')})$"), broadcast_start)],
    states={
        GET_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, get_broadcast_message)],
        CONFIRM_BROADCAST: [CallbackQueryHandler(confirm_and_send_broadcast, pattern="^confirm_broadcast$")],
    },
    fallbacks=[CallbackQueryHandler(cancel_broadcast, pattern="^admin_broadcast_cancel$")],
)