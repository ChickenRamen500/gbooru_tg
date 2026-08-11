"""Inline query handler."""

import asyncio
import logging
import time
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

# In-memory deduplication: {key: (post_ids_set, last_access_time)}
_seen_posts: dict[str, tuple[set[int], float]] = {}
_DEDUP_TTL = 600  # 10 minutes

# Track large video post IDs for chosen_inline_result
_large_video_results: dict[str, int] = {}  # result_id -> post_id


def _cleanup_seen_posts() -> None:
    """Remove old entries from dedup cache."""
    now = time.monotonic()
    expired = [k for k, (_, t) in _seen_posts.items() if now - t > _DEDUP_TTL]
    for k in expired:
        del _seen_posts[k]


def _normalize_tags(tags: str) -> str:
    """Normalize tags string for consistent hashing."""
    return " ".join(sorted(tags.lower().split()))


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
        f"Inline query: user_id={user_id}, query='{query}', offset={offset}, "
        f"chat_type={inline_query.chat_type}, user_role={user_role}"
    )

    # VIP check for groups
    chat_type = inline_query.chat_type
    if chat_type in ("group", "supergroup") and user_role not in ("vip", "owner"):
        await inline_query.answer([])
        return

    if user_role is None:
        await inline_query.answer([])
        return

    # Cleanup old dedup entries periodically
    _cleanup_seen_posts()

    # Search posts
    posts = await gelbooru_client.search_posts(tags, pid=pid, limit=50)

    logger.info(f"API returned {len(posts)} posts, first 3 ids: {[p.get('id') for p in posts[:3]]}")

    # Deduplicate
    norm_tags = _normalize_tags(query if query else "empty")
    cache_key = f"{user_id}:{norm_tags}"

    if cache_key not in _seen_posts:
        _seen_posts[cache_key] = (set(), time.monotonic())

    seen, _ = _seen_posts[cache_key]
    results = []
    # Save recent query once per inline request
    query_id = await db.save_recent_query(user_id, query if query else tags)
    original_tags = query if query else tags

    for idx, post in enumerate(posts):
        post_id = post.get("id")
        if post_id in seen:
            logger.debug(f"Skip post {post_id}: dedup")
            break
        seen.add(post_id)

        # Additional blacklist filter on post tags
        post_tags = post.get("tags", "")
        post_tag_set = set(post_tags.lower().split())
        skip = False
        for bl_tag in blacklisted_tags:
            if bl_tag.lower().lstrip("-") in post_tag_set:
                skip = True
                break
        if skip:
            logger.debug(f"Skip post {post_id}: blacklist")
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
        photo_url = sample_url or preview_url
        thumbnail_url = preview_url

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

        # Log details for each result
        log_msg = (
            f"Result[{idx}]: post_id={post_id}, is_video={is_video}, file_size={file_size}, "
            f"photo_url_len={len(photo_url)}, thumbnail_url_len={len(thumbnail_url)}"
        )
        if idx == 0:
            # Log full URLs for the first post
            log_msg += f", photo_url='{photo_url}', thumbnail_url='{thumbnail_url}'"
        logger.debug(log_msg)

        # Warning if URLs are empty
        if not photo_url:
            logger.warning(f"post_id={post_id}: photo_url is empty")
        if not thumbnail_url:
            logger.warning(f"post_id={post_id}: thumbnail_url is empty")

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

    logger.info(f"Sending {len(results)} results, next_offset='{next_offset}'")
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
