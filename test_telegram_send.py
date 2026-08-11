"""Test: Send images to Telegram via bot API to verify inline mode works.

Tests both direct Gelbooru URLs and proxy URLs (if PUBLIC_URL is set).
Sends photos and immediately deletes them to avoid spam.

Run on HOST:  python test_telegram_send.py [CHAT_ID]
Run in Docker: docker compose exec bot python test_telegram_send.py [CHAT_ID]

If CHAT_ID not provided, uses OWNER_ID from .env.
Bot must be STOPPED (docker compose down) to avoid token conflict.

Output: ./test_output/telegram_log.txt
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv
import aiohttp

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = os.getenv("OWNER_ID", "")
CHAT_ID = sys.argv[1] if len(sys.argv) > 1 else OWNER_ID
API_KEY = os.getenv("GELBOORU_API_KEY", "")
USER_ID = os.getenv("GELBOORU_USER_ID", "")
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")

BASE_URL = "https://gelbooru.com/index.php"
DOWNLOAD_DIR = Path("test_output")
LOG_FILE = DOWNLOAD_DIR / "telegram_log.txt"


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def proxy_url(original_url: str) -> str:
    """Build proxy URL using the same format as the bot."""
    if not PUBLIC_URL:
        return ""
    return f"{PUBLIC_URL}/proxy.jpg?url={quote(original_url, safe='')}"


def build_url(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


async def telegram_send_photo(session, chat_id: str, photo_url: str, label: str) -> dict:
    """Send photo via Telegram Bot API, then delete the message."""
    url = build_url("sendPhoto")
    result = {"ok": False, "error": "", "time_ms": 0, "msg_id": None}

    log(f"  [{label}]")
    log(f"    URL: {photo_url[:120]}")

    try:
        start = time.monotonic()
        async with session.post(url, data={"chat_id": chat_id, "photo": photo_url}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp_json = await resp.json()
        result["time_ms"] = int((time.monotonic() - start) * 1000)

        if resp_json.get("ok"):
            result["ok"] = True
            msg_id = resp_json["result"].get("message_id")
            result["msg_id"] = msg_id
            log(f"    OK {result['time_ms']}ms (msg #{msg_id})")
            # Delete message
            if msg_id:
                del_url = build_url("deleteMessage")
                await session.post(del_url, data={"chat_id": chat_id, "message_id": msg_id})
        else:
            result["error"] = f"{resp_json.get('error_code', '?')}: {resp_json.get('description', '')[:200]}"
            log(f"    FAIL {result['time_ms']}ms")
            log(f"    {result['error'][:300]}")
    except Exception as e:
        result["error"] = str(e)[:300]
        log(f"    EXCEPTION: {result['error']}")

    return result


async def main() -> None:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    LOG_FILE.write_text("", encoding="utf-8")

    if not BOT_TOKEN:
        log("ERROR: BOT_TOKEN not set in .env")
        return
    if not CHAT_ID:
        log("ERROR: CHAT_ID not provided and OWNER_ID not set")
        log("   Usage: python test_telegram_send.py YOUR_TELEGRAM_ID")
        return

    log("=" * 70)
    log("TEST: Send images to Telegram via Bot API")
    log(f"Chat ID: {CHAT_ID}")
    log(f"PUBLIC_URL: {PUBLIC_URL or '(not set - testing direct URLs only)'}")
    log("=" * 70)

    # Get posts from Gelbooru API
    log("\n[Step 1] Fetching posts from Gelbooru API...")
    params = {
        "page": "dapi", "s": "post", "q": "index",
        "tags": "1girl solo", "pid": 0, "limit": 3,
        "api_key": API_KEY, "user_id": USER_ID, "json": "1",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            api_text = await resp.text()

        if resp.status != 200:
            log(f"ERROR: API returned {resp.status}")
            return

        data = json.loads(api_text)
        posts = data.get("post", [])
        if isinstance(posts, dict):
            posts = [posts]
        log(f"  Got {len(posts)} posts")

        # Test sendPhoto with different URLs
        log("\n[Step 2] Testing sendPhoto...")
        results = []

        for i, post in enumerate(posts):
            post_id = post.get("id")
            preview_url = post.get("preview_url", "")
            sample_url = post.get("sample_url", "")

            log(f"\n--- Post #{post_id} ({i+1}/{len(posts)}) ---")

            # Test 1: Direct preview URL (will fail - no Referer from Telegram)
            if preview_url:
                r = await telegram_send_photo(session, CHAT_ID, preview_url, "direct preview")
                results.append(("direct preview", r["ok"]))
                await asyncio.sleep(1)

            # Test 2: Direct sample URL (will fail)
            if sample_url:
                r = await telegram_send_photo(session, CHAT_ID, sample_url, "direct sample")
                results.append(("direct sample", r["ok"]))
                await asyncio.sleep(1)

            # Test 3: Preview via proxy (should work)
            if preview_url and PUBLIC_URL:
                p_url = proxy_url(preview_url)
                r = await telegram_send_photo(session, CHAT_ID, p_url, "proxy preview")
                results.append(("proxy preview", r["ok"]))
                await asyncio.sleep(1)

            # Test 4: Sample via proxy (should work)
            if sample_url and PUBLIC_URL:
                p_url = proxy_url(sample_url)
                r = await telegram_send_photo(session, CHAT_ID, p_url, "proxy sample")
                results.append(("proxy sample", r["ok"]))
                await asyncio.sleep(1)

    # Summary
    log("\n" + "=" * 70)
    log("RESULTS:")
    for label, ok in results:
        log(f"  {label}: {'OK' if ok else 'FAIL'}")
    log("")

    proxy_ok = [ok for l, ok in results if "proxy" in l]
    if PUBLIC_URL and all(proxy_ok):
        log("RESULT: Proxy WORKS! Inline mode should display images correctly.")
    elif PUBLIC_URL and not all(proxy_ok):
        log("RESULT: Proxy NOT working. Check your Cloudflare Worker.")
    elif not PUBLIC_URL:
        log("RESULT: Set PUBLIC_URL to test proxy. Direct URLs expected to fail.")
    log("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
