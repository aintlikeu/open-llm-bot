from sqlalchemy import delete, func, select

from bot.database.models import Base, ChatHistory, LLMModel, UsageLog, User
from bot.database.session import async_session, engine

# Sentinel user_id used for group/channel shared history
_GROUP_USER_ID = 0


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_default_models() -> None:
    async with async_session() as session:
        result = await session.execute(select(func.count(LLMModel.id)))
        if result.scalar() == 0:
            session.add_all(
                [
                    LLMModel(name="deepseek-chat", provider="deepseek"),
                    LLMModel(name="deepseek-reasoner", provider="deepseek"),
                ]
            )
            await session.commit()


async def get_or_create_user(
    telegram_id: int, username: str | None = None
) -> User:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        elif username and user.username != username:
            user.username = username
            await session.commit()
        return user


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def get_allowed_users() -> list[User]:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_allowed == True).order_by(User.id)  # noqa: E712
        )
        return list(result.scalars().all())


async def set_user_allowed(
    telegram_id: int, allowed: bool, username: str | None = None
) -> User:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id, username=username, is_allowed=allowed
            )
            session.add(user)
        else:
            user.is_allowed = allowed
        await session.commit()
        await session.refresh(user)
        return user


async def update_user_model(telegram_id: int, model_id: int) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.selected_model_id = model_id
            await session.commit()


async def get_models(*, enabled_only: bool = False) -> list[LLMModel]:
    async with async_session() as session:
        stmt = select(LLMModel).order_by(LLMModel.id)
        if enabled_only:
            stmt = stmt.where(LLMModel.is_enabled == True)  # noqa: E712
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_model(model_id: int) -> LLMModel | None:
    async with async_session() as session:
        result = await session.execute(
            select(LLMModel).where(LLMModel.id == model_id)
        )
        return result.scalar_one_or_none()


async def toggle_model(model_id: int) -> LLMModel | None:
    async with async_session() as session:
        result = await session.execute(
            select(LLMModel).where(LLMModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.is_enabled = not model.is_enabled
            await session.commit()
            await session.refresh(model)
        return model


def _history_user_id(is_group: bool, db_user_id: int) -> int:
    """In groups history is shared (user_id=0). In private chats it's per-user."""
    return _GROUP_USER_ID if is_group else db_user_id


async def add_chat_message(
    db_user_id: int, chat_id: int, role: str, content: str, *, is_group: bool = False
) -> None:
    uid = _history_user_id(is_group, db_user_id)
    async with async_session() as session:
        session.add(ChatHistory(user_id=uid, chat_id=chat_id, role=role, content=content))
        await session.commit()


async def get_chat_history(
    db_user_id: int, chat_id: int, limit: int = 20, *, is_group: bool = False
) -> list[ChatHistory]:
    uid = _history_user_id(is_group, db_user_id)
    async with async_session() as session:
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == uid, ChatHistory.chat_id == chat_id)
            .order_by(ChatHistory.id.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages


async def clear_chat_history(
    db_user_id: int, chat_id: int | None = None, *, is_group: bool = False
) -> int:
    """Clear history.

    In group context clears shared history for the chat.
    In private context clears history for the user (optionally scoped to chat_id).
    If chat_id is None and not a group, clears all history for the user.
    """
    uid = _history_user_id(is_group, db_user_id)
    async with async_session() as session:
        stmt = delete(ChatHistory).where(ChatHistory.user_id == uid)
        if chat_id is not None:
            stmt = stmt.where(ChatHistory.chat_id == chat_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]


async def log_usage(
    user_id: int,
    model_id: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float,
) -> None:
    async with async_session() as session:
        session.add(
            UsageLog(
                user_id=user_id,
                model_id=model_id,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
            )
        )
        await session.commit()


async def get_usage_stats() -> dict:
    async with async_session() as session:
        total = await session.execute(
            select(
                func.count(UsageLog.id),
                func.coalesce(func.sum(UsageLog.prompt_tokens), 0),
                func.coalesce(func.sum(UsageLog.completion_tokens), 0),
                func.coalesce(func.sum(UsageLog.cost), 0),
            )
        )
        total_row = total.one()

        per_model = await session.execute(
            select(
                LLMModel.name,
                func.count(UsageLog.id),
                func.coalesce(func.sum(UsageLog.prompt_tokens), 0),
                func.coalesce(func.sum(UsageLog.completion_tokens), 0),
                func.coalesce(func.sum(UsageLog.cost), 0),
            )
            .join(LLMModel, UsageLog.model_id == LLMModel.id)
            .group_by(LLMModel.name)
        )

        users_count = await session.execute(
            select(func.count(User.id)).where(User.is_allowed == True)  # noqa: E712
        )

        return {
            "total_requests": total_row[0],
            "total_prompt_tokens": total_row[1],
            "total_completion_tokens": total_row[2],
            "total_cost": total_row[3],
            "users_count": users_count.scalar(),
            "per_model": [
                {
                    "name": row[0],
                    "requests": row[1],
                    "prompt_tokens": row[2],
                    "completion_tokens": row[3],
                    "cost": row[4],
                }
                for row in per_model.all()
            ],
        }
