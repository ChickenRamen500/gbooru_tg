"""Message handlers for text messages (keyboard buttons)."""

import logging

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

import db
from handlers.keyboard import (
    make_main_keyboard,
    make_rating_keyboard,
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

    # Build media group using saved preview_url
    media_items = []
    for p in posts:
        post_id = p["post_id"]
        thumb_url = p.get("preview_url", "")
        if not thumb_url:
            # Fallback: fetch from API
            from gelbooru import gelbooru_client
            post_data = await gelbooru_client.get_post(post_id)
            if post_data:
                thumb_url = post_data.get("preview_url", "")
                # Save preview_url for next time
                await db.save_post(user_id, post_id, thumb_url, p.get("tags"))
        if thumb_url:
            media_items.append(
                InputMediaPhoto(
                    media=thumb_url,
                    caption=f"Post #{post_id}",
                )
            )

    if media_items:
        try:
            if len(media_items) > 1:
                await message.answer_media_group(media=media_items)
            else:
                await message.answer_photo(
                    photo=media_items[0].media,
                    caption=media_items[0].caption,
                )
        except Exception as e:
            logger.warning(f"Failed to send media: {e}")
            text = "**Сохранённые посты:**\n"
            for p in posts:
                text += f"- Post #{p['post_id']}\n"
            await message.answer(text, parse_mode="Markdown")
    else:
        text = "**Сохранённые посты:**\n"
        for p in posts:
            text += f"- Post #{p['post_id']}\n"
        await message.answer(text, parse_mode="Markdown")

    # Delete buttons
    del_buttons = []
    for p in posts:
        del_buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ Post #{p['post_id']}",
                callback_data=f"del_saved:{p['post_id']}",
            )
        ])

    await message.answer(
        "Удалить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=del_buttons),
    )

    # Pagination
    if has_more or page > 0:
        await message.answer(
            "Навигация:",
            reply_markup=make_saved_posts_page_keyboard(page, has_more),
        )


async def handle_blacklist(message: Message, user_id: int) -> None:
    """Handle '🚫 Чёрный список' button."""
    blacklist = await db.get_blacklist(user_id)

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

    # Add button to enter tag addition mode
    keyboard.append([InlineKeyboardButton(text="➕ Добавить тег", callback_data="add_bl:")])

    if not blacklist:
        text = "Ваш чёрный список пуст."
    else:
        text = "**Чёрный список:**\n\n"
        for item in blacklist:
            text += f"`{item['tag']}`\n"

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

    if " " in tag:
        await message.answer(
            "Тег не должен содержать пробелов. Отправьте один тег."
        )
        return

    success, msg = await db.add_to_blacklist(user_id, tag)
    await message.answer(msg, parse_mode="Markdown")

    # Show updated blacklist
    await handle_blacklist(message, user_id)
