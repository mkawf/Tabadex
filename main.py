# tabadex_bot/main.py

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, TypeHandler
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings, logger
from .database.session import AsyncSessionLocal, async_engine
from .database.models import Base
from .utils.swapzone_api import swapzone_api_client

# --- Import All Handlers with correct names ---
from .handlers.start_handler import start_handler, language_handler
from .handlers.menu_handler import menu_handler
from .handlers.exchange_handler import exchange_handler
from .handlers.account_handler import add_address_conv_handler, account_handlers
from .handlers.support_handler import create_ticket_conv, reply_ticket_conv, support_handlers
from .handlers.admin.panel_handler import admin_panel_callback_handler, admin_panel_entry_handler
from .handlers.admin.ticket_management import admin_reply_conv, admin_ticket_handlers
from .handlers.admin.user_management import search_user_conv, admin_user_handlers
from .handlers.admin.broadcast import broadcast_conv_handler
from .handlers.admin.settings_handler import set_markup_conv, admin_settings_handlers

class DBSessionContext(ContextTypes.DEFAULT_TYPE):
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
    async with AsyncSessionLocal() as session:
        context.db_session = session

async def on_startup(app: Application):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created and bot started.")

async def on_shutdown(app: Application):
    await swapzone_api_client.close_session()
    logger.info("Bot shutdown tasks completed.")

def main() -> None:
    context_types = ContextTypes(context=DBSessionContext)
    application = (
        ApplicationBuilder().token(settings.BOT_TOKEN).context_types(context_types)
        .post_init(on_startup).post_shutdown(on_shutdown).build()
    )
    
    application.add_handler(TypeHandler(Update, db_middleware), group=-1)

    # Conversation Handlers
    conv_handlers = [
        exchange_handler, add_address_conv_handler, create_ticket_conv,
        reply_ticket_conv, admin_reply_conv, search_user_conv,
        broadcast_conv_handler, set_markup_conv
    ]
    application.add_handlers(conv_handlers)

    # Command & Basic Handlers
    application.add_handler(start_handler)
    application.add_handler(language_handler)

    # All other CallbackQueryHandlers and MessageHandlers from submenus
    all_other_handlers = [
        *account_handlers, *support_handlers,
        admin_panel_callback_handler, admin_panel_entry_handler,
        *admin_ticket_handlers, *admin_user_handlers, *admin_settings_handlers
    ]
    application.add_handlers(all_other_handlers)

    # Central Menu Router (must be one of the last handlers)
    application.add_handler(menu_handler)
    
    logger.info("Bot is now polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
