"""Callback query handlers."""

import logging
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Optional

import aiohttp
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.exceptions import TelegramBadRequest

import db
from gelbooru import gelbooru_client
from handlers.keyboard import (
    make_info_keyboard, 
    make_post_keyboard,
    make_settings_keyboard,
    make_rating_keyboard,
    make_blacklist_keyboard,
    make_users_manage_keyboard,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _parse_tags(tags_string: str) -> dict[str, list[str]]:
    """Parse tags by category.
    
    Gelbooru returns tags in a specific order: artist, copyright, character, general.
    Tags may or may not have prefixes like 'artist:', 'copyright:', etc.
    We use the order to determine categories if prefixes are missing.
    """
    result = {"artist": [], "character": [], "copyright": [], "general": []}
    
    if not tags_string:
        return result
    
    tags = tags_string.split()
    
    # Check if tags have prefixes
    has_prefixes = any(":" in tag for tag in tags[:10])  # Check first 10 tags
    
    if has_prefixes:
        # Parse by prefixes
        for tag in tags:
            if tag.startswith("artist:"):
                result["artist"].append(tag[7:])
            elif tag.startswith("character:"):
                result["character"].append(tag[12:])
            elif tag.startswith("copyright:"):
                result["copyright"].append(tag[12:])
            elif tag.startswith("meta:"):
                result["general"].append(tag[5:])
            else:
                result["general"].append(tag)
    else:
        # Parse by order: artist(s) -> copyright(s) -> character(s) -> general
        # This is the standard Gelbooru order
        i = 0
        n = len(tags)
        
        # Artists: usually 1-3 tags at the beginning
        while i < n and i < 5:  # Max 5 artists
            # Stop if we hit a known copyright tag pattern
            if tags[i] in ["original", "commission"]:
                break
            result["artist"].append(tags[i])
            i += 1
        
        # Copyrights: series names, games, etc.
        copyright_start = i
        while i < n and i < copyright_start + 5:  # Max 5 copyrights
            # Common copyright patterns or stop if looks like character/general
            result["copyright"].append(tags[i])
            i += 1
        
        # Characters: usually specific names
        char_start = i
        while i < n and i < char_start + 10:  # Max 10 characters
            result["character"].append(tags[i])
            i += 1
        
        # General: everything else
        while i < n:
            result["general"].append(tags[i])
            i += 1
    
    return result


def _format_tags_section(tags: list[str], max_count: int = 15) -> str:
    """Format tags as comma-separated list with underscores escaped, max N tags."""
    if not tags:
        return ""

    displayed = tags[:max_count]
    # Escape underscores for Markdown, but keep them readable (not in code blocks)
    formatted = ", ".join(tag.replace('_', '\\_') for tag in displayed)

    if len(tags) > max_count:
        remaining = len(tags) - max_count
        formatted += f" ... и ещё {remaining}"

    return formatted


def _get_extension(url: str) -> str:
    """Get file extension from URL."""
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".png"):
        return ".png"
    if url_lower.endswith(".webp"):
        return ".webp"
    if url_lower.endswith(".mp4"):
        return ".mp4"
    if url_lower.endswith(".webm"):
        return ".webm"
    if url_lower.endswith(".gif"):
        return ".gif"
    return ".jpg"


async def _check_post_status(post_id: int) -> tuple[str, Optional[dict]]:
    """
    Check post status and return (status, post_data).
    status: 'alive', 'deleted_file', 'deleted_post'
    """
    cached = await db.get_post_status(post_id)
    now = datetime.now()

    if cached:
        try:
            checked_at = datetime.fromisoformat(cached["checked_at"])
            age = now - checked_at

            if cached["status"] == "alive" and age < timedelta(hours=24):
                return "alive", None
            elif cached["status"] in ("deleted_file", "deleted_post") and age < timedelta(hours=24):
                return cached["status"], None
        except (ValueError, TypeError):
            pass

    # Recheck from API
    post = await gelbooru_client.get_post(post_id)

    if post is None:
        await db.update_post_status(post_id, "deleted_post")
        return "deleted_post", None

    # If the API returns the post, it's alive.
    # We don't check the file URL separately because Gelbooru's CDN
    # returns unreliable results for HEAD requests even with Referer.
    await db.update_post_status(post_id, "alive")
    return "alive", post


