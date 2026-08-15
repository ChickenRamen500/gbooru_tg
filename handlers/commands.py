"""Command handlers."""

import logging

from aiogram.types import Message

import db
from config import config
from handlers.keyboard import make_main_keyboard

logger = logging.getLogger(__name__)


def _parse_user_id(args: str) -> int | None:
    """Parse a Telegram user ID from command arguments."""
    if not args:
        return None
    try:
        return int(args.strip())
    except ValueError:
        return None


async def cmd_start(message: Message, user_role: str) -> None:
    """Handle /start command."""
    is_owner = message.from_user.id == config.owner_id
    text = (
        "Бот для поиска изображений с Gelbooru.\n\n"
        "Использование: @botname теги — в любом чате.\n\n"
        "Для управления — используйте меню ниже 👇"
    )
    await message.answer(text, reply_markup=make_main_keyboard(is_owner=is_owner))


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
        "**Меню (в чате с ботом):**\n"
        "📌 Мои поиски — сохранённые поиски\n"
        "❤️ Сохранённое и подписки — в разработке\n"
        "⚙️ Настройки — рейтинг по умолчанию, чёрный список\n"
        "👑 Админ-панель (только владелец) — пользователи, заявки, рассылка, статистика, система\n\n"
        "**Админ-команды (только владелец):**\n"
        "/adduser <id> — добавить пользователя\n"
        "/ban <id> — забанить\n"
        "/unban <id> — разбанить\n"
        "/vip <id> — выдать VIP\n"
        "/unvip <id> — снять VIP\n"
        "/users — список пользователей"
    )
    await message.answer(text, parse_mode="Markdown")


async def cmd_adduser(message: Message, user_role: str, args: str) -> None:
    """Handle /adduser command (owner only)."""
    if message.from_user.id != config.owner_id:
        await message.answer("Эта команда доступна только владельцу.")
        return

    user_id = _parse_user_id(args)
    if user_id is None:
        await message.answer("Использование: `/adduser <id>`", parse_mode="Markdown")
        return

    inserted = await db.add_user(user_id, role="user")
    if inserted:
        await message.answer(f"✅ Пользователь `{user_id}` добавлен.", parse_mode="Markdown")
    else:
        await message.answer(f"Пользователь `{user_id}` уже существует.", parse_mode="Markdown")


async def cmd_ban(message: Message, user_role: str, args: str) -> None:
    """Handle /ban command (owner only)."""
    if message.from_user.id != config.owner_id:
        await message.answer("Эта команда доступна только владельцу.")
        return

    user_id = _parse_user_id(args)
    if user_id is None:
        await message.answer("Использование: `/ban <id>`", parse_mode="Markdown")
        return

    if user_id == config.owner_id:
        await message.answer("Нельзя забанить владельца.")
        return

    updated = await db.set_user_banned(user_id, True)
    if updated:
        await message.answer(f"🔨 Пользователь `{user_id}` забанен.", parse_mode="Markdown")
    else:
        await message.answer(f"Пользователь `{user_id}` не найден.", parse_mode="Markdown")


async def cmd_unban(message: Message, user_role: str, args: str) -> None:
    """Handle /unban command (owner only)."""
    if message.from_user.id != config.owner_id:
        await message.answer("Эта команда доступна только владельцу.")
        return

    user_id = _parse_user_id(args)
    if user_id is None:
        await message.answer("Использование: `/unban <id>`", parse_mode="Markdown")
        return

    updated = await db.set_user_banned(user_id, False)
    if updated:
        await message.answer(f"🔓 Пользователь `{user_id}` разбанен.", parse_mode="Markdown")
    else:
        await message.answer(f"Пользователь `{user_id}` не найден.", parse_mode="Markdown")


async def cmd_vip(message: Message, user_role: str, args: str) -> None:
    """Handle /vip command (owner only)."""
    if message.from_user.id != config.owner_id:
        await message.answer("Эта команда доступна только владельцу.")
        return

    user_id = _parse_user_id(args)
    if user_id is None:
        await message.answer("Использование: `/vip <id>`", parse_mode="Markdown")
        return

    updated = await db.set_user_vip(user_id, True)
    if updated:
        await message.answer(f"⭐ VIP выдан пользователю `{user_id}`.", parse_mode="Markdown")
    else:
        await message.answer(f"Пользователь `{user_id}` не найден.", parse_mode="Markdown")


async def cmd_unvip(message: Message, user_role: str, args: str) -> None:
    """Handle /unvip command (owner only)."""
    if message.from_user.id != config.owner_id:
        await message.answer("Эта команда доступна только владельцу.")
        return

    user_id = _parse_user_id(args)
    if user_id is None:
        await message.answer("Использование: `/unvip <id>`", parse_mode="Markdown")
        return

    updated = await db.set_user_vip(user_id, False)
    if updated:
        await message.answer(f"❌ VIP снят с пользователя `{user_id}`.", parse_mode="Markdown")
    else:
        await message.answer(f"Пользователь `{user_id}` не найден.", parse_mode="Markdown")


async def cmd_users(message: Message, user_role: str) -> None:
    """Handle /users command (owner only)."""
    if message.from_user.id != config.owner_id:
        await message.answer("Эта команда доступна только владельцу.")
        return

    users = await db.get_all_users()
    if not users:
        await message.answer("Пользователей нет.")
        return

    lines = [f"👥 Всего пользователей: {len(users)}\n"]
    for u in users[:50]:
        uname = u.get("username") or "—"
        role = u.get("role", "user")
        mark = {"vip": "⭐", "banned": "🚫", "owner": "👑"}.get(role, "")
        lines.append(f"`{u['user_id']}` @{uname} {mark}")

    if len(users) > 50:
        lines.append(f"\n... и ещё {len(users) - 50}")

    await message.answer("\n".join(lines), parse_mode="Markdown")
