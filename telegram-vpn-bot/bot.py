import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from loader import config
from tgbot.handlers import routers_list
from tgbot.handlers.tariffs import tariffs_router  # тарифы
from tgbot.handlers.payments import payments_router  # оплатa
from tgbot.handlers.referrals import router as referrals_router #
from tgbot.handlers.start import router as start_router

from tgbot.middlewares.flood import ThrottlingMiddleware
from utils import broadcaster
from db_manager import init_db

from tgbot.handlers.payments_yookassa import payments_yookassa_router




logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    await broadcaster.broadcast(bot, [config.tg_bot.admin_id], "Бот запущен")
    await register_commands(bot)
    if config.webhook.use_webhook:
        await bot.set_webhook(f"https://{config.webhook.domain}{config.webhook.url}webhook")


async def register_commands(bot: Bot):
    commands = [
        BotCommand(command='start', description='Главное меню 🏠'),
        BotCommand(command='help', description='Помощь'),
        BotCommand(command='/ref', description='получить впн бесплатно'),
        BotCommand(command='tariffs', description='Тарифы 💰'),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


def register_global_middlewares(dp: Dispatcher):
    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(CallbackAnswerMiddleware())
    dp.message.filter(F.chat.type == ChatType.PRIVATE)


def main_webhook():
    from loader import bot, dp

    dp.include_routers(*routers_list)
    dp.include_router(tariffs_router)   # тарифы
    dp.include_router(payments_router)  # оплатa
    dp.include_router(referrals_router) # рефервлы
    dp.include_router(start_router)
    dp.startup.register(on_startup)
    register_global_middlewares(dp)

    asyncio.run(init_db())
    logger.info("База данных инициализирована (webhook) ✅")

    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=f'{config.webhook.url}webhook')

    setup_application(app, dp, bot=bot)
    web.run_app(app, host='vpn_bot', port=config.tg_bot.port)


async def main_polling():
    from loader import bot, dp

    await init_db()
    logger.info("База данных инициализирована (polling) ✅")

    dp.include_router(payments_yookassa_router)
    dp.include_routers(*routers_list)
    dp.include_router(tariffs_router)
    dp.include_router(payments_router)  # оплата
    dp.include_router(referrals_router) # рефервлы
    dp.include_router(start_router)

    register_global_middlewares(dp)

    await on_startup(bot)
    await bot.delete_webhook()
    await dp.start_polling(bot)


if __name__ == '__main__':
    if config.webhook.use_webhook:
        main_webhook()
    else:
        try:
            asyncio.run(main_polling())
        except (KeyboardInterrupt, SystemExit):
            logging.error("Бот выключен!")
