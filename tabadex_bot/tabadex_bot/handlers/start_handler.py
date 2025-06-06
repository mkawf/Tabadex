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
    """Handles the /start command."""
    user = update.effective_user
    session: AsyncSession = context.db_session
    
    db_user = await get_or_create_user(session, user.id, user.username, user.first_name)
    
    # Store user language in context for easy access
    context.user_data['lang'] = db_user.language_code
    
    # اگر کاربر از قبل زبان را انتخاب کرده، مستقیما منوی اصلی را نشان بده
    await show_main_menu(update, context)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles language selection from the callback query."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split('_')[-1]
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session

    stmt = sql_update(User).where(User.user_id == user_id).values(language_code=lang_code)
    await session.execute(stmt)
    await session.commit()
    
    context.user_data['lang'] = lang_code
    
    await show_main_menu(update, context, is_edit=True)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = False):
    """
    Displays the main menu.
    If the user has not selected a language, it prompts them to.
    """
    lang = context.user_data.get("lang")
    
    # اگر زبان کاربر در context یا دیتابیس موجود نیست، ابتدا درخواست انتخاب زبان کن
    if not lang:
        text = get_text("choose_language")
        keyboard = get_language_selection_keyboard()
        await update.message.reply_text(text, reply_markup=keyboard)
        return

    is_admin = update.effective_user.id in settings.ADMIN_ID_SET
    text = get_text("welcome_message", lang)
    keyboard = get_main_menu_keyboard(lang, is_admin)
    
    # اگر is_edit=True باشد و آپدیت از نوع کلیک باشد، پیام را ویرایش کن
    if is_edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
    # در غیر این صورت (مثلا بعد از /start یا لغو مکالمه)، پیام جدید بفرست
    else:
        await context.bot.send_message(update.effective_chat.id, text, reply_markup=keyboard, parse_mode='HTML')

# Define handlers
start_handler = CommandHandler("start", start_command)
language_callback_handler = CallbackQueryHandler(set_language, pattern=r'^set_lang_')