"""Quick Gelbooru API diagnostic script.

Run on HOST:  python test_api.py
Run in Docker: docker compose exec bot python test_api.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

API_KEY = os.getenv("GELBOORU_API_KEY", "")
USER_ID = os.getenv("GELBOORU_USER_ID", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

BASE_URL = "https://gelbooru.com/index.php"
TEST_TAGS = "1girl solo kasane_teto"


def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


async def test_api() -> None:
    print_header("ENV CHECK")
    print(f"  BOT_TOKEN:       {'OK' if BOT_TOKEN else 'EMPTY'}")
    print(f"  GELBOORU_API_KEY: {'OK' if API_KEY else 'EMPTY'}")
    print(f"  GELBOORU_USER_ID: {USER_ID!r}")

    print_header(f"API call with tags: \"{TEST_TAGS}\"")

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "tags": TEST_TAGS,
        "pid": 0,
        "limit": 3,
        "api_key": API_KEY,
        "user_id": USER_ID,
        "json": "1",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params) as resp:
            print(f"  Status: {resp.status}")
            print(f"  Content-Type: {resp.headers.get('Content-Type')}")

            text = await resp.text()
            print(f"  Response length: {len(text)} bytes")
            print(f"  Response (first 2000 chars):\n")
            print(text[:2000])

            if resp.status == 200:
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        print(f"\n  Parsed as list, {len(data)} items")
                        if data:
                            print(f"  First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                            if isinstance(data[0], dict):
                                print(f"  First item id: {data[0].get('id')}")
                                print(f"  First item rating: {data[0].get('rating', 'N/A')}")
                                print(f"  First item file_url: {data[0].get('file_url', 'N/A')}")
                                print(f"  First item preview_url: {data[0].get('preview_url', 'N/A')}")
                    elif isinstance(data, dict):
                        print(f"\n  Parsed as dict. Keys: {list(data.keys())}")
                        if 'post' in data:
                            posts = data['post']
                            if isinstance(posts, list):
                                print(f"  data['post'] is a list with {len(posts)} items")
                                if posts:
                                    print(f"  First post rating: {posts[0].get('rating', 'N/A')}")
                except json.JSONDecodeError as e:
                    print(f"  JSON parse error: {e}")


if __name__ == "__main__":
    asyncio.run(test_api())
