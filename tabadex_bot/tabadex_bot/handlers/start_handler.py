# tabadex_bot/handlers/start_handler.py
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update as sql_update
from ..database.crud import get_or_create_user
from ..database.models import User
from ..keyboards import get_language_selection_keyboard, get_main_menu_keyboard
from ..locales import get_text
from ..config import settings

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bilingual_prompt = "🌐 Please choose your preferred language:\n\n🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:"
    await update.message.reply_text(text=bilingual_prompt, reply_markup=get_language_selection_keyboard())

async def set_language_and_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_text = update.message.text
    lang_code = "fa" if "فارسی" in lang_text else "en"
    user_id = update.effective_user.id
    session: AsyncSession = context.db_session
    await get_or_create_user(session, user_id, update.effective_user.username, update.effective_user.first_name)
    stmt = sql_update(User).where(User.user_id == user_id).values(language_code=lang_code)
    await session.execute(stmt)
    await session.commit()
    context.user_data['lang'] = lang_code
    await show_main_menu(update, context, lang_code)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str = None):
    lang = lang or context.user_data.get("lang", "fa")
    text = get_text("welcome_message", lang)
    is_admin = update.effective_user.id in settings.ADMIN_ID_SET
    keyboard = get_main_menu_keyboard(lang, is_admin)
    await update.effective_message.reply_text(text, reply_markup=keyboard, parse_mode='HTML')

start_handler = CommandHandler("start", start_command)
language_handler = MessageHandler(filters.Text(["🇮🇷 فارسی (Persian)", "🇬🇧 English"]), set_language_and_show_menu)