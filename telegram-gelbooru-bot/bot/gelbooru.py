"""Gelbooru API client with rate limiting."""

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp

from .config import config

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

    async def _request(self, params: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Make a request to Gelbooru API with rate limiting."""
        async with self._semaphore:
            await self._rate_limit()
            session = await self._get_session()

            params["api_key"] = config.gelbooru_api_key
            params["user_id"] = config.gelbooru_user_id
            params["json"] = "1"

            try:
                async with session.get(GELBOORU_API_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
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
        """
        Search posts on Gelbooru.

        Args:
            tags: Space-separated tags string
            pid: Page ID (for pagination)
            limit: Number of results (max 50 for inline)

        Returns:
            List of post dictionaries from JSON response
        """
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "tags": tags,
            "pid": pid,
            "limit": limit,
        }

        data = await self._request(params)
        if data and isinstance(data, list):
            return data
        elif data and isinstance(data, dict) and "post" in data:
            # Some API responses wrap posts in "post" key
            posts = data["post"]
            if isinstance(posts, list):
                return posts
            elif isinstance(posts, dict):
                return [posts]
        return []

    async def get_post(self, post_id: int) -> Optional[dict[str, Any]]:
        """
        Get a single post by ID.

        Args:
            post_id: Post ID

        Returns:
            Post dictionary or None if not found
        """
        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "id": post_id,
            "limit": 1,
        }

        data = await self._request(params)
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        elif data and isinstance(data, dict):
            if "post" in data:
                posts = data["post"]
                if isinstance(posts, list) and len(posts) > 0:
                    return posts[0]
                elif isinstance(posts, dict):
                    return posts
            if "id" in data:
                return data
        return None

    async def check_file_alive(self, file_url: str) -> bool:
        """
        Check if a file URL is accessible via HEAD request.

        Args:
            file_url: URL to the file

        Returns:
            True if file exists and is an image/video
        """
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
