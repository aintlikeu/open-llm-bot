from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.database import crud
from bot.utils.formatting import escape_markdown_v2

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, is_admin: bool) -> None:
    user = message.from_user
    if user is None:
        return

    db_user = await crud.get_or_create_user(user.id, user.username)

    if is_admin and not db_user.is_allowed:
        await crud.set_user_allowed(user.id, True, user.username)

    name = escape_markdown_v2(user.first_name)

    if is_admin or db_user.is_allowed:
        role = "Admin" if is_admin else "User"
        text = (
            f"Welcome, *{name}*\\!\n\n"
            f"Role: *{role}*\n\n"
            "Commands:\n"
            "/cabinet — Model selection & settings\n"
            "/new — Start a new conversation\n"
            "/help — Show help"
        )
        if is_admin:
            text += "\n/admin — Admin panel"
        await message.answer(text, parse_mode="MarkdownV2")
    else:
        await message.answer(
            f"Welcome, {user.first_name}!\n\n"
            f"Your ID: {user.id}\n"
            "Share this ID with the administrator to get access."
        )


@router.message(Command("help"))
async def cmd_help(message: Message, is_admin: bool) -> None:
    text = (
        "*Available commands:*\n\n"
        "/cabinet — Select model & view settings\n"
        "/new — Clear history & start fresh\n"
        "/help — This message"
    )
    if is_admin:
        text += "\n/admin — Admin panel"
    text += "\n\nSend any message to chat with the AI\\."
    await message.answer(text, parse_mode="MarkdownV2")
