"""Inline query handler."""

import logging
from typing import Any, Optional

from aiogram import Bot
from aiogram.types import (
    InlineQuery,
    InlineQueryResultPhoto,
    InlineQueryResultVideo,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ChosenInlineResult,
)
from aiogram.exceptions import TelegramBadRequest

import db
from gelbooru import gelbooru_client
from handlers.keyboard import make_post_keyboard

logger = logging.getLogger(__name__)

# Track large video post IDs for chosen_inline_result
_large_video_results: dict[str, int] = {}  # result_id -> post_id


def _is_video_post(post: dict) -> bool:
    """Reliably detect if a post is a video."""
    file_url = post.get("file_url", "")
    if file_url.endswith((".mp4", ".webm")):
        return True
    image_url = post.get("sample_url", "") or file_url
    if not image_url.endswith((".mp4", ".webm")):
        return False
    return True


def _get_video_mime(file_url: str) -> str:
    """Get MIME type from file URL."""
    if file_url.endswith(".webm"):
        return "video/webm"
    return "video/mp4"


async def handle_inline_query(inline_query: InlineQuery, user_role: Optional[str]) -> None:
    """Handle inline query from Telegram."""
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    offset = inline_query.offset or "0"

    # Build tags with blacklist (minus-tags for Gelbooru API)
    tags = query
    blacklist = await db.get_blacklist(user_id)
    blacklisted_tags: list[str] = []
    if blacklist:
        blacklisted_tags = [item["tag"] for item in blacklist]
        for bl_tag in blacklisted_tags:
            if not bl_tag.startswith("-"):
                tags += f" -{bl_tag}"

    # Add default rating if not specified
    if "rating:" not in tags.lower():
        user_rating = await db.get_user_rating(user_id)
        if user_rating:
            tags = f"{tags} rating:{user_rating}".strip()

    # Parse offset for pagination
    try:
        pid = int(offset)
    except ValueError:
        pid = 0

    logger.info(
        "Inline query: user_id=%s, query='%s', offset=%s, chat_type=%s, user_role=%s",
        user_id, query, offset, inline_query.chat_type, user_role
    )

    # VIP check for groups
    chat_type = inline_query.chat_type
    if chat_type in ("group", "supergroup") and user_role not in ("vip", "owner"):
        await inline_query.answer([])
        return

    if user_role is None:
        await inline_query.answer([])
        return

    # Search posts
    posts = await gelbooru_client.search_posts(tags, pid=pid, limit=50)

    logger.info("API returned %d posts for tags='%s' pid=%d", len(posts), tags, pid)

    results = []
    # Save recent query once per inline request
    query_id = await db.save_recent_query(user_id, query if query else tags)
    original_tags = query if query else tags

    for idx, post in enumerate(posts):
        post_id = post.get("id")

        # Additional blacklist filter on post tags
        post_tags = post.get("tags", "")
        post_tag_set = set(post_tags.lower().split())
        skip = False
        for bl_tag in blacklisted_tags:
            if bl_tag.lower().lstrip("-") in post_tag_set:
                skip = True
                break
        if skip:
            logger.debug("Skip post %s: blacklist", post_id)
            continue

        file_url = post.get("file_url", "")
        sample_url = post.get("sample_url", "") or post.get("preview_url", "")
        preview_url = post.get("preview_url", "") or sample_url or file_url
        file_size = post.get("file_size", 0) or 0

        is_video = _is_video_post(post)

        keyboard = make_post_keyboard(query_id, post_id, original_tags)

        # Determine photo_url and thumbnail_url for inline results
        # photo_url: use sample_url (resized ~850px) for faster preview loading
        # thumbnail_url: use preview_url (smallest ~150px)
        photo_url = sample_url or preview_url or file_url
        thumbnail_url = preview_url

        logger.debug(
            "Post #%s: file_url=%s, sample_url=%s, preview_url=%s, is_video=%s, file_size=%s",
            post_id, bool(file_url), bool(sample_url), bool(preview_url), is_video, file_size
        )

        if not photo_url:
            logger.warning(
                "Post #%s: empty photo_url! file_url=%s, sample_url=%s, preview_url=%s",
                post_id,
                file_url[:80] if file_url else "EMPTY",
                sample_url[:80] if sample_url else "EMPTY",
                preview_url[:80] if preview_url else "EMPTY"
            )
        if not thumbnail_url:
            logger.warning("Post #%s: empty thumbnail_url!", post_id)

        if is_video and file_size >= 20 * 1024 * 1024:
            # Video >= 20MB: show as photo with warning
            _large_video_results[str(post_id)] = post_id
            results.append(
                InlineQueryResultPhoto(
                    id=str(post_id),
                    photo_url=photo_url,
                    thumbnail_url=thumbnail_url,
                    caption="⚠️ Файл превышает 20 МБ",
                    reply_markup=keyboard,
                )
            )
        elif is_video and file_size < 20 * 1024 * 1024:
            results.append(
                InlineQueryResultVideo(
                    id=str(post_id),
                    video_url=file_url,
                    thumbnail_url=preview_url,
                    mime_type=_get_video_mime(file_url),
                    title=f"Post #{post_id}",
                    reply_markup=keyboard,
                )
            )
        else:
            results.append(
                InlineQueryResultPhoto(
                    id=str(post_id),
                    photo_url=photo_url,
                    thumbnail_url=thumbnail_url,
                    reply_markup=keyboard,
                )
            )

    if not results:
        results = [
            InlineQueryResultArticle(
                id="empty",
                title="Ничего не найдено",
                description=f"По тегам: {query if query else 'пустой запрос'}",
                input_message_content=InputTextMessageContent(
                    message_text="Ничего не найдено"
                ),
            )
        ]
        next_offset = ""
    else:
        # Tell Telegram there may be more results
        next_offset = str(pid + 1)

    logger.info("Sending %d results, next_offset='%s'", len(results), next_offset)
    await inline_query.answer(results, next_offset=next_offset, cache_time=30)


async def handle_chosen_inline_result(chosen: ChosenInlineResult, bot: Bot) -> None:
    """Handle when user taps an inline result — edit caption for large videos."""
    result_id = chosen.result_id
    inline_message_id = chosen.inline_message_id

    if not inline_message_id:
        return

    # Check if this was a large video result
    if result_id in _large_video_results:
        post_id = _large_video_results.pop(result_id)
        link = f"https://gelbooru.com/index.php?page=post&s=view&id={post_id}"
        try:
            from handlers.keyboard import make_post_keyboard
            query_id = await db.save_recent_query(chosen.from_user.id, "")
            await bot.edit_message_caption(
                inline_message_id=inline_message_id,
                caption="⚠️ Файл превышает 20 МБ и не может быть отправлен.",
                reply_markup=make_post_keyboard(query_id, post_id, ""),
            )
        except TelegramBadRequest as e:
            logger.warning(f"Failed to edit caption for large video {post_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling chosen result {result_id}: {e}")
