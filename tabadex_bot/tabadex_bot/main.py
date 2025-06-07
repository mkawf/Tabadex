# tabadex_bot/main.py
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, TypeHandler
from .config import settings, logger
from .database.session import AsyncSessionLocal, async_engine
from .database.models import Base
from .utils.swapzone_api import swapzone_api_client
from .handlers.start_handler import start_handler, language_handler
from .handlers.menu_handler import menu_handler
from .handlers.exchange_handler import exchange_handler
from .handlers.account_handler import account_handlers, add_address_conv_handler
from .handlers.support_handler import support_handlers, create_ticket_conv, reply_ticket_conv
from .handlers.admin_handler import admin_handlers, admin_conv_handlers

class DBSessionContext(ContextTypes.DEFAULT_TYPE):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db_session: AsyncSession | None = None
    @property
    def db_session(self) -> AsyncSession:
        if self._db_session is None: raise AttributeError("db_session is not set.")
        return self._db_session
    @db_session.setter
    def db_session(self, value: AsyncSession): self._db_session = value

async def db_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with AsyncSessionLocal() as session: context.db_session = session

async def on_startup(app: Application):
    async with async_engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
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

    # Register all handlers
    application.add_handler(start_handler)
    application.add_handler(language_handler)
    
    # Conversation Handlers
    application.add_handler(exchange_handler)
    application.add_handler(add_address_conv_handler)
    application.add_handler(create_ticket_conv)
    application.add_handler(reply_ticket_conv)
    application.add_handlers(admin_conv_handlers)

    # Callback and Message Handlers
    application.add_handlers(account_handlers)
    application.add_handlers(support_handlers)
    application.add_handlers(admin_handlers)
    
    # Main menu router must be last
    application.add_handler(menu_handler)
    
    logger.info("Bot is now polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()