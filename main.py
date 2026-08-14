"""Main bot entry point."""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineQuery, ChosenInlineResult

from config import config
import db
from gelbooru import gelbooru_client
from cache import init_cache, start_cleanup_task
from middleware.access import AccessMiddleware
from handlers.inline import handle_inline_query, handle_chosen_inline_result
from handlers.callbacks import (
    handle_save_search,
    handle_info,
    handle_full_size,
    handle_delete_message,
    handle_delete_search,
    handle_delete_saved_post,
)
from handlers.commands import (
    cmd_start,
    cmd_help,
    cmd_adduser,
    cmd_ban,
    cmd_vip,
    cmd_unvip,
    cmd_users,
)
from handlers.messages import (
    handle_my_searches,
    handle_saved_posts,
    handle_blacklist,
    handle_settings,
    handle_add_blacklist_tag,
)
from handlers.keyboard import make_main_keyboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# State for blacklist context: user_id -> bool (waiting for tag input)
_bl_context: dict[int, bool] = {}


def setup_handlers(dp: Dispatcher, bot: Bot) -> None:
    """Register all handlers."""

    # Add access middleware
    access_middleware = AccessMiddleware(owner_id=config.owner_id)
    dp.inline_query.middleware(access_middleware)
    dp.message.middleware(access_middleware)
    dp.callback_query.middleware(access_middleware)

    # --- Inline query handler ---
    @dp.inline_query()
    async def inline_handler(inline_query: InlineQuery, user_role: str = None):
        await handle_inline_query(inline_query, user_role)

    # --- Chosen inline result (for video > 20MB caption edit) ---
    @dp.chosen_inline_result()
    async def chosen_result(chosen: ChosenInlineResult, user_role: str = None):
        await handle_chosen_inline_result(chosen, bot)

    # --- Callback handlers ---
    @dp.callback_query(F.data.startswith("sq:"))
    async def callback_save_search(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            query_id = int(callback.data.split(":")[1])
            await handle_save_search(callback, query_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("i:"))
    async def callback_info(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            post_id = int(callback.data.split(":")[1])
            await handle_info(callback, post_id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("fs:"))
    async def callback_full_size(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            post_id = int(callback.data.split(":")[1])
            await handle_full_size(
                callback, post_id, callback.from_user.id, (await bot.get_me()).username
            )
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data == "delmsg")
    async def callback_delmsg(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await handle_delete_message(callback)

    @dp.callback_query(F.data.startswith("del_search:"))
    async def callback_del_search(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            search_id = int(callback.data.split(":")[1])
            await handle_delete_search(callback, search_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("del_saved:"))
    async def callback_del_saved(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            post_id = int(callback.data.split(":")[1])
            await handle_delete_saved_post(callback, post_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("set_rating:"))
    async def callback_set_rating(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            rating = callback.data.split(":")[1]
            if rating in ("", "general", "sensitive", "questionable", "explicit"):
                display = rating if rating else "all"
                await db.set_user_setting(callback.from_user.id, "rating", rating)
                logger.info(
                    "User %s set rating to '%s'", callback.from_user.id, display
                )
                from handlers.keyboard import make_rating_keyboard
                await callback.message.edit_text(
                    f"**Настройки**\n\nТекущий рейтинг: `{display}`",
                    parse_mode="Markdown",
                    reply_markup=make_rating_keyboard(rating),
                )
                await callback.answer(f"✅ Рейтинг установлен: {display}")
            else:
                await callback.answer("⚠️ Неверный рейтинг", show_alert=True)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)

    @dp.callback_query(F.data.startswith("del_bl:"))
    async def callback_del_blacklist(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            bl_id = int(callback.data.split(":")[1])
            deleted = await db.remove_from_blacklist(bl_id, callback.from_user.id)
            if deleted:
                await callback.answer("🗑️ Тег удалён из чёрного списка")
                await handle_blacklist(callback.message, callback.from_user.id)
            else:
                await callback.answer("Тег не найден", show_alert=True)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("saved_page:"))
    async def callback_saved_page(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            page = int(callback.data.split(":")[1])
            await handle_saved_posts(callback.message, callback.from_user.id, page)
            await callback.answer()
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)

    @dp.callback_query(F.data.startswith("add_bl:"))
    async def callback_start_add_bl(callback: CallbackQuery, user_role: str = None):
        """Enter blacklist tag addition mode."""
        if user_role is None:
            return
        _bl_context[callback.from_user.id] = True
        await callback.answer()
        await callback.message.answer("Отправьте тег, который нужно добавить в чёрный список:")

    # Settings menu callbacks
    @dp.callback_query(F.data == "settings_rating")
    async def callback_settings_rating(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        from handlers.keyboard import make_rating_menu_keyboard
        text = (
            "**Настройки рейтинга постов**\n\n"
            "Выберите рейтинг по умолчанию для поиска:\n\n"
            "⚪ Все — все рейтинги\n"
            "🟢 General — безопасный контент\n"
            "🟡 Sensitive — лёгкая нагота\n"
            "🟠 Questionable — откровенный контент\n"
            "🔴 Explicit — порнография"
        )
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=make_rating_menu_keyboard(),
        )
        await callback.answer()

    @dp.callback_query(F.data == "settings_blacklist")
    async def callback_settings_blacklist(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await handle_blacklist(callback.message, callback.from_user.id)
        await callback.answer()

    @dp.callback_query(F.data == "settings_users")
    async def callback_settings_users(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        from handlers.keyboard import make_users_management_keyboard
        text = "**Настройки пользователей**\n\nУправление доступом и заявками:"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=make_users_management_keyboard(),
        )
        await callback.answer()

    @dp.callback_query(F.data == "settings_back")
    async def callback_settings_back(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        is_owner = callback.from_user.id == config.owner_id
        text = "**Настройки**\n\nВыберите раздел:"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=make_settings_keyboard(is_owner),
        )
        await callback.answer()

    @dp.callback_query(F.data == "main_menu")
    async def callback_main_menu(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        text = (
            "Бот для поиска изображений с Gelbooru.\n\n"
            "Использование: @botname теги — в любом чате.\n\n"
            "Для управления — используйте меню ниже 👇"
        )
        await callback.message.edit_text(
            text,
            reply_markup=make_main_keyboard(),
        )
        await callback.answer()

    @dp.callback_query(F.data == "request_access")
    async def callback_request_access(callback: CallbackQuery, user_role: str = None):
        """Handle access request from unauthorized user."""
        user = callback.from_user
        request_text = (
            f"📩 **Новая заявка на доступ**\n\n"
            f"ID: `{user.id}`\n"
            f"Username: @{user.username or 'нет'}\n"
            f"Имя: {user.first_name or ''} {user.last_name or ''}\n"
            f"Язык: {user.language_code or 'не указан'}"
        )
        try:
            await bot.send_message(
                chat_id=config.owner_id,
                text=request_text,
                parse_mode="Markdown",
            )
            await callback.answer("✅ Заявка отправлена владельцу бота")
        except Exception as e:
            logger.error(f"Failed to send access request: {e}")
            await callback.answer("⚠️ Ошибка при отправке заявки", show_alert=True)

    # --- Command handlers ---
    @dp.message(Command("start"))
    async def start_cmd(message: Message, user_role: str = None):
        await cmd_start(message, user_role)

    @dp.message(Command("help"))
    async def help_cmd(message: Message, user_role: str = None):
        await cmd_help(message, user_role)

    @dp.message(Command("adduser"))
    async def adduser_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_adduser(message, user_role, args)

    @dp.message(Command("ban"))
    async def ban_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_ban(message, user_role, args)

    @dp.message(Command("vip"))
    async def vip_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_vip(message, user_role, args)

    @dp.message(Command("unvip"))
    async def unvip_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_unvip(message, user_role, args)

    @dp.message(Command("users"))
    async def users_cmd(message: Message, user_role: str = None):
        await cmd_users(message, user_role)

    # --- Text message handlers (keyboard buttons) ---
    @dp.message(F.text == "📌 Мои поиски")
    async def my_searches_msg(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_my_searches(message, message.from_user.id)

    @dp.message(F.text == "❤️ Сохраненные посты и подписки на теги")
    async def saved_posts_msg(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_saved_posts(message, message.from_user.id)

    @dp.message(F.text == "🚫 Чёрный список")
    async def blacklist_msg(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_blacklist(message, message.from_user.id)

    @dp.message(F.text == "⚙️ Настройки")
    async def settings_msg(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_settings(message, message.from_user.id)

    # --- Blacklist tag input (when in add-blacklist context) ---
    @dp.message(F.text)
    async def text_handler(message: Message, user_role: str = None):
        if user_role is None:
            return
        user_id = message.from_user.id
        if _bl_context.get(user_id):
            _bl_context.pop(user_id, None)
            await handle_add_blacklist_tag(message, user_id)


async def on_startup(bot: Bot) -> None:
    """Startup tasks."""
    logger.info("Bot starting up...")

    # Initialize database
    db.init_db()

    # Initialize cache directories
    init_cache()

    # Start cleanup task
    await start_cleanup_task()

    # Add owner to database if not exists
    await db.add_user(config.owner_id, "owner", "owner")

    logger.info(f"Bot started. Owner ID: {config.owner_id}")


async def on_shutdown(bot: Bot) -> None:
    """Shutdown tasks."""
    logger.info("Bot shutting down...")
    await gelbooru_client.close()


def main() -> None:
    """Main entry point."""
    if not config.is_valid:
        logger.error("Invalid configuration. Check .env file.")
        sys.exit(1)

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    setup_handlers(dp, bot)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting bot polling...")
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
