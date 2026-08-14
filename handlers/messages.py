"""Message handlers for text messages (keyboard buttons)."""

import logging

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

import db
from handlers.keyboard import (
    make_main_keyboard,
    make_rating_menu_keyboard,
    make_saved_posts_page_keyboard,
    make_settings_keyboard,
    make_blacklist_keyboard,
    make_users_management_keyboard,
)

logger = logging.getLogger(__name__)


async def handle_my_searches(message: Message, user_id: int) -> None:
    """Handle '📌 Мои поиски' button."""
    searches = await db.get_saved_searches(user_id)

    if not searches:
        await message.answer(
            "У вас нет сохранённых поисков.",
            reply_markup=make_main_keyboard(),
        )
        return

    text = "**Ваши сохранённые поиски:**\n\n"
    keyboard = []

    for s in searches[:15]:
        tags = s["tags"]
        label = tags[:30] + ("..." if len(tags) > 30 else "")
        text += f"{len(keyboard)+1}. `{tags}`\n"

        row = [
            InlineKeyboardButton(
                text=label,
                switch_inline_query_current_chat=tags,
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"del_search:{s['id']}",
            ),
        ]
        keyboard.append(row)

    if len(searches) > 15:
        text += f"\n... и ещё {len(searches) - 15}"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def handle_saved_posts(message: Message, user_id: int, page: int = 0) -> None:
    """Handle '❤️ Сохраненные посты и подписки на теги' button."""
    future_text = (
        "В будущем тут будет список ID хранных постов и ссылки на них, "
        "а так же настройки подписок на теги.\n\n"
        "Сохраненки и подписки — планы на будущее, которые сейчас не реализованы."
    )
    await message.answer(future_text)


async def handle_blacklist(message: Message, user_id: int) -> None:
    """Handle blacklist from settings."""
    blacklist = await db.get_blacklist(user_id)

    if not blacklist:
        text = "Ваш чёрный список пуст."
    else:
        text = "**Чёрный список:**\n\n"
        for item in blacklist:
            text += f"`{item['tag']}`\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_blacklist_keyboard(blacklist),
    )


async def handle_settings(message: Message, user_id: int, is_owner: bool = False) -> None:
    """Handle '⚙️ Настройки' button."""
    text = "**Настройки**\n\nВыберите раздел:"
    
    # Edit the message to replace keyboard with settings menu
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_settings_keyboard(is_owner),
    )


async def handle_add_blacklist_tag(message: Message, user_id: int) -> None:
    """Handle adding a tag to blacklist via text message."""
    tag = message.text.strip()

    if not tag:
        return

    if " " in tag:
        await message.answer(
            "Тег не должен содержать пробелов. Отправьте один тег."
        )
        return

    success, msg = await db.add_to_blacklist(user_id, tag)
    await message.answer(msg, parse_mode="Markdown")

    # Show updated blacklist
    await handle_blacklist(message, user_id)
