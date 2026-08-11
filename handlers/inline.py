"""Inline query handler."""

import logging
from typing import Any

from aiogram.types import InlineQuery, InlineQueryResultPhoto, InlineQueryResultVideo, InlineQueryResultArticle, InputTextMessageContent

from .. import db
from ..gelbooru import gelbooru_client
from .keyboard import make_post_keyboard

logger = logging.getLogger(__name__)

# In-memory deduplication: {user_id:normalized_tags: set[post_id]}
_seen_posts: dict[str, set[int]] = {}


def _normalize_tags(tags: str) -> str:
    """Normalize tags string for consistent hashing."""
    return " ".join(sorted(tags.lower().split()))


def _parse_tags_by_category(tags_string: str) -> dict[str, list[str]]:
    """Parse tags by category based on prefixes."""
    result = {"artist": [], "character": [], "copyright": [], "general": []}
    
    for tag in tags_string.split():
        if tag.startswith("artist:"):
            result["artist"].append(tag[7:])
        elif tag.startswith("character:"):
            result["character"].append(tag[12:])
        elif tag.startswith("copyright:"):
            result["copyright"].append(tag[12:])
        else:
            result["general"].append(tag)
    
    return result


async def handle_inline_query(inline_query: InlineQuery, user_role: str) -> None:
    """
    Handle inline query from Telegram.

    Args:
        inline_query: The inline query event
        user_role: User's role ('user', 'vip', 'owner')
    """
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    offset = inline_query.offset or "0"

    # VIP check for groups - in private chats all users can search
    chat_type = inline_query.chat_type
    if chat_type in ("group", "supergroup") and user_role not in ("vip", "owner"):
        await inline_query.answer([])
        return

    # If no access (not in whitelist), return empty
    if user_role is None:
        await inline_query.answer([])
        return

    # Build tags with blacklist
    tags = query
    blacklist = await db.get_blacklist(user_id)
    if blacklist:
        blacklisted_tags = [item["tag"] for item in blacklist]
        # Add negative tags for blacklist
        for bl_tag in blacklisted_tags:
            if not bl_tag.startswith("-"):
                tags += f" -{bl_tag}"

    # Add default rating if not specified
    if "rating:" not in tags.lower():
        user_rating = await db.get_user_rating(user_id)
        tags = f"{tags} rating:{user_rating}".strip()

    # Parse offset for pagination
    try:
        pid = int(offset)
    except ValueError:
        pid = 0

    # Search posts
    posts = await gelbooru_client.search_posts(tags, pid=pid, limit=50)

    # Deduplicate
    norm_tags = _normalize_tags(query if query else "empty")
    cache_key = f"{user_id}:{norm_tags}"
    
    if cache_key not in _seen_posts:
        _seen_posts[cache_key] = set()

    seen = _seen_posts[cache_key]
    results = []

    for post in posts:
        post_id = post.get("id")
        if post_id in seen:
            # Duplicate found, stop loading
            break
        seen.add(post_id)

        # Additional blacklist filter (in case Gelbooru returned despite minus tags)
        post_tags = post.get("tags", "")
        skip = False
        for bl_item in blacklist:
            bl_tag = bl_item["tag"]
            if bl_tag in post_tags.split():
                skip = True
                break
        if skip:
            continue

        # Determine result type based on file size and type
        file_size = post.get("file_size", 0)
        file_url = post.get("file_url", "")
        sample_url = post.get("sample_url", post.get("preview_url", ""))
        preview_url = post.get("preview_url", "")

        # Check if video
        is_video = file_url.endswith((".mp4", ".webm")) or post.get("tags", "").find("video") >= 0
        
        if is_video and file_size >= 20 * 1024 * 1024:
            # Video >= 20MB: show as photo with warning
            results.append(
                InlineQueryResultPhoto(
                    id=str(post_id),
                    photo_url=sample_url or preview_url,
                    thumb_url=preview_url,
                    caption="⚠️ Файл превышает 20 МБ",
                    reply_markup=make_post_keyboard(
                        await db.save_recent_query(user_id, query if query else tags),
                        post_id,
                        query if query else tags,
                    ),
                )
            )
        elif is_video and file_size < 20 * 1024 * 1024:
            # Video < 20MB: show as video
            results.append(
                InlineQueryResultVideo(
                    id=str(post_id),
                    video_url=file_url,
                    thumb_url=preview_url,
                    mime_type="video/mp4",
                    title=f"Post #{post_id}",
                    reply_markup=make_post_keyboard(
                        await db.save_recent_query(user_id, query if query else tags),
                        post_id,
                        query if query else tags,
                    ),
                )
            )
        else:
            # Photo or image
            results.append(
                InlineQueryResultPhoto(
                    id=str(post_id),
                    photo_url=file_url or sample_url,
                    thumb_url=preview_url,
                    caption="",
                    reply_markup=make_post_keyboard(
                        await db.save_recent_query(user_id, query if query else tags),
                        post_id,
                        query if query else tags,
                    ),
                )
            )

    # If no results
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

    await inline_query.answer(results, cache_time=30)
