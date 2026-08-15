"""Access control middleware."""

import logging
from typing import Any, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineQuery
from aiogram.types import TelegramObject

import db

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
        user_id: Optional[int] = None
        username: Optional[str] = None
        first_name: Optional[str] = None
        last_name: Optional[str] = None
        language_code: Optional[str] = None

        if isinstance(event, InlineQuery):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
            last_name = event.from_user.last_name
            language_code = event.from_user.language_code
        elif isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
            last_name = event.from_user.last_name
            language_code = event.from_user.language_code
        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username
                first_name = event.from_user.first_name
                last_name = event.from_user.last_name
                language_code = event.from_user.language_code

        if user_id is None:
            return await handler(event, data)

        # Owner always has access
        if user_id == self.owner_id:
            data["user_role"] = "owner"
            return await handler(event, data)

        # Check user in database
        user = await db.get_user(user_id)

        if user is None:
            # User not in database - no access, but can request access
            if isinstance(event, InlineQuery):
                return await event.answer([])
            elif isinstance(event, Message):
                # Access denied message with request button (inline)
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                no_access_text = (
                    "👋 Привет! Я бот для поиска артов через Gelbooru.\n\n"
                    "🔒 У тебя нет доступа. Нажми кнопку ниже, чтобы запросить."
                )
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📩 Запросить доступ", callback_data="request_access")]]
                )
                await event.answer(no_access_text, reply_markup=keyboard)
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

        # Update username if changed (preserve first/last name via COALESCE in add_user)
        if username and user.get("username") != username:
            await db.add_user(user_id, username, user.get("role", "user"))

        # Refresh first/last name if they changed and we have them
        if first_name and user.get("first_name") != first_name:
            await db.add_user(
                user_id,
                username or user.get("username"),
                user.get("role", "user"),
                first_name,
                last_name,
            )

        # Store user info for handlers
        data["user"] = user
        data["user_role"] = user.get("role", "user")

        return await handler(event, data)
