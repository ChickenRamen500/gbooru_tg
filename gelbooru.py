"""Gelbooru API client with rate limiting."""

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp

from config import config
import cache

logger = logging.getLogger(__name__)

GELBOORU_API_URL = "https://gelbooru.com/index.php"
RATE_LIMIT = 8  # requests per second
RATE_LIMIT_INTERVAL = 1.0 / RATE_LIMIT  # ~125ms


class GelbooruClient:
    """Async Gelbooru API client with rate limiting."""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(RATE_LIMIT)
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def _rate_limit(self) -> None:
        """Apply rate limiting to requests."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < RATE_LIMIT_INTERVAL:
                await asyncio.sleep(RATE_LIMIT_INTERVAL - elapsed)
            self._last_request_time = time.monotonic()

    async def _request(self, params: dict[str, Any]) -> Optional[list | dict]:
        """Make a request to Gelbooru API with rate limiting."""
        async with self._semaphore:
            await self._rate_limit()
            session = await self._get_session()

            # Mask api_key for logging
            safe_params = {k: ('***' if k == 'api_key' else v) for k, v in params.items()}
            logger.debug("Gelbooru request: %s", safe_params)
            
            params["api_key"] = config.gelbooru_api_key
            params["user_id"] = config.gelbooru_user_id
            params["json"] = "1"

            try:
                async with session.get(GELBOORU_API_URL, params=params) as response:
                    body = await response.read()
                    if response.status == 200:
                        logger.info("Gelbooru response: status=%d, size=%d bytes", response.status, len(body))
                        data = await response.json()
                        # Log count if available
                        if isinstance(data, dict) and "@attributes" in data:
                            attrs = data["@attributes"]
                            if isinstance(attrs, dict) and "count" in attrs:
                                logger.debug("Gelbooru API count: %s", attrs['count'])
                        return data
                    elif response.status == 404:
                        logger.info("Gelbooru response: status=404")
                        return None
                    else:
                        logger.warning("Gelbooru API returned status %d", response.status)
                        return None
            except asyncio.TimeoutError:
                logger.error("Gelbooru API request timed out")
                return None
            except Exception as e:
                logger.error("Gelbooru API request failed: %s", e)
                return None

    async def search_posts(
        self, tags: str, pid: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search posts on Gelbooru. Results are cached for 10 minutes."""
        cache_key = f"search:{tags}|{pid}|{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("search_posts: %d posts (CACHE HIT)", len(cached))
            return cached

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags,
            "pid": pid,
            "limit": limit,
        }

        logger.info("search_posts: tags='%s', pid=%d, limit=%d", tags, pid, limit)

        data = await self._request(params)
        posts: list[dict[str, Any]] = []
        if data is None:
            logger.info("search_posts: 0 posts (data=None)")
        elif isinstance(data, list):
            posts = data
            logger.info("search_posts: %d posts (list response)", len(posts))
        elif isinstance(data, dict):
            if "post" in data:
                raw = data["post"]
                if isinstance(raw, list):
                    posts = raw
                    logger.info("search_posts: %d posts (dict['post'] list)", len(posts))
                elif isinstance(raw, dict):
                    posts = [raw]
                    logger.info("search_posts: 1 post (dict['post'] single)")
            elif "id" in data:
                posts = [data]
                logger.info("search_posts: 1 post (single dict)")

        # Cache even empty results to avoid hammering the API for tags
        # that return nothing, but with a shorter TTL.
        cache.set(cache_key, posts, ttl=cache.DEFAULT_TTL if posts else 60)
        return posts

    async def get_post(self, post_id: int) -> Optional[dict[str, Any]]:
        """Get a single post by ID. Cached for 1 hour (posts rarely change)."""
        cache_key = f"post:{post_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("get_post: %d (CACHE HIT)", post_id)
            return cached

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "id": post_id,
            "limit": 1,
        }

        data = await self._request(params)
        post: Optional[dict[str, Any]] = None
        if data is None:
            return None
        if isinstance(data, list) and len(data) > 0:
            post = data[0]
        elif isinstance(data, dict):
            if "post" in data:
                raw = data["post"]
                if isinstance(raw, list) and len(raw) > 0:
                    post = raw[0]
                elif isinstance(raw, dict):
                    post = raw
            elif "id" in data:
                post = data

        if post is not None:
            cache.set(cache_key, post, ttl=cache.POST_TTL)
        return post

    async def check_file_alive(self, file_url: str) -> bool:
        """Check if a file URL is accessible via HEAD request."""
        session = await self._get_session()
        try:
            async with session.head(
                file_url,
                allow_redirects=True,
                headers={
                    "Referer": "https://gelbooru.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            ) as response:
                if response.status != 200:
                    return False
                content_type = response.headers.get("Content-Type", "")
                return content_type.startswith(("image/", "video/"))
        except Exception as e:
            logger.warning(f"Failed to check file {file_url}: {e}")
            return False

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global client instance
gelbooru_client = GelbooruClient()
