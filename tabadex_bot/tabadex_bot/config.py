# tabadex_bot/config.py

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Set

class Settings(BaseSettings):
    # .env variables
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    BOT_TOKEN: str
    DATABASE_URL: str
    ADMIN_IDS: str
    SWAPZONE_API_KEY: str

    @property
    def ADMIN_ID_SET(self) -> Set[int]:
        """Returns a set of integer admin IDs."""
        return {int(admin_id.strip()) for admin_id in self.ADMIN_IDS.split(',')}

# Instantiate the settings
settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)

# Get a logger instance
logger = logging.getLogger(__name__)