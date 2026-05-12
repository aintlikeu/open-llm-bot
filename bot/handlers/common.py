from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.database import crud
from bot.utils.formatting import escape_html

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, is_admin: bool) -> None:
    user = message.from_user
    if user is None:
        return

    db_user = await crud.get_or_create_user(user.id, user.username)

    if is_admin and not db_user.is_allowed:
        await crud.set_user_allowed(user.id, True, user.username)

    name = escape_html(user.first_name)

    if is_admin or db_user.is_allowed:
        role = "Admin" if is_admin else "User"
        text = (
            f"Welcome, <b>{name}</b>!\n\n"
            f"Role: <b>{role}</b>\n\n"
            "Commands:\n"
            "/cabinet — Model selection &amp; settings\n"
            "/new — Start a new conversation\n"
            "/help — Show help"
        )
        if is_admin:
            text += "\n/admin — Admin panel"
        await message.answer(text, parse_mode="HTML")
    else:
        await message.answer(
            f"Welcome, {escape_html(user.first_name)}!\n\n"
            f"Your ID: <code>{user.id}</code>\n"
            "Share this ID with the administrator to get access.",
            parse_mode="HTML",
        )


@router.message(Command("help"))
async def cmd_help(message: Message, is_admin: bool) -> None:
    text = (
        "<b>Available commands:</b>\n\n"
        "/cabinet — Select model &amp; view settings\n"
        "/new — Clear history &amp; start fresh\n"
        "/help — This message"
    )
    if is_admin:
        text += "\n/admin — Admin panel"
    text += "\n\nSend any message to chat with the AI."
    await message.answer(text, parse_mode="HTML")
