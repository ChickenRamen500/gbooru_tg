# Telegram Gelbooru Bot

Telegram-бот для поиска изображений и видео с Gelbooru через inline-режим.

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
├── main.py                 # Точка входа
├── config.py               # Конфигурация (.env)
├── db.py                   # SQLite: инициализация, хелперы
├── gelbooru.py             # Gelbooru API клиент + rate limiter
├── cache.py                # Дисковый кэш превью + cleanup
├── handlers/
│   ├── inline.py           # Inline query + chosen result
│   ├── callbacks.py        # Callback handlers (info, save, etc.)
│   ├── commands.py         # /start, /help, admin commands
│   ├── messages.py         # Клавиатура (поиски, сохранёнки, ЧС, настройки)
│   └── keyboard.py         # Генерация клавиатур
├── middleware/
│   └── access.py           # Проверка доступа (owner/user/vip/banned)
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── .gitignore
```

---

## Роли

| Роль | Доступ |
|------|--------|
| Нет доступа | Бот игнорирует |
| `user` | Inline в ЛС и личных чатах |
| `vip` | + Inline в группах |
| `owner` | + Админ-команды |