# SRS: Telegram Gelbooru Bot

## 1. Общее описание

Telegram-бот для поиска и отправки изображений/видео с Gelbooru по тегам через **inline-режим**. Под каждым отправленным медиа — 4 кнопки. Управление сохранёнными постами, поисками и чёрным списком — в **личке с ботом** через кастомную клавиатуру и команды.

**Стек:** Python 3.12+ / aiogram 3.x / SQLite / asyncio / aiohttp / Docker
**Деплой:** Docker на Windows Server, один контейнер, volume для БД и кэша
**Ожидаемая нагрузка:** 10–20 пользователей (закрытый бот), масштабирование не требуется

---

## 2. Модель доступа

Бот **закрытый**. Доступ только по whitelist'у владельца.

| Роль | Доступ |
|------|--------|
| **Нет доступа** | Бот игнорирует все запросы (inline, сообщения). |
| **Пользователь** | Inline в личке и личных чатах с другими пользователями. Личные команды бота. |
| **VIP** | Всё, что у пользователя + inline в **группах**. |
| **Владелец** | Всё + админ-команды (`/vip`, `/adduser`, `/ban`). |

Управление ролями — только владелец через команды.

**Проверка доступа:**
- **Inline-запросы:** бот проверяет `from.id` перед обработкой. Нет доступа → пустой результат (панель не откроется).
- **Группы:** обычные пользователи получают пустой результат. VIP — обрабатываются.
- **Личные сообщения:** нет доступа → «Доступ закрыт. Обратитесь к администратору.»

---

## 3. Основной флоу — Inline-поиск

```
Пользователь: @botname tag1 tag2 tag3
                         ↓
            Telegram отправляет inline_query боту
                         ↓
         Бот проверяет доступ + фильтрует чёрный список тегов
                         ↓
       Запрос к Gelbooru API (pid=0, limit=50, tags=...)
                         ↓
       Бот возвращает до 50 InlineQueryResultPhoto/Video
                         ↓
    Пользователь скроллит → Telegram шлёт новый inline_query
       с offset (автоматическая подгрузка страниц)
                         ↓
       Пользователь тапает на результат →
       медиа отправляется в чат С inline-кнопками
```

### 3.1. Пагинация (подгрузка)

- Telegram inline: до 50 результатов за ответ
- При прокрутке — Telegram автоматически отправляет новый `inline_query` с `offset`
- Бот парсит offset → запрашивает Gelbooru с нужным `pid`
- При получении дубликатов (Gelbooru вернул уже показанные посты) — подгрузка прекращается
- Последняя страница содержит Article-результат «✅ Больше результатов нет»

### 3.2. Кнопка 🔁 (Повторить поиск)

- Действие: `switch_inline_query_current_chat` с текущими тегами
- Telegram автоматически подставляет `@botname tag1 tag2` в строку ввода
- Inline-запрос **всегда** начинается с offset 0 (свежий поиск)
- **Обоснование:** в Telegram inline-панель скроллируема — пользователь может вернуться к любому результату текущей сессии. Сохранение offset лишало бы возможности вернуться к начальным результатам.

### 3.3. Защита от зацикливания

- Бот хранит множество `post_id` в рамках текущей сессии inline-запроса (ключ: `user_id + normalized_tags`)
- При получении поста, чей `id` уже в множестве — прекращает подгрузку
- Очистка множества: через 10 минут неактивности (TTL в памяти)

---

## 4. Кнопки под медиа

При отправке inline-результата под медиа — 4 кнопки в один ряд:

| Кнопка | Тип | Data | Действие |
|--------|-----|------|----------|
| 📌 Сохранить поиск | callback | `sq:{query_id}` | Сохраняет теги в список поисков |
| ℹ️ Инфо | callback | `i:{post_id}` | Отправляет ответное сообщение с деталями поста |
| 🔗 Ссылка | url | `gelbooru.com/...?id={id}` | Открывает пост на Gelbooru |
| 🔁 Повторить | switch_inline_query_current_chat | `{tags_string}` | Открывает строку ввода с тегами |

### 4.1. Callback data и лимит 64 байта

Теги могут быть длинными (например `kobayashi-san_chi_no_maidragon kanna_kamui toast_in_mouth bread_slice` = 76 символов). callback_data ограничен 64 байтами.

