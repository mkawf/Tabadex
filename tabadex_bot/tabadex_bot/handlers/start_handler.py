# tabadex_bot/handlers/start_handler.py

from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update as sql_update

from ..database.crud import get_or_create_user
from ..database.models import User
from ..keyboards import get_language_selection_keyboard, get_main_menu_keyboard
from ..locales import get_text
from ..config import settings

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command by asking for language selection."""
    await get_or_create_user(
        context.db_session,
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name
    )
    await update.message.reply_text(
        text=get_text("choose_language"),
        reply_markup=get_language_selection_keyboard()
    )

async def set_language_and_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the chosen language and displays the main menu with ReplyKeyboard."""
    query = update.callback_query
    await query.answer()
    lang_code = query.data.split('_')[-1]
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    
    stmt = sql_update(User).where(User.user_id == user_id).values(language_code=lang_code)
    await session.execute(stmt)
    await session.commit()
    context.user_data['lang'] = lang_code
    
    await query.message.delete()
    await show_main_menu(update, context, lang_code)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str | None = None):
    """Sends the main menu message with ReplyKeyboard."""
    lang = lang or context.user_data.get("lang", "fa")
    text = get_text("welcome_message", lang)
    is_admin = update.effective_user.id in settings.ADMIN_ID_SET
    keyboard = get_main_menu_keyboard(lang, is_admin)
    await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode='HTML')

# Handlers
start_handler = CommandHandler("start", start_command)
language_callback_handler = CallbackQueryHandler(set_language_and_show_menu, pattern=r'^set_lang_')