"""Keyboard helpers module.

All callback_data prefixes produced here are matched by handlers in main.py.
Reply keyboards are used for pure navigation screens; inline keyboards are used
for screens that need per-item action buttons (searches, blacklist, users, etc.).
"""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from constants import Buttons

USERS_PER_PAGE = 10


# =============================================================================
# REPLY KEYBOARDS (navigation)
# =============================================================================

def make_main_keyboard(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """Create main reply keyboard (Level 1)."""
    keyboard = [
        [
            KeyboardButton(text=Buttons.MY_SEARCHES),
            KeyboardButton(text=Buttons.SAVED_AND_SUBS),
        ],
        [
            KeyboardButton(text=Buttons.SETTINGS),
        ],
    ]
    if is_owner:
        keyboard.append([KeyboardButton(text=Buttons.ADMIN_PANEL)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def make_saved_and_subs_keyboard() -> ReplyKeyboardMarkup:
    """Create saved and subscriptions reply keyboard (Level 11)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=Buttons.SAVED_POSTS),
                KeyboardButton(text=Buttons.SUBSCRIPTIONS),
            ],
            [KeyboardButton(text=Buttons.BACK)],
        ],
        resize_keyboard=True,
    )


def make_settings_keyboard(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """Create settings menu reply keyboard (Level 20)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=Buttons.RATING),
                KeyboardButton(text=Buttons.BLACKLIST),
            ],
            [KeyboardButton(text=Buttons.BACK)],
        ],
        resize_keyboard=True,
    )


def make_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """Create admin panel reply keyboard (Level 50)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=Buttons.USERS_MANAGE),
                KeyboardButton(text=Buttons.REQUESTS),
            ],
            [
                KeyboardButton(text=Buttons.BROADCAST),
                KeyboardButton(text=Buttons.STATS),
            ],
            [
                KeyboardButton(text=Buttons.SYSTEM),
                KeyboardButton(text=Buttons.BACK),
            ],
        ],
        resize_keyboard=True,
    )


def make_users_manage_keyboard() -> ReplyKeyboardMarkup:
    """Create user management reply keyboard (Level 51)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=Buttons.USERS_LIST),
                KeyboardButton(text=Buttons.FIND_BY_ID),
            ],
            [KeyboardButton(text=Buttons.BACK_TO_ADMIN)],
        ],
        resize_keyboard=True,
    )


def make_system_keyboard() -> ReplyKeyboardMarkup:
    """Create system settings reply keyboard (Level 80)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=Buttons.GLOBAL_BLACKLIST),
                KeyboardButton(text=Buttons.CLEAR_CACHE),
            ],
            [KeyboardButton(text=Buttons.BACK_TO_ADMIN)],
        ],
        resize_keyboard=True,
    )


def make_requests_keyboard(pending_count: int = 0) -> ReplyKeyboardMarkup:
    """Create requests menu reply keyboard (Level 60)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"⏳ Ожидают ({pending_count})")],
            [KeyboardButton(text=Buttons.BACK_TO_ADMIN)],
        ],
        resize_keyboard=True,
    )


def make_stats_keyboard() -> ReplyKeyboardMarkup:
    """Create stats reply keyboard (Level 70)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Обновить")],
            [KeyboardButton(text=Buttons.BACK_TO_ADMIN)],
        ],
        resize_keyboard=True,
    )


def make_broadcast_keyboard() -> ReplyKeyboardMarkup:
    """Create broadcast input reply keyboard (Level 71)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def make_back_keyboard() -> ReplyKeyboardMarkup:
    """Create simple back button keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=Buttons.BACK)]],
        resize_keyboard=True,
    )


# =============================================================================
# INLINE KEYBOARDS (screens with per-item actions)
# =============================================================================

def make_post_keyboard(query_id: int, post_id: int, tags: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for inline search results."""
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


