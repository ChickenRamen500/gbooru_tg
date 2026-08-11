"""Test: Download images from Gelbooru with and without proxy.

Saves files to ./test_output/ (accessible on host, not inside Docker).
Also tests the Cloudflare Worker proxy if PUBLIC_URL is set.

Run on HOST:  python test_download.py
Run in Docker: docker compose exec bot python test_download.py
              docker compose cp bot:/app/test_output ./test_output

Output: ./test_output/ folder with images, ./test_output/log.txt
"""

import asyncio
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

load_dotenv()

API_KEY = os.getenv("GELBOORU_API_KEY", "")
USER_ID = os.getenv("GELBOORU_USER_ID", "")
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")

BASE_URL = "https://gelbooru.com/index.php"
TEST_TAGS = "1girl solo"
LIMIT = 5
DOWNLOAD_DIR = Path("test_output")
LOG_FILE = DOWNLOAD_DIR / "log.txt"

GELBOORU_HEADERS = {
    "Referer": "https://gelbooru.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def log(msg: str) -> None:
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def log_sep() -> None:
    log("-" * 80)


async def download_file(session, url: str, save_path: Path, headers: dict = None) -> dict:
    """Download a file, return status dict."""
    result = {"url": url, "status": "", "size": 0, "content_type": "", "time_ms": 0}
    start = time.monotonic()
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            result["status"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            if resp.status == 200:
                content = await resp.read()
                result["size"] = len(content)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(content)
            else:
                result["error"] = await resp.text()
    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)
    result["time_ms"] = int((time.monotonic() - start) * 1000)
    return result


def proxy_url(original_url: str) -> str:
    """Build proxy URL using the same format as the bot."""
    if not PUBLIC_URL:
        return ""
    from urllib.parse import quote
    return f"{PUBLIC_URL}/proxy.jpg?url={quote(original_url, safe='')}"


async def main() -> None:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    LOG_FILE.write_text("", encoding="utf-8")

    log(f"[{time.strftime('%H:%M:%S')}] === Gelbooru Download Test ===")
    log(f"Tags: {TEST_TAGS}")
    log(f"Limit: {LIMIT}")
    log(f"Output: {DOWNLOAD_DIR.absolute()}")
    log(f"PUBLIC_URL: {PUBLIC_URL or '(not set)'}")
    log_sep()

    # Step 1: API request
    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "tags": TEST_TAGS,
        "pid": 0,
        "limit": LIMIT,
        "api_key": API_KEY,
        "user_id": USER_ID,
        "json": "1",
    }

    async with aiohttp.ClientSession() as session:
        log(f"[{time.strftime('%H:%M:%S')}] Requesting Gelbooru API...")
        async with session.get(BASE_URL, params=params) as resp:
            api_text = await resp.text()

        if resp.status != 200:
            log(f"  ERROR: API returned {resp.status}")
            log(f"  Response: {api_text[:500]}")
            return

        data = json.loads(api_text)
        posts = data.get("post", []) if isinstance(data, dict) else data
        if isinstance(posts, dict):
            posts = [posts]
        log(f"  Got {len(posts)} posts")

        # Save JSON
        with open(DOWNLOAD_DIR / "api_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log_sep()

        # Step 2: Download images for each post
        for i, post in enumerate(posts):
            post_id = post.get("id")
            file_url = post.get("file_url", "")
            sample_url = post.get("sample_url", "")
            preview_url = post.get("preview_url", "")

            log(f"\nPost #{post_id} ({i+1}/{len(posts)})")
            log(f"  preview: {preview_url[:100]}")
            log(f"  sample:  {sample_url[:100]}")
            log(f"  file:    {file_url[:100]}")

            # A) Download preview WITH Referer header (direct)
            if preview_url:
                log(f"  [A] preview with Referer (direct):")
                r = await download_file(session, preview_url, DOWNLOAD_DIR / f"{post_id}_preview_direct.jpg", GELBOORU_HEADERS)
                log(f"    status={r['status']}, size={r['size']}B, type={r['content_type']}")
                if r["content_type"] and not r["content_type"].startswith("image/"):
                    log(f"    NOT AN IMAGE! Got HTML/other content instead.")

            # B) Download preview via Cloudflare Worker proxy
            if preview_url and PUBLIC_URL:
                p_url = proxy_url(preview_url)
                log(f"  [B] preview via proxy:")
                log(f"    URL: {p_url[:120]}")
                r = await download_file(session, p_url, DOWNLOAD_DIR / f"{post_id}_preview_proxy.jpg")
                log(f"    status={r['status']}, size={r['size']}B, type={r['content_type']}")
                if r["content_type"] and not r["content_type"].startswith("image/"):
                    log(f"    NOT AN IMAGE! Proxy not working?")

            # C) Download sample WITH Referer header
            if sample_url:
                log(f"  [C] sample with Referer (direct):")
                r = await download_file(session, sample_url, DOWNLOAD_DIR / f"{post_id}_sample_direct.jpg", GELBOORU_HEADERS)
                log(f"    status={r['status']}, size={r['size']}B, type={r['content_type']}")
                if r["content_type"] and not r["content_type"].startswith("image/"):
                    log(f"    NOT AN IMAGE!")

            # D) Download sample via proxy
            if sample_url and PUBLIC_URL:
                p_url = proxy_url(sample_url)
                log(f"  [D] sample via proxy:")
                log(f"    URL: {p_url[:120]}")
                r = await download_file(session, p_url, DOWNLOAD_DIR / f"{post_id}_sample_proxy.jpg")
                log(f"    status={r['status']}, size={r['size']}B, type={r['content_type']}")

            await asyncio.sleep(0.5)

    log_sep()
    log(f"\n[{time.strftime('%H:%M:%S')}] === DONE ===")
    log(f"Files saved to: {DOWNLOAD_DIR.absolute()}")
    if not PUBLIC_URL:
        log("\nTIP: Set PUBLIC_URL in .env to also test the Cloudflare Worker proxy.")


if __name__ == "__main__":
    asyncio.run(main())
