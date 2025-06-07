import logging
import os
import traceback
import html
import json
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

from tabadex_bot.db.database import init_db, get_or_create_user
from tabadex_bot.handlers.start_handler import start
from tabadex_bot.handlers.account_handler import add_address_conv_handler
from tabadex_bot.handlers.support_handler import support_handler, create_ticket_conv, reply_ticket_conv
from tabadex_bot.handlers.admin.user_management import search_user_conv
from tabadex_bot.handlers.admin.ticket_management import admin_reply_conv, ticket_management_handler
from tabadex_bot.handlers.admin.broadcast import broadcast_conv_handler
from tabadex_bot.handlers.admin.settings_handler import set_markup_conv, settings_handler
from tabadex_bot.handlers.exchange_handler import exchange_handler
from tabadex_bot.config import setup_logging, setup_scheduler, DEVELOPER_CHAT_ID

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)

# --- Global Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    if DEVELOPER_CHAT_ID:
        await context.bot.send_message(
            chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML
        )
    
    # Optionally, send a generic message to the user
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="متاسفانه خطایی در ربات رخ داده است. این موضوع به پشتیبانی گزارش شد. لطفاً دوباره تلاش کنید."
        )


async def post_init(application: Application) -> None:
    """
    Function to run after the bot has been initialized.
    It creates the database tables and starts the scheduler.
    """
    await init_db()
    await get_or_create_user(int(os.getenv("ADMIN_ID")), is_admin=True)
    logger.info("Database tables created and bot started.")
    
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    
    # Set bot commands
    commands = [
        ("start", "شروع مجدد ربات"),
        ("exchange", "شروع فرآیند تبادل"),
        ("account", "مدیریت حساب کاربری"),
        ("support", "ارتباط با پشتیبانی"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Start the bot."""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN is not set in the environment variables.")
        return
    
    application = Application.builder().token(bot_token).post_init(post_init).build()

    # --- Add Error Handler ---
    application.add_error_handler(error_handler)

    # --- Conversation Handlers ---
    application.add_handler(add_address_conv_handler)
    application.add_handler(create_ticket_conv)
    application.add_handler(reply_ticket_conv)
    application.add_handler(search_user_conv)
    application.add_handler(admin_reply_conv)
    application.add_handler(broadcast_conv_handler)
    application.add_handler(set_markup_conv)
    application.add_handler(exchange_handler)

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("support", support_handler))
    application.add_handler(CommandHandler("ticket_management", ticket_management_handler))
    application.add_handler(CommandHandler("settings", settings_handler))

    # --- Message Handlers for commands ---
    application.add_handler(MessageHandler(filters.Regex(r'^🚀 شروع تبادل$'), start))
    application.add_handler(MessageHandler(filters.Regex(r'^👤 حساب کاربری$'), start))
    application.add_handler(MessageHandler(filters.Regex(r'^📞 پشتیبانی$'), support_handler))
    application.add_handler(MessageHandler(filters.Regex(r'^⚙️ پنل مدیریت$'), start))

    logger.info("Bot is now polling for updates...")
    application.run_polling()

if __name__ == '__main__':
    main()