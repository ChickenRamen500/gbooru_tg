"""Inline query handler."""

import logging
from typing import Optional
from urllib.parse import quote

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
from config import config
from gelbooru import gelbooru_client
from handlers.keyboard import make_post_keyboard

logger = logging.getLogger(__name__)

# Track large video post IDs for chosen_inline_result.
# Keyed by (user_id, result_id) to avoid cross-user collisions and leaks.
_large_video_results: dict[tuple[int, str], int] = {}


def _proxy_url(original_url: str) -> str:
    """Route a Gelbooru image URL through Cloudflare Worker proxy.

    PUBLIC_URL must point to a Cloudflare Worker that adds the Referer header
    required by Gelbooru's hotlink protection.
    The .jpg suffix tricks Telegram into treating the URL as a direct image link.
    """
    if not config.has_proxy:
        return original_url
    return f"{config.public_url}/proxy.jpg?url={quote(original_url, safe='')}"


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
    chat_type = inline_query.chat_type

    logger.info(
        "Inline query: user_id=%s, query='%s', offset=%s, chat_type=%s, user_role=%s",
        user_id, query, offset, chat_type, user_role
    )

    # VIP check for groups
    if chat_type in ("group", "supergroup") and user_role not in ("vip", "owner"):
        logger.info("Rejected: non-VIP in group, user_id=%s role=%s", user_id, user_role)
        await inline_query.answer([])
        return

    if user_role is None:
        logger.info("Rejected: unknown user, user_id=%s", user_id)
        await inline_query.answer([])
        return

    # Build tags with blacklist (minus-tags for Gelbooru API)
    tags = query
    blacklist = await db.get_blacklist(user_id)
    blacklisted_tags: list[str] = []
    if blacklist:
        blacklisted_tags = [item["tag"] for item in blacklist]
        for bl_tag in blacklisted_tags:
            if not bl_tag.startswith("-"):
                tags += f" -{bl_tag}"

    # Apply global blacklist (same for all users)
    global_bl = await db.get_global_blacklist()
    global_bl_tags = [item["tag"] for item in global_bl]
    for gbl_tag in global_bl_tags:
        if not gbl_tag.startswith("-"):
            tags += f" -{gbl_tag}"
    blacklisted_tags.extend(global_bl_tags)

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

    # Search posts
    posts = await gelbooru_client.search_posts(tags, pid=pid, limit=50)

    results = []
    # Save recent query once per inline request
    query_id = await db.save_recent_query(user_id, query if query else tags)
    original_tags = query if query else tags

    for post in posts:
        post_id = post.get("id")

        # Additional blacklist filter on post tags
        post_tags = post.get("tags", "")
        post_tag_set = set(post_tags.lower().split())
        skip = False
        for bl_tag in blacklisted_tags:
            if bl_tag.lower().lstrip("-") in post_tag_set:
                logger.debug("Skip post %s: blacklist tag '%s'", post_id, bl_tag)
                skip = True
                break
        if skip:
            continue

        file_url = post.get("file_url", "")
        sample_url = post.get("sample_url", "") or post.get("preview_url", "")
        preview_url = post.get("preview_url", "") or sample_url or file_url
        file_size = post.get("file_size", 0) or 0

        is_video = _is_video_post(post)

        keyboard = make_post_keyboard(query_id, post_id, original_tags)

        # Route through proxy so Telegram can fetch the images
        # photo_url: sample (~850px) is best for Telegram inline preview
        # thumbnail_url: preview (~150px) for the small thumbnail
        raw_photo = sample_url or preview_url or file_url
        raw_thumb = preview_url
        photo_url = _proxy_url(raw_photo)
        thumbnail_url = _proxy_url(raw_thumb)

        logger.debug(
            "Post #%s: file=%s sample=%s preview=%s video=%s size=%s",
            post_id, bool(file_url), bool(sample_url), bool(preview_url), is_video, file_size
        )

        if not raw_photo:
            logger.warning(
                "Post #%s: empty photo_url! file=%s sample=%s preview=%s",
                post_id,
                file_url[:80] if file_url else "EMPTY",
                sample_url[:80] if sample_url else "EMPTY",
                preview_url[:80] if preview_url else "EMPTY",
            )
            continue
        if not raw_thumb:
            logger.warning("Post #%s: empty thumbnail_url!", post_id)
            continue

        if is_video and file_size >= 20 * 1024 * 1024:
            # Video >= 20MB: show as photo with warning
            _large_video_results[(user_id, str(post_id))] = post_id
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
                    video_url=_proxy_url(file_url),
                    thumbnail_url=thumbnail_url,
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
        # Only offer a next page when we fetched a full batch
        next_offset = str(pid + 1) if len(posts) >= 50 else ""

    logger.info("Sending %d results, next_offset='%s'", len(results), next_offset)
    await inline_query.answer(results, next_offset=next_offset, cache_time=30)


async def handle_chosen_inline_result(chosen: ChosenInlineResult, bot: Bot) -> None:
    """Handle when user taps an inline result — edit caption for large videos."""
    result_id = chosen.result_id
    inline_message_id = chosen.inline_message_id

    if not inline_message_id:
        return

    # Look up the chosen result among tracked large videos (keyed by user+result_id)
    key = (chosen.from_user.id, result_id)
    post_id = _large_video_results.pop(key, None)
    if post_id is None:
        return

    try:
        query_id = await db.save_recent_query(chosen.from_user.id, "")
        await bot.edit_message_caption(
            inline_message_id=inline_message_id,
            caption="⚠️ Файл превышает 20 МБ и не может быть отправлен.",
            reply_markup=make_post_keyboard(query_id, post_id, ""),
        )
    except TelegramBadRequest as e:
        logger.warning("Failed to edit caption for large video %s: %s", post_id, e)
    except Exception as e:
        logger.error("Error handling chosen result %s: %s", result_id, e)