**Решение:** числовые ID через таблицу `recent_queries`.
- При обработке inline-запроса: `MD5(user_id + tags)` → UPSERT в `recent_queries` → получаем числовой ID
- В callback-кнопках используем короткий ID (`sq:42`, `i:12345678`)
- Дубликация по хешу гарантирует, что одинаковый поиск у одного пользователя всегда получает один ID
- Кнопка 🔁 использует `switch_inline_query_current_chat` — у этого поля **нет** лимита 64 байт, теги подставляются напрямую

### 4.2. Lifetime кнопок

Callback data содержит всю необходимую информацию (ID) — кнопки работают **вечно**, пока существует запись в БД. Таблица `recent_queries` не очищается (с 20 пользователями рост минимален).

---

## 5. Обработка callback-кнопок

### 5.1. 📌 Сохранить поиск (`sq:{query_id}`)

1. Декодировать `query_id` из callback_data
2. Найти запись в `recent_queries` по `id`
3. Если не найдена → `answerCallbackQuery("⚠️ История поиска устарела. Повторите поиск.")`
4. Сохранить в `saved_searches`: `(user_id, tags_string, created_at)`
5. Если уже существует → `answerCallbackQuery("Поиск уже сохранён")`
6. Если успешно → `answerCallbackQuery("✅ Поиск сохранён")`

### 5.2. ℹ️ Инфо (`i:{post_id}`)

1. Раскодировать `post_id` из callback_data
2. **Проверка существования файла** (см. §5.4)
3. Если пост недоступен → §5.5
4. Отправить **новое сообщение** (reply на медиа) с форматированием:

```
🖼 <title или "Без названия">

🎨 **Artist:** `artist1` `artist2`
👤 **Character:** `char1` `char2` `char3`
©️ **Copyright:** `series1` `series2`
🏷 **Tags:** `tag1` `tag2` `tag3` ... (до 15)

📊 **Statistics:**
ID: 1234567
Posted: 2024-01-15 14:30
Size: 1920×1080 (2.4 MB)
Source: pixiv.net/...
Rating: safe
```

- Каждый тег обёрнут в **отдельный** inline `code` блок → при тапе копируется только этот тег
- Максимум **15 тегов** на секцию. Если больше — обрезка + текст `... и ещё N`
- Категории тегов (artist/character/copyright/general) определяются через Gelbooru API

**Кнопки под сообщением-инфо:**

| Кнопка | Тип | Действие |
|--------|-----|----------|
| 📐 Посмотреть в оригинале | callback `fs:{post_id}` | Скачивает и отправляет оригинал в ЛС |
| 🗑️ Удалить сообщение | callback `delmsg` | Удаляет сообщение с инфо |

### 5.3. 📐 Посмотреть в оригинале (`fs:{post_id}`)

1. Запросить пост из Gelbooru API → получить `file_url` и `file_size`
2. **Проверка существования файла** (см. §5.4)
3. **Если < 20 МБ:**
   - Скачать файл через `aiohttp`
   - Отправить в **личку** пользователя как документ (без сжатия): `bot.send_document(chat_id=user_id, document=BufferedReader(...), caption="...")`
   - `answerCallbackQuery("✅ Файл отправлен в личные сообщения")`
4. **Если ≥ 20 МБ:**
   - Отправить в личку текстовое сообщение: «⚠️ Файл превышает 20 МБ» + кнопка 🔗 на пост
   - `answerCallbackQuery("⚠️ Файл слишком большой, ссылка отправлена в ЛС")`
5. Если пользователь не начал личку с ботом → `answerCallbackQuery("⚠️ Для получения файлов начните диалог с @botname")`

### 5.4. Проверка существования поста и файла

Gelbooru может вернуть JSON поста (теги, id, метаданные), но сам файл удалён — страница показывает "This post was deleted. Reason: ...".

```
Callback с post_id получен
        ↓
Проверка в post_status (локальный кэш БД)
        ├── status = 'alive' AND checked_at < 24ч → обрабатываем нормально
        ├── status = 'deleted_file' / 'deleted_post' → ❌ кнопки (без повторной проверки)
        └── не найден / устарел (> 24ч) →
                ↓
        Запрос к Gelbooru API → получаем JSON
                ├── Пост не найден (404/пустой ответ) → status = 'deleted_post' → ❌
                └── Пост найден →
                        ↓
                HEAD-запрос к file_url
                        ├── 200 + image/video Content-Type → status = 'alive' → OK
                        └── 404/403/HTML-ответ → status = 'deleted_file' → ❌
```

