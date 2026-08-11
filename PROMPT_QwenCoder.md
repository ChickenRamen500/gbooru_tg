# Prompt: Telegram Gelbooru Bot — Implementation

Ты — senior Python-разработчик. Твоя задача — реализовать Telegram-бота для поиска изображений с Gelbooru по inline-режиму.

Полные требования — в файле `SRS_GelbooruBot.md` в корне репозитория. Ниже — концентрат всего необходимого для старта.

---

## Стек

- **Python 3.12+**, **aiogram 3.x**, **aiohttp**, **sqlite3** (stdlib), **asyncio**
- Docker (Dockerfile + docker-compose.yml)
- Зависимости — в `requirements.txt`

---

## Структура проекта (создай все файлы)

```
/telegram-gelbooru-bot/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
├── bot/
│   ├── __init__.py
│   ├── main.py             # Точка входа
│   ├── config.py           # from dotenv import load_dotenv; настройки
│   ├── db.py               # SQLite: init, helpers
│   ├── gelbooru.py         # API клиент + rate limiter (8 req/s)
│   ├── cache.py            # Дисковый кэш превью + cleanup task
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── inline.py       # inline_query handler
│   │   ├── callbacks.py    # все callback handlers
│   │   ├── commands.py     # /start, /help, admin commands
│   │   ├── messages.py     # текстовые сообщения (добавление в ЧС и т.д.)
│   │   └── keyboard.py     # кастомная клавиатура (поиски, сохранёнки, ЧС, настройки)
│   └── middleware/
│       ├── __init__.py
│       └── access.py       # проверка доступа по роли
├── cache/                  # Docker volume
└── data/                   # Docker volume (bot.db)
```

---

## Конфигурация (.env)

```
BOT_TOKEN=...
GELBOORU_API_KEY=...
GELBOORU_USER_ID=...
OWNER_ID=...
```

`config.py` — загружает переменные, экспортирует как данныекласс или модуль-константы.

---

## База данных (SQLite)

Файл: `data/bot.db`. Инициализация в `db.py`.

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    role       TEXT NOT NULL DEFAULT 'user',  -- 'user', 'vip', 'banned'
    added_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS saved_searches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    tags       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, tags)
);

CREATE TABLE IF NOT EXISTS saved_posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    post_id    INTEGER NOT NULL,
    tags       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, post_id)
);

CREATE TABLE IF NOT EXISTS blacklist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    tag        TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, tag)
);

CREATE TABLE IF NOT EXISTS settings (
    user_id    INTEGER PRIMARY KEY,
    rating     TEXT NOT NULL DEFAULT 'safe',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS recent_queries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    tags_hash  TEXT NOT NULL,
    tags       TEXT NOT NULL,
    last_used  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, tags_hash)
);

