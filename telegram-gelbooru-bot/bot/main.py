"""Main bot entry point."""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineQuery
from aiogram.fsm.state import State, StatesGroup

from .config import config
from . import db
from .gelbooru import gelbooru_client
from .cache import init_cache, start_cleanup_task
from .middleware.access import AccessMiddleware
from .handlers.inline import handle_inline_query
from .handlers.callbacks import (
    handle_save_search,
    handle_info,
    handle_full_size,
    handle_delete_message,
    handle_delete_search,
    handle_delete_saved_post,
    handle_use_search,
)
from .handlers.commands import (
    cmd_start,
    cmd_help,
    cmd_adduser,
    cmd_ban,
    cmd_vip,
    cmd_unvip,
    cmd_users,
)
from .handlers.messages import (
    handle_my_searches,
    handle_saved_posts,
    handle_blacklist,
    handle_settings,
    handle_add_blacklist_tag,
)
from .handlers.keyboard import make_main_keyboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def setup_handlers(dp: Dispatcher, bot: Bot) -> None:
    """Register all handlers."""
    
    # Add access middleware
    access_middleware = AccessMiddleware(owner_id=config.owner_id)
    dp.inline_query.middleware(access_middleware)
    dp.message.middleware(access_middleware)
    dp.callback_query.middleware(access_middleware)
    
    # Inline query handler
    @dp.inline_query()
    async def inline_handler(inline_query: InlineQuery, user_role: str = None):
        await handle_inline_query(inline_query, user_role)
    
    # Callback handlers
    @dp.callback_query(F.data.startswith("sq:"))
    async def callback_save_search(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            query_id = int(callback.data.split(":")[1])
            await handle_save_search(callback, query_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)
    
    @dp.callback_query(F.data.startswith("i:"))
    async def callback_info(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            post_id = int(callback.data.split(":")[1])
            await handle_info(callback, post_id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)
    
    @dp.callback_query(F.data.startswith("fs:"))
    async def callback_full_size(callback: CallbackQuery, user_role: str):
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
    async def callback_delmsg(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        await handle_delete_message(callback)
    
    @dp.callback_query(F.data.startswith("del_search:"))
    async def callback_del_search(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            search_id = int(callback.data.split(":")[1])
            await handle_delete_search(callback, search_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)
    
    @dp.callback_query(F.data.startswith("del_saved:"))
    async def callback_del_saved(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            post_id = int(callback.data.split(":")[1])
            await handle_delete_saved_post(callback, post_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)
    
    @dp.callback_query(F.data.startswith("use_search:"))
    async def callback_use_search(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            query_id = int(callback.data.split(":")[1])
            await handle_use_search(callback, query_id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)
    
    @dp.callback_query(F.data.startswith("set_rating:"))
    async def callback_set_rating(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            rating = callback.data.split(":")[1]
            if rating in ("safe", "questionable", "explicit", "all"):
                await db.set_user_setting(callback.from_user.id, "rating", rating)
                await callback.answer(f"✅ Рейтинг установлен: {rating}")
                # Update the settings message
                await callback.message.edit_text(
                    f"**Настройки**\n\nТекущий рейтинг: `{rating}`",
                    parse_mode="Markdown",
                    reply_markup=callback.message.reply_markup,
                )
            else:
                await callback.answer("⚠️ Неверный рейтинг", show_alert=True)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
    
    @dp.callback_query(F.data.startswith("del_bl:"))
    async def callback_del_blacklist(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            bl_id = int(callback.data.split(":")[1])
            deleted = await db.remove_from_blacklist(bl_id, callback.from_user.id)
            if deleted:
                await callback.answer("🗑️ Тег удалён из чёрного списка")
                # Refresh blacklist view
                await handle_blacklist(callback.message, callback.from_user.id)
            else:
                await callback.answer("Тег не найден", show_alert=True)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)
    
    @dp.callback_query(F.data.startswith("saved_page:"))
    async def callback_saved_page(callback: CallbackQuery, user_role: str):
        if user_role is None:
            return
        try:
            page = int(callback.data.split(":")[1])
            await handle_saved_posts(callback.message, callback.from_user.id, page)
            await callback.answer()
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
    
    # Command handlers
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
    
    # Text message handlers (keyboard buttons)
    @dp.message(F.text == "📌 Мои поиски")
    async def my_searches_msg(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_my_searches(message, message.from_user.id)
    
    @dp.message(F.text == "❤️ Сохранённые")
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
    
    # Handle text messages for adding to blacklist (when in blacklist context)
    # For simplicity, we'll just ignore them or provide a hint
    @dp.message()
    async def other_message(message: Message, user_role: str = None):
        # Could implement context-aware handling here
        pass


async def on_startup(bot: Bot) -> None:
    """Startup tasks."""
    logger.info("Bot starting up...")
    
    # Initialize database
    db.init_db()
    
    # Initialize cache
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
    try:
        dp.run_polling(bot)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        asyncio.run(on_shutdown(bot))


if __name__ == "__main__":
    main()
