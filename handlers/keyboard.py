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


def make_settings_keyboard(is_owner: bool = False) -> InlineKeyboardMarkup:
    """Create settings menu keyboard."""
    buttons = [
        [InlineKeyboardButton(text="📊 Настройки рейтинга постов", callback_data="settings_rating")],
    ]
    if is_owner:
        buttons.append([InlineKeyboardButton(text="👥 Настройки пользователей", callback_data="settings_users")])
    buttons.append([InlineKeyboardButton(text="🚫 Черный список", callback_data="settings_blacklist")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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


def make_rating_menu_keyboard(current_rating: str = "") -> InlineKeyboardMarkup:
    """Create rating selection menu keyboard with back button."""
    options = [
        ("", "⚪ Все"),
        ("general", "🟢 General"),
        ("sensitive", "🟡 Sensitive"),
        ("questionable", "🟠 Questionable"),
        ("explicit", "🔴 Explicit"),
    ]

    buttons = []
    row = []
    for rating_value, label in options:
        if rating_value == current_rating:
            label = f"✓ {label}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"set_rating:{rating_value}"))
        if len(row) >= 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