CREATE TABLE IF NOT EXISTS post_status (
    post_id    INTEGER PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'alive',  -- 'alive', 'deleted_file', 'deleted_post'
    checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## Модель доступа

4 роли: нет доступа, `user`, `vip`, `owner`.
- Владелец задаётся через `OWNER_ID` из .env
- Остальные добавляются/банируются командами владельца
- **Inline:** бот проверяет `from.id` → нет доступа = пустой результат
- **Группы:** `user` получает пустой результат. `vip` — обрабатывается
- **ЛС:** нет доступа → «Доступ закрыт»

---

## Gelbooru API клиент (`gelbooru.py`)

### Endpoint
```
https://gelbooru.com/index.php?page=dapi&s=post&q=index&api_key={KEY}&user_id={UID}&tags={TAGS}&pid={PID}&limit={LIMIT}&json=1
```

### Rate Limiter
- Глобальный: **8 запросов/сек**
- Реализация: `asyncio.Semaphore(8)` + минимальный интервал 125ms между запросами через `asyncio.Lock` + `time.monotonic()`
- Таймаут запроса: 10 секунд

### Функции

```python
async def search_posts(tags: str, pid: int = 0, limit: int = 50) -> list[dict]
    """Поиск постов. Возвращает список dict из JSON Gelbooru API."""

async def get_post(post_id: int) -> dict | None
    """Получить один пост по ID. None если не найден."""

async def check_file_alive(file_url: str) -> bool
    """HEAD-запрос к file_url. True если 200 + image/video content-type."""
```

Ответ Gelbooru API для поста (relevant fields):
```json
{
  "id": 1234567,
  "created_at": "2024-01-15T14:30:00+00:00",
  "file_url": "https://...",
  "file_size": 2400000,
  "width": 1920,
  "height": 1080,
  "tags": "tag1 tag2 artist:xxx character:yyy copyright:zzz",
  "source": "https://pixiv.net/...",
  "rating": "safe",
  "sample_url": "https://...",
  "preview_url": "https://...",
  "has_notes": false,
  "score": 150
}
```

Теги приходят одной строкой. Artist-теги содержат префикс `artist:`, character — `character:`, copyright — `copyright:`. Остальные — общие теги. Парси по префиксам.

---

## Inline handler (`handlers/inline.py`)

### Логика

1. Получить `inline_query` → извлечь `query` (теги), `from.id`, `from.is_bot` (игнорить ботов)
2. **Проверка доступа:** middleware или вручную. Нет доступа → пустой `InlineQueryResults`
3. **Чёрный список:** получить теги ЧС пользователя из БД. Добавить их к запросу с минусом (`-blacklisted_tag`), чтобы Gelbooru сам их исключил
4. **Рейтинг по умолчанию:** если в тегах нет `rating:`, подставить из настроек пользователя
5. **Пагинация:** `offset` из inline_query → `pid` для Gelbooru (int, по умолчанию 0)
6. **Сохранить запрос в `recent_queries`:** `md5(user_id + tags)` → UPSERT → получить `query_id`
7. **Запрос к Gelbooru:** `search_posts(tags, pid, 50)`
8. **Фильтр дубликатов:** хранить `set[post_id]` в памяти (ключ: `user_id + normalized_tags`). Пропускать дубликаты. При обнаружении → прекратить подгрузку, вернуть Article «Больше результатов нет»
9. **Фильтр чёрного списка (дополнительно):** проверить каждый пост на наличие тегов из ЧС (на случай если Gelbooru вернул пост с тегом несмотря на минус-тег)
10. **Построить InlineQueryResults:**

### Типы результатов

**Фото (image/video, file_size < 20MB или не видео):**
```python
InlineQueryResultPhoto(
    id=str(post['id']),
    photo_url=post['file_url'],    # или sample_url для экономии трафика
    thumb_url=post['preview_url'],
    caption='...',                  # можно пустую
    reply_markup=make_post_keyboard(query_id, post['id'], tags)
)
```

**Видео < 20 МБ:**
```python
InlineQueryResultVideo(
    id=str(post['id']),
    video_url=post['file_url'],
    thumb_url=post['preview_url'],
    mime_type='video/mp4',
    title=f'Post #{post["id"]}',
    reply_markup=make_post_keyboard(query_id, post['id'], tags)
)
```

**Видео/GIF ≥ 20 МБ:**
```python
InlineQueryResultPhoto(
    id=str(post['id']),
    photo_url=post['sample_url'],   # sample вместо оригинала
    thumb_url=post['preview_url'],
    caption='⚠️ Файл превышает 20 МБ',
    reply_markup=make_post_keyboard(query_id, post['id'], tags)
)
```

### Кнопки под медиа

```python
def make_post_keyboard(query_id: int, post_id: int, tags: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📌 Сохранить поиск", callback_data=f"sq:{query_id}"),
            InlineKeyboardButton(text="ℹ️ Инфо", callback_data=f"i:{post_id}"),
            InlineKeyboardButton(text="🔗", url=f"https://gelbooru.com/index.php?page=post&s=view&id={post_id}"),
            InlineKeyboardButton(text="🔁", switch_inline_query_current_chat=tags),
        ]
    ])
```

**ВАЖНО:** `callback_data` строго ≤ 64 байта. `sq:{query_id}` и `i:{post_id}` — короткие числовые ID, влезают. `switch_inline_query_current_chat` — **не имеет** лимита 64 байт.

### chosen_inline_result

Когда пользователь тапает на результат:
- Получаем `inline_message_id` и `result_id` (= post_id)
- Если пост — видео ≥ 20 МБ: отредактировать caption отправленного сообщения через `bot.edit_message_caption(inline_message_id=..., caption="⚠️ Файл превышает 20 МБ", reply_markup=...)`

### Пустой результат
```python
[InlineQueryResultArticle(
    id='empty',
    title='Ничего не найдено',
    description=f'По тегам: {tags}',
    input_message_content=InputTextMessageContent(message_text='Ничего не найдено')
)]
```

---

## Callback handlers (`handlers/callbacks.py`)

Все callback_data парсятся по префиксу:

### `sq:{query_id}` — Сохранить поиск
1. Найти `recent_queries` по id
2. Не найдена → `answerCallbackQuery("⚠️ История устарела. Повторите поиск.")`
3. UPSERT в `saved_searches` (UNIQUE на user_id+tags → игнорим дубликат)
4. `answerCallbackQuery("✅ Поиск сохранён")`

### `i:{post_id}` — Инфо
1. **Проверка поста:**
   - Запросить `post_status` из БД
   - Если `alive` и `checked_at` < 24ч → OK
   - Если `deleted_*` → §5.5 (❌ кнопки)
   - Иначе → проверить через Gelbooru API + HEAD `file_url` → обновить `post_status`
2. Запросить пост через `get_post(post_id)`
3. Спарсить теги по категориям (префиксы `artist:`, `character:`, `copyright:`)
4. Отправить **reply-сообщение** к медиа:

```
🖼 Post #{post_id}

🎨 **Artist:** `artist1` `artist2`
👤 **Character:** `char1` `char2`
©️ **Copyright:** `series1`
🏷 **Tags:** `tag1` `tag2` ... (до 15)

📊 **Statistics:**
ID: {post_id}
Posted: {created_at}
Size: {width}×{height} ({file_size_human})
Source: {source}
Rating: {rating}
```

- Каждый тег — **отдельный** inline `\`code\`` блок (при тапе в Telegram копируется только этот тег)
- Максимум **15 тегов** на секцию. Остальные: `... и ещё N`

5. Кнопки под сообщением-инфо:
```python
InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📐 Посмотреть в оригинале", callback_data=f"fs:{post_id}")],
    [InlineKeyboardButton(text="🗑️ Удалить сообщение", callback_data="delmsg")],
])
```

### `fs:{post_id}` — Посмотреть в оригинале
1. Проверить пост (та же логика что в `i:` — статус + HEAD)
2. Получить `file_url` и `file_size` из API
3. **< 20 МБ:** скачать `aiohttp`, отправить в **личку** (`user_id`) как документ (`bot.send_document`)
4. **≥ 20 МБ:** отправить в личку текст + кнопку 🔗
5. `answerCallbackQuery("✅ Файл отправлен в личные сообщения" или ошибка)`
6. Если бот не может написать в ЛС → `answerCallbackQuery("⚠️ Начните диалог с @{bot_username}")`

### `delmsg` — Удалить сообщение с инфо
- Удалить сообщение, к которому привязан callback

### `del_search:{query_id}` — Удалить сохранённый поиск
- Удалить из `saved_searches` по query_id
- `answerCallbackQuery("🗑️ Поиск удалён")`

### `del_saved:{post_id}` — Удалить сохранённый пост
- Удалить из `saved_posts`
- `answerCallbackQuery("🗑️ Пост удалён из сохранённых")`

### `use_search:{query_id}` — Использовать сохранённый поиск
- Найти теги в `saved_searches` или `recent_queries`
- `answerInlineQuery` не работает из callback — используем `switch_inline_query_current_chat`

### Удалённый пост (общая логика)

Когда проверка показывает что пост/файл удалён:
1. Обновить `post_status` = `deleted_file` или `deleted_post`
2. `answerCallbackQuery("❌ Пост удалён с Gelbooru")`
3. Отредактировать сообщение с медиа: заменить все callback-кнопки на `[❌ Удалено]`
4. Кнопка 🔗 (url) остаётся

---

## Commands (`handlers/commands.py`)

### `/start`
```
Бот для поиска изображений с Gelbooru.

Использование: @botname теги — в любом чате.

Для управления — используйте меню ниже 👇
```
+ показать кастомную клавиатуру

### `/help`
Расширенная справка: команды, кнопки, описание функционала.

### Админ-команды (только OWNER_ID)

- `/adduser <user_id или @username>` → INSERT в users с role='user'. Если @username — сначала получить user_id из предыдущего взаимодействия.
- `/ban <user_id>` → UPDATE users SET role='banned'
- `/vip <user_id>` → UPDATE users SET role='vip'
- `/unvip <user_id>` → UPDATE users SET role='user'
- `/users` → список: user_id, username, role, added_at

---

## Кастомная клавиатура (`handlers/keyboard.py`)

### Главная (ReplyKeyboardMarkup)
```python
ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Мои поиски"), KeyboardButton(text="❤️ Сохранённые")],
        [KeyboardButton(text="🚫 Чёрный список"), KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True,
)
```

Обработка текстовых сообщений из клавиатуры — в `messages.py`:
- «📌 Мои поиски» → показать список `saved_searches` с inline-кнопками
- «❤️ Сохранённые» → показать сетку `saved_posts` с пагинацией
- «🚫 Чёрный список» → показать ЧС + кнопки управления
- «⚙️ Настройки» → показать текущий рейтинг + inline-кнопки выбора

### Настройки — рейтинг
```python
InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Safe", callback_data="set_rating:safe"),
        InlineKeyboardButton(text="Questionable", callback_data="set_rating:questionable"),
        InlineKeyboardButton(text="Explicit", callback_data="set_rating:explicit"),
        InlineKeyboardButton(text="All", callback_data="set_rating:all"),
    ]
])
```

---

## Кэш превью (`cache.py`)

- Путь: `cache/thumbs/{post_id}.{ext}`
- TTL: 24 часа
- Фоновый cleanup: `asyncio.Task`, каждые 6 часов, удаляет файлы старше 24ч
- Функция:

```python
async def get_or_cache_thumbnail(post_id: int, url: str) -> str
    """Возвращает локальный путь к файлу. Если нет — скачивает."""
```

---

## Middleware доступа (`middleware/access.py`)

Aiogram middleware (используй `BaseMiddleware`):
- Для inline queries: проверить `from.id` в таблице users
- Для сообщений в личке: аналогично
- OWNER_ID всегда имеет полный доступ

---

## Docker

### Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "bot.main"]
```

### docker-compose.yml
```yaml
services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
```

---

## Критически важно

1. **callback_data ≤ 64 байта** — используй только короткие числовые ID. Никаких тегов в callback_data.
2. **Проверка удаления поста** — API может вернуть JSON, но файл мёртв. Всегда HEAD к `file_url` + кэшируй результат в `post_status`.
3. **Rate limiter** — строго 8 req/s. Используй семафор + таймер.
4. **Видео ≥ 20 МБ** — показывай как фото с thumbnail + caption об ошибке.
5. **Кнопка 🔁** — `switch_inline_query_current_chat` (не callback). Лимит 64 байт на неё не распространяется.
6. **Теги в «Инфо»** — каждый тег в отдельном `` `code` `` блоке. До 15 на секцию.
7. **Чёрный список** — фильтрация постов (пропускать посты с тегами из ЧС), не просто тегов запроса.
8. **Inline в группах** — только для VIP. Остальные — пустой результат.
9. **Зацикливание** — отслеживание post_id в памяти. При дубле — стоп подгрузки.
10. **Кэш превью** — автоматическая очистка каждые 6 часов, TTL 24ч.

---

## Порядок реализации

1. `config.py`, `db.py` — конфигурация и БД
2. `gelbooru.py` — API клиент с rate limiter
3. `cache.py` — кэш превью
4. `middleware/access.py` — проверка доступа
5. `handlers/inline.py` — основной inline handler
6. `handlers/callbacks.py` — все callback handlers
7. `handlers/commands.py` — команды
8. `handlers/messages.py` + `handlers/keyboard.py` — клавиатура и текстовые обработчики
9. `main.py` — сборка и запуск
10. `Dockerfile` + `docker-compose.yml` + `.env.example`
11. Протестировать: `docker-compose up --build`

---

**Начинай реализацию. Создай все файлы проекта. Код должен быть production-ready: обработка ошибок, логирование (logging), type hints, docstrings.**