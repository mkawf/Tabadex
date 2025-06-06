# tabadex_bot/handlers/admin/user_management.py

import math
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
from ...database import crud
from ...keyboards import (
    get_admin_user_management_keyboard,
    get_admin_users_list_keyboard,
    get_admin_user_details_keyboard,
    get_cancel_keyboard,
)
from ...utils.decorators import admin_required
from .panel_handler import admin_panel

# Constants
USERS_PER_PAGE = 10

# Conversation states for user search
SEARCH_GET_ID = range(40, 41)

# --- Main User Management Menu ---
@admin_required
async def user_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main user management menu."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    
    text = get_text("admin_user_management_title", lang)
    keyboard = get_admin_user_management_keyboard(lang)
    await query.edit_message_text(text, reply_markup=keyboard)


# --- List and View Users ---
@admin_required
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a paginated list of all users."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    page = int(query.data.split("_")[-1])

    total_users = await crud.get_total_user_count(session)
    total_pages = math.ceil(total_users / USERS_PER_PAGE)
    users = await crud.get_users_paginated(session, page=page, limit=USERS_PER_PAGE)

    text = get_text("admin_users_list_title", lang).format(page=page, total_pages=total_pages)
    keyboard = get_admin_users_list_keyboard(users, lang, page, total_pages)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


async def view_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_from_search: int = None):
    """Displays details for a single user and provides actions."""
    query = update.callback_query
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session
    
    if user_id_from_search:
        user_id = user_id_from_search
    else:
        await query.answer()
        user_id = int(query.data.split("_")[-1])

    user = await crud.get_user_by_user_id(session, user_id)
    if not user:
        if query:
            await query.edit_message_text(get_text("admin_user_not_found", lang))
        else:
            await update.effective_message.reply_text(get_text("admin_user_not_found", lang))
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
    
    if query:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)


# --- Block/Unblock User ---
@admin_required
async def toggle_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles blocking or unblocking a user."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    session: AsyncSession = context.db_session

    parts = query.data.split("_")
    action = parts[1] # "block" or "unblock"
    user_id = int(parts[2])
    
    is_blocked = True if action == "block" else False
    await crud.update_user_block_status(session, user_id, is_blocked)
    
    # Refresh the user details view
    await view_user_details(update, context)


# --- Search User Conversation ---
@admin_required
async def search_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the user search conversation."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "fa")
    text = get_text("admin_enter_user_id_prompt", lang)
    keyboard = get_cancel_keyboard(lang, "admin_search_user_cancel")
    await query.edit_message_text(text, reply_markup=keyboard)
    return SEARCH_GET_ID

async def search_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the user ID and shows the user's details."""
    lang = context.user_data.get("lang", "fa")
    try:
        user_id = int(update.message.text)
        await view_user_details(update, context, user_id_from_search=user_id)
        return ConversationHandler.END
    except (ValueError, TypeError):
        await update.message.reply_text(get_text("error_invalid_user_id", lang))
        return SEARCH_GET_ID

async def search_user_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the user search."""
    query = update.callback_query
    await query.answer()
    await user_management_menu(update, context)
    return ConversationHandler.END

# --- Handler Definitions ---
user_management_handler = CallbackQueryHandler(user_management_menu, pattern="^admin_users_main$")
list_users_handler = CallbackQueryHandler(list_users, pattern="^admin_users_list_")
view_user_handler = CallbackQueryHandler(view_user_details, pattern="^admin_view_user_")
toggle_block_handler = CallbackQueryHandler(toggle_block_user, pattern="^admin_(un)?block_")

search_user_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(search_user_start, pattern="^admin_search_user_start$")],
    states={SEARCH_GET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_get_id)]},
    fallbacks=[CallbackQueryHandler(search_user_cancel, pattern="^admin_search_user_cancel$")]
)