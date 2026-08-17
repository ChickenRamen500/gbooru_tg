"""Message handlers for text messages (keyboard buttons) and FSM flows."""

import logging
from typing import Any

from aiogram.types import Message

import db
from handlers.keyboard import (
    make_main_keyboard,
    make_saved_and_subs_keyboard,
    make_settings_keyboard,
    make_blacklist_inline_keyboard,
    make_my_searches_inline_keyboard,
    make_admin_panel_keyboard,
    make_users_manage_keyboard,
    make_system_keyboard,
    make_requests_keyboard,
    make_stats_keyboard,
    make_broadcast_keyboard,
    make_back_keyboard,
    make_rating_inline_keyboard,
)

logger = logging.getLogger(__name__)

DEV_MESSAGE = (
    "🚧 Этот раздел пока в разработке.\n"
    "Скоро здесь появится соответствующий функционал."
)

# FSM state per user: user_id -> state name
_fsm: dict[int, str] = {}
# FSM data per user: user_id -> dict
_fsm_data: dict[int, Any] = {}
# Current reply-menu screen per user (for contextual "🔙 Назад")
_user_menu_state: dict[int, str] = {}

# FSM states
FSM_ADD_SEARCH = "add_search"
FSM_ADD_BL_TAG = "add_bl_tag"
FSM_ADD_GBL_TAG = "add_gbl_tag"
FSM_FIND_USER = "find_user"
FSM_BROADCAST = "broadcast"


def clear_fsm(user_id: int) -> None:
    """Clear any active FSM state for the user."""
    _fsm.pop(user_id, None)
    _fsm_data.pop(user_id, None)


def set_menu_state(user_id: int, state: str) -> None:
    """Record the current reply-keyboard screen for context-aware back navigation."""
    _user_menu_state[user_id] = state


# =============================================================================
# MAIN / NAV
# =============================================================================

async def show_main_menu(message: Message, user_id: int, is_owner: bool) -> None:
    """Show the main menu with reply keyboard."""
    clear_fsm(user_id)
    set_menu_state(user_id, "main")
    await message.answer(
        "🏠 **Главное меню**\n\nПривет! Я бот для поиска артов. "
        "Выбери нужное действие в меню ниже.",
        parse_mode="Markdown",
        reply_markup=make_main_keyboard(is_owner=is_owner),
    )


# =============================================================================
# MY SEARCHES
# =============================================================================

async def handle_my_searches(message: Message, user_id: int) -> None:
    """Handle '📌 Мои поиски' button."""
    clear_fsm(user_id)
    set_menu_state(user_id, "my_searches")
    searches = await db.get_saved_searches(user_id)

    if not searches:
        await message.answer(
            "📌 **Мои поиски**\n\nУ тебя пока нет сохраненных поисков.\n"
            "Нажми «➕ Добавить поиск», чтобы создать первый.",
            parse_mode="Markdown",
            reply_markup=make_my_searches_inline_keyboard(searches),
        )
        return

    text = "📌 **Мои поиски**\n\nТапни поиск, чтобы запустить:"
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_my_searches_inline_keyboard(searches),
    )


async def handle_add_search_input(message: Message, user_id: int) -> None:
    """FSM: receive tags for a new saved search."""
    tags = message.text.strip()
    if not tags:
        await message.answer("❌ Пустой запрос. Отправь теги ещё раз.")
        return

    success, msg = await db.save_search(user_id, tags)
    if success:
        await message.answer(f"✅ Поиск `{tags}` сохранён.", parse_mode="Markdown")
    else:
        await message.answer("❌ Такой поиск уже сохранён.", parse_mode="Markdown")
    # Re-show my searches
    await handle_my_searches(message, user_id)


# =============================================================================
# SAVED & SUBS (under development)
# =============================================================================

async def handle_saved_and_subs(message: Message, user_id: int) -> None:
    """Handle '❤️ Сохраненное и подписки' button - show submenu."""
    clear_fsm(user_id)
    set_menu_state(user_id, "saved_and_subs")
    await message.answer(
        "❤️ **Сохраненное и подписки**\n\nВыбери раздел.",
        parse_mode="Markdown",
        reply_markup=make_saved_and_subs_keyboard(),
    )


async def handle_saved_posts(message: Message, user_id: int, page: int = 0) -> None:
    """Saved posts — under development."""
    set_menu_state(user_id, "saved_posts")
    await message.answer(
        "🖼 **Сохраненные посты**\n\n" + DEV_MESSAGE,
        parse_mode="Markdown",
        reply_markup=make_saved_and_subs_keyboard(),
    )


async def handle_subscriptions(message: Message, user_id: int) -> None:
    """Subscriptions — under development."""
    set_menu_state(user_id, "subscriptions")
    await message.answer(
        f"🔔 **Подписки на теги**\n\n{DEV_MESSAGE}",
        parse_mode="Markdown",
        reply_markup=make_saved_and_subs_keyboard(),
    )


