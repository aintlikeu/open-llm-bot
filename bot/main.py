import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database import crud
from bot.handlers import admin, common, user
from bot.middlewares.access import AccessMiddleware
from bot.providers.deepseek import DeepSeekProvider
from bot.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()

    await crud.init_db()
    await crud.ensure_default_models()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=MemoryStorage())

    provider = DeepSeekProvider(settings.deepseek_api_key)
    dp["provider"] = provider

    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    dp.include_routers(common.router, admin.router, user.router)

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
