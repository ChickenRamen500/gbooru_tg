"""Thumbnail caching module."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache" / "thumbs"
TTL_SECONDS = 24 * 60 * 60  # 24 hours
CLEANUP_INTERVAL = 6 * 60 * 60  # 6 hours


def init_cache() -> None:
    """Initialize cache directory."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Cache directory initialized at {CACHE_DIR}")


def _get_extension(url: str) -> str:
    """Extract file extension from URL."""
    url_lower = url.lower().split("?")[0]  # strip query string
    if url_lower.endswith(".png"):
        return ".png"
    if url_lower.endswith(".webp"):
        return ".webp"
    if url_lower.endswith(".gif"):
        return ".gif"
    if url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
        return ".jpg"
    return ".jpg"


async def get_or_cache_thumbnail(
    session: aiohttp.ClientSession, post_id: int, url: str
) -> Optional[Path]:
    """Get cached thumbnail or download it."""
    ext = _get_extension(url)
    cache_path = CACHE_DIR / f"{post_id}{ext}"

    # Check if exists and not expired
    if cache_path.exists():
        mtime = cache_path.stat().st_mtime
        if time.time() - mtime < TTL_SECONDS:
            return cache_path
        else:
            try:
                cache_path.unlink()
            except OSError:
                pass

    # Download thumbnail
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                cache_path.write_bytes(content)
                logger.debug(f"Cached thumbnail {post_id}")
                return cache_path
    except Exception as e:
        logger.warning(f"Failed to cache thumbnail {post_id}: {e}")

    return None


async def cleanup_old_thumbnails() -> None:
    """Remove thumbnails older than TTL."""
    now = time.time()
    removed_count = 0

    try:
        for file_path in CACHE_DIR.glob("*"):
            if file_path.is_file():
                mtime = file_path.stat().st_mtime
                if now - mtime > TTL_SECONDS:
                    try:
                        file_path.unlink()
                        removed_count += 1
                    except OSError as e:
                        logger.warning(f"Failed to remove {file_path}: {e}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} old thumbnails")


async def start_cleanup_task() -> asyncio.Task:
    """Start background cleanup task."""

    async def cleanup_loop():
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL)
            await cleanup_old_thumbnails()

    task = asyncio.create_task(cleanup_loop())
    logger.info("Started thumbnail cleanup task")
    return task
