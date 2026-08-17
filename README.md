# Telegram Gelbooru Bot

Telegram-бот для поиска изображений и видео с Gelbooru через inline-режим.

## ⚠️ Важно: Cloudflare Worker для работы бота

**Gelbooru блокирует прямые запросы от Telegram**, поэтому для корректной работы бота необходимо настроить Cloudflare Worker в качестве прокси для изображений. Без этого превью будут отображаться как «серые квадраты».

### Как создать Cloudflare Worker (5 минут)

1. **Зарегистрируйтесь на [Cloudflare](https://dash.cloudflare.com/sign-up)** (бесплатно)

2. **Создайте Worker:**
   - Перейдите в [Workers & Pages](https://dash.cloudflare.com/?to=/:account/workers-and-pages)
   - Нажмите **Create** → **Create Worker**
   - Назовите его (например, `gelbooru-proxy`)
   - Нажмите **Deploy**

3. **Вставьте код прокси:**

   - В редакторе кода Worker замените содержимое файла на этот код:

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const targetUrl = url.searchParams.get('url');
    if (!targetUrl) return new Response('Missing url', { status: 400 });
    try {
      const response = await fetch(targetUrl, {
        headers: {
          'Referer': 'https://gelbooru.com/',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      });
      const contentType = response.headers.get('Content-Type') || '';
      if (!contentType.startsWith('image/') && !contentType.startsWith('video/')) {
        return new Response('Blocked', { status: 502 });
      }
      const newResponse = new Response(response.body, response);
      newResponse.headers.set('Cache-Control', 'public, max-age=86400');
      newResponse.headers.set('Access-Control-Allow-Origin', '*');
      return newResponse;
    } catch (e) {
      return new Response('Error: ' + e.message, { status: 500 });
    }
  }
};
```

**Что делает этот код:**
- Принимает параметр `?url=` с оригинальным URL изображения Gelbooru
- Добавляет заголовок `Referer: https://gelbooru.com/` (обходит блокировку хотлинков)
- Добавляет `User-Agent` браузера (дополнительная маскировка)
- Проверяет что контент — изображение или видео (блокирует попытки доступа к HTML)
- Кэширует ответ на 24 часа (экономит лимиты Cloudflare)
- Возвращает файл с правильным `Content-Type`

4. **Разверните Worker:**
   - Нажмите **Save and Deploy**
   - Скопируйте URL вашего Worker (вида `https://gelbooru-proxy.yourname.workers.dev`)

5. **Добавьте URL в `.env`:**

```env
PUBLIC_URL=https://gelbooru-proxy.yourname.workers.dev
```

---

## Быстрый старт (Docker)

### 1. Подготовка

Убедитесь что установлены:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows Server / Windows)
- Git

### 2. Клонируйте репозиторий

```bash
git clone https://github.com/ChickenRamen500/gbooru_tg.git
cd gbooru_tg
```

### 3. Настройте переменные окружения

```bash
copy .env.example .env
```

Откройте `.env` и заполните:

```env
BOT_TOKEN=123456:ABC-DEF...           # Токен бота от @BotFather
GELBOORU_API_KEY=xxxxx               # API ключ с gelbooru.com/account
GELBOORU_USER_ID=12345                 # Ваш user ID на Gelbooru
OWNER_ID=987654321                     # Ваш Telegram ID (для админ-команд)
PUBLIC_URL=https://gelbooru-proxy.yourname.workers.dev  # Cloudflare Worker (см. выше)
```

