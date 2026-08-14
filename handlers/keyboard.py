"""Keyboard helpers module."""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def make_main_keyboard() -> ReplyKeyboardMarkup:
    """Create main reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📌 Мои поиски"),
                KeyboardButton(text="❤️ Сохраненные посты и подписки на теги"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
    )


def make_settings_keyboard(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """Create settings menu reply keyboard."""
    keyboard = [
        [KeyboardButton(text="📊 Настройки рейтинга постов")],
    ]
    if is_owner:
        keyboard.append([KeyboardButton(text="👥 Настройки пользователей")])
    keyboard.append([KeyboardButton(text="🚫 Черный список")])
    keyboard.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def make_rating_menu_keyboard(current_rating: str = "") -> ReplyKeyboardMarkup:
    """Create rating selection menu reply keyboard with back button."""
    options = [
        ("", "⚪ Все"),
        ("general", "🟢 General"),
        ("sensitive", "🟡 Sensitive"),
        ("questionable", "🟠 Questionable"),
        ("explicit", "🔴 Explicit"),
    ]
    
    keyboard = []
    for rating_value, label in options:
        if rating_value == current_rating:
            label = f"✓ {label}"
        keyboard.append([KeyboardButton(text=label)])
    keyboard.append([KeyboardButton(text="🔙 Назад")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def make_users_management_keyboard() -> ReplyKeyboardMarkup:
    """Create user management reply keyboard for owner."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Список пользователей")],
            [KeyboardButton(text="➕ Добавить пользователя")],
            [KeyboardButton(text="🚫 Забанить")],
            [KeyboardButton(text="⭐ Выдать VIP")],
            [KeyboardButton(text="❌ Снять VIP")],
            [KeyboardButton(text="📩 Заявки на доступ")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def make_blacklist_reply_keyboard() -> ReplyKeyboardMarkup:
    """Create blacklist management reply keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить тег")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


# Note: make_blacklist_keyboard with inline buttons for tag deletion is defined below


def make_blacklist_keyboard(blacklist: list) -> InlineKeyboardMarkup:
    """Create blacklist management keyboard with inline buttons for tag deletion."""
    keyboard = []
    for item in blacklist:
        row = [
            InlineKeyboardButton(text=item["tag"], callback_data="noop"),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"del_bl:{item['id']}",
            ),
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="➕ Добавить тег", callback_data="add_bl:")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_post_keyboard(query_id: int, post_id: int, tags: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for post results."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📌 Сохранить поиск",
                    callback_data=f"sq:{query_id}",
                ),
                InlineKeyboardButton(
                    text="ℹ️ Инфо",
                    callback_data=f"i:{post_id}",
                ),
                InlineKeyboardButton(
                    text="🔗",
                    url=f"https://gelbooru.com/index.php?page=post&s=view&id={post_id}",
                ),
                InlineKeyboardButton(
                    text="🔁",
                    switch_inline_query_current_chat=tags,
                ),
            ]
        ]
    )


def make_info_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Create keyboard for info message."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📐 Посмотреть в оригинале",
                    callback_data=f"fs:{post_id}",
                )
            ],
            [InlineKeyboardButton(text="🗑️ Удалить сообщение", callback_data="delmsg")],
        ]
    )


def make_saved_posts_page_keyboard(page: int, has_more: bool) -> InlineKeyboardMarkup:
    """Create pagination keyboard for saved posts."""
    buttons = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"saved_page:{page - 1}",
            )
        )
    if has_more:
        buttons.append(
            InlineKeyboardButton(
                text="▶️ Далее",
                callback_data=f"saved_page:{page + 1}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])


def make_blacklist_keyboard(blacklist: list) -> InlineKeyboardMarkup:
    """Create blacklist management keyboard."""
    keyboard = []
    for item in blacklist:
        row = [
            InlineKeyboardButton(text=item["tag"], callback_data="noop"),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"del_bl:{item['id']}",
            ),
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="➕ Добавить тег", callback_data="add_bl:")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_users_management_keyboard() -> InlineKeyboardMarkup:
    """Create user management keyboard for owner."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Список пользователей", callback_data="users_list")],
            [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="user_add")],
            [InlineKeyboardButton(text="🚫 Забанить", callback_data="user_ban")],
            [InlineKeyboardButton(text="⭐ Выдать VIP", callback_data="user_vip")],
            [InlineKeyboardButton(text="❌ Снять VIP", callback_data="user_unvip")],
            [InlineKeyboardButton(text="📩 Заявки на доступ", callback_data="user_requests")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")],
        ]
    )


def make_user_action_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create keyboard for specific user action (add, ban, vip, unvip)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="settings_users")]
        ]
    )
