"""Main bot entry point."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineQuery, ChosenInlineResult

from config import config
import db
import tags_db
from cache import init_cache, start_cleanup_task, clear_all_cache
from constants import Buttons
from gelbooru import gelbooru_client
from middleware.access import AccessMiddleware
from handlers.inline import handle_inline_query, handle_chosen_inline_result
from handlers.callbacks import (
    handle_save_search,
    handle_info,
    handle_full_size,
    handle_delete_message,
)
from handlers.commands import (
    cmd_start,
    cmd_help,
    cmd_adduser,
    cmd_ban,
    cmd_unban,
    cmd_vip,
    cmd_unvip,
    cmd_users,
)
from handlers.messages import (
    handle_my_searches,
    handle_saved_and_subs,
    handle_saved_posts,
    handle_subscriptions,
    handle_blacklist,
    handle_settings,
    handle_rating_menu,
    handle_add_blacklist_tag,
    handle_add_search_input,
    handle_admin_panel,
    handle_users_manage,
    handle_users_list,
    handle_find_user_prompt,
    handle_find_user_input,
    handle_requests_menu,
    handle_requests_pending,
    handle_stats,
    handle_broadcast_prompt,
    handle_broadcast_input,
    handle_system,
    handle_global_blacklist,
    handle_add_gbl_tag_input,
    handle_clear_cache_prompt,
    show_main_menu,
    clear_fsm,
    _fsm,
    _fsm_data,
    FSM_ADD_SEARCH,
    FSM_ADD_BL_TAG,
    FSM_ADD_GBL_TAG,
    FSM_FIND_USER,
    FSM_BROADCAST,
)
from handlers.keyboard import (
    make_rating_inline_keyboard,
    make_blacklist_inline_keyboard,
    make_my_searches_inline_keyboard,
    make_users_list_inline_keyboard,
    make_user_card_inline_keyboard,
    make_requests_list_inline_keyboard,
    make_request_card_inline_keyboard,
    make_global_blacklist_inline_keyboard,
    make_broadcast_keyboard,
    USERS_PER_PAGE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def setup_handlers(dp: Dispatcher, bot: Bot) -> None:
    """Register all handlers."""

    access_middleware = AccessMiddleware(owner_id=config.owner_id)
    dp.inline_query.middleware(access_middleware)
    dp.message.middleware(access_middleware)
    dp.callback_query.middleware(access_middleware)

    # --- Inline query handler ---
    @dp.inline_query()
    async def inline_handler(inline_query: InlineQuery, user_role: str = None):
        await handle_inline_query(inline_query, user_role)

    @dp.chosen_inline_result()
    async def chosen_result(chosen: ChosenInlineResult, user_role: str = None):
        await handle_chosen_inline_result(chosen, bot)

    # =========================================================================
    # CALLBACKS — inline results (search/info/fullsize)
    # =========================================================================
    @dp.callback_query(F.data.startswith("sq:"))
    async def cb_save_search(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            query_id = int(callback.data.split(":")[1])
            await handle_save_search(callback, query_id, callback.from_user.id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("i:"))
    async def cb_info(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            post_id = int(callback.data.split(":")[1])
            await handle_info(callback, post_id)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data.startswith("fs:"))
    async def cb_full_size(callback: CallbackQuery, user_role: str = None):
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
    async def cb_delmsg(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await handle_delete_message(callback)

    @dp.callback_query(F.data == "noop")
    async def cb_noop(callback: CallbackQuery, user_role: str = None):
        await callback.answer()

    # --- Saved searches (inline list) ---
    @dp.callback_query(F.data.startswith("searches:del:"))
    async def cb_del_search(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            search_id = int(callback.data.split(":")[2])
            deleted = await db.delete_saved_search(search_id, callback.from_user.id)
            if deleted:
                await callback.answer("🗑️ Поиск удалён")
                # Re-render the my-searches list message
                searches = await db.get_saved_searches(callback.from_user.id)
                try:
                    await callback.message.edit_reply_markup(
                        reply_markup=make_my_searches_inline_keyboard(searches)
                    )
                except Exception:
                    pass
            else:
                await callback.answer("Поиск не найден", show_alert=True)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data == "search:add")
    async def cb_search_add(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        _fsm[callback.from_user.id] = FSM_ADD_SEARCH
        await callback.answer()
        await callback.message.answer(
            "✍️ **Добавить поиск**\n\nОтправь тег или набор тегов одним сообщением.\n"
            "_Пример: `neko landscape`_",
            parse_mode="Markdown",
        )

    # =========================================================================
    # CALLBACKS — rating (inline)
    # =========================================================================
    @dp.callback_query(F.data.startswith("set_rating:"))
    async def cb_set_rating(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        rating = callback.data.split(":", 1)[1]
        if rating in ("", "general", "sensitive", "questionable", "explicit"):
            display = rating if rating else "all"
            await db.set_user_setting(callback.from_user.id, "rating", rating)
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=make_rating_inline_keyboard(rating)
                )
            except Exception:
                pass
            await callback.answer(f"✅ Рейтинг установлен: {display}")
        else:
            await callback.answer("⚠️ Неверный рейтинг", show_alert=True)

    # =========================================================================
    # CALLBACKS — blacklist (inline)
    # =========================================================================
    @dp.callback_query(F.data.startswith("bl:del:"))
    async def cb_del_bl(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            bl_id = int(callback.data.split(":")[2])
            deleted = await db.remove_from_blacklist(bl_id, callback.from_user.id)
            if deleted:
                await callback.answer("🗑️ Тег удалён из чёрного списка")
                blacklist = await db.get_blacklist(callback.from_user.id)
                try:
                    await callback.message.edit_reply_markup(
                        reply_markup=make_blacklist_inline_keyboard(blacklist)
                    )
                except Exception:
                    pass
            else:
                await callback.answer("Тег не найден", show_alert=True)
        except (ValueError, IndexError):
            await callback.answer("⚠️ Неверный формат данных", show_alert=True)

    @dp.callback_query(F.data == "bl:add")
    async def cb_bl_add(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        _fsm[callback.from_user.id] = FSM_ADD_BL_TAG
        await callback.answer()
        await callback.message.answer(
            "✍️ **Добавить тег в ЧС**\n\nОтправь тег одним сообщением.",
            parse_mode="Markdown",
        )

    # =========================================================================
    # CALLBACKS — back navigation (inline -> reply screen)
    # =========================================================================
    async def _send_reply_screen(callback: CallbackQuery, screen: str):
        """Delete the inline message and send a new reply-keyboard screen."""
        user_id = callback.from_user.id
        is_owner = user_id == config.owner_id
        message = callback.message
        try:
            await message.delete()
        except Exception:
            pass
        # Wrap a fake message-like object: we use message.answer directly
        if screen == "main":
            await show_main_menu(message, user_id, is_owner)
        elif screen == "settings":
            await handle_settings(message, user_id, is_owner)
        elif screen == "admin":
            await handle_admin_panel(message, user_id)
        elif screen == "users_manage":
            await handle_users_manage(message, user_id)
        elif screen == "system":
            await handle_system(message, user_id)
        elif screen == "requests_menu":
            await handle_requests_menu(message, user_id)

    @dp.callback_query(F.data == "back:main")
    async def cb_back_main(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer()
        await _send_reply_screen(callback, "main")

    @dp.callback_query(F.data == "back:settings")
    async def cb_back_settings(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer()
        await _send_reply_screen(callback, "settings")

    @dp.callback_query(F.data == "back:users_manage")
    async def cb_back_users_manage(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer()
        await _send_reply_screen(callback, "users_manage")

    @dp.callback_query(F.data == "back:requests_menu")
    async def cb_back_requests_menu(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer()
        await _send_reply_screen(callback, "requests_menu")

    @dp.callback_query(F.data == "back:system")
    async def cb_back_system(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer()
        await _send_reply_screen(callback, "system")

    # =========================================================================
    # CALLBACKS — users management (inline)
    # =========================================================================
    _users_page: dict[int, int] = {}

    async def _render_users_list(callback: CallbackQuery, page: int):
        users, total = await db.get_users_paginated(
            limit=USERS_PER_PAGE, offset=page * USERS_PER_PAGE
        )
        pages = max((total + USERS_PER_PAGE - 1) // USERS_PER_PAGE, 1)
        text = f"👥 **Список пользователей**\n\nВсего: {total}\nСтраница {page + 1}/{pages}"
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_users_list_inline_keyboard(users, page, pages),
            )
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("users:card:"))
    async def cb_user_card(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        user = await db.get_user_by_id(target_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        role = user.get("role", "user")
        status = {"vip": "⭐ VIP", "banned": "🚫 Забанен", "owner": "👑 Владелец"}.get(role, "Обычный")
        text = (
            "👤 **Карточка пользователя**\n\n"
            f"ID: `{user['user_id']}`\n"
            f"User: @{user.get('username') or 'нет'}\n"
            f"Статус: {status}"
        )
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_user_card_inline_keyboard(user["user_id"], role),
            )
        except Exception:
            pass
        await callback.answer()

    @dp.callback_query(F.data == "users:list")
    async def cb_users_list(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        page = _users_page.get(callback.from_user.id, 0)
        await callback.answer()
        await _render_users_list(callback, page)

    @dp.callback_query(F.data == "users:prev")
    async def cb_users_prev(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        uid = callback.from_user.id
        _users_page[uid] = max(0, _users_page.get(uid, 0) - 1)
        await callback.answer()
        await _render_users_list(callback, _users_page[uid])

    @dp.callback_query(F.data == "users:next")
    async def cb_users_next(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        uid = callback.from_user.id
        _users_page[uid] = _users_page.get(uid, 0) + 1
        await callback.answer()
        await _render_users_list(callback, _users_page[uid])

    @dp.callback_query(F.data.startswith("users:vip:"))
    async def cb_user_vip(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        user = await db.get_user_by_id(target_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        new_vip = user.get("role") != "vip"
        await db.set_user_vip(target_id, new_vip)
        await callback.answer("⭐ VIP выдан" if new_vip else "❌ VIP снят")
        refreshed = await db.get_user_by_id(target_id)
        role = refreshed.get("role", "user")
        status = {"vip": "⭐ VIP", "banned": "🚫 Забанен", "owner": "👑 Владелец"}.get(role, "Обычный")
        text = (
            "👤 **Карточка пользователя**\n\n"
            f"ID: `{refreshed['user_id']}`\n"
            f"User: @{refreshed.get('username') or 'нет'}\n"
            f"Статус: {status}"
        )
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_user_card_inline_keyboard(refreshed["user_id"], role),
            )
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("users:ban:"))
    async def cb_user_ban(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        if target_id == config.owner_id:
            await callback.answer("Нельзя забанить владельца", show_alert=True)
            return
        user = await db.get_user_by_id(target_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        new_ban = user.get("role") != "banned"
        await db.set_user_banned(target_id, new_ban)
        await callback.answer("🔨 Забанен" if new_ban else "🔓 Разбанен")
        refreshed = await db.get_user_by_id(target_id)
        role = refreshed.get("role", "user")
        status = {"vip": "⭐ VIP", "banned": "🚫 Забанен", "owner": "👑 Владелец"}.get(role, "Обычный")
        text = (
            "👤 **Карточка пользователя**\n\n"
            f"ID: `{refreshed['user_id']}`\n"
            f"User: @{refreshed.get('username') or 'нет'}\n"
            f"Статус: {status}"
        )
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_user_card_inline_keyboard(refreshed["user_id"], role),
            )
        except Exception:
            pass

    # =========================================================================
    # CALLBACKS — access requests (inline)
    # =========================================================================
    @dp.callback_query(F.data == "request_access")
    async def cb_request_access(callback: CallbackQuery, user_role: str = None):
        """Save access request to DB and notify owner."""
        user = callback.from_user
        inserted = await db.add_access_request(
            user.id,
            user.username or "",
            user.first_name or "",
            user.last_name or "",
            user.language_code or "",
        )
        if inserted:
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
            except Exception as e:
                logger.error(f"Failed to send access request notification: {e}")
            await callback.answer("✅ Заявка отправлена владельцу бота")
        else:
            await callback.answer("Ты уже отправлял заявку. Ожидай решения.", show_alert=True)

    @dp.callback_query(F.data.startswith("req:card:"))
    async def cb_req_card(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        requests = await db.get_pending_access_requests()
        req = next((r for r in requests if r["user_id"] == target_id), None)
        if not req:
            await callback.answer("Заявка не найдена (возможно, уже обработана)", show_alert=True)
            return
        text = (
            "📝 **Заявка**\n\n"
            f"ID: `{req['user_id']}`\n"
            f"User: @{req.get('username') or 'нет'}\n"
            f"Имя: {req.get('first_name') or ''} {req.get('last_name') or ''}\n"
            f"Время: {req.get('requested_at', '')[:19]}"
        )
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_request_card_inline_keyboard(req["user_id"]),
            )
        except Exception:
            pass
        await callback.answer()

    @dp.callback_query(F.data == "req:list")
    async def cb_req_list(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer()
        requests = await db.get_pending_access_requests()
        text = "⏳ **Ожидают одобрения**\n\nТапни заявку, чтобы открыть карточку."
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_requests_list_inline_keyboard(requests),
            )
        except Exception:
            pass

    async def _process_request(callback: CallbackQuery, target_id: int, action: str):
        if action == "ok":
            ok = await db.process_access_request(target_id, "approved")
            await callback.answer("✅ Заявка одобрена" if ok else "Заявка не найдена", show_alert=not ok)
            try:
                await bot.send_message(
                    target_id,
                    "✅ Твоя заявка на доступ одобрена! Теперь можешь пользоваться ботом.",
                )
            except Exception as e:
                logger.warning(f"Could not notify approved user {target_id}: {e}")
        elif action == "no":
            ok = await db.process_access_request(target_id, "rejected")
            await callback.answer("❌ Заявка отклонена" if ok else "Заявка не найдена", show_alert=not ok)
        elif action == "ban":
            ok = await db.process_access_request(target_id, "rejected", ban=True)
            await callback.answer("🚫 Заявка отклонена, пользователь забанен" if ok else "Заявка не найдена", show_alert=not ok)
        # Re-render requests list
        requests = await db.get_pending_access_requests()
        text = f"⏳ **Ожидают одобрения**\n\nОжидают: {len(requests)}"
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=make_requests_list_inline_keyboard(requests),
            )
        except Exception:
            pass

    @dp.callback_query(F.data.startswith("req:ok:"))
    async def cb_req_ok(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        await _process_request(callback, target_id, "ok")

    @dp.callback_query(F.data.startswith("req:no:"))
    async def cb_req_no(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        await _process_request(callback, target_id, "no")

    @dp.callback_query(F.data.startswith("req:ban:"))
    async def cb_req_ban(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            target_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        await _process_request(callback, target_id, "ban")

    # =========================================================================
    # CALLBACKS — broadcast (inline)
    # =========================================================================
    @dp.callback_query(F.data == "broadcast:send")
    async def cb_broadcast_send(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        data = _fsm_data.get(callback.from_user.id, {})
        draft = data.get("draft")
        if not draft:
            await callback.answer("Черновик потерян. Начни заново.", show_alert=True)
            await _send_reply_screen(callback, "admin")
            return
        clear_fsm(callback.from_user.id)
        await callback.answer("📢 Рассылка запущена...")
        user_ids = await db.get_all_user_ids()
        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await bot.send_message(uid, draft)
                sent += 1
            except Exception as e:
                failed += 1
                logger.debug(f"Broadcast failed for {uid}: {e}")
        try:
            await callback.message.edit_text(
                f"📢 **Рассылка отправлена**\n\nДоставлено: {sent}\nНе доставлено: {failed}",
                parse_mode="Markdown",
            )
        except Exception:
            await callback.message.answer(
                f"📢 Рассылка отправлена. Доставлено: {sent}, не доставлено: {failed}."
            )

    @dp.callback_query(F.data == "broadcast:edit")
    async def cb_broadcast_edit(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        _fsm[callback.from_user.id] = FSM_BROADCAST
        await callback.answer()
        await callback.message.answer(
            "✏️ Отправь новый текст рассылки.",
            reply_markup=make_broadcast_keyboard(),
        )

    @dp.callback_query(F.data == "broadcast:cancel")
    async def cb_broadcast_cancel(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        clear_fsm(callback.from_user.id)
        await callback.answer("❌ Рассылка отменена")
        await _send_reply_screen(callback, "admin")

    # =========================================================================
    # CALLBACKS — global blacklist (inline)
    # =========================================================================
    @dp.callback_query(F.data.startswith("gbl:del:"))
    async def cb_gbl_del(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        try:
            gbl_id = int(callback.data.split(":")[2])
        except (ValueError, IndexError):
            await callback.answer("⚠️ Ошибка", show_alert=True)
            return
        deleted = await db.remove_from_global_blacklist(gbl_id)
        if deleted:
            await callback.answer("🗑️ Тег удалён из глобального ЧС")
            gbl = await db.get_global_blacklist()
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=make_global_blacklist_inline_keyboard(gbl)
                )
            except Exception:
                pass
        else:
            await callback.answer("Тег не найден", show_alert=True)

    @dp.callback_query(F.data == "gbl:add")
    async def cb_gbl_add(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        _fsm[callback.from_user.id] = FSM_ADD_GBL_TAG
        await callback.answer()
        await callback.message.answer(
            "✍️ **Добавить тег в глобальный ЧС**\n\nОтправь тег одним сообщением.",
            parse_mode="Markdown",
        )

    # =========================================================================
    # CALLBACKS — clear cache (inline)
    # =========================================================================
    @dp.callback_query(F.data == "cache:clear:confirm")
    async def cb_cache_clear_yes(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        removed = clear_all_cache()
        await callback.answer(f"🔄 Кэш очищен: удалено {removed} файлов", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await handle_system(callback.message, callback.from_user.id)

    @dp.callback_query(F.data == "cache:clear:cancel")
    async def cb_cache_clear_no(callback: CallbackQuery, user_role: str = None):
        if user_role is None:
            return
        await callback.answer("Отмена")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await handle_system(callback.message, callback.from_user.id)

    # =========================================================================
    # COMMANDS
    # =========================================================================
    @dp.message(Command("start"))
    async def start_cmd(message: Message, user_role: str = None):
        await cmd_start(message, user_role)

    @dp.message(Command("help"))
    async def help_cmd(message: Message, user_role: str = None):
        await cmd_help(message, user_role)

    @dp.message(Command("cancel"))
    async def cancel_cmd(message: Message, user_role: str = None):
        if user_role is None:
            return
        clear_fsm(message.from_user.id)
        await message.answer("❌ Действие отменено.")

    @dp.message(Command("adduser"))
    async def adduser_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_adduser(message, user_role, args)

    @dp.message(Command("ban"))
    async def ban_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_ban(message, user_role, args)

    @dp.message(Command("unban"))
    async def unban_cmd(message: Message, user_role: str = None):
        args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
        await cmd_unban(message, user_role, args)

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

    # =========================================================================
    # REPLY KEYBOARD BUTTONS (main navigation)
    # =========================================================================
    @dp.message(F.text == Buttons.MY_SEARCHES)
    async def msg_my_searches(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_my_searches(message, message.from_user.id)

    @dp.message(F.text == Buttons.SAVED_AND_SUBS)
    async def msg_saved_and_subs(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_saved_and_subs(message, message.from_user.id)

    @dp.message(F.text == Buttons.SAVED_POSTS)
    async def msg_saved_posts(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_saved_posts(message, message.from_user.id)

    @dp.message(F.text == Buttons.SUBSCRIPTIONS)
    async def msg_subscriptions(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_subscriptions(message, message.from_user.id)

    @dp.message(F.text == Buttons.SETTINGS)
    async def msg_settings(message: Message, user_role: str = None):
        if user_role is None:
            return
        is_owner = message.from_user.id == config.owner_id
        await handle_settings(message, message.from_user.id, is_owner)

    @dp.message(F.text == Buttons.RATING)
    async def msg_rating(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_rating_menu(message, message.from_user.id)

    @dp.message(F.text == Buttons.BLACKLIST)
    async def msg_blacklist(message: Message, user_role: str = None):
        if user_role is None:
            return
        await handle_blacklist(message, message.from_user.id)

    # --- Admin panel ---
    @dp.message(F.text == Buttons.ADMIN_PANEL)
    async def msg_admin_panel(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_admin_panel(message, message.from_user.id)

    @dp.message(F.text == Buttons.USERS_MANAGE)
    async def msg_users_manage(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_users_manage(message, message.from_user.id)

    @dp.message(F.text == Buttons.USERS_LIST)
    async def msg_users_list(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        _users_page[message.from_user.id] = 0
        await handle_users_list(message, message.from_user.id, page=0)

    @dp.message(F.text == Buttons.FIND_BY_ID)
    async def msg_find_by_id(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_find_user_prompt(message, message.from_user.id)

    @dp.message(F.text == Buttons.REQUESTS)
    async def msg_requests(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_requests_menu(message, message.from_user.id)

    @dp.message(F.text.startswith("⏳ Ожидают"))
    async def msg_requests_pending(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_requests_pending(message, message.from_user.id)

    @dp.message(F.text == Buttons.BROADCAST)
    async def msg_broadcast(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_broadcast_prompt(message, message.from_user.id)

    @dp.message(F.text == Buttons.STATS)
    async def msg_stats(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_stats(message, message.from_user.id)

    @dp.message(F.text == "🔄 Обновить")
    async def msg_stats_refresh(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_stats(message, message.from_user.id)

    @dp.message(F.text == Buttons.SYSTEM)
    async def msg_system(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_system(message, message.from_user.id)

    @dp.message(F.text == Buttons.GLOBAL_BLACKLIST)
    async def msg_global_blacklist(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_global_blacklist(message, message.from_user.id)

    @dp.message(F.text == Buttons.CLEAR_CACHE)
    async def msg_clear_cache(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        await handle_clear_cache_prompt(message, message.from_user.id)

    # --- Back buttons ---
    @dp.message(F.text == Buttons.BACK)
    async def msg_back(message: Message, user_role: str = None):
        if user_role is None:
            return
        uid = message.from_user.id
        clear_fsm(uid)
        is_owner = uid == config.owner_id
        state = _get_menu_state(uid)
        parent = {
            "my_searches": "main",
            "saved_and_subs": "main",
            "saved_posts": "saved_and_subs",
            "subscriptions": "saved_and_subs",
            "settings": "main",
            "rating": "settings",
            "blacklist": "settings",
            "find_user": "users_manage",
            "broadcast": "admin",
            "admin": "main",
            "users_manage": "admin",
            "users_list": "users_manage",
            "requests_menu": "admin",
            "requests_pending": "admin",
            "stats": "admin",
            "system": "admin",
            "global_blacklist": "system",
            "clear_cache": "system",
            "broadcast_preview": "admin",
        }.get(state, "main")

        if parent == "saved_and_subs":
            await handle_saved_and_subs(message, uid)
        elif parent == "settings":
            await handle_settings(message, uid, is_owner)
        elif parent == "admin":
            await handle_admin_panel(message, uid)
        elif parent == "users_manage":
            await handle_users_manage(message, uid)
        elif parent == "system":
            await handle_system(message, uid)
        elif parent == "requests_menu":
            await handle_requests_menu(message, uid)
        else:
            await show_main_menu(message, uid, is_owner)

    @dp.message(F.text == Buttons.BACK_TO_ADMIN)
    async def msg_back_to_admin(message: Message, user_role: str = None):
        if user_role is None or message.from_user.id != config.owner_id:
            return
        clear_fsm(message.from_user.id)
        await handle_admin_panel(message, message.from_user.id)

    @dp.message(F.text == Buttons.BROADCAST_CANCEL)
    async def msg_broadcast_cancel(message: Message, user_role: str = None):
        if user_role is None:
            return
        clear_fsm(message.from_user.id)
        if message.from_user.id == config.owner_id:
            await handle_admin_panel(message, message.from_user.id)
        else:
            await show_main_menu(message, message.from_user.id, False)

    # =========================================================================
    # GENERIC TEXT HANDLER (FSM input capture)
    # =========================================================================
    @dp.message(F.text)
    async def text_handler(message: Message, user_role: str = None):
        if user_role is None:
            return
        uid = message.from_user.id
        state = _fsm.get(uid)

        if state == FSM_ADD_SEARCH:
            clear_fsm(uid)
            await handle_add_search_input(message, uid)
        elif state == FSM_ADD_BL_TAG:
            clear_fsm(uid)
            await handle_add_blacklist_tag(message, uid)
        elif state == FSM_ADD_GBL_TAG:
            clear_fsm(uid)
            await handle_add_gbl_tag_input(message, uid)
        elif state == FSM_FIND_USER:
            clear_fsm(uid)
            await handle_find_user_input(message, uid)
        elif state == FSM_BROADCAST:
            await handle_broadcast_input(message, uid)
        # else: ignore unrecognized text


def _get_menu_state(user_id: int) -> str:
    from handlers.messages import _user_menu_state
    return _user_menu_state.get(user_id, "main")


async def on_startup(bot: Bot) -> None:
    """Startup tasks."""
    logger.info("Bot starting up...")
    db.init_db()
    tags_db.init_tags_db()
    init_cache()
    await start_cleanup_task()
    await db.add_user(config.owner_id, "owner", "owner")

    # Kick off background population of the tags DB if it's nearly empty.
    # This fetches the most popular tags from Gelbooru so that autocomplete
    # and tag categorization work well from the start.
    existing_tags = tags_db.get_tags_count()
    logger.info("Tags DB has %d tags", existing_tags)
    if existing_tags < 5000:
        asyncio.create_task(_populate_tags_background(target=50000))

    logger.info(f"Bot started. Owner ID: {config.owner_id}")


async def _populate_tags_background(target: int = 50000) -> None:
    """Background task: fetch the most popular tags from Gelbooru and store them.

    Runs in chunks of 100 tags per API call (Gelbooru limit), respecting the
    8 req/s rate limiter. Stops early if the API returns fewer tags than
    requested (reached the end) or if interrupted.
    """
    logger.info("Starting background tag population (target=%d)...", target)
    pages = (target + 99) // 100
    total_fetched = 0
    try:
        for pid in range(pages):
            tags, _ = await gelbooru_client.fetch_tags_page(pid=pid, limit=100, orderby="count")
            if not tags:
                logger.info("Tag population: no more tags at page %d", pid)
                break
            tags_db.upsert_tags(tags)
            total_fetched += len(tags)
            if (pid + 1) % 10 == 0:
                logger.info("Tag population: %d tags stored (%d pages)", total_fetched, pid + 1)
            if len(tags) < 100:
                break
    except Exception as e:
        logger.error("Tag population failed at %d tags: %s", total_fetched, e)
        return
    logger.info("Tag population complete: %d tags stored locally", total_fetched)


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
