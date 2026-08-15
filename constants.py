"""Constants for button texts and menu levels."""

# =============================================================================
# BUTTON TEXTS (Reply keyboards)
# =============================================================================

class Buttons:
    """Reply keyboard button texts."""
    
    # Main menu (Level 1)
    MY_SEARCHES = "📌 Мои поиски"
    SAVED_AND_SUBS = "❤️ Сохраненное и подписки"
    SETTINGS = "⚙️ Настройки"
    ADMIN_PANEL = "👑 Админ-панель"
    
    # Level 10 - My searches
    ADD_SEARCH = "➕ Добавить поиск"
    BACK = "🔙 Назад"
    
    # Level 11 - Saved and subscriptions
    SAVED_POSTS = "🖼 Сохраненные посты"
    SUBSCRIPTIONS = "🔔 Подписки на теги"
    
    # Level 12 - Saved posts
    CLEAR_ALL = "🗑 Очистить все"
    
    # Level 13 - Subscriptions
    ADD_SUBSCRIPTION = "➕ Новая подписка"
    
    # Level 20 - Settings
    RATING = "📊 Рейтинг постов"
    BLACKLIST = "🚫 Черный список тегов"
    
    # Level 21 - Rating
    RATING_ALL = "⚪ Все"
    RATING_GENERAL = "🟢 General"
    RATING_SENSITIVE = "🟡 Sensitive"
    RATING_QUESTIONABLE = "🟠 Questionable"
    RATING_EXPLICIT = "🔴 Explicit"
    
    # Level 22 - Blacklist
    ADD_TAG = "➕ Добавить тег"
    
    # Level 50 - Admin panel
    USERS_MANAGE = "👥 Управление пользователями"
    REQUESTS = "📩 Заявки на доступ"
    BROADCAST = "📢 Рассылка"
    STATS = "📈 Статистика"
    SYSTEM = "⚙️ Система"
    BACK_TO_ADMIN = "🔙 Назад в Админку"
    
    # Level 51 - User management
    USERS_LIST = "📋 Список пользователей"
    FIND_BY_ID = "🔍 Найти по ID"
    
    # Level 61 - Requests list
    BACK_TO_REQUESTS = "🔙 Назад"
    
    # Level 80 - System
    GLOBAL_BLACKLIST = "🌍 Глобальный ЧС"
    CLEAR_CACHE = "🔄 Сбросить кэш"


# =============================================================================
# CALLBACK DATA PREFIXES
# =============================================================================

class Callbacks:
    """Callback data prefixes."""
    
    # Access
    ACCESS_REQUEST = "access:request"
    
    # Searches
    SEARCH_RUN = "searches:run"
    SEARCH_DEL = "searches:del"
    
    # Posts
    POSTS_PREV = "posts:prev"
    POSTS_NEXT = "posts:next"
    POSTS_PAGE = "posts:page"
    POSTS_CLEAR = "posts:clear"
    POSTS_CLEAR_CONFIRM = "posts:clear:confirm"
    POSTS_CLEAR_CANCEL = "posts:clear:cancel"
    
    # Subscriptions
    SUBS_OPEN = "subs:open"
    SUBS_DEL = "subs:del"
    
    # Blacklist
    BL_DEL = "bl:del"
    
    # Users
    USERS_PREV = "users:prev"
    USERS_NEXT = "users:next"
    USERS_PAGE = "users:page"
    USERS_CARD = "users:card"
    USERS_VIP = "users:vip"
    USERS_BAN = "users:ban"
    USERS_LIST = "users:list"
    
    # Requests
    REQ_CARD = "req:card"
    REQ_OK = "req:ok"
    REQ_NO = "req:no"
    REQ_BAN = "req:ban"
    REQ_LIST = "req:list"
    
    # System
    SYS_CACHE_CLEAR = "sys:cache:clear"
    
    # Global blacklist
    GBL_DEL = "gbl:del"


# =============================================================================
# MENU LEVELS
# =============================================================================

class Levels:
    """Menu level constants."""
    
    # Guest
    GUEST = 0
    
    # Main menu
    MAIN = 1
    
    # User menus
    MY_SEARCHES = 10
    SAVED_AND_SUBS = 11
    SAVED_POSTS = 12
    SUBSCRIPTIONS = 13
    FSM_ADD_SEARCH_OR_SUB = 14
    
    # Settings
    SETTINGS = 20
    RATING = 21
    BLACKLIST = 22
    FSM_ADD_BLACKLIST_TAG = 23
    
    # Admin
    ADMIN_PANEL = 50
    USERS_MANAGE = 51
    USERS_LIST = 52
    USER_CARD = 53
    FSM_FIND_USER = 54
    
    # Requests
    REQUESTS_MENU = 60  # Redirect to 61
    REQUESTS_PENDING = 61
    REQUEST_CARD = 62
    
    # Broadcast
    BROADCAST_FSM = 71
    BROADCAST_PREVIEW = 72
    
    # Stats
    STATS = 70
    
    # System
    SYSTEM = 80
    GLOBAL_BLACKLIST = 81
    FSM_ADD_GLOBAL_TAG = 82


# =============================================================================
# MESSAGES
# =============================================================================

