import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import settings
from bot.database import crud
from bot.providers.deepseek import DeepSeekProvider
from bot.utils.formatting import format_llm_response, split_message, unescape_markdown_v2

logger = logging.getLogger(__name__)

router = Router(name="user")


# ── Cabinet ──────────────────────────────────────────────────────────────────


async def _cabinet_keyboard(
    telegram_id: int,
) -> tuple[str, InlineKeyboardMarkup]:
    db_user = await crud.get_user(telegram_id)
    models = await crud.get_models(enabled_only=True)

    selected_name = "Not selected"
    selected_id = db_user.selected_model_id if db_user else None
    if selected_id:
        selected_model = await crud.get_model(selected_id)
        if selected_model:
            selected_name = selected_model.name

    buttons: list[list[InlineKeyboardButton]] = []
    for model in models:
        prefix = "> " if model.id == selected_id else "  "
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}{model.name}",
                    callback_data=f"u:m:{model.id}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="Clear History", callback_data="u:clear")]
    )

    text = f"Cabinet\n\nCurrent model: {selected_name}"
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("cabinet"))
async def cmd_cabinet(message: Message) -> None:
    text, kb = await _cabinet_keyboard(message.from_user.id)  # type: ignore[union-attr]
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("u:m:"))
async def cb_select_model(callback: CallbackQuery) -> None:
    model_id = int(callback.data.split(":")[2])  # type: ignore[union-attr]
    model = await crud.get_model(model_id)
    if not model or not model.is_enabled:
        await callback.answer("Model not available", show_alert=True)
        return

    await crud.update_user_model(callback.from_user.id, model_id)
    await callback.answer(f"Model set to {model.name}")

    text, kb = await _cabinet_keyboard(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]


@router.callback_query(F.data == "u:clear")
async def cb_clear_history(callback: CallbackQuery) -> None:
    db_user = await crud.get_user(callback.from_user.id)
    if db_user:
        count = await crud.clear_chat_history(db_user.id)
        await callback.answer(f"Cleared {count} messages")
    else:
        await callback.answer("No history to clear")


# ── New conversation ─────────────────────────────────────────────────────────


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    db_user = await crud.get_user(message.from_user.id)  # type: ignore[union-attr]
    if db_user:
        count = await crud.clear_chat_history(db_user.id)
        await message.answer(f"New conversation started. Cleared {count} messages.")
    else:
        await message.answer("New conversation started.")


# ── Chat with LLM ───────────────────────────────────────────────────────────


@router.message(F.text)
async def handle_chat(message: Message, provider: DeepSeekProvider) -> None:
    user = message.from_user
    if user is None:
        return

    db_user = await crud.get_or_create_user(user.id, user.username)

    if not db_user.selected_model_id:
        models = await crud.get_models(enabled_only=True)
        if not models:
            await message.answer("No models available. Contact admin.")
            return
        await crud.update_user_model(user.id, models[0].id)
        db_user = await crud.get_user(user.id)
        if db_user is None:
            return

    model = await crud.get_model(db_user.selected_model_id)  # type: ignore[arg-type]
    if not model or not model.is_enabled:
        await message.answer(
            "Selected model is disabled. Use /cabinet to pick another."
        )
        return

    history = await crud.get_chat_history(db_user.id, settings.chat_history_window)
    messages = [{"role": h.role, "content": h.content} for h in history]
    messages.append({"role": "user", "content": message.text})

    await message.bot.send_chat_action(message.chat.id, "typing")  # type: ignore[union-attr]

    try:
        response = await provider.chat_completion(messages, model.name)
    except Exception:
        logger.exception("LLM API error")
        await message.answer(
            "An error occurred while processing your request. Please try again."
        )
        return

    await crud.add_chat_message(db_user.id, "user", message.text)
    await crud.add_chat_message(db_user.id, "assistant", response.content)

    cost = DeepSeekProvider.calculate_cost(
        model.name, response.prompt_tokens, response.completion_tokens
    )
    await crud.log_usage(
        db_user.id, model.id, response.prompt_tokens, response.completion_tokens, cost
    )

    formatted = format_llm_response(response.content)
    for part in split_message(formatted):
        try:
            await message.answer(part, parse_mode="MarkdownV2")
        except Exception:
            await message.answer(unescape_markdown_v2(part))
