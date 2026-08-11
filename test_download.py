"""Test 1: Download first 10 posts from Gelbooru with images.
Save JSON response + thumbnail + full image for each post.
Run: python test_download.py
Output: log.txt, downloads/ folder, api_response.json
"""

import asyncio
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GELBOORU_API_KEY", "")
USER_ID = os.getenv("GELBOORU_USER_ID", "")

BASE_URL = "https://gelbooru.com/index.php"
TEST_TAGS = "1girl solo kasane_teto"
LIMIT = 10
DOWNLOAD_DIR = Path("test_downloads")
LOG_FILE = Path("log.txt")


def log(msg: str) -> None:
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def log_sep() -> None:
    log("-" * 80)


async def download_file(session, url: str, save_path: Path) -> dict:
    """Download a file, return status dict."""
    result = {"url": url, "status": "", "size": 0, "content_type": "", "time_ms": 0}
    try:
        start = time.monotonic()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
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
        result["time_ms"] = int((time.monotonic() - start) * 1000)
    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)
        result["time_ms"] = int((time.monotonic() - start) * 1000) if "start" in dir() else 0
    return result


async def main() -> None:
    import aiohttp

    # Clear log
    LOG_FILE.write_text("", encoding="utf-8")
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    log(f"[{time.strftime('%H:%M:%S')}] === TEST 1: Gelbooru Download ===")
    log(f"Tags: {TEST_TAGS}")
    log(f"Limit: {LIMIT}")
    log(f"Output dir: {DOWNLOAD_DIR.absolute()}")
    log_sep()

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
        # Step 1: API request
        log(f"[{time.strftime('%H:%M:%S')}] Requesting API...")
        start = time.monotonic()
        async with session.get(BASE_URL, params=params) as resp:
            api_status = resp.status
            api_text = await resp.text()
        api_time = int((time.monotonic() - start) * 1000)

        log(f"  Status: {api_status} ({api_time}ms)")
        log(f"  Response size: {len(api_text)} bytes")

        if api_status != 200:
            log(f"  ERROR: API returned {api_status}")
            log(f"  Response: {api_text[:500]}")
            return

        # Parse JSON
        try:
            data = json.loads(api_text)
        except json.JSONDecodeError as e:
            log(f"  ERROR: JSON parse failed: {e}")
            return

        # Extract posts
        if isinstance(data, dict) and "post" in data:
            posts = data["post"]
            total_count = data.get("@attributes", {}).get("count", "?")
        elif isinstance(data, list):
            posts = data
            total_count = len(data)
        else:
            log(f"  ERROR: Unexpected response structure: {type(data)}")
            return

        if not isinstance(posts, list):
            posts = [posts]

        log(f"  Total posts on Gelbooru: {total_count}")
        log(f"  Posts in response: {len(posts)}")

        # Save full JSON
        json_path = DOWNLOAD_DIR / "api_response.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log(f"  Saved JSON: {json_path}")
        log_sep()

        # Step 2: Download images for each post
        for i, post in enumerate(posts):
            post_id = post.get("id")
            file_url = post.get("file_url", "")
            sample_url = post.get("sample_url", "")
            preview_url = post.get("preview_url", "")
            rating = post.get("rating", "?")
            width = post.get("width", "?")
            height = post.get("height", "?")
            file_size = post.get("file_size", 0) or 0

            log(f"\n[{time.strftime('%H:%M:%S')}] Post #{post_id} ({i+1}/{len(posts)})")
            log(f"  Rating: {rating}, Size: {width}x{height}, File size: {file_size}")
            log(f"  file_url:    {file_url}")
            log(f"  sample_url:  {sample_url}")
            log(f"  preview_url: {preview_url}")

            # Download preview (thumbnail)
            if preview_url:
                preview_path = DOWNLOAD_DIR / f"{post_id}_preview.jpg"
                log(f"  Downloading preview...")
                result = await download_file(session, preview_url, preview_path)
                log(f"    → status={result['status']}, size={result['size']} bytes, "
                    f"type={result['content_type']}, time={result['time_ms']}ms")
                if "error" in result:
                    log(f"    → ERROR: {result['error'][:200]}")
            else:
                log(f"  preview_url is EMPTY")

            # Download sample
            if sample_url:
                sample_path = DOWNLOAD_DIR / f"{post_id}_sample.jpg"
                log(f"  Downloading sample...")
                result = await download_file(session, sample_url, sample_path)
                log(f"    → status={result['status']}, size={result['size']} bytes, "
                    f"type={result['content_type']}, time={result['time_ms']}ms")
                if "error" in result:
                    log(f"    → ERROR: {result['error'][:200]}")
            else:
                log(f"  sample_url is EMPTY")

            # Download full image
            if file_url:
                ext = file_url.rsplit(".", 1)[-1].split("?")[0][:4]
                full_path = DOWNLOAD_DIR / f"{post_id}_full.{ext}"
                log(f"  Downloading full image...")
                result = await download_file(session, file_url, full_path)
                log(f"    → status={result['status']}, size={result['size']} bytes, "
                    f"type={result['content_type']}, time={result['time_ms']}ms")
                if "error" in result:
                    log(f"    → ERROR: {result['error'][:200]}")
            else:
                log(f"  file_url is EMPTY")

            # Rate limit: ~0.5s between downloads
            if i < len(posts) - 1:
                await asyncio.sleep(0.5)

    log_sep()
    log(f"\n[{time.strftime('%H:%M:%S')}] === DONE ===")
    log(f"Check {DOWNLOAD_DIR.absolute()} for downloaded files")
    log(f"Check {LOG_FILE.absolute()} for full log")


if __name__ == "__main__":
    asyncio.run(main())