async def _mark_post_deleted(callback: CallbackQuery) -> None:
    """Edit the inline message to show deleted state."""
    try:
        if callback.inline_message_id:
            dead_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Удалено", callback_data="noop")]
                ]
            )
            await callback.bot.edit_message_reply_markup(
                inline_message_id=callback.inline_message_id,
                reply_markup=dead_keyboard,
            )
    except TelegramBadRequest:
        pass
    except Exception as e:
        logger.warning(f"Failed to mark post as deleted: {e}")


async def handle_save_search(callback: CallbackQuery, query_id: int, user_id: int) -> None:
    """Handle save search callback."""
    recent = await db.get_recent_query(query_id)

    if not recent:
        await callback.answer(
            "⚠️ История поиска устарела. Повторите поиск.", show_alert=True
        )
        return

    tags = recent["tags"]
    success, message = await db.save_search(user_id, tags)
    await callback.answer(message, show_alert=not success)


async def handle_info(callback: CallbackQuery, post_id: int) -> None:
    """Handle info callback."""
    logger.info("Info callback: post_id=%d, user_id=%d", post_id, callback.from_user.id)
    status, post = await _check_post_status(post_id)
    logger.info("Post #%d status: %s", post_id, status)

    if status != "alive":
        await callback.answer("❌ Пост удалён с Gelbooru", show_alert=True)
        await _mark_post_deleted(callback)
        return

    if not post:
        post = await gelbooru_client.get_post(post_id)

    if not post:
        await callback.answer("❌ Пост не найден", show_alert=True)
        await _mark_post_deleted(callback)
        return

    tags_str = post.get("tags", "")
    parsed = _parse_tags(tags_str)

    lines = [f"🖼 Post #{post_id}", ""]

    if parsed["artist"]:
        lines.append(f"🎨 **Artist:** {_format_tags_section(parsed['artist'])}")
    if parsed["character"]:
        lines.append(f"👤 **Character:** {_format_tags_section(parsed['character'])}")
    if parsed["copyright"]:
        lines.append(f"©️ **Copyright:** {_format_tags_section(parsed['copyright'])}")
    if parsed["general"]:
        lines.append(f"🏷 **Tags:** {_format_tags_section(parsed['general'])}")

    lines.append("")
    lines.append("📊 **Statistics:**")
    lines.append(f"ID: {post_id}")

    created_at = post.get("created_at", "Unknown")
    if isinstance(created_at, str):
        created_at = created_at.split("T")[0]
    lines.append(f"Posted: {created_at}")

    width = post.get("width", 0) or 0
    height = post.get("height", 0) or 0
    file_size = post.get("file_size", 0) or 0
    lines.append(f"Size: {width}×{height} ({_format_file_size(file_size)})")

    source = post.get("source", "")
    if source:
        lines.append(f"Source: {source}")

    rating = post.get("rating", "unknown")
    lines.append(f"Rating: {rating}")

    info_text = "\n".join(lines)

    try:
        if callback.inline_message_id:
            # Inline message: bot didn't send the message itself,
            # so callback.message is None. Edit the inline caption instead.
            # Telegram caption limit is 1024 chars.
            caption = info_text[:1020] + "..." if len(info_text) > 1024 else info_text
            await callback.bot.edit_message_caption(
                inline_message_id=callback.inline_message_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=make_info_keyboard(post_id),
            )
        else:
            # Regular message: send a new message with info
            await callback.message.answer(
                info_text,
                parse_mode="Markdown",
                reply_markup=make_info_keyboard(post_id),
                reply_to_message_id=callback.message.message_id,
            )
    except Exception as e:
        logger.error("Failed to send info: %s", e)
        await callback.answer("Не удалось отправить информацию", show_alert=True)
        return

    await callback.answer()


