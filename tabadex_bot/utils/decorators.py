# tabadex_bot/utils/decorators.py

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from ..config import settings
from ..locales import get_text

def admin_required(func):
    """
    A decorator to restrict access to handlers to admin users only.
    Checks if the update.effective_user.id is in the ADMIN_IDS set from config.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in settings.ADMIN_ID_SET:
            lang = context.user_data.get('lang', 'fa')
            # If it's a callback query, answer it to give feedback.
            if update.callback_query:
                await update.callback_query.answer(
                    text=get_text("error_not_authorized", lang),
                    show_alert=True
                )
            return  # Stop execution if not an admin
        
        # If the user is an admin, proceed with the actual handler.
        return await func(update, context, *args, **kwargs)
    return wrapped