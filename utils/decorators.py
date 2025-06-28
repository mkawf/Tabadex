# tabadex_bot/utils/decorators.py

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from ..config import settings
from ..locales import get_text

def admin_required(func):
    """
    دکوریتوری برای محدود کردن دسترسی به هندلرها فقط برای کاربران ادمین.
    این دکوریتور بررسی می‌کند که آیا آیدی کاربر در لیست ADMIN_IDS تعریف شده در کانفیگ وجود دارد یا خیر.
    """
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in settings.ADMIN_ID_SET:
            lang = context.user_data.get('lang', 'fa')
            # اگر آپدیت از نوع کلیک روی دکمه بود، با یک پیام به آن پاسخ می‌دهیم
            if update.callback_query:
                await update.callback_query.answer(
                    text=get_text("error_not_authorized", lang),
                    show_alert=True
                )
            # اجرای هندلر اصلی را متوقف می‌کنیم
            return
        
        # اگر کاربر ادمین بود، هندلر اصلی را اجرا می‌کنیم
        return await func(update, context, *args, **kwargs)
    return wrapped