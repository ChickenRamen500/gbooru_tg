"""Gelbooru API client with rate limiting."""

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp

from config import config

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
            log_params = {k: v for k, v in params.items()}
            if "api_key" in log_params:
                log_params["api_key"] = "***"
            
            # Build URL for logging (without actual api_key value)
            from urllib.parse import urlencode
            query_string = urlencode(log_params)
            full_url = f"{GELBOORU_API_URL}?{query_string}"
            
            params["api_key"] = config.gelbooru_api_key
            params["user_id"] = config.gelbooru_user_id
            params["json"] = "1"

            try:
                async with session.get(GELBOORU_API_URL, params=params) as response:
                    body = await response.read()
                    logger.debug(
                        f"Gelbooru API: status={response.status}, body_size={len(body)}, url={full_url}"
                    )
                    if response.status == 200:
                        data = await response.json()
                        # Log count if available
                        if isinstance(data, dict) and "@attributes" in data:
                            attrs = data["@attributes"]
                            if isinstance(attrs, dict) and "count" in attrs:
                                logger.debug(f"Gelbooru API count: {attrs['count']}")
                        return data
                    elif response.status == 404:
                        return None
                    else:
                        logger.warning(f"Gelbooru API returned status {response.status}")
                        return None
            except asyncio.TimeoutError:
                logger.error("Gelbooru API request timed out")
                return None
            except Exception as e:
                logger.error(f"Gelbooru API request failed: {e}")
                return None

    async def search_posts(
        self, tags: str, pid: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search posts on Gelbooru."""
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags,
            "pid": pid,
            "limit": limit,
        }

        logger.debug(f"search_posts: tags='{tags}', pid={pid}, limit={limit}")

        data = await self._request(params)
        if data is None:
            return []
        if isinstance(data, list):
            logger.debug(f"search_posts parsed {len(data)} posts from list response")
            return data
        if isinstance(data, dict):
            if "post" in data:
                posts = data["post"]
                if isinstance(posts, list):
                    logger.debug(f"search_posts parsed {len(posts)} posts from dict['post']")
                    return posts
                if isinstance(posts, dict):
                    logger.debug("search_posts parsed 1 post from dict['post'] (single)")
                    return [posts]
            if "id" in data:
                logger.debug("search_posts parsed 1 post from dict (single post)")
                return [data]
        logger.debug("search_posts parsed 0 posts")
        return []

    async def get_post(self, post_id: int) -> Optional[dict[str, Any]]:
        """Get a single post by ID."""
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "id": post_id,
            "limit": 1,
        }

        data = await self._request(params)
        if data is None:
            return None
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        if isinstance(data, dict):
            if "post" in data:
                posts = data["post"]
                if isinstance(posts, list) and len(posts) > 0:
                    return posts[0]
                if isinstance(posts, dict):
                    return posts
            if "id" in data:
                return data
        return None

    async def check_file_alive(self, file_url: str) -> bool:
        """Check if a file URL is accessible via HEAD request."""
        session = await self._get_session()
        try:
            async with session.head(file_url, allow_redirects=True) as response:
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
