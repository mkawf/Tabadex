# tabadex_bot/handlers/base_handler.py
from telegram.ext import ContextTypes, Application
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import crud
from ..locales import get_text

class BaseHandler:
    def __init__(self, application: Application):
        self.application = application
        self.db_session: AsyncSession = None
        self.lang = "fa"
        self.user_id = 0

    @classmethod
    def register(cls, application: Application):
        handler = cls(application)
        for handler_func in handler.get_handlers():
            application.add_handler(handler_func)

    def get_handlers(self) -> list:
        raise NotImplementedError

    async def post_init(self, context: ContextTypes.DEFAULT_TYPE):
        self.db_session = context.db_session
        self.user_id = context._user_id
        if self.user_id:
            user = await crud.get_user_by_user_id(self.db_session, self.user_id)
            if user:
                self.lang = user.language_code
                context.user_data["lang"] = self.lang
    
    def _(self, key: str, **kwargs):
        return get_text(key, self.lang).format(**kwargs)