"""Message handlers for text messages (keyboard buttons)."""

import logging

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

import db
from handlers.keyboard import (
    make_main_keyboard,
    make_saved_and_subs_keyboard,
    make_saved_posts_keyboard,
    make_subscriptions_keyboard,
    make_settings_keyboard,
    make_blacklist_keyboard,
    make_saved_posts_page_keyboard,
    make_subscriptions_inline_keyboard,
)

logger = logging.getLogger(__name__)

# State tracking for menu navigation
_user_menu_state: dict[int, str] = {}  # user_id -> current menu


async def handle_my_searches(message: Message, user_id: int) -> None:
    """Handle '📌 Мои поиски' button."""
    searches = await db.get_saved_searches(user_id)

    if not searches:
        await message.answer(
            "У тебя пока нет сохраненных поисков.",
            reply_markup=make_main_keyboard(),
        )
        return

    text = "**📌 Мои поиски**\n\n"
    keyboard = []

    for s in searches[:15]:
        tags = s["tags"]
        label = tags[:30] + ("..." if len(tags) > 30 else "")
        text += f"`{tags}`\n"

        row = [
            InlineKeyboardButton(
                text="▶️ Запустить",
                switch_inline_query_current_chat=tags,
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"searches:del:{s['id']}",
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


async def handle_saved_and_subs(message: Message, user_id: int) -> None:
    """Handle '❤️ Сохраненное и подписки' button - show submenu."""
    text = (
        "❤️ **Сохраненное и подписки**\n\n"
        "Выбери раздел:"
    )
    
    # Delete the original message and send new one with saved_and_subs keyboard
    await message.delete()
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_saved_and_subs_keyboard(),
    )


async def handle_saved_posts(message: Message, user_id: int, page: int = 0) -> None:
    """Handle '🖼 Сохраненные посты' button."""
    posts = await db.get_saved_posts(user_id, limit=10, offset=page * 10)
    
    if not posts:
        text = "У тебя пока нет сохраненных постов."
        await message.answer(
            text,
            reply_markup=make_main_keyboard(),
        )
        return
    
    total_count = await db.get_saved_posts_count(user_id)
    total_pages = (total_count + 9) // 10
    
    text = "**🖼 Сохраненные посты**\n\n"
    for i, post in enumerate(posts, start=1):
        post_id = post["post_id"]
        text += f"`{post_id}` "
    
    text += f"\n\nВсего: {total_count}\nСтраница {page + 1}/{total_pages}"
    
    has_more = page + 1 < total_pages
    inline_kb = make_saved_posts_page_keyboard(page, has_more)
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )


async def handle_subscriptions(message: Message, user_id: int) -> None:
    """Handle '🔔 Подписки на теги' button."""
    subscriptions = await db.get_subscriptions(user_id)
    
    if not subscriptions:
        text = "У тебя пока нет подписок на теги."
        await message.answer(
            text,
            reply_markup=make_main_keyboard(),
        )
        return
    
    text = "**🔔 Подписки на теги**\n\nБот может присылать новые посты по этим тегам:\n\n"
    inline_kb = make_subscriptions_inline_keyboard(subscriptions)
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )


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
    """Handle '⚙️ Настройки' button - edit message and replace keyboard."""
    text = "**Настройки**\n\nВыберите раздел:"
    
    # Delete the original message and send new one with settings keyboard
    await message.delete()
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_settings_keyboard(is_owner),
    )
    _user_menu_state[user_id] = "settings"


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
