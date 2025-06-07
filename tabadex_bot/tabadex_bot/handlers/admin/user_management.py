# tabadex_bot/handlers/admin/user_management.py

import math
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from ...locales import get_text
from ...database import crud
from ...keyboards import (
    get_admin_user_management_keyboard,
    get_admin_users_list_keyboard,
    get_admin_user_details_keyboard,
    get_cancel_keyboard
)
from ...utils.decorators import admin_required

USERS_PER_PAGE = 10
SEARCH_GET_ID = range(40, 41)

@admin_required
async def show_user_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    await update.message.reply_text(
        text=get_text("admin_user_management_title", lang),
        reply_markup=get_admin_user_management_keyboard(lang)
    )
    await update.message.reply_text("...", reply_markup=ReplyKeyboardRemove())

@admin_required
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    page = 1
    if update.callback_query:
        await update.callback_query.answer()
        page = int(update.callback_query.data.split("_")[-1])
    
    total_users = await crud.get_total_user_count(session)
    total_pages = math.ceil(total_users / USERS_PER_PAGE)
    users = await crud.get_users_paginated(session, page=page, limit=USERS_PER_PAGE)

    text = get_text("admin_users_list_title", lang).format(page=page, total_pages=total_pages)
    keyboard = get_admin_users_list_keyboard(users, lang, page, total_pages)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@admin_required
async def view_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_from_search: int = None):
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    user_id = user_id_from_search
    if not user_id and update.callback_query:
        await update.callback_query.answer()
        user_id = int(update.callback_query.data.split("_")[-1])

    user = await crud.get_user_by_user_id(session, user_id)
    if not user:
        text = get_text("admin_user_not_found", lang)
        if update.callback_query: await update.callback_query.edit_message_text(text)
        else: await update.effective_message.reply_text(text)
        return

    status = get_text("user_status_blocked", lang) if user.is_blocked else get_text("user_status_active", lang)
    text = get_text("admin_user_details_format", lang).format(
        user_id=user.user_id,
        username=f"@{user.username}" if user.username else "N/A",
        first_name=user.first_name,
        created_at=user.created_at.strftime('%Y-%m-%d %H:%M'),
        status=status
    )
    keyboard = get_admin_user_details_keyboard(lang, user.user_id, user.is_blocked)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

@admin_required
async def toggle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session: AsyncSession = context.db_session
    parts = query.data.split("_")
    action = parts[1]
    user_id = int(parts[2])
    await crud.update_user_block_status(session, user_id, is_blocked=(action == "block"))
    await view_user_details(update, context)

@admin_required
async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    await query.edit_message_text(
        text=get_text("admin_enter_user_id_prompt", lang),
        reply_markup=get_cancel_keyboard(lang, "admin_search_user_cancel")
    )
    return SEARCH_GET_ID

async def search_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "fa")
    try:
        user_id = int(update.message.text)
        await view_user_details(update, context, user_id_from_search=user_id)
    except (ValueError, TypeError):
        await update.message.reply_text(get_text("error_invalid_user_id", lang))
        return SEARCH_GET_ID
    
    return ConversationHandler.END

async def search_user_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Cancelled.")
    return ConversationHandler.END

search_user_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(search_user_start, pattern="^admin_search_user_start$")],
    states={SEARCH_GET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_id)]},
    fallbacks=[CallbackQueryHandler(search_user_cancel, pattern="^admin_search_user_cancel$")]
)

admin_user_handlers = [
    CallbackQueryHandler(list_users, pattern="^admin_users_list_"),
    CallbackQueryHandler(view_user_details, pattern="^admin_view_user_"),
    CallbackQueryHandler(toggle_block_user, pattern="^admin_(un)?block_"),
]