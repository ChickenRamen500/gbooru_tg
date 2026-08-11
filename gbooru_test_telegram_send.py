"""TEST 2: Проверяет, может ли TELEGRAM скачать картинку по Gelbooru URL.

Это КЛЮЧЕВОЙ тест. Он имитирует то, что происходит при инлайн-режиме:
Telegram получает URL и сам скачивает картинку со своего сервера.

Запускай ПРЯМО на сервере (не в докере!):
  python test_telegram_send.py
  python test_telegram_send.py ЧАТ_ID

Если не указать CHAT_ID — берёт OWNER_ID из .env.
Важно: бот должен быть ОСТАНОВЛЕН (docker compose down), иначе будет конфликт.

Вывод: test2_result.txt (туда же, куда test1)
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
API_KEY = os.getenv("GELBOORU_API_KEY", "")
USER_ID = os.getenv("GELBOORU_USER_ID", "")

BASE_URL = "https://gelbooru.com/index.php"
RESULT_FILE = Path("test2_result.txt")


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def telegram_send_photo(session, chat_id: str, photo_url: str, label: str) -> dict:
    """Отправить photo через Telegram Bot API (POST с URL).

    Telegram сам скачает картинку по URL — это то же самое,
    что происходит при инлайн-результате.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    result = {"ok": False, "error": "", "time_ms": 0, "msg_id": None}

    log(f"  [{label}]")
    log(f"    URL: {photo_url[:120]}")

    try:
        start = time.monotonic()
        # POST с form-data — Telegram документация рекомендует POST
        data = {"chat_id": chat_id, "photo": photo_url}
        async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp_json = await resp.json()
        result["time_ms"] = int((time.monotonic() - start) * 1000)

        if resp_json.get("ok"):
            result["ok"] = True
            msg_id = resp_json["result"].get("message_id")
            result["msg_id"] = msg_id
            log(f"    ✅ ОК за {result['time_ms']}ms (msg #{msg_id})")

            # Удалить сообщение чтобы не засорять чат
            if msg_id:
                del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                await session.post(del_url, data={"chat_id": chat_id, "message_id": msg_id})
        else:
            error_desc = resp_json.get("description", "unknown")
            error_code = resp_json.get("error_code", "?")
            result["error"] = f"{error_code}: {error_desc}"
            log(f"    ❌ ОШИБКА за {result['time_ms']}ms")
            log(f"    {result['error'][:300]}")

    except Exception as e:
        result["error"] = str(e)[:300]
        log(f"    ❌ ИСКЛЮЧЕНИЕ: {result['error']}")

    return result


async def main() -> None:
    import aiohttp

    RESULT_FILE.write_text("", encoding="utf-8")

    if not BOT_TOKEN:
        log("❌ BOT_TOKEN не задан в .env!")
        return
    if not CHAT_ID:
        log("❌ CHAT_ID не указан и OWNER_ID не задан в .env!")
        log("   Укажи: python test_telegram_send.py ТВОЙ_TELEGRAM_ID")
        return

    log("=" * 70)
    log("TEST 2: Отправка картинок через Telegram Bot API")
    log(f"Chat ID: {CHAT_ID}")
    log(f"Bot token: {BOT_TOKEN[:10]}...")
    log("=" * 70)

    # Step 1: Get posts from Gelbooru API
    log("\n[ШАГ 1] Получаем посты от Gelbooru API...")
    params = {
        "page": "dapi", "s": "post", "q": "index",
        "tags": "1girl solo", "pid": 0, "limit": 3,
        "api_key": API_KEY, "user_id": USER_ID, "json": "1",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            api_text = await resp.text()

        if resp.status != 200:
            log(f"❌ API вернул {resp.status}")
            return

        data = json.loads(api_text)
        posts = data.get("post", [])
        if isinstance(posts, dict):
            posts = [posts]
        log(f"  ✅ Получено {len(posts)} постов")

        # Step 2: Test sendPhoto with different URLs
        log("\n[ШАГ 2] Тестируем sendPhoto (Telegram скачивает URL сам):")

        preview_ok = 0
        preview_fail = 0
        sample_ok = 0
        sample_fail = 0

        for i, post in enumerate(posts):
            post_id = post.get("id")
            preview_url = post.get("preview_url", "")
            sample_url = post.get("sample_url", "")
            file_url = post.get("file_url", "")

            log(f"\n--- Пост #{post_id} ({i+1}/{len(posts)}) ---")

            # A) preview_url as photo (самое важное — это thumbnail_url в инлайне)
            if preview_url:
                r = await telegram_send_photo(session, CHAT_ID, preview_url, "preview_url (thumbnail)")
                if r["ok"]:
                    preview_ok += 1
                else:
                    preview_fail += 1
                await asyncio.sleep(1)
            else:
                log(f"  [preview_url] ПУСТОЙ — пропускаем")
                preview_fail += 1

            # B) sample_url as photo (это photo_url в инлайне)
            if sample_url:
                r = await telegram_send_photo(session, CHAT_ID, sample_url, "sample_url (photo)")
                if r["ok"]:
                    sample_ok += 1
                else:
                    sample_fail += 1
                await asyncio.sleep(1)
            else:
                log(f"  [sample_url] ПУСТОЙ — пропускаем")

    # Summary
    log("\n" + "=" * 70)
    log("РЕЗУЛЬТАТЫ:")
    log(f"  preview_url (thumbnail): {preview_ok} ✅ / {preview_fail} ❌")
    log(f"  sample_url (photo):      {sample_ok} ✅ / {sample_fail} ❌")
    log("")

    if preview_ok > 0 and sample_ok > 0:
        log("🟢🟢 ВЫВОД: Telegram МОЖЕТ скачать И preview И sample с Gelbooru!")
        log("   Инлайн-режим ДОЛЖЕН работать с прямыми URL.")
        log("   ➜ Убедись что PUBLIC_URL в .env ПУСТОЙ или отсутствует.")
        log("   ➜ Пересобери бот: docker compose build --no-cache && docker compose up -d")
    elif preview_ok > 0:
        log("🟡 ВЫВОД: Preview работает, но sample — нет.")
        log("   Проблема может быть в размере файла (sample больше).")
        log("   ➜ Как временное решение: использовать preview_url для обоих полей.")
    else:
        log("🔴 ВЫВОД: Telegram НЕ МОЖЕТ скачать картинки с Gelbooru по URL!")
        log("   Это значит Gelbooru блокирует запросы от серверов Telegram.")
        log("")
        log("   РЕШЕНИЕ — нужен общедоступный прокси. Варианты:")
        log("   1) cloudflared tunnel — бесплатно, проброс порта через Cloudflare:")
        log("      a) Зарегистрируйся на cloudflare.com, создай домен (или используешь свой)")
        log("      b) Установи cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        log("      c) Запусти: cloudflared tunnel --url http://localhost:3001")
        log("      d) Получишь публичный URL вида https://xxx.trycloudflare.com")
        log("      e) Поставь PUBLIC_URL=https://xxx.trycloudflare.com в .env")
        log("   2) VPS с белым IP (от $3/мес) — развернуть прокси там")

    log("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
