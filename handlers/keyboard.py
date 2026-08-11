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
                KeyboardButton(text="❤️ Сохранённые"),
            ],
            [
                KeyboardButton(text="🚫 Чёрный список"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
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


def make_rating_keyboard(current_rating: str = "") -> InlineKeyboardMarkup:
    """Create rating selection keyboard. Uses Gelbooru's actual rating values."""
    # Gelbooru ratings: general, sensitive, questionable, explicit
    # '' (empty) = no filter (all)
    options = [
        ("", "⚪ Все"),
        ("general", "🟢 General"),
        ("sensitive", "🟡 Sensitive"),
        ("questionable", "🟠 Questionable"),
        ("explicit", "🔴 Explicit"),
    ]

    buttons = []
    for rating_value, label in options:
        if rating_value == current_rating:
            label = f"✓ {label}"
        buttons.append(
            InlineKeyboardButton(text=label, callback_data=f"set_rating:{rating_value}")
        )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


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