### 5.5. Обработка удалённого поста

1. `answerCallbackQuery("❌ Пост удалён с Gelbooru")`
2. Отредактировать сообщение с медиа: все callback-кнопки заменяются на `[❌ Удалено]`
3. Кнопка 🔗 остаётся (ссылка на страницу — пользователь может увидеть причину удаления)

---

## 6. Лимиты и Rate Limiting

### 6.1. Gelbooru API

| Параметр | Значение |
|----------|----------|
| Лимит запросов | 8 req/s (глобально на бота) |
| Результатов на запрос | до 50 (лимит Telegram inline) |
| API-ключ | из `.env` (`GELBOORU_API_KEY`, `GELBOORU_USER_ID`) |

**Реализация rate limiter:**
- Глобальный семафор: 8 concurrent API-запросов
- Минимальный интервал: 125ms между запросами
- Очередь (`asyncio.Queue`) для ожидающих запросов
- Таймаут запроса: 10 секунд

### 6.2. Размер файлов

| Тип | Лимит | В inline-результате | При отправке (chosen_inline_result) |
|-----|-------|---------------------|-------------------------------------|
| Фото | Без лимита | `InlineQueryResultPhoto` | Нормальная отправка |
| Видео/GIF < 20 МБ | 20 МБ | `InlineQueryResultVideo` | Нормальная отправка |
| Видео/GIF ≥ 20 МБ | 20 МБ | `InlineQueryResultPhoto` (thumbnail) | Бот редактирует caption: «⚠️ Файл превышает 20 МБ» |

**Логика для видео ≥ 20 МБ:**
1. В inline-результате показываем как фото (thumbnail)
2. При тапе → thumbnail отправляется в чат с кнопками
3. Бот получает `chosen_inline_result` → редактирует caption: «⚠️ Файл превышает 20 МБ»
4. Кнопки остаются (🔗 — ссылка на оригинал, остальные — работают)

**Проверка размера:**
- Gelbooru API возвращает `file_size` в байтах — проверяем до скачивания
- Если `file_size` не указан → HEAD-запрос для `Content-Length`
- Если HEAD не отдаёт размер → скачиваем с ограничением 20 МБ, при превышении — прерываем

---

## 7. Кэширование

| Что кэшируем | Где | TTL | Автоудаление |
|-------------|-----|-----|-------------|
| Превью (thumbnail) | Локальный диск (Docker volume) | 1 день | Фоновая задача каждые 6 часов |
| Результаты API (посты) | In-memory (dict) | 10 минут | Авто по TTL |
| Полноразмерные файлы | **Не кэшируем** | — | — |
| Статус поста (жив/удалён) | SQLite (`post_status`) | 24 часа | Перепроверка при обращении |

**Структура кэша на диске:**
```
/cache/
  /thumbs/
    {post_id}.jpg
    {post_id}.png
    {post_id}.webp
```

**Cleanup:**
- При старте бота: фоновая `asyncio.Task` с циклом каждые 6 часов
- Удаляет файлы старше 24 часов по `os.path.getmtime()`

---

## 8. Команды

### 8.1. Общие (пользователь + VIP + владелец)

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие + краткая инструкция |
| `/help` | Расширенная справка |

### 8.2. Владелец

| Команда | Описание |
|---------|----------|
| `/adduser <user_id или @username>` | Добавить (роль: пользователь) |
| `/ban <user_id или @username>` | Забанить (удалить доступ) |
| `/vip <user_id или @username>` | Назначить VIP |
| `/unvip <user_id или @username>` | Снять VIP |
| `/users` | Список всех пользователей с ролями |

---

## 9. Кастомная клавиатура (личка с ботом)

**Главная (ReplyKeyboardMarkup, resize_keyboard=True):**

```
[ 📌 Мои поиски    ] [ ❤️ Сохранённые  ]
[ 🚫 Чёрный список ] [ ⚙️ Настройки    ]
```

### 9.1. 📌 Мои поиски

- Сообщение: «**Ваши сохранённые поиски:**»
- Inline-кнопки: каждая = теги (callback `use_search:{query_id}` → `switch_inline_query_current_chat`)
- 🗑️ рядом с каждым (callback `del_search:{query_id}`)
- Нет сохранённых → «У вас нет сохранённых поисков»

### 9.2. ❤️ Сохранённые посты

