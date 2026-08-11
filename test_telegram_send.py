"""Test 2: Send downloaded images to Telegram via bot API.
Reads files from test_downloads/ and tries to send each as:
  1) sendPhoto (as photo) using preview, sample, and full image
  2) sendDocument (as file) for the full image

For INLINE mode simulation, also tests:
  3) answerInlineQuery with InlineQueryResultPhoto using different URL combinations

Run AFTER test_download.py!
Usage: python test_telegram_send.py [CHAT_ID]
If CHAT_ID not provided, sends to OWNER_ID from .env
Output: log.txt (appends)
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = os.getenv("OWNER_ID", "")
CHAT_ID = sys.argv[1] if len(sys.argv) > 1 else OWNER_ID

DOWNLOAD_DIR = Path("test_downloads")
LOG_FILE = Path("log.txt")

# Read the saved JSON to get post URLs
API_JSON = DOWNLOAD_DIR / "api_response.json"


def log(msg: str) -> None:
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def log_sep() -> None:
    log("-" * 80)


def build_url(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


async def api_request(session, method: str, params: dict = None, files: dict = None) -> dict:
    """Make a Telegram Bot API request, return response dict."""
    url = build_url(method)
    result = {"method": method, "ok": False, "status": 0, "response": None, "error": "", "time_ms": 0}

    try:
        start = time.monotonic()
        if files:
            async with session.post(url, data=files) as resp:
                result["status"] = resp.status
                result["response"] = await resp.json()
        else:
            async with session.get(url, params=params) as resp:
                result["status"] = resp.status
                result["response"] = await resp.json()
        result["time_ms"] = int((time.monotonic() - start) * 1000)
        result["ok"] = result["response"].get("ok", False)
        if not result["ok"]:
            result["error"] = json.dumps(result["response"].get("description", ""), ensure_ascii=False)
    except Exception as e:
        result["error"] = str(e)

    return result


async def send_photo_by_url(session, chat_id: str, photo_url: str, label: str) -> dict:
    """Try sendPhoto with a URL (this is what inline mode uses internally)."""
    log(f"    sendPhoto URL [{label}]: {photo_url[:80]}...")
    result = await api_request(session, "sendPhoto", params={
        "chat_id": chat_id,
        "photo": photo_url,
    })
    log(f"      → ok={result['ok']}, time={result['time_ms']}ms")
    if not result["ok"]:
        log(f"      → ERROR: {result['error'][:300]}")
    else:
        # Delete the sent message to avoid spam
        msg_id = result["response"].get("result", {}).get("message_id")
        if msg_id:
            await api_request(session, "deleteMessage", params={
                "chat_id": chat_id, "message_id": msg_id
            })
    return result


async def send_document_by_file(session, chat_id: str, file_path: Path, label: str) -> dict:
    """Try sendDocument with an actual file upload."""
    log(f"    sendDocument file [{label}]: {file_path.name} ({file_path.stat().st_size} bytes)")
    if not file_path.exists():
        log(f"      → SKIP: file not found")
        return {"ok": False, "error": "file not found"}

    with open(file_path, "rb") as f:
        result = await api_request(session, "sendDocument", files={
            "chat_id": (None, chat_id),
            "document": (file_path.name, f),
        })
    log(f"      → ok={result['ok']}, time={result['time_ms']}ms")
    if not result["ok"]:
        log(f"      → ERROR: {result['error'][:300]}")
    else:
        msg_id = result["response"].get("result", {}).get("message_id")
        if msg_id:
            await api_request(session, "deleteMessage", params={
                "chat_id": chat_id, "message_id": msg_id
            })
    return result


async def test_inline_simulate(session, post: dict) -> dict:
    """Simulate what the bot sends to Telegram for inline mode."""
    post_id = post.get("id")
    file_url = post.get("file_url", "")
    sample_url = post.get("sample_url", "")
    preview_url = post.get("preview_url", "")

    # Test different photo_url/thumbnail_url combinations
    combos = [
        ("file as photo, preview as thumb", file_url or sample_url, preview_url),
        ("sample as photo, preview as thumb", sample_url or preview_url, preview_url),
        ("preview as photo, preview as thumb", preview_url, preview_url),
    ]

    results = {}
    for label, photo, thumb in combos:
        if not photo or not thumb:
            results[label] = {"ok": False, "error": "empty URL"}
            log(f"    [{label}] SKIP: photo={bool(photo)}, thumb={bool(thumb)}")
            continue

        # Use answerInlineQuery - but we need a fake inline_query_id
        # Instead, use sendPhoto to test if Telegram can fetch the URLs
        log(f"    Testing combo: {label}")
        log(f"      photo_url:    {photo[:100]}")
        log(f"      thumbnail_url: {thumb[:100]}")

        # Just test if Telegram can download photo_url (sendPhoto uses same mechanism)
        r = await send_photo_by_url(session, CHAT_ID, photo, label)
        results[label] = r

    return results


async def main() -> None:
    import aiohttp

    if not BOT_TOKEN:
        log("ERROR: BOT_TOKEN not set in .env")
        return
    if not CHAT_ID:
        log("ERROR: CHAT_ID not provided and OWNER_ID not set")
        return

    log(f"\n{'='*80}")
    log(f"[{time.strftime('%H:%M:%S')}] === TEST 2: Telegram Send ===")
    log(f"Chat ID: {CHAT_ID}")
    log(f"Bot: {BOT_TOKEN[:10]}...")
    log_sep()

    # Load API response
    if not API_JSON.exists():
        log(f"ERROR: {API_JSON} not found. Run test_download.py first!")
        return

    with open(API_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("post", [])
    if isinstance(posts, dict):
        posts = [posts]

    # Test first 5 posts
    test_posts = posts[:5]
    log(f"Testing {len(test_posts)} posts from API response")

    async with aiohttp.ClientSession() as session:
        for i, post in enumerate(test_posts):
            post_id = post.get("id")
            file_url = post.get("file_url", "")
            sample_url = post.get("sample_url", "")
            preview_url = post.get("preview_url", "")
            rating = post.get("rating", "?")

            log(f"\n[{time.strftime('%H:%M:%S')}] Post #{post_id} ({i+1}/{len(test_posts)})")
            log(f"  Rating: {rating}")
            log(f"  file_url:    {file_url[:100]}")
            log(f"  sample_url:  {sample_url[:100]}")
            log(f"  preview_url: {preview_url[:100]}")

            # --- A) Test sendPhoto with URL (mimics what inline mode does) ---
            log(f"\n  --- A) sendPhoto by URL (like inline mode) ---")

            # A1: photo_url = file_url (what bot currently does - WRONG)
            if file_url:
                await send_photo_by_url(session, CHAT_ID, file_url, "file_url (current bot)")
                await asyncio.sleep(0.5)

            # A2: photo_url = sample_url (proposed fix)
            if sample_url:
                await send_photo_by_url(session, CHAT_ID, sample_url, "sample_url (proposed fix)")
                await asyncio.sleep(0.5)

            # A3: photo_url = preview_url (smallest)
            if preview_url:
                await send_photo_by_url(session, CHAT_ID, preview_url, "preview_url (thumbnail)")
                await asyncio.sleep(0.5)

            # --- B) Test sendDocument with actual file (bypasses URL fetching) ---
            log(f"\n  --- B) sendDocument with file upload ---")

            full_file = DOWNLOAD_DIR / f"{post_id}_full.jpg"
            if not full_file.exists():
                full_file = DOWNLOAD_DIR / f"{post_id}_full.png"
            if not full_file.exists():
                full_file = DOWNLOAD_DIR / f"{post_id}_full.webp"

            if full_file.exists():
                await send_document_by_file(session, CHAT_ID, full_file, "full image")
                await asyncio.sleep(0.5)
            else:
                log(f"    Full image file not found (skipped)")

            log_sep()

    log(f"\n[{time.strftime('%H:%M:%S')}] === TEST 2 DONE ===")
    log(f"Check {LOG_FILE} for full log")


if __name__ == "__main__":
    asyncio.run(main())
