# tabadex_bot/main.py

import asyncio
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, TypeHandler
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings, logger
from .database.session import AsyncSessionLocal, async_engine
from .database.models import Base
from .utils.swapzone_api import swapzone_api_client

# --- وارد کردن تمام هندلرها از سراسر پروژه ---

# هندلرهای اصلی و هسته
from .handlers.start_handler import start_handler, language_callback_handler
from .handlers.main_menu_handler import main_menu_handler
from .handlers.exchange_handler import exchange_handler

# هندلرهای بخش‌های کاربر
from .handlers.account_handler import (
    account_menu_handler, orders_list_handler, order_details_handler,
    addresses_list_handler, delete_address_handler, change_language_handler,
    add_address_conv_handler,
)
from .handlers.support_handler import (
    support_menu_handler, view_tickets_handler, view_ticket_details_handler,
    close_ticket_handler, create_ticket_conv, reply_ticket_conv,
)

# هندلرهای پنل مدیریت
from .handlers.admin.panel_handler import admin_panel_handler
from .handlers.admin.ticket_management import (
    admin_tickets_list_handler, admin_view_ticket_handler,
    admin_close_ticket_handler, admin_reply_conv,
)
from .handlers.admin.user_management import (
    user_management_handler, list_users_handler, view_user_handler,
    toggle_block_handler, search_user_conv,
)
from .handlers.admin.statistics import statistics_handler
from .handlers.admin.broadcast import broadcast_conv_handler
from .handlers.admin.settings_handler import settings_menu_handler, set_markup_conv


class DBSessionContext(ContextTypes.DEFAULT_TYPE):
    """کلاس سفارشی برای Context که سشن دیتابیس را نگهداری می‌کند."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db_session: AsyncSession | None = None

    @property
    def db_session(self) -> AsyncSession:
        if self._db_session is None:
            raise AttributeError("db_session is not set.")
        return self._db_session

    @db_session.setter
    def db_session(self, value: AsyncSession):
        self._db_session = value

async def db_middleware(update: Update, context: DBSessionContext):
    """میدلور برای تزریق سشن دیتابیس به context در هر آپدیت."""
    async with AsyncSessionLocal() as session:
        context.db_session = session

async def on_startup_tasks(app: Application):
    """وظایفی که هنگام روشن شدن ربات باید انجام شوند."""
    async with async_engine.begin() as conn:
        # این خط تمام جداول تعریف شده در models.py را در دیتابیس ایجاد می‌کند
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created or already exist.")
    
async def on_shutdown_tasks(app: Application):
    """وظایفی که هنگام خاموش شدن ربات باید انجام شوند."""
    await swapzone_api_client.close_session()
    logger.info("Bot shutdown tasks completed.")

def main() -> None:
    """نقطه ورود اصلی برنامه؛ ربات را راه‌اندازی و اجرا می‌کند."""
    logger.info("Starting Tabadex Bot...")
    context_types = ContextTypes(context=DBSessionContext)
    application = ApplicationBuilder().token(settings.BOT_TOKEN).context_types(context_types).build()
    
    # گروه 1-: این میدلور قبل از تمام هندلرها اجرا می‌شود
    application.add_handler(TypeHandler(Update, db_middleware), group=-1)

    # --- ثبت هندلرها ---
    # ترتیب ثبت هندلرها برای عملکرد صحیح ربات حیاتی است.

    # گروه 0: هندلرهای مکالمه (ConversationHandlers)
    # این‌ها بالاترین اولویت را دارند تا پیام‌ها را در حین یک مکالمه دریافت کنند.
    conversation_handlers = [
        exchange_handler, add_address_conv_handler, create_ticket_conv,
        reply_ticket_conv, admin_reply_conv, search_user_conv,
        broadcast_conv_handler, set_markup_conv,
    ]
    for handler in conversation_handlers:
        application.add_handler(handler, group=0)

    # گروه 1: هندلرهای اصلی ورود به بخش‌های مختلف
    entry_handlers = [
        start_handler, language_callback_handler, account_menu_handler,
        support_menu_handler, admin_panel_handler, user_management_handler,
        settings_menu_handler,
    ]
    for handler in entry_handlers:
        application.add_handler(handler, group=1)

    # گروه 2: هندلرهای کلیک‌های خاص در داخل هر بخش
    callback_handlers = [
        orders_list_handler, order_details_handler, addresses_list_handler,
        delete_address_handler, change_language_handler, view_tickets_handler,
        view_ticket_details_handler, close_ticket_handler, admin_tickets_list_handler,
        admin_view_ticket_handler, admin_close_ticket_handler, list_users_handler,
        view_user_handler, toggle_block_handler, statistics_handler,
    ]
    for handler in callback_handlers:
        application.add_handler(handler, group=2)

    # گروه 3: هندلر عمومی منوی اصلی
    # این هندلر در آخر قرار می‌گیرد تا اگر هیچکدام از کلیک‌های خاص بالا تطابق نداشت، اجرا شود.
    application.add_handler(main_menu_handler, group=3)

    logger.info("Bot is now polling for updates...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        on_startup=on_startup_tasks,
        on_shutdown=on_shutdown_tasks,
    )

if __name__ == "__main__":
    main()