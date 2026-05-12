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


def _build_dispatcher(provider: DeepSeekProvider) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp["provider"] = provider

    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    dp.include_routers(common.router, admin.router, user.router)
    return dp


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Bot starting in polling mode...")
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher) -> None:
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    webhook_url = f"{settings.webhook_url.rstrip('/')}{settings.webhook_path}"
    logger.info("Setting webhook: %s", webhook_url)
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret or None,
        drop_pending_updates=True,
    )

    app = web.Application()
    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret or None,
    )
    handler.register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webhook_host, settings.webhook_port)
    logger.info(
        "Webhook server listening on %s:%d",
        settings.webhook_host,
        settings.webhook_port,
    )
    await site.start()
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    setup_logging()

    await crud.init_db()
    await crud.ensure_default_models()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )

    provider = DeepSeekProvider(settings.deepseek_api_key)
    dp = _build_dispatcher(provider)

    try:
        if settings.bot_mode == "webhook":
            await _run_webhook(bot, dp)
        else:
            await _run_polling(bot, dp)
    finally:
        if settings.bot_mode == "webhook":
            await bot.delete_webhook()
        await provider.close()


if __name__ == "__main__":
    asyncio.run(main())
