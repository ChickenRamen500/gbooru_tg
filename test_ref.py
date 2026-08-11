import aiohttp, asyncio, json, os
from dotenv import load_dotenv
load_dotenv()
async def test():
    api = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&tags=1girl+solo&pid=0&limit=1&json=1&api_key=" + os.getenv("GELBOORU_API_KEY","") + "&user_id=" + os.getenv("GELBOORU_USER_ID","")
    async with aiohttp.ClientSession() as s:
        async with s.get(api) as r:
            data = await r.json()
        url = data.get("post",[])[0].get("preview_url","")
        print("URL:", url)
        print()
        print("--- NO Referer ---")
        async with s.get(url, headers={"User-Agent": "Mozilla/5.0"}) as r:
            b = await r.read()
        print("Status:", r.status, "Type:", r.headers.get("Content-Type",""), "Size:", len(b))
        print("HTML:", b[:30])
        print()
        print("--- WITH Referer ---")
        async with s.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://gelbooru.com/"}) as r:
            b2 = await r.read()
        print("Status:", r.status, "Type:", r.headers.get("Content-Type",""), "Size:", len(b2))
        print("First 30 bytes:", b2[:30])
        print()
        ct = r.headers.get("Content-Type", "")
        if ct.startswith("image/"):
            print("RESULT: REFERER WORKS!")
        else:
            print("RESULT: REFERER NOT HELP")
asyncio.run(test())