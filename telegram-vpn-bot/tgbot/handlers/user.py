from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from loader import bot
from tgbot.keyboards.inline import keyboard_about 

user_router = Router()



# приветствие /start
# @user_router.message(Command("start"))
# async def user_start(message: Message):
#     await message.answer(
#         "<b>👋 Добро пожаловать в Work VPN!</b>\n\n"
#         "🔒 <b>Мы даём вам:</b>\n"
#         "• Полный доступ к сайтам без блокировок\n"
#         "• Защиту личных данных и анонимность\n"
#         "• Высокую скорость без ограничений\n\n"
#         "🎁 Попробуйте VPN бесплатно на <b>3 дня</b> и убедитесь сами!\n\n"
#         "👇 Выберите действие:",
#         reply_markup=keyboard_start(),
#         disable_web_page_preview=True
#     )
# тарифы /pay
# @user_router.message(Command('pay'))
# async def help_handler(message: Message):
#     await message.answer(f'тарифы'
#                          f'',
#                          reply_markup=keyboard_pay(), disable_web_page_preview=True)


# @user_router.callback_query(F.data == 'pay')
# async def help_callback_handler(callback_query: CallbackQuery):
#     await callback_query.answer()
#     await bot.send_message(callback_query.from_user.id,
#                            f'тарифы'
#                            f'',
#                            reply_markup=keyboard_pay(), disable_web_page_preview=True)


# помощ /help
# @user_router.message(Command('help'))
# async def help_handler(message: Message):
#     await message.answer(f'help'
#                          f'',
#                          reply_markup=keyboard_help(), disable_web_page_preview=True)


# @user_router.callback_query(F.data == 'help')
# async def help_callback_handler(callback_query: CallbackQuery):
#     await callback_query.answer()
#     await bot.send_message(callback_query.from_user.id,
#                            f'help'
#                            f'',
#                            reply_markup=keyboard_help(), disable_web_page_preview=True)



@user_router.message(Command("about"))
async def about_handler(message: Message):
    await message.answer(
        "<b>🌐 Work VPN — твоя свобода в интернете!</b>\n\n"
        "🚀 <b>Быстро</b> — подключение за 10 секунд.\n"
        "🔒 <b>Безопасно</b> — шифрование военного уровня.\n"
        "🌍 <b>Доступно</b> — работаем в любой точке мира.\n\n"
        "Мы создаём VPN для тех, кто ценит <b>скорость, приватность и стабильность</b>.\n"
        "Наши сервера работают 24/7, обеспечивая доступ без лагов и блокировок.\n\n"
        "💬 Остались вопросы?\n"
        "Свяжись с нашей поддержкой — мы всегда на связи 👇",
        reply_markup=keyboard_about(), disable_web_page_preview=True)


@user_router.callback_query(F.data == 'about')
async def help_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id,
        "<b>🌐 Work VPN — твоя свобода в интернете!</b>\n\n"
        "🚀 <b>Быстро</b> — подключение за 10 секунд.\n"
        "🔒 <b>Безопасно</b> — шифрование военного уровня.\n"
        "🌍 <b>Доступно</b> — работаем в любой точке мира.\n\n"
        "Мы создаём VPN для тех, кто ценит <b>скорость, приватность и стабильность</b>.\n"
        "Наши сервера работают 24/7, обеспечивая доступ без лагов и блокировок.\n\n"
        "💬 Остались вопросы?\n"
        "Свяжись с нашей поддержкой — мы всегда на связи 👇",
        reply_markup=keyboard_about(), disable_web_page_preview=True)


#  пробный приод /try
# @user_router.message(Command('try'))
# async def help_handler(message: Message):
#     await message.answer(f'try'
#                          f'',
#                          reply_markup=keyboard_try(), disable_web_page_preview=True)


# @user_router.callback_query(F.data == 'try')
# async def help_callback_handler(callback_query: CallbackQuery):
#     await callback_query.answer()
#     await bot.send_message(callback_query.from_user.id,
#                            f'try'
#                            f'',
#                            reply_markup=keyboard_try(), disable_web_page_preview=True)