async def handle_full_size(
    callback: CallbackQuery, post_id: int, user_id: int, bot_username: str
) -> None:
    """Handle full size download callback."""
    status, post = await _check_post_status(post_id)

    if status != "alive":
        await callback.answer("❌ Пост удалён с Gelbooru", show_alert=True)
        await _mark_post_deleted(callback)
        return

    if not post:
        post = await gelbooru_client.get_post(post_id)

    if not post:
        await callback.answer("❌ Пост не найден", show_alert=True)
        return

    file_url = post.get("file_url", "")
    file_size = post.get("file_size", 0) or 0

    if file_size >= MAX_FILE_SIZE:
        gelbooru_link = f"https://gelbooru.com/index.php?page=post&s=view&id={post_id}"
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=f"⚠️ Файл превышает 20 МБ\n\n🔗 [Открыть оригинал на Gelbooru]({gelbooru_link})",
                parse_mode="Markdown",
            )
            await callback.answer("⚠️ Файл слишком большой, ссылка отправлена в ЛС")
        except TelegramBadRequest as e:
            if "bot can't initiate conversation" in str(e).lower():
                await callback.answer(
                    f"⚠️ Для получения файлов начните диалог с @{bot_username}",
                    show_alert=True,
                )
            else:
                raise
        return

    # Сначала отвечаем на callback, чтобы избежать таймаута
    # Отправляем сообщение о начале загрузки
    try:
        await callback.answer("⏳ Файл будет отправлен в ближайшее время...")
    except TelegramBadRequest:
        pass  # Query мог истечь, но продолжаем работу

    # Определяем тип контекста для отправки уведомления
    is_inline = callback.inline_message_id is not None
    
    # Download and send file
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                file_url,
                headers={
                    "Referer": "https://gelbooru.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            ) as response:
                if response.status != 200:
                    if is_inline:
                        try:
                            await callback.message.answer("❌ Не удалось скачать файл")
                        except Exception:
                            pass
                    else:
                        await callback.answer("❌ Не удалось скачать файл", show_alert=True)
                    return

                content = await response.read()
                filename = f"post_{post_id}{_get_extension(file_url)}"

                file_obj = BufferedInputFile(
                    content,
                    filename=filename,
                )

                # Отправляем файл
                if is_inline:
                    # Вызов из чата: отправляем новым сообщением в ЛС
                    await callback.bot.send_document(
                        chat_id=user_id,
                        document=file_obj,
                        caption=f"Post #{post_id}",
                    )
                    # И уведомление в чат (если message доступен)
                    try:
                        await callback.message.answer(f"✅ Файл Post #{post_id} отправлен в личные сообщения")
                    except Exception:
                        pass
                else:
                    # Вызов из ЛС с ботом: отправляем в ответ на исходное сообщение
                    await callback.bot.send_document(
                        chat_id=user_id,
                        document=file_obj,
                        caption=f"Post #{post_id}",
                        reply_to_message_id=callback.message.message_id if callback.message else None,
                    )
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "bot can't initiate conversation" in error_msg:
            await callback.answer(
                f"⚠️ Для получения файлов начните диалог с @{bot_username}",
                show_alert=True,
            )
        elif "query is too old" in error_msg:
            logger.warning(f"Callback query expired during file send: {e}")
            # Файл мог быть отправлен, просто query истек
            if is_inline:
                try:
                    await callback.message.answer("⚠️ Задержка при отправке. Проверьте ЛС.")
                except Exception:
                    pass
        else:
            logger.error(f"Failed to send file: {e}")
            if is_inline:
                try:
                    await callback.message.answer("❌ Ошибка при отправке файла")
                except Exception:
                    pass
            else:
                await callback.answer("❌ Ошибка при отправке файла", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to download/send file: {e}")
        if is_inline:
            try:
                await callback.message.answer("❌ Ошибка при загрузке файла")
            except Exception:
                pass
        else:
            await callback.answer("❌ Ошибка при загрузке файла", show_alert=True)


async def handle_delete_message(callback: CallbackQuery) -> None:
    """Handle delete message callback."""
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message: {e}")
    await callback.answer()


async def handle_delete_search(callback: CallbackQuery, search_id: int, user_id: int) -> None:
    """Handle delete saved search callback."""
    deleted = await db.delete_saved_search(search_id, user_id)
    if deleted:
        await callback.answer("🗑️ Поиск удалён")
    else:
        await callback.answer("Поиск не найден", show_alert=True)


async def handle_delete_saved_post(
    callback: CallbackQuery, post_id: int, user_id: int
) -> None:
    """Handle delete saved post callback."""
    deleted = await db.delete_saved_post(post_id, user_id)
    if deleted:
        await callback.answer("🗑️ Пост удалён из сохранённых")
    else:
        await callback.answer("Пост не найден", show_alert=True)


async def handle_delete_subscription(callback: CallbackQuery, sub_id: int, user_id: int) -> None:
    """Handle delete subscription callback."""
    deleted = await db.remove_subscription(sub_id, user_id)
    if deleted:
        await callback.answer("🗑️ Подписка удалена")
    else:
        await callback.answer("Подписка не найдена", show_alert=True)
