from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import ADMIN_IDS
from bot.database import crud


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return None

        data["is_admin"] = user.id in ADMIN_IDS

        if data["is_admin"]:
            return await handler(event, data)

        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            return await handler(event, data)

        db_user = await crud.get_user(user.id)
        if db_user and db_user.is_allowed:
            return await handler(event, data)

        # In groups — silently ignore to avoid spamming the chat
        if isinstance(event, Message):
            if event.chat.type == "private":
                await event.answer(
                    "Access denied. Contact the administrator to get access."
                )
        elif isinstance(event, CallbackQuery):
            await event.answer("Access denied", show_alert=True)

        return None
