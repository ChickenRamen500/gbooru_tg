"""In-memory cache for Gelbooru API responses.

The previous version cached thumbnails on disk, but that function was never
called (inline mode proxies images via Cloudflare Worker, and Telegram caches
on its own side). The whole module was effectively dead code.

This rewrite provides an in-memory TTL cache for API responses
(search results, single posts), which:
  * reduces the number of Gelbooru API calls (respecting the 8 req/s limit),
  * makes repeated searches and repeated info/full-size lookups instant,
  * gives the admin "🔄 Сбросить кэш" button a real effect.
"""

import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default TTLs (seconds)
DEFAULT_TTL = 10 * 60          # 10 minutes for search results
POST_TTL = 60 * 60             # 1 hour for single posts (rarely change)
CLEANUP_INTERVAL = 10 * 60     # prune expired entries every 10 minutes

# key -> (value, expire_at_monotonic)
_cache: dict[str, tuple[Any, float]] = {}


def init_cache() -> None:
    """Initialize the in-memory cache. Kept for startup symmetry."""
    _cache.clear()
    logger.info("In-memory API cache initialized")


def get(key: str) -> Optional[Any]:
    """Return cached value if present and not expired, else None.

    Expired entries are evicted lazily on access.
    """
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expire_at = entry
    if time.monotonic() > expire_at:
        _cache.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store a value with the given TTL (seconds)."""
    _cache[key] = (value, time.monotonic() + ttl)


def delete(key: str) -> bool:
    """Remove a single key. Returns True if it existed."""
    return _cache.pop(key, None) is not None


def clear_all() -> int:
    """Remove ALL cached entries immediately. Returns number of removed keys."""
    removed = len(_cache)
    _cache.clear()
    if removed > 0:
        logger.info("Cleared %d cached entries", removed)
    return removed


def stats() -> dict[str, int]:
    """Return basic cache statistics."""
    now = time.monotonic()
    alive = sum(1 for _, expire_at in _cache.values() if now <= expire_at)
    expired = len(_cache) - alive
    return {"total": len(_cache), "alive": alive, "expired": expired}


def cleanup_expired() -> int:
    """Remove all expired entries. Returns number of removed entries."""
    now = time.monotonic()
    expired_keys = [k for k, (_, expire_at) in _cache.items() if now > expire_at]
    for k in expired_keys:
        _cache.pop(k, None)
    if expired_keys:
        logger.info("Cleaned up %d expired cache entries", len(expired_keys))
    return len(expired_keys)


async def start_cleanup_task() -> asyncio.Task:
    """Start background task that periodically prunes expired entries."""

    async def cleanup_loop():
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL)
            try:
                cleanup_expired()
            except Exception as e:  # noqa: BLE001 - never let the loop die
                logger.error("Cache cleanup error: %s", e)

    task = asyncio.create_task(cleanup_loop())
    logger.info("Started cache cleanup task (interval=%ds)", CLEANUP_INTERVAL)
    return task


# --- Backwards-compatible aliases (old API names used in main.py) ---
# These keep main.py working without changes while reflecting the new semantics.

def clear_all_cache() -> int:
    """Backwards-compatible alias for clear_all()."""
    return clear_all()