# =============================================================================
# SETTINGS
# =============================================================================

async def handle_settings(message: Message, user_id: int, is_owner: bool = False) -> None:
    """Handle '⚙️ Настройки' button."""
    clear_fsm(user_id)
    set_menu_state(user_id, "settings")
    await message.answer(
        "⚙️ **Меню настроек**\n\nЗдесь ты можешь настроить фильтры и чёрные списки.",
        parse_mode="Markdown",
        reply_markup=make_settings_keyboard(is_owner=is_owner),
    )


async def handle_rating_menu(message: Message, user_id: int) -> None:
    """Show rating selection inline keyboard."""
    set_menu_state(user_id, "rating")
    current = await db.get_user_rating(user_id)
    await message.answer(
        "📊 **Рейтинг постов**\n\nВыбери рейтинг по умолчанию:\n\n"
        "⚪ Все • 🟢 General • 🟡 Sensitive • 🟠 Questionable • 🔴 Explicit",
        parse_mode="Markdown",
        reply_markup=make_rating_inline_keyboard(current),
    )


async def handle_blacklist(message: Message, user_id: int) -> None:
    """Handle blacklist management screen."""
    set_menu_state(user_id, "blacklist")
    blacklist = await db.get_blacklist(user_id)
    if not blacklist:
        text = "🚫 **Чёрный список тегов**\n\nЧёрный список пуст."
    else:
        text = "🚫 **Чёрный список тегов**\n\nПосты с этими тегами не будут показываться."
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_blacklist_inline_keyboard(blacklist),
    )


async def handle_add_blacklist_tag(message: Message, user_id: int) -> None:
    """FSM: receive a tag to add to blacklist."""
    tag = message.text.strip()
    if not tag:
        await message.answer("❌ Пустой тег. Отправь тег ещё раз.")
        return
    if " " in tag:
        await message.answer("❌ Тег не должен содержать пробелов. Отправь один тег.")
        return

    success, msg = await db.add_to_blacklist(user_id, tag)
    await message.answer(msg, parse_mode="Markdown")
    await handle_blacklist(message, user_id)


# =============================================================================
# ADMIN PANEL
# =============================================================================

async def handle_admin_panel(message: Message, user_id: int) -> None:
    """Show admin panel reply keyboard."""
    clear_fsm(user_id)
    set_menu_state(user_id, "admin")
    await message.answer(
        "👑 **Панель управления ботом**\n\nВыберите раздел:",
        parse_mode="Markdown",
        reply_markup=make_admin_panel_keyboard(),
    )


async def handle_users_manage(message: Message, user_id: int) -> None:
    """Show user management reply keyboard."""
    set_menu_state(user_id, "users_manage")
    await message.answer(
        "👥 **Управление пользователями**",
        parse_mode="Markdown",
        reply_markup=make_users_manage_keyboard(),
    )


async def handle_users_list(message: Message, user_id: int, page: int = 0) -> None:
    """Show paginated users list (inline)."""
    from handlers.keyboard import make_users_list_inline_keyboard, USERS_PER_PAGE

    set_menu_state(user_id, "users_list")
    users, total = await db.get_users_paginated(limit=USERS_PER_PAGE, offset=page * USERS_PER_PAGE)
    pages = (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    text = f"👥 **Список пользователей**\n\nВсего: {total}\nСтраница {page + 1}/{max(pages, 1)}"
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_users_list_inline_keyboard(users, page, max(pages, 1)),
    )


async def handle_find_user_prompt(message: Message, user_id: int) -> None:
    """Ask owner for a user ID to find."""
    _fsm[user_id] = FSM_FIND_USER
    await message.answer(
        "🔍 **Поиск по ID**\n\nОтправь ID пользователя числом.",
        parse_mode="Markdown",
        reply_markup=make_back_keyboard(),
    )


async def handle_find_user_input(message: Message, user_id: int) -> None:
    """FSM: receive user ID and show their card."""
    from handlers.keyboard import make_user_card_inline_keyboard

    raw = message.text.strip()
    try:
        target_id = int(raw)
    except ValueError:
        await message.answer("❌ Неверный формат. Отправь число (ID пользователя).")
        return

    user = await db.get_user_by_id(target_id)
    if not user:
        await message.answer(f"❌ Пользователь `{target_id}` не найден.", parse_mode="Markdown")
        await handle_users_manage(message, user_id)
        return

    role = user.get("role", "user")
    status = {"vip": "⭐ VIP", "banned": "🚫 Забанен", "owner": "👑 Владелец"}.get(role, "Обычный")
    text = (
        "👤 **Карточка пользователя**\n\n"
        f"ID: `{user['user_id']}`\n"
        f"User: @{user.get('username') or 'нет'}\n"
        f"Статус: {status}"
    )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_user_card_inline_keyboard(user["user_id"], role),
    )


