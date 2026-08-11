"""Message handlers for text messages (keyboard buttons)."""

import logging

from aiogram.types import Message, InputMediaPhoto
from aiogram.filters import CommandObject

from .. import db
from .keyboard import (
    make_main_keyboard,
    make_rating_keyboard,
    make_saved_searches_keyboard,
    make_blacklist_keyboard,
    make_saved_posts_page_keyboard,
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
    for i, s in enumerate(searches[:10], 1):
        tags = s["tags"][:40] + ("..." if len(s["tags"]) > 40 else "")
        text += f"{i}. `{tags}`\n"
    
    if len(searches) > 10:
        text += f"\n... и ещё {len(searches) - 10}"
    
    # Send with inline keyboard for actions
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = []
    for s in searches[:15]:  # Limit inline buttons
        row = [
            InlineKeyboardButton(
                text=s["tags"][:25] + "...",
                callback_data=f"use_search:{s['id']}",
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"del_search:{s['id']}",
            ),
        ]
        keyboard.append(row)
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def handle_saved_posts(message: Message, user_id: int, page: int = 0) -> None:
    """Handle '❤️ Сохранённые' button."""
    limit = 6
    offset = page * limit
    
    posts = await db.get_saved_posts(user_id, limit=limit + 1, offset=offset)
    
    if not posts:
        await message.answer(
            "У вас нет сохранённых постов.",
            reply_markup=make_main_keyboard(),
        )
        return
    
    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]
    
    # Send as media group if possible
    media_items = []
    for p in posts:
        post_id = p["post_id"]
        # We need to fetch post data from Gelbooru to get thumbnail
        from ..gelbooru import gelbooru_client
        post_data = await gelbooru_client.get_post(post_id)
        if post_data:
            thumb_url = post_data.get("preview_url", "")
            if thumb_url:
                media_items.append(
                    InputMediaPhoto(
                        media=thumb_url,
                        caption=f"Post #{post_id}",
                    )
                )
    
    if media_items:
        try:
            sent = await message.answer_media_group(media=media_items)
            # Add pagination buttons as a separate message
            if has_more or page > 0:
                kb = make_saved_posts_page_keyboard(page, has_more)
                await message.answer("Навигация:", reply_markup=kb)
        except Exception as e:
            logger.warning(f"Failed to send media group: {e}")
            # Fallback to text list
            text = "**Сохранённые посты:**\n"
            for p in posts:
                text += f"- Post #{p['post_id']}\n"
            await message.answer(text, parse_mode="Markdown")
    else:
        text = "**Сохранённые посты:**\n"
        for p in posts:
            text += f"- Post #{p['post_id']}\n"
        await message.answer(text, parse_mode="Markdown")
    
    # Add delete buttons
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    del_buttons = []
    for p in posts:
        del_buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ Post #{p['post_id']}",
                callback_data=f"del_saved:{p['post_id']}",
            )
        ])
    
    if del_buttons:
        await message.answer(
            "Удалить:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=del_buttons),
        )


async def handle_blacklist(message: Message, user_id: int) -> None:
    """Handle '🚫 Чёрный список' button."""
    blacklist = await db.get_blacklist(user_id)
    
    if not blacklist:
        await message.answer(
            "Ваш чёрный список пуст.\n\nОтправьте тег текстом, чтобы добавить его.",
            reply_markup=make_main_keyboard(),
        )
        return
    
    text = "**Чёрный список:**\n\n"
    for item in blacklist:
        text += f"`{item['tag']}`\n"
    
    # Build keyboard with delete buttons
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = []
    for item in blacklist:
        row = [
            InlineKeyboardButton(text=item["tag"], callback_data="noop"),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"del_bl:{item['id']}",
            ),
        ]
        keyboard.append(row)
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def handle_settings(message: Message, user_id: int) -> None:
    """Handle '⚙️ Настройки' button."""
    rating = await db.get_user_rating(user_id)
    
    text = f"**Настройки**\n\nТекущий рейтинг: `{rating}`"
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_rating_keyboard(rating),
    )


async def handle_add_blacklist_tag(message: Message, user_id: int) -> None:
    """Handle adding a tag to blacklist via text message."""
    tag = message.text.strip()
    
    if not tag:
        return
    
    # Check if it's a valid tag (no spaces)
    if " " in tag:
        await message.answer(
            "Тег не должен содержать пробелов. Отправьте один тег."
        )
        return
    
    success, msg = await db.add_to_blacklist(user_id, tag)
    await message.answer(msg)


async def handle_callback_response(
    message: Message, user_id: int, callback_data: str
) -> None:
    """Handle various callback responses that need message handling."""
    # This is a fallback for any message-based interactions
    pass
