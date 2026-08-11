"""Image proxy server for Gelbooru.

Gelbooru blocks direct access from Telegram servers (hotlink protection).
This proxy downloads images with proper headers and serves them to Telegram.

Run: python image_proxy.py
Listens on port 3001.
"""

import hashlib
import logging
import os
import time
from pathlib import Path

import aiohttp
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.getenv("PROXY_CACHE_DIR", "cache/proxy"))
CACHE_TTL = int(os.getenv("PROXY_CACHE_TTL", "86400"))  # 24 hours
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Only allow proxying from these domains
ALLOWED_DOMAINS = (
    "gelbooru.com",
    "img.gelbooru.com",
    "img1.gelbooru.com",
    "img2.gelbooru.com",
    "img3.gelbooru.com",
    "img4.gelbooru.com",
    "img5.gelbooru.com",
)


def _url_to_cache_path(url: str) -> Path:
    """Convert URL to a local cache file path."""
    h = hashlib.sha256(url.encode()).hexdigest()
    ext = ".jpg"
    lower = url.lower().split("?")[0]
    for e in (".png", ".webp", ".gif", ".jpeg", ".webm", ".mp4"):
        if lower.endswith(e):
            ext = e
            break
    return CACHE_DIR / h[:2] / f"{h}{ext}"


def _is_cache_valid(path: Path) -> bool:
    """Check if cached file exists and is fresh."""
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < CACHE_TTL


def _is_allowed_url(url: str) -> bool:
    """Check if URL is from an allowed domain."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).hostname or ""
        return domain.endswith(ALLOWED_DOMAINS) or any(
            domain == d for d in ALLOWED_DOMAINS
        )
    except Exception:
        return False


async def proxy_handler(request: web.Request) -> web.Response:
    """Proxy an image from Gelbooru."""
    url = request.query.get("url", "")
    if not url:
        return web.Response(status=400, text="Missing url parameter")

    if not _is_allowed_url(url):
        logger.warning("Blocked proxy request to non-allowed domain: %s", url[:100])
        return web.Response(status=403, text="Domain not allowed")

    cache_path = _url_to_cache_path(url)

    # Serve from cache if valid
    if _is_cache_valid(cache_path):
        logger.debug("Cache hit: %s", url[:80])
        try:
            content = cache_path.read_bytes()
            # Determine content type from extension
            ext = cache_path.suffix.lower()
            ct_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
                ".webm": "video/webm",
                ".mp4": "video/mp4",
            }
            ct = ct_map.get(ext, "image/jpeg")
            return web.Response(
                body=content,
                content_type=ct,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "X-Cache": "HIT",
                },
            )
        except Exception as e:
            logger.warning("Failed to read cache %s: %s", cache_path, e)

    # Fetch from Gelbooru
    logger.info("Fetching: %s", url[:100])
    try:
        # Use a short-lived session with Referer header
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                url,
                headers={
                    "Referer": "https://gelbooru.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    logger.warning("Upstream returned %d for %s", resp.status, url[:80])
                    return web.Response(status=resp.status, text=f"Upstream error: {resp.status}")

                content_type = resp.headers.get("Content-Type", "image/jpeg")
                content = await resp.read()

                if len(content) > MAX_FILE_SIZE:
                    logger.warning("File too large: %d bytes for %s", len(content), url[:80])
                    return web.Response(status=413, text="File too large")

                if not content_type.startswith(("image/", "video/")):
                    logger.warning(
                        "Non-media content type '%s' for %s", content_type, url[:80]
                    )
                    return web.Response(
                        status=502,
                        text=f"Upstream returned non-media content: {content_type}",
                    )

                # Save to cache
                try:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(content)
                except Exception as e:
                    logger.warning("Failed to cache %s: %s", cache_path, e)

                logger.info("Proxied %d bytes (%s) from %s", len(content), content_type, url[:80])

                return web.Response(
                    body=content,
                    content_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=86400",
                        "X-Cache": "MISS",
                    },
                )
    except asyncio.TimeoutError:
        logger.error("Timeout fetching %s", url[:80])
        return web.Response(status=504, text="Upstream timeout")
    except Exception as e:
        logger.error("Error fetching %s: %s", url[:80], e)
        return web.Response(status=502, text=f"Proxy error: {e}")


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.Response(text="OK")


async def on_startup(app: web.Application) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Image proxy started, cache dir: %s", CACHE_DIR.resolve())


app = web.Application()
app.router.add_get("/proxy", proxy_handler)
app.router.add_get("/health", health_handler)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    import asyncio
    web.run_app(app, host="0.0.0.0", port=3001)
