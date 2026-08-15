"""Keyboard helpers module."""

from typing import Optional

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from constants import Buttons


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


def make_my_searches_keyboard() -> ReplyKeyboardMarkup:
    """Create my searches reply keyboard (Level 10)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Buttons.ADD_SEARCH)],
            [KeyboardButton(text=Buttons.BACK)],
        ],
        resize_keyboard=True,
    )


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


def make_saved_posts_keyboard() -> ReplyKeyboardMarkup:
    """Create saved posts reply keyboard (Level 12)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Buttons.CLEAR_ALL)],
            [KeyboardButton(text=Buttons.BACK)],
        ],
        resize_keyboard=True,
    )


def make_subscriptions_keyboard() -> ReplyKeyboardMarkup:
    """Create subscriptions reply keyboard (Level 13)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Buttons.ADD_SUBSCRIPTION)],
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


def make_rating_keyboard(current_rating: str = "") -> ReplyKeyboardMarkup:
    """Create rating selection reply keyboard (Level 21)."""
    options = [
        ("", Buttons.RATING_ALL),
        ("general", Buttons.RATING_GENERAL),
        ("sensitive", Buttons.RATING_SENSITIVE),
        ("questionable", Buttons.RATING_QUESTIONABLE),
        ("explicit", Buttons.RATING_EXPLICIT),
    ]
    
    keyboard = []
    # Row 1: All | General
    row1 = []
    for rating_value, label in options[0:2]:
        display_label = f"✓ {label}" if rating_value == current_rating else label
        row1.append(KeyboardButton(text=display_label))
    keyboard.append(row1)
    
    # Row 2: Sensitive | Questionable
    row2 = []
    for rating_value, label in options[2:4]:
        display_label = f"✓ {label}" if rating_value == current_rating else label
        row2.append(KeyboardButton(text=display_label))
    keyboard.append(row2)
    
    # Row 3: Explicit
    row3 = []
    for rating_value, label in options[4:5]:
        display_label = f"✓ {label}" if rating_value == current_rating else label
        row3.append(KeyboardButton(text=display_label))
    keyboard.append(row3)
    
    # Row 4: Back
    keyboard.append([KeyboardButton(text=Buttons.BACK)])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def make_blacklist_keyboard(blacklist: list = None) -> ReplyKeyboardMarkup:
    """Create blacklist management reply keyboard (Level 22)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Buttons.ADD_TAG)],
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
                KeyboardButton(text=Buttons.SYSTEM),
            ],
            [KeyboardButton(text=Buttons.BACK_TO_ADMIN)],
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


def make_back_keyboard() -> ReplyKeyboardMarkup:
    """Create simple back button keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=Buttons.BACK)]],
        resize_keyboard=True,
    )


def make_back_to_admin_keyboard() -> ReplyKeyboardMarkup:
    """Create back to admin button keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=Buttons.BACK_TO_ADMIN)]],
        resize_keyboard=True,
    )


def make_blacklist_inline_keyboard(blacklist: list) -> InlineKeyboardMarkup:
    """Create blacklist management inline keyboard with tag deletion buttons."""
    keyboard = []
    for item in blacklist:
        row = [
            InlineKeyboardButton(text=item["tag"], callback_data="noop"),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"bl:del:{item['id']}",
            ),
        ]
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard if keyboard else [])


def make_saved_posts_page_keyboard(page: int, has_more: bool) -> InlineKeyboardMarkup:
    """Create pagination keyboard for saved posts (Level 12)."""
    buttons = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=f"posts:prev",
            )
        )
    buttons.append(
        InlineKeyboardButton(text=f"{page + 1}", callback_data="noop")
    )
    if has_more:
        buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=f"posts:next",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])


def make_subscriptions_inline_keyboard(subscriptions: list) -> InlineKeyboardMarkup:
    """Create subscriptions inline keyboard with delete buttons."""
    keyboard = []
    for sub in subscriptions:
        row = [
            InlineKeyboardButton(text=sub["tag"], callback_data="noop"),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"subs:del:{sub['id']}",
            ),
        ]
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard if keyboard else [])


def make_users_list_inline_keyboard(users: list, page: int, pages: int) -> InlineKeyboardMarkup:
    """Create users list inline keyboard (Level 52)."""
    keyboard = []
    
    for user in users:
        badges = ""
        if user.get("is_vip"):
            badges += " ⭐"
        if user.get("is_banned"):
            badges += " 🚫"
        
        username = user.get("username") or "N/A"
        user_id = user.get("user_id")
        
        row = [
            InlineKeyboardButton(
                text=f"👤 @{username} (ID: {user_id}){badges}",
                callback_data=f"users:card:{user_id}",
            )
        ]
        keyboard.append(row)
    
    # Pagination row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data="users:prev")
        )
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop")
    )
    if page < pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data="users:next")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_user_card_inline_keyboard(user_id: int, is_vip: bool, is_banned: bool) -> InlineKeyboardMarkup:
    """Create user card inline keyboard (Level 53)."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="❌ Снять VIP" if is_vip else "⭐ Выдать VIP",
                callback_data=f"users:vip:{user_id}",
            ),
            InlineKeyboardButton(
                text="🔓 Разбанить" if is_banned else "🔨 Забанить",
                callback_data=f"users:ban:{user_id}",
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="users:list"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_requests_list_inline_keyboard(requests: list) -> InlineKeyboardMarkup:
    """Create requests list inline keyboard (Level 61)."""
    keyboard = []
    
    for req in requests:
        username = req.get("username") or "N/A"
        requested_at = req.get("requested_at", "")[:16] if req.get("requested_at") else ""
        
        row = [
            InlineKeyboardButton(
                text=f"📩 @{username} ({requested_at})",
                callback_data=f"req:card:{req['user_id']}",
            )
        ]
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard if keyboard else [])


def make_request_card_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Create request card inline keyboard (Level 62)."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"req:ok:{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"req:no:{user_id}"),
        ],
        [
            InlineKeyboardButton(text="🚫 Отклонить + Бан", callback_data=f"req:ban:{user_id}"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="req:list"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def make_global_blacklist_inline_keyboard(global_blacklist: list) -> InlineKeyboardMarkup:
    """Create global blacklist inline keyboard (Level 81)."""
    keyboard = []
    for item in global_blacklist:
        row = [
            InlineKeyboardButton(text=item["tag"], callback_data="noop"),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"gbl:del:{item['id']}",
            ),
        ]
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard if keyboard else [])


def make_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    """Create clear all confirmation keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="posts:clear:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="posts:clear:cancel"),
            ],
        ]
    )


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


def make_user_action_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create keyboard for specific user action (add, ban, vip, unvip)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="settings_users")]
        ]
    )