def make_my_searches_inline_keyboard(searches: list) -> InlineKeyboardMarkup:
    """Create my searches inline keyboard (Level 10)."""
    rows = []
    for s in searches[:15]:
        tags = s["tags"]
        label = tags[:30] + ("…" if len(tags) > 30 else "")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"▶️ {label}",
                    switch_inline_query_current_chat=tags,
                ),
                InlineKeyboardButton(
                    text="🗑️",
                    callback_data=f"searches:del:{s['id']}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text=Buttons.ADD_SEARCH, callback_data="search:add")])
    rows.append([InlineKeyboardButton(text=Buttons.BACK, callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_rating_inline_keyboard(current_rating: str = "") -> InlineKeyboardMarkup:
    """Create rating selection inline keyboard (Level 21)."""
    options = [
        ("", Buttons.RATING_ALL),
        ("general", Buttons.RATING_GENERAL),
        ("sensitive", Buttons.RATING_SENSITIVE),
        ("questionable", Buttons.RATING_QUESTIONABLE),
        ("explicit", Buttons.RATING_EXPLICIT),
    ]
    rows = []
    for val, label in options:
        mark = "✓ " if val == current_rating else ""
        rows.append(
            [InlineKeyboardButton(text=f"{mark}{label}", callback_data=f"set_rating:{val}")]
        )
    rows.append([InlineKeyboardButton(text=Buttons.BACK, callback_data="back:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_blacklist_inline_keyboard(blacklist: list) -> InlineKeyboardMarkup:
    """Create blacklist management inline keyboard (Level 22)."""
    rows = []
    for item in blacklist:
        rows.append(
            [
                InlineKeyboardButton(text=item["tag"], callback_data="noop"),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"bl:del:{item['id']}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text=Buttons.ADD_TAG, callback_data="bl:add")])
    rows.append([InlineKeyboardButton(text=Buttons.BACK, callback_data="back:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_users_list_inline_keyboard(users: list, page: int, pages: int) -> InlineKeyboardMarkup:
    """Create users list inline keyboard (Level 52)."""
    keyboard = []

    for user in users:
        badges = ""
        role = user.get("role", "user")
        if role == "vip":
            badges += " ⭐"
        if role == "banned":
            badges += " 🚫"
        if role == "owner":
            badges += " 👑"

        username = user.get("username") or "N/A"
        user_id = user.get("user_id")

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"👤 @{username} (ID: {user_id}){badges}",
                    callback_data=f"users:card:{user_id}",
                )
            ]
        )

    # Pagination row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data="users:prev"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{max(pages, 1)}", callback_data="noop"))
    if page < pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data="users:next"))
    keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton(text=Buttons.BACK_TO_ADMIN, callback_data="back:users_manage")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_user_card_inline_keyboard(user_id: int, role: str) -> InlineKeyboardMarkup:
    """Create user card inline keyboard (Level 53)."""
    is_vip = role == "vip"
    is_banned = role == "banned"
    is_owner = role == "owner"

    rows = []
    if not is_owner:
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ Снять VIP" if is_vip else "⭐ Выдать VIP",
                    callback_data=f"users:vip:{user_id}",
                ),
                InlineKeyboardButton(
                    text="🔓 Разбанить" if is_banned else "🔨 Забанить",
                    callback_data=f"users:ban:{user_id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data="users:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_requests_list_inline_keyboard(requests: list) -> InlineKeyboardMarkup:
    """Create requests list inline keyboard (Level 61)."""
    keyboard = []
    for req in requests:
        username = req.get("username") or "N/A"
        requested_at = req.get("requested_at", "")[:16] if req.get("requested_at") else ""
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"📩 @{username} ({requested_at})",
                    callback_data=f"req:card:{req['user_id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton(text=Buttons.BACK, callback_data="back:requests_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard if keyboard else [[
        InlineKeyboardButton(text=Buttons.BACK, callback_data="back:requests_menu")
    ]])


def make_request_card_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create request card inline keyboard (Level 62)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"req:ok:{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"req:no:{user_id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Отклонить + Бан", callback_data=f"req:ban:{user_id}"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="req:list"),
            ],
        ]
    )


def make_global_blacklist_inline_keyboard(global_blacklist: list) -> InlineKeyboardMarkup:
    """Create global blacklist inline keyboard (Level 81)."""
    rows = []
    for item in global_blacklist:
        rows.append(
            [
                InlineKeyboardButton(text=item["tag"], callback_data="noop"),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"gbl:del:{item['id']}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text=Buttons.ADD_TAG, callback_data="gbl:add")])
    rows.append([InlineKeyboardButton(text=Buttons.BACK, callback_data="back:system")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def make_broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    """Create broadcast preview inline keyboard (Level 72)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Отправить всем", callback_data="broadcast:send"),
                InlineKeyboardButton(text="✏️ Изменить текст", callback_data="broadcast:edit"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast:cancel")],
        ]
    )


def make_clear_cache_confirm_keyboard() -> InlineKeyboardMarkup:
    """Create clear cache confirmation inline keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="cache:clear:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cache:clear:cancel"),
            ],
        ]
    )
