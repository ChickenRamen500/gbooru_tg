"""Quick Gelbooru API diagnostic script.
Run inside Docker: docker compose exec bot python test_api.py
Or locally: python test_api.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GELBOORU_API_KEY", "")
USER_ID = os.getenv("GELBOORU_USER_ID", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

BASE_URL = "https://gelbooru.com/index.php"
TEST_TAGS = "1girl solo kasane_teto -1boy"


def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


async def test_api() -> None:
    import aiohttp

    print_header("ENV CHECK")
    print(f"  BOT_TOKEN:      {'OK' if BOT_TOKEN else 'EMPTY'} ({BOT_TOKEN[:10]}...)" )
    print(f"  GELBOORU_API_KEY: {'OK' if API_KEY else 'EMPTY'} ({API_KEY[:10]}...)" )
    print(f"  GELBOORU_USER_ID: {USER_ID!r}")

    print_header(f"TEST 1: Raw API call with tags: \"{TEST_TAGS}\"")

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

    print(f"  Request params: {json.dumps({k:v for k,v in params.items() if k not in ('api_key',)}, indent=4)}")
    print(f"  api_key: {API_KEY[:10]}...")
    print(f"  user_id: {USER_ID}")

    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}?page=dapi&s=post&q=index&tags={TEST_TAGS}&pid=0&limit=3&api_key={API_KEY}&user_id={USER_ID}&json=1"
        print(f"\n  GET {BASE_URL}")
        print(f"  (full URL hidden for brevity)\n")

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
                        print(f"\n  ✅ Parsed as list, {len(data)} items")
                        if data:
                            print(f"  First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                            if isinstance(data[0], dict):
                                print(f"  First item id: {data[0].get('id')}")
                                print(f"  First item file_url: {data[0].get('file_url', 'N/A')}")
                                print(f"  First item preview_url: {data[0].get('preview_url', 'N/A')}")
                    elif isinstance(data, dict):
                        print(f"\n  ⚠️ Parsed as dict (not list). Keys: {list(data.keys())}")
                        if 'post' in data:
                            posts = data['post']
                            if isinstance(posts, list):
                                print(f"  data['post'] is a list with {len(posts)} items")
                            elif isinstance(posts, dict):
                                print(f"  data['post'] is a dict. Keys: {list(posts.keys())}")
                        print(f"  Full response:\n{json.dumps(data, indent=2)[:2000]}")
                    else:
                        print(f"  ⚠️ Unexpected type: {type(data)}")
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON parse error: {e}")

        # Test 2: with rating:safe appended (what the bot actually sends)
        print_header(f"TEST 2: With rating:safe (what bot sends)")
        tags_with_rating = f"{TEST_TAGS} rating:safe"
        params2 = params.copy()
        params2["tags"] = tags_with_rating

        async with session.get(BASE_URL, params=params2) as resp2:
            print(f"  Status: {resp2.status}")
            text2 = await resp2.text()
            print(f"  Response length: {len(text2)} bytes")
            if resp2.status == 200:
                try:
                    data2 = json.loads(text2)
                    if isinstance(data2, list):
                        print(f"  ✅ Parsed as list, {len(data2)} items")
                    elif isinstance(data2, dict):
                        print(f"  ⚠️ Parsed as dict. Keys: {list(data2.keys())}")
                except json.JSONDecodeError:
                    print(f"  ❌ JSON parse error")
                print(f"  Response (first 500 chars): {text2[:500]}")


if __name__ == "__main__":
    asyncio.run(test_api())