class Messages:
    """Static messages."""
    
    # Level 0 - Guest
    GUEST_NO_ACCESS = (
        "👋 Привет! Я бот для поиска артов через Gelbooru.\n\n"
        "🔒 У тебя нет доступа. Нажми кнопку ниже, чтобы запросить."
    )
    GUEST_REQUEST_SENT = "✅ Заявка отправлена владельцу. Ожидай решения."
    
    # Level 1 - Main menu
    MAIN_MENU = (
        "🏠 Главное меню\n\n"
        "Привет! Я бот для поиска артов. Выбери нужное действие в меню ниже."
    )
    
    # Level 10 - My searches
    MY_SEARCHES_TITLE = "📌 Мои поиски"
    NO_SAVED_SEARCHES = "У тебя пока нет сохраненных поисков."
    
    # Level 11 - Saved and subscriptions
    SAVED_AND_SUBS = (
        "❤️ Сохраненное и подписки\n\n"
        "Выбери раздел."
    )
    
    # Level 12 - Saved posts
    SAVED_POSTS_TITLE = "🖼 Сохраненные посты"
    SAVED_POSTS_COUNT = "Всего: {count}\nСтраница {page}/{pages}"
    NO_SAVED_POSTS = "У тебя пока нет сохраненных постов."
    
    # Level 13 - Subscriptions
    SUBSCRIPTIONS_TITLE = (
        "🔔 Подписки на теги\n\n"
        "Бот может присылать новые посты по этим тегам."
    )
    NO_SUBSCRIPTIONS = "У тебя пока нет подписок на теги."
    
    # Level 20 - Settings
    SETTINGS_TITLE = (
        "⚙️ Меню настроек\n\n"
        "Здесь ты можешь настроить фильтры и черные списки."
    )
    
    # Level 21 - Rating
    RATING_TITLE = "📊 Рейтинг постов"
    RATING_CURRENT = "Текущий рейтинг: {current_rating}"
    RATING_SET = "✅ Установлен рейтинг: {rating}"
    
    # Level 22 - Blacklist
    BLACKLIST_TITLE = (
        "🚫 Черный список тегов\n\n"
        "Посты с этими тегами не будут показываться тебе."
    )
    BLACKLIST_EMPTY = "Черный список пуст."
    
    # Level 50 - Admin panel
    ADMIN_PANEL_TITLE = (
        "👑 Панель управления ботом\n\n"
        "Выберите раздел:"
    )
    
    # Level 51 - User management
    USERS_MANAGE_TITLE = "👥 Управление пользователями"
    
    # Level 52 - Users list
    USERS_LIST_TITLE = "👥 Список пользователей"
    USERS_LIST_PAGE = "Страница {page}/{pages}"
    
    # Level 53 - User card
    USER_CARD_TITLE = "👤 Карточка пользователя"
    USER_CARD_INFO = (
        "ID: {user_id}\n"
        "User: @{username}\n"
        "Статус: {status}\n"
        "Бан: {ban_status}"
    )
    
    # Level 54 - Find user by ID
    FIND_USER_TITLE = "🔍 Поиск по ID"
    FIND_USER_PROMPT = "Отправь ID пользователя числом."
    FIND_USER_ERROR = "❌ ID не найден или неверный формат."
    
    # Level 61 - Requests pending
    REQUESTS_PENDING_TITLE = "📩 Заявки на доступ"
    NO_REQUESTS = "Сейчас нет заявок на доступ."
    
    # Level 62 - Request card
    REQUEST_CARD_TITLE = "📝 Заявка"
    REQUEST_CARD_INFO = (
        "ID: {user_id}\n"
        "User: @{username}\n"
        "Имя: {first_name}\n"
        "Время: {time}"
    )
    
    # Level 70 - Stats
    STATS_TITLE = "📈 Статистика"
    STATS_INFO = (
        "• Пользователей: {users_count}\n"
        "• VIP: {vip_count}\n"
        "• Забанено: {banned_count}\n"
        "• Заявок в ожидании: {requests_count}\n"
        "• Сохраненных постов: {saved_posts_count}\n"
        "• Размер БД: {db_size}"
    )
    
    # Level 71 - Broadcast
    BROADCAST_TITLE = "📢 Рассылка"
    BROADCAST_PROMPT = "Отправь сообщение, которое получат все пользователи."
    
    # Level 72 - Broadcast preview
    BROADCAST_PREVIEW_TITLE = "👁 Предпросмотр рассылки"
    BROADCAST_PREVIEW_PROMPT = "{message_text}\n\nОтправить всем пользователям?"
    BROADCAST_SENT = "📢 Рассылка запущена."
    
    # Level 80 - System
    SYSTEM_TITLE = "⚙️ Системные настройки"
    
    # Level 81 - Global blacklist
    GLOBAL_BLACKLIST_TITLE = (
        "🌍 Глобальный черный список\n\n"
        "Эти теги запрещены для всех пользователей."
    )
    GLOBAL_BLACKLIST_EMPTY = "Глобальный черный список пуст."
    
    # Errors
    NO_ACCESS = "Нет доступа."
    INVALID_TAG = "❌ Некорректный тег. Можно использовать только английский тег без пробелов."
    TAG_ADDED = "✅ Тег {tag} добавлен в черный список"
    TAG_ADDED_GLOBAL = "✅ Тег {tag} добавлен в глобальный черный список"