- Сетка медиа (2-3 в ряд) через `send_media_group` / `InputMediaPhoto`
- Кнопки: 🗑️ удалить (`del_saved:{post_id}`), очистить все (`clear_saved` с подтверждением)
- Пагинация: если > 6 постов → кнопки ← → (`saved_page:{n}`)
- Нет сохранённых → «У вас нет сохранённых постов»

### 9.3. 🚫 Чёрный список тегов

- Сообщение: «**Чёрный список:** `tag1` `tag2` `tag3`»
- ➕ Добавить → бот ждёт текстовое сообщение с тегом
- 🗑️ рядом с каждым тегом → удалить
- **Фильтрация:** при inline-запросе, посты содержащие теги из ЧС пользователя — пропускаются (не показываются)

### 9.4. ⚙️ Настройки

Единственная настройка — **рейтинг по умолчанию:**
- Варианты: `safe` / `questionable` / `explicit` / `all`
- Inline-кнопки для выбора
- Если пользователь не указал рейтинг в тегах → подставляется из настроек как `rating:safe` и т.д.

---

## 10. База данных (SQLite)

```sql
-- Пользователи и роли
CREATE TABLE users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    role       TEXT NOT NULL DEFAULT 'user',
    added_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Сохранённые поиски
CREATE TABLE saved_searches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    tags       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, tags)
);

-- Сохранённые посты
CREATE TABLE saved_posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    post_id    INTEGER NOT NULL,
    tags       TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, post_id)
);

-- Чёрный список тегов
CREATE TABLE blacklist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    tag        TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, tag)
);

-- Настройки пользователя
CREATE TABLE settings (
    user_id    INTEGER PRIMARY KEY,
    rating     TEXT NOT NULL DEFAULT 'safe',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Недавние запросы (для коротких callback_data)
CREATE TABLE recent_queries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    tags_hash  TEXT NOT NULL,
    tags       TEXT NOT NULL,
    last_used  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, tags_hash)
);

-- Кэш статуса постов
CREATE TABLE post_status (
    post_id    INTEGER PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'alive',
    checked_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 11. Структура проекта

```
/telegram-gelbooru-bot/
├── Dockerfile
├── docker-compose.yml
├── .env
├── requirements.txt
├── bot/
│   ├── __init__.py
│   ├── main.py             # Точка входа, запуск бота
│   ├── config.py           # Загрузка .env
│   ├── db.py               # SQLite инициализация, хелперы
│   ├── gelbooru.py         # Gelbooru API клиент + rate limiter
│   ├── cache.py            # Кэширование превью на диске + cleanup
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── inline.py       # Inline query handler
│   │   ├── callbacks.py    # Callback query handlers
│   │   ├── commands.py     # /start, /help, /vip, /adduser, etc.
│   │   ├── messages.py     # Текстовые сообщения (добавление в ЧС)
│   │   └── keyboard.py     # Кастомная клавиатура
│   └── middleware/
│       ├── __init__.py
│       └── access.py       # Проверка доступа
├── cache/                  # Volume mount
└── data/
    └── bot.db              # Volume mount
```

---

## 12. Docker

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
```

```
# .env
BOT_TOKEN=...
GELBOORU_API_KEY=...
GELBOORU_USER_ID=...
OWNER_ID=...
```

---

## 13. Edge Cases

| Ситуация | Обработка |
|----------|-----------|
| Пост удалён (файл недоступен) | ❌ кнопки + alert (§5.4–5.5) |
| Видео > 20 МБ | Превью + caption об ошибке + 🔗 |
| Пользователь не начал ЛС с ботом | При «В оригинале» → сообщение «Начните диалог с @botname» |
| Gelbooru API недоступен | Inline Article: «⚠️ Gelbooru недоступен» |
| Дубликаты при подгрузке | Прекращение пагинации + «Больше результатов нет» |
| Пустой результат | Inline Article: «Ничего не найдено: ...» |
| Пользователь не в whitelist | Пустой inline-результат / сообщение в ЛС |
| Rate limit Gelbooru | Очередь с ожиданием (asyncio) |
| Callback на устаревший query_id | «⚠️ История поиска устарела» |

---

## 14. Out of scope (v1)

- Публичный доступ
- Платный VIP
- Папки/коллекции для сохранённых постов
- Поиск по сохранёнкам
- Кэширование полноразмерных файлов
- `/tags` автодополнение (Gelbooru tag autocomplete endpoint)
