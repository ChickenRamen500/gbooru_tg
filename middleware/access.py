"""Access control middleware."""

import logging
from typing import Any, Callable, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineQuery
from aiogram.types import TelegramObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
                # Send standard bot description
                bot_info_text = (
                    "Бот для поиска изображений с Gelbooru.\n\n"
                    "Использование: @botname теги — в любом чате.\n\n"
                    "Возможности:\n"
                    "• Поиск изображений по тегам\n"
                    "• Сохранение поисковых запросов\n"
                    "• Сохранение понравившихся постов\n"
                    "• Чёрный список тегов\n"
                    "• Настройка рейтинга контента"
                )
                await event.answer(bot_info_text)
                
                # Send access denied message with request button
                no_access_text = (
                    "⛔ У вас нет доступа к боту.\n\n"
                    "Вы можете запросить доступ у владельца бота."
                )
                keyboard = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="📩 Запросить доступ")]],
                    resize_keyboard=True,
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

        # Update username if changed
        if username and user.get("username") != username:
            await db.add_user(user_id, username, user.get("role", "user"))

        # Store user info for handlers
        data["user"] = user
        data["user_role"] = user.get("role", "user")

        return await handler(event, data)
