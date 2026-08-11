"""Access control middleware."""

import logging
from typing import Any, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineQuery
from aiogram.types import TelegramObject

from .. import db

logger = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Middleware to check user access based on role."""

    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Any],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check user access before handling the event."""
        # Get user ID from different event types
        user_id: Optional[int] = None
        username: Optional[str] = None

        if isinstance(event, InlineQuery):
            user_id = event.from_user.id
            username = event.from_user.username
        elif isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username
        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username

        if user_id is None:
            return await handler(event, data)

        # Owner always has access
        if user_id == self.owner_id:
            return await handler(event, data)

        # Check user in database
        user = await db.get_user(user_id)

        if user is None:
            # User not in whitelist
            if isinstance(event, InlineQuery):
                # Return empty results for inline queries
                return await event.answer([])
            elif isinstance(event, Message):
                # Send access denied message
                await event.answer("Доступ закрыт. Обратитесь к администратору.")
                return None
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ закрыт.", show_alert=True)
                return None
            return await handler(event, data)

        # Check if banned
        if user.get("role") == "banned":
            if isinstance(event, InlineQuery):
                return await event.answer([])
            elif isinstance(event, Message):
                await event.answer("Вы забанены.")
                return None
            elif isinstance(event, CallbackQuery):
                await event.answer("Вы забанены.", show_alert=True)
                return None
            return await handler(event, data)

        # Update username if changed
        if username and user.get("username") != username:
            await db.add_user(user_id, username, user.get("role", "user"))

        # Store user info for handlers
        data["user"] = user
        data["user_role"] = user.get("role", "user")

        return await handler(event, data)
