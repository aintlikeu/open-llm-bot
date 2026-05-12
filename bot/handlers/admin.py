from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import ADMIN_IDS
from bot.database import crud

router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_user_id = State()


def _admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Users", callback_data="a:users")],
            [InlineKeyboardButton(text="Models", callback_data="a:models")],
            [InlineKeyboardButton(text="Statistics", callback_data="a:stats")],
        ]
    )


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ── Menu ─────────────────────────────────────────────────────────────────────


@router.message(Command("admin"))
async def cmd_admin(message: Message, is_admin: bool) -> None:
    if not is_admin:
        return
    await message.answer("Admin Panel", reply_markup=_admin_menu_kb())


@router.callback_query(F.data == "a:back")
async def cb_back(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("Admin Panel", reply_markup=_admin_menu_kb())  # type: ignore[union-attr]
    await callback.answer()


# ── Users ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "a:users")
async def cb_users(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    users = await crud.get_allowed_users()

    buttons: list[list[InlineKeyboardButton]] = []
    for user in users:
        name = user.username or str(user.telegram_id)
        is_admin = user.telegram_id in ADMIN_IDS
        prefix = "★" if is_admin else "X"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}  {name} ({user.telegram_id})",
                    callback_data=f"a:ur:{user.telegram_id}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="+ Add User", callback_data="a:au")]
    )
    buttons.append(
        [InlineKeyboardButton(text="< Back", callback_data="a:back")]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "Allowed Users (tap to remove):", reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("a:ur:"))
async def cb_remove_user_confirm(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    telegram_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]

    if telegram_id in ADMIN_IDS:
        await callback.answer("Cannot remove an admin user", show_alert=True)
        return

    user = await crud.get_user(telegram_id)
    name = (user.username if user and user.username else str(telegram_id))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Yes, remove", callback_data=f"a:uc:{telegram_id}"),
                InlineKeyboardButton(text="Cancel", callback_data="a:users"),
            ]
        ]
    )
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"Remove user {name} ({telegram_id})?", reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data.startswith("a:uc:"))
async def cb_remove_user(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    telegram_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]

    if telegram_id in ADMIN_IDS:
        await callback.answer("Cannot remove an admin user", show_alert=True)
        return

    await crud.set_user_allowed(telegram_id, False)
    await cb_users(callback)


@router.callback_query(F.data == "a:au")
async def cb_add_user_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.message.edit_text(  # type: ignore[union-attr]
        "Send the Telegram user ID to add, or forward a message from the user."
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_id)
async def process_add_user(message: Message, state: FSMContext) -> None:
    await state.clear()

    if message.forward_from:
        telegram_id = message.forward_from.id
        username = message.forward_from.username
    else:
        try:
            telegram_id = int(message.text.strip())  # type: ignore[union-attr]
            username = None
        except (ValueError, AttributeError):
            await message.answer(
                "Invalid user ID. Please send a number.",
                reply_markup=_admin_menu_kb(),
            )
            return

    await crud.set_user_allowed(telegram_id, True, username)
    await message.answer(
        f"User {telegram_id} has been added.",
        reply_markup=_admin_menu_kb(),
    )


# ── Models ───────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "a:models")
async def cb_models(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    models = await crud.get_models()

    buttons: list[list[InlineKeyboardButton]] = []
    for model in models:
        status = "ON " if model.is_enabled else "OFF"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"[{status}] {model.name}",
                    callback_data=f"a:mt:{model.id}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="< Back", callback_data="a:back")]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Models (tap to toggle):", reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data.startswith("a:mt:"))
async def cb_toggle_model(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    model_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    await crud.toggle_model(model_id)
    await cb_models(callback)


# ── Statistics ───────────────────────────────────────────────────────────────


@router.callback_query(F.data == "a:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        return
    stats = await crud.get_usage_stats()

    text = (
        "Usage Statistics\n\n"
        f"Allowed users: {stats['users_count']}\n"
        f"Total requests: {stats['total_requests']}\n"
        f"Prompt tokens: {stats['total_prompt_tokens']:,}\n"
        f"Completion tokens: {stats['total_completion_tokens']:,}\n"
        f"Total cost: ${stats['total_cost']:.4f}"
    )

    if stats["per_model"]:
        text += "\n\nPer model:\n"
        for m in stats["per_model"]:
            text += (
                f"\n{m['name']}\n"
                f"  Requests: {m['requests']}\n"
                f"  Tokens: {m['prompt_tokens']:,} in / {m['completion_tokens']:,} out\n"
                f"  Cost: ${m['cost']:.4f}\n"
            )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="< Back", callback_data="a:back")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer()