async def handle_requests_menu(message: Message, user_id: int) -> None:
    """Show requests menu reply keyboard."""
    set_menu_state(user_id, "requests_menu")
    pending = await db.get_pending_access_requests()
    await message.answer(
        f"📩 **Заявки на доступ**\n\nОжидают: **{len(pending)}**",
        parse_mode="Markdown",
        reply_markup=make_requests_keyboard(len(pending)),
    )


async def handle_requests_pending(message: Message, user_id: int) -> None:
    """Show pending requests inline list."""
    from handlers.keyboard import make_requests_list_inline_keyboard

    set_menu_state(user_id, "requests_pending")
    requests = await db.get_pending_access_requests()
    if not requests:
        await message.answer(
            "⏳ **Ожидают одобрения**\n\nСейчас нет заявок на доступ.",
            parse_mode="Markdown",
            reply_markup=make_requests_list_inline_keyboard(requests),
        )
        return
    await message.answer(
        "⏳ **Ожидают одобрения**\n\nТапни заявку, чтобы открыть карточку.",
        parse_mode="Markdown",
        reply_markup=make_requests_list_inline_keyboard(requests),
    )


async def handle_stats(message: Message, user_id: int) -> None:
    """Show bot statistics."""
    set_menu_state(user_id, "stats")
    stats = await db.get_stats()
    text = (
        "📈 **Статистика**\n\n"
        f"• Пользователей: {stats['users_count']}\n"
        f"• VIP: {stats['vip_count']}\n"
        f"• Забанено: {stats['banned_count']}\n"
        f"• Заявок в ожидании: {stats['requests_count']}\n"
        f"• Сохранённых постов: {stats['saved_posts_count']}\n"
        f"• Размер БД: {stats['db_size']}"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=make_stats_keyboard())


async def handle_broadcast_prompt(message: Message, user_id: int) -> None:
    """Ask owner for broadcast text."""
    _fsm[user_id] = FSM_BROADCAST
    _fsm_data[user_id] = {}
    await message.answer(
        "📢 **Рассылка**\n\nОтправь сообщение, которое получат все пользователи.",
        parse_mode="Markdown",
        reply_markup=make_broadcast_keyboard(),
    )


async def handle_broadcast_input(message: Message, user_id: int) -> None:
    """FSM: receive broadcast text and show preview."""
    from handlers.keyboard import make_broadcast_preview_keyboard

    draft = message.text.strip()
    if not draft or len(draft) > 4096:
        await message.answer("❌ Сообщение пустое или слишком длинное (макс. 4096 символов).")
        return
    _fsm_data[user_id] = {"draft": draft}
    set_menu_state(user_id, "broadcast_preview")
    await message.answer(
        f"👁 **Предпросмотр рассылки**\n\n{draft}\n\nОтправить всем пользователям?",
        parse_mode="Markdown",
        reply_markup=make_broadcast_preview_keyboard(),
    )


async def handle_system(message: Message, user_id: int) -> None:
    """Show system settings reply keyboard."""
    set_menu_state(user_id, "system")
    await message.answer(
        "⚙️ **Системные настройки**",
        parse_mode="Markdown",
        reply_markup=make_system_keyboard(),
    )


async def handle_global_blacklist(message: Message, user_id: int) -> None:
    """Show global blacklist management inline keyboard."""
    from handlers.keyboard import make_global_blacklist_inline_keyboard

    set_menu_state(user_id, "global_blacklist")
    gbl = await db.get_global_blacklist()
    if not gbl:
        text = "🌍 **Глобальный чёрный список**\n\nЭти теги запрещены для всех пользователей.\n\nСписок пуст."
    else:
        text = "🌍 **Глобальный чёрный список**\n\nЭти теги запрещены для всех пользователей."
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=make_global_blacklist_inline_keyboard(gbl),
    )


async def handle_add_gbl_tag_input(message: Message, user_id: int) -> None:
    """FSM: receive a tag to add to global blacklist."""
    tag = message.text.strip()
    if not tag:
        await message.answer("❌ Пустой тег. Отправь тег ещё раз.")
        return
    if " " in tag:
        await message.answer("❌ Тег не должен содержать пробелов. Отправь один тег.")
        return

    success, msg = await db.add_to_global_blacklist(tag)
    await message.answer(msg, parse_mode="Markdown")
    await handle_global_blacklist(message, user_id)


async def handle_clear_cache_prompt(message: Message, user_id: int) -> None:
    """Ask for confirmation to clear cache."""
    from handlers.keyboard import make_clear_cache_confirm_keyboard

    set_menu_state(user_id, "clear_cache")
    await message.answer(
        "🔄 **Сбросить кэш**\n\nЭто очистит кэш ответов Gelbooru API (поиски и посты). Продолжить?",
        parse_mode="Markdown",
        reply_markup=make_clear_cache_confirm_keyboard(),
    )
