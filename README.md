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

- **📌 Мои поиски** — сохранённые поиски (тапните для повтора)
- **❤️ Сохранённые** — сохранённые посты
- **🚫 Чёрный список** — теги, которые не будут показываться
- **⚙️ Настройки** — рейтинг по умолчанию (safe/questionable/explicit/all)

### Админ-команды

| Команда | Описание |
|---------|----------|
| `/adduser <id>` | Добавить пользователя |
| `/ban <id>` | Забанить |
| `/vip <id>` | Дать VIP (доступ в группах) |
| `/unvip <id>` | Снять VIP |
| `/users` | Список всех пользователей |

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

## Структура проекта

```
├── main.py                 # Точка входа (запуск бота, регистрация хендлеров)
├── config.py               # Конфигурация из .env (BOT_TOKEN, PUBLIC_URL и др.)
├── db.py                   # SQLite: инициализация, функции для пользователей/поисков/постов
├── gelbooru.py             # Gelbooru API клиент с rate limiting (8 req/sec)
├── cache.py                # Дисковый кэш превью + фоновая очистка старых файлов
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
| Нет доступа | Бот игнорирует |
| `user` | Inline в ЛС и личных чатах |
| `vip` | + Inline в группах |
| `owner` | + Админ-команды |