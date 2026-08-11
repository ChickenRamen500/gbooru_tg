"""Configuration module for the bot."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Bot configuration loaded from environment variables."""

    bot_token: str = os.getenv("BOT_TOKEN", "")
    gelbooru_api_key: str = os.getenv("GELBOORU_API_KEY", "")
    gelbooru_user_id: str = os.getenv("GELBOORU_USER_ID", "")
    owner_id: int = int(os.getenv("OWNER_ID", "0"))

    @property
    def is_valid(self) -> bool:
        """Check if all required configuration values are present."""
        return bool(
            self.bot_token
            and self.gelbooru_api_key
            and self.gelbooru_user_id
            and self.owner_id
        )


config = Config()