**Как получить:**
- **BOT_TOKEN** — напишите [@BotFather](https://t.me/BotFather), `/newbot`, скопируйте токен
- **GELBOORU_API_KEY** — залогиньтесь на [gelbooru.com](https://gelbooru.com), перейдите в Account → API Key
- **OWNER_ID** — напишите [@userinfobot](https://t.me/userinfobot) в Telegram, он пришлёт ваш ID

### 4. Запуск

```bash
docker compose up --build -d
```

Бот запущен. Логи:

```bash
docker compose logs -f
```

Остановка:

```bash
docker compose down
```

### 5. Добавьте себя как владельца

Бот автоматически добавляет OWNER_ID как owner при старте.

Добавьте других пользователей (нужен их Telegram ID):

```
/adduser 123456789
```

Дайте VIP (доступ в группах):

```
/vip 123456789
```

---

## Использование

### Поиск (inline-режим)

В любом чате напишите:

```
@botname tag1 tag2 tag3
```

Откроется панель с результатами. Скролльте для подгрузки. Тапните на результат — отправится в чат.

### Кнопки под результатами

| Кнопка | Действие |
|--------|----------|
| 📌 Сохранить поиск | Сохраняет теги для быстрого доступа |
| ℹ️ Инфо | Показывает детали поста (теги, размер, рейтинг) |
| 🔗 | Открывает пост на Gelbooru |
| 🔁 | Повторяет поиск (подставляет теги в строку) |

### Меню в личке с ботом

- **📌 Мои поиски** — сохранённые поиски (тапните ▶️ для повтора, 🗑️ для удаления, ➕ чтобы добавить новый)
- **❤️ Сохранённое и подписки** — раздел в разработке (сохранённые посты и подписки на теги появятся позже)
- **⚙️ Настройки**
  - **📊 Рейтинг постов** — выбор рейтинга по умолчанию (Все / General / Sensitive / Questionable / Explicit)
  - **🚫 Чёрный список тегов** — теги, которые не будут показываться (с удалением и добавлением)
- **👑 Админ-панель** (только владелец)
  - **👥 Управление пользователями** — список с пагинацией, карточка пользователя (выдача/снятие VIP, бан/разбан), поиск по ID
  - **📩 Заявки на доступ** — список заявок, одобрение / отклонение / отклонение + бан
  - **📢 Рассылка** — отправка сообщения всем пользователям с предпросмотром
  - **📈 Статистика** — количество пользователей, VIP, забаненных, заявок, сохранённых постов, размер БД
  - **⚙️ Система** — глобальный чёрный список (действует на всех пользователей) и сброс кэша

> Глобальный чёрный список автоматически применяется при каждом поиске вместе с личным чёрным списком пользователя.

### Админ-команды

| Команда | Описание |
|---------|----------|
| `/adduser <id>` | Добавить пользователя |
| `/ban <id>` | Забанить |
| `/unban <id>` | Разбанить |
| `/vip <id>` | Дать VIP (доступ в группах) |
| `/unvip <id>` | Снять VIP |
| `/users` | Список всех пользователей |
| `/cancel` | Отменить текущее действие (ввод тега, поиск и т.п.) |

> Тем же функционалом можно управлять через меню 👑 Админ-панель.

---

## Запуск без Docker (для разработки)

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env
# заполните .env
python main.py
```

---

## Тестирование (test_*.py)

В репозитории есть три тестовых скрипта для проверки работы компонентов бота. Запускайте их **в указанном порядке** при первой настройке или при возникновении проблем.

### Порядок запуска

1. **`test_api.py`** — проверка подключения к Gelbooru API
2. **`test_download.py`** — проверка скачивания файлов через Cloudflare Worker
3. **`test_telegram_send.py`** — проверка отправки сообщений в Telegram

---

### 1. test_api.py — Проверка Gelbooru API

**Что проверяет:**
- Подключение к API Gelbooru
- Корректность API ключа и User ID
- Возможность получения постов по тегам

#### Запуск в Docker:

```bash
docker compose run --rm bot python test_api.py
```

#### Запуск без Docker:

```bash
python test_api.py
```

#### ✅ Ожидаемый успех:
```
============================================================
  ENV CHECK
============================================================
  BOT_TOKEN:       OK
  GELBOORU_API_KEY: OK
  GELBOORU_USER_ID: '12345'

============================================================
  API call with tags: "1girl solo kasane_teto"
============================================================
  Status: 200
  Content-Type: application/json; charset=utf-8
  Response length: 5432 bytes
  
  Parsed as list, 3 items
  First item keys: ['id', 'tags', 'rating', 'file_url', ...]
  First item id: 123456
  First item rating: s
  First item file_url: https://gelbooru.com/images/...
  
[SUCCESS] Все проверки пройдены
```

#### ❌ Возможные проблемы:

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `BOT_TOKEN: EMPTY` | Не заполнен `.env` | Добавьте `BOT_TOKEN` в `.env` |
| `GELBOORU_API_KEY: EMPTY` | Не заполнен `.env` | Добавьте `GELBOORU_API_KEY` в `.env` |
| `Status: 403` | Неверный API ключ | Проверьте `GELBOORU_API_KEY` на gelbooru.com/account |
| `Status: 404` | Неверный User ID | Проверьте `GELBOORU_USER_ID` (число, не имя) |
| `Connection timeout` | Блокировка сети | Убедитесь что есть доступ к gelbooru.com |
| `JSON parse error` | Gelbooru вернул HTML вместо JSON | Возможно временная блокировка, подождите 5 минут |

---

### 2. test_download.py — Проверка скачивания через прокси

**Что проверяет:**
- Работоспособность Cloudflare Worker (`PUBLIC_URL`)
- Возможность скачивания изображений/видео напрямую и через прокси
- Корректность заголовков (Referer, User-Agent)
- Сравнение прямого доступа и прокси

#### Запуск в Docker:

```bash
docker compose run --rm bot python test_download.py
# Скопируйте результаты на хост:
docker compose cp bot:/app/test_output ./test_output
```

#### Запуск без Docker:

```bash
python test_download.py
```

#### ✅ Ожидаемый успех:
```
[HH:MM:SS] === Gelbooru Download Test ===
Tags: 1girl solo
Limit: 5
Output: /workspace/test_output
PUBLIC_URL: https://gelbooru-proxy.yourname.workers.dev
--------------------------------------------------------------------------------
[HH:MM:SS] Requesting Gelbooru API...
  Got 5 posts
--------------------------------------------------------------------------------

Post #123456 (1/5)
  preview: https://gelbooru.com/thumbnails/...
  sample:  https://gelbooru.com/samples/...
  file:    https://gelbooru.com/images/...
  [A] preview with Referer (direct):
    status=200, size=45678B, type=image/jpeg
  [B] preview via proxy:
    URL: https://gelbooru-proxy.yourname.workers.dev/proxy.jpg?url=...
    status=200, size=45678B, type=image/jpeg
  [C] sample with Referer (direct):
    status=200, size=234567B, type=image/jpeg
  [D] sample via proxy:
    status=200, size=234567B, type=image/jpeg

--------------------------------------------------------------------------------
[HH:MM:SS] === DONE ===
Files saved to: /workspace/test_output
```

**Файлы в test_output/:**
- `*_preview_direct.jpg` — превью напрямую с Gelbooru
- `*_preview_proxy.jpg` — превью через Cloudflare Worker
- `*_sample_direct.jpg` — sample напрямую
- `*_sample_proxy.jpg` — sample через прокси
- `api_response.json` — сырой ответ API
- `log.txt` — лог теста

#### ❌ Возможные проблемы:

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `PUBLIC_URL: (not set)` | Не заполнен `.env` | Добавьте URL Cloudflare Worker в `.env` |
| `[A] status=403, type=text/html` | Gelbooru блокирует прямой доступ | Это нормально! Используйте прокси [B] |
| `[B] status=400 Bad Request` | Worker не читает параметр `url` | Проверьте код Worker: `url.searchParams.get('url')` |
| `[B] status=502 Blocked` | Worker блокирует контент | Проверьте что `Content-Type` начинается с `image/` или `video/` |
| `[B] status=500 Error` | Ошибка в коде Worker | Перепроверьте синтаксис JavaScript, особенно скобки |
| `[B] NOT AN IMAGE!` | Прокси вернул HTML вместо картинки | Worker неправильно настроен, пересоздайте его |

> ⚠️ **Важно:** Ошибка `[A] status=403` — это **нормально**! Gelbooru блокирует прямые запросы без Referer. Главное чтобы `[B]` (прокси) работал с `status=200` и `type=image/*`.

> ⚠️ **Это самый важный тест!** Если он падает — превью в Telegram не будут работать.

---

### 3. test_telegram_send.py — Проверка отправки в Telegram

**Что проверяет:**
- Подключение к Telegram Bot API
- Корректность токена бота
- Возможность отправки изображений по прямым URL и через прокси
- **Важно:** Тест отправляет фото в чат и сразу удаляет их (не спамит)

#### Подготовка:
⚠️ **Бот должен быть остановлен** перед запуском теста (иначе конфликт токена):
```bash
docker compose down
# или если запускали без Docker — остановите процесс main.py
```

#### Запуск в Docker:

```bash
# Свой CHAT_ID (не обязательно, по умолчанию OWNER_ID из .env):
docker compose run --rm bot python test_telegram_send.py 987654321
```

#### Запуск без Docker:

```bash
python test_telegram_send.py 987654321
```

#### ✅ Ожидаемый успех:
```
======================================================================
TEST: Send images to Telegram via Bot API
Chat ID: 987654321
PUBLIC_URL: https://gelbooru-proxy.yourname.workers.dev
======================================================================

[Step 1] Fetching posts from Gelbooru API...
  Got 3 posts

[Step 2] Testing sendPhoto...

--- Post #123456 (1/3) ---
  [direct preview]
    URL: https://gelbooru.com/thumbnails/...
    FAIL 234ms
    403: Forbidden
  [direct sample]
    URL: https://gelbooru.com/samples/...
    FAIL 189ms
    403: Forbidden
  [proxy preview]
    URL: https://gelbooru-proxy.yourname.workers.dev/proxy.jpg?url=...
    OK 456ms (msg #12345)
  [proxy sample]
    URL: https://gelbooru-proxy.yourname.workers.dev/proxy.jpg?url=...
    OK 512ms (msg #12346)

--- Post #789012 (2/3) ---
  ...

======================================================================
RESULTS:
  direct preview: FAIL
  direct sample: FAIL
  proxy preview: OK
  proxy sample: OK

RESULT: Proxy WORKS! Inline mode should display images correctly.
======================================================================
```

**Файлы в test_output/:**
- `telegram_log.txt` — подробный лог всех запросов

#### ❌ Возможные проблемы:

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `ERROR: BOT_TOKEN not set` | Не заполнен `.env` | Добавьте `BOT_TOKEN` в `.env` |
| `ERROR: CHAT_ID not provided` | Нет `OWNER_ID` в `.env` и не передан в аргументе | Запустите `python test_telegram_send.py ВАШ_ID` |
| `401: Unauthorized` | Неверный токен бота | Проверьте `BOT_TOKEN` (скопируйте заново от @BotFather) |
| `403: Forbidden` (на direct) | Telegram не может скачать с Gelbooru | **Это нормально!** Прокси [proxy] должен работать |
| `403: Forbidden` (на proxy) | Worker не работает | Проверьте `test_download.py`, пересоздайте Worker |
| `Bot was blocked by the user` | Вы заблокировали бота | Напишите боту `/start` в Telegram |
| `Connection timeout` | Нет доступа к api.telegram.org | Проверьте сеть/прокси/файрвол |

#### Интерпретация результатов:

| Результат | Что значит |
|-----------|------------|
| `direct: FAIL`, `proxy: OK` | ✅ **Норма!** Прокси работает, бот готов |
| `direct: OK`, `proxy: OK` | ✅ Работает всё (редко, Gelbooru иногда не блокирует) |
| `direct: FAIL`, `proxy: FAIL` | ❌ Прокси не работает — чините Cloudflare Worker |
| Все `FAIL` | ❌ Проблема с токеном бота или сетью |

> ⚠️ **Ожидаемое поведение:** Прямые URL (`direct`) должны падать с `403 Forbidden`, а прокси (`proxy`) — работать с `OK`. Если прямые URL работают — вам повезло, но прокси всё равно нужен для стабильности.

---

### Полный цикл тестирования (все тесты подряд)

#### В Docker:
```bash
# Запуск всех трёх тестов по очереди:
docker compose run --rm bot python test_api.py && \
docker compose run --rm bot python test_download.py && \
docker compose cp bot:/app/test_output ./test_output && \
docker compose run --rm bot python test_telegram_send.py
```

#### Без Docker:
```bash
python test_api.py && python test_download.py && python test_telegram_send.py
```

#### ✅ Если все три теста прошли:
Бот полностью готов к запуску! Можете стартовать:
```bash
docker compose up -d
# или
python main.py
```

#### ❌ Если какой-то тест упал:
1. Исправьте проблему согласно таблице выше
2. Перезапустите только упавший тест
3. После успеха всех трёх — запускайте бота

---

## Структура проекта

```
├── main.py                 # Точка входа (запуск бота, регистрация хендлеров)
├── config.py               # Конфигурация из .env (BOT_TOKEN, PUBLIC_URL и др.)
├── db.py                   # SQLite: инициализация, функции для пользователей/поисков/постов
├── gelbooru.py             # Gelbooru API клиент с rate limiting (8 req/sec)
├── cache.py                # In-memory кэш ответов Gelbooru API + фоновая очистка
├── handlers/
│   ├── inline.py           # Inline query (поиск) + chosen result (для видео >20MB)
│   ├── callbacks.py        # Callback handlers (инфо, сохранить, полный размер, удаление)
│   ├── commands.py         # Команды: /start, /help, /adduser, /ban, /vip, /unvip, /users
│   ├── messages.py         # Обработка кнопок меню (поиски, сохранёнки, ЧС, настройки)
│   └── keyboard.py         # Генерация клавиатур (inline + reply)
├── middleware/
│   └── access.py           # Middleware проверки доступа (owner/user/vip/banned)
├── Dockerfile              # Образ Python 3.12
├── docker-compose.yml      # Запуск с томами для data и cache
├── .env.example            # Шаблон переменных окружения
├── requirements.txt        # Зависимости (aiogram, aiohttp, python-dotenv)
├── test_api.py             # Тест Gelbooru API
├── test_download.py        # Тест скачивания файлов через прокси
└── test_telegram_send.py   # Тест отправки в Telegram
```

---

## Роли

| Роль | Доступ |
|------|--------|
| Нет доступа | Бот предлагает кнопку «📩 Запросить доступ» (заявка попадает владельцу) |
| `user` | Inline в ЛС и личных чатах |
| `vip` | + Inline в группах |
| `banned` | Полностью заблокирован |
| `owner` | + Админ-панель и админ-команды |