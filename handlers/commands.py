"""Command handlers."""

import logging

from aiogram.types import Message

import db
from config import config
from handlers.keyboard import make_main_keyboard

logger = logging.getLogger(__name__)


async def cmd_start(message: Message, user_role: str) -> None:
    """Handle /start command."""
    text = (
        "Бот для поиска изображений с Gelbooru.\n\n"
        "Использование: @botname теги — в любом чате.\n\n"
        "Для управления — используйте меню ниже 👇"
    )
    await message.answer(text, reply_markup=make_main_keyboard())


async def cmd_help(message: Message, user_role: str) -> None:
    """Handle /help command."""
    text = (
        "**Gelbooru Bot — справка**\n\n"
        "**Поиск:**\n"
        "Используйте inline-режим: @botname теги\n"
        "Пример: @botname anime girl blue_eyes\n\n"
        "**Кнопки под результатами:**\n"
        "📌 Сохранить поиск — сохранить текущие теги\n"
        "ℹ️ Инфо — показать детали поста\n"
        "🔗 — открыть пост на Gelbooru\n"
        "🔁 — повторить поиск с теми же тегами\n\n"
        "**Меню:**\n"
        "📌 Мои поиски — список сохранённых поисков\n"
        "❤️ Сохраненные посты и подписки на теги — сохранённые посты (планы на будущее)\n"
        "⚙️ Настройки — выбор рейтинга по умолчанию, чёрный список, управление пользователями\n\n"
        "**Админ-команды (только владелец):**\n"
        "Управление пользователями теперь доступно через меню настроек."
    )
    await message.answer(text, parse_mode="Markdown")


async def cmd_adduser(message: Message, user_role: str, args: str) -> None:
    """Handle /adduser command (owner only)."""
    await message.answer("Управление пользователями теперь доступно через меню настроек.")


async def cmd_ban(message: Message, user_role: str, args: str) -> None:
    """Handle /ban command (owner only)."""
    await message.answer("Управление пользователями теперь доступно через меню настроек.")


async def cmd_vip(message: Message, user_role: str, args: str) -> None:
    """Handle /vip command (owner only)."""
    await message.answer("Управление пользователями теперь доступно через меню настроек.")


async def cmd_unvip(message: Message, user_role: str, args: str) -> None:
    """Handle /unvip command (owner only)."""
    await message.answer("Управление пользователями теперь доступно через меню настроек.")


async def cmd_users(message: Message, user_role: str) -> None:
    """Handle /users command (owner only)."""
    await message.answer("Управление пользователями теперь доступно через меню настроек.")
