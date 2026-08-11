"""Command handlers."""

import logging

from aiogram.types import Message
from aiogram.filters import Command

from .. import db
from ..config import config
from .keyboard import make_main_keyboard, make_rating_keyboard

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
        "❤️ Сохранённые — сохранённые посты\n"
        "🚫 Чёрный список — управление запрещёнными тегами\n"
        "⚙️ Настройки — выбор рейтинга по умолчанию\n\n"
        "**Админ-команды:**\n"
        "/adduser <id|@username> — добавить пользователя\n"
        "/ban <id|@username> — забанить\n"
        "/vip <id|@username> — дать VIP\n"
        "/unvip <id|@username> — снять VIP\n"
        "/users — список пользователей"
    )
    await message.answer(text, parse_mode="Markdown")


async def cmd_adduser(message: Message, user_role: str, args: str) -> None:
    """Handle /adduser command (owner only)."""
    if user_role != "owner":
        await message.answer("Только владелец может использовать эту команду.")
        return
    
    if not args.strip():
        await message.answer("Использование: /adduser <user_id или @username>")
        return
    
    target = args.strip()
    
    # Try to parse as user ID
    try:
        user_id = int(target)
        username = None
    except ValueError:
        # It's a username
        if not target.startswith("@"):
            await message.answer("Укажите корректный user_id или @username")
            return
        username = target[1:]  # Remove @
        # We don't have a way to resolve username to ID without prior interaction
        await message.answer(
            f"Пользователь @{username} должен сначала написать боту, "
            "чтобы мы могли получить его ID."
        )
        return
    
    inserted = await db.add_user(user_id, username, "user")
    if inserted:
        await message.answer(f"✅ Пользователь {user_id} добавлен.")
    else:
        await message.answer(f"✅ Пользователь {user_id} обновлён (роль: user).")


async def cmd_ban(message: Message, user_role: str, args: str) -> None:
    """Handle /ban command (owner only)."""
    if user_role != "owner":
        await message.answer("Только владелец может использовать эту команду.")
        return
    
    if not args.strip():
        await message.answer("Использование: /ban <user_id>")
        return
    
    try:
        user_id = int(args.strip())
    except ValueError:
        await message.answer("Укажите корректный user_id")
        return
    
    updated = await db.update_user_role(user_id, "banned")
    if updated:
        await message.answer(f"✅ Пользователь {user_id} забанен.")
    else:
        await message.answer(f"Пользователь {user_id} не найден.")


async def cmd_vip(message: Message, user_role: str, args: str) -> None:
    """Handle /vip command (owner only)."""
    if user_role != "owner":
        await message.answer("Только владелец может использовать эту команду.")
        return
    
    if not args.strip():
        await message.answer("Использование: /vip <user_id>")
        return
    
    try:
        user_id = int(args.strip())
    except ValueError:
        await message.answer("Укажите корректный user_id")
        return
    
    updated = await db.update_user_role(user_id, "vip")
    if updated:
        await message.answer(f"✅ Пользователь {user_id} получил VIP.")
    else:
        await message.answer(f"Пользователь {user_id} не найден.")


async def cmd_unvip(message: Message, user_role: str, args: str) -> None:
    """Handle /unvip command (owner only)."""
    if user_role != "owner":
        await message.answer("Только владелец может использовать эту команду.")
        return
    
    if not args.strip():
        await message.answer("Использование: /unvip <user_id>")
        return
    
    try:
        user_id = int(args.strip())
    except ValueError:
        await message.answer("Укажите корректный user_id")
        return
    
    updated = await db.update_user_role(user_id, "user")
    if updated:
        await message.answer(f"✅ Пользователь {user_id} снят с VIP.")
    else:
        await message.answer(f"Пользователь {user_id} не найден.")


async def cmd_users(message: Message, user_role: str) -> None:
    """Handle /users command (owner only)."""
    if user_role != "owner":
        await message.answer("Только владелец может использовать эту команду.")
        return
    
    users = await db.get_all_users()
    
    if not users:
        await message.answer("Список пользователей пуст.")
        return
    
    lines = ["**Пользователи:**"]
    for u in users:
        uid = u["user_id"]
        uname = u.get("username") or "—"
        role = u.get("role", "user")
        added = u.get("added_at", "?")
        lines.append(f"`{uid}` | {uname} | {role} | {added}")
    
    text = "\n".join(lines)
    
    # Split if too long
    if len(text) > 4000:
        text = text[:4000] + "\n... (слишком много)"
    
    await message.answer(text, parse_mode="Markdown")
