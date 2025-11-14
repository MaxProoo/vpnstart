# tgbot/handlers/start.py

import logging
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from tgbot.handlers import referrals  # <-- добавь этот импорт
from tgbot.keyboards.inline import keyboard_start

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandStart):
    """
    Обработка команды /start (в том числе с реферальной ссылкой).
    """
    user_id = message.from_user.id
    payload = command.args  # <-- аргументы /start ref_123456

    logger.info(f"➡️ /start от {user_id}, payload={payload}")

    # --- Проверяем, есть ли реферальный payload ---
    if payload and payload.startswith("ref_"):
        ref_code = payload.split("_", 1)[1]
        try:
            referrer_id = int(ref_code)
        except ValueError:
            await message.answer("❌ Неверная реферальная ссылка.")
            return

        if referrer_id == user_id:
            await message.answer("🚫 Нельзя использовать свою же ссылку.")
            return

        # --- вызываем твою функцию из referrals.py ---
        await referrals.handle_ref_start(message)
        return

    # --- обычный старт ---
    await message.answer(
        "<b>👋 Добро пожаловать в Work VPN!</b>\n\n"
        "🔒 <b>Мы даём вам:</b>\n"
        "• Полный доступ к сайтам без блокировок\n"
        "• Защиту личных данных и анонимность\n"
        "• Высокую скорость без ограничений\n\n"
        "🎁 Попробуйте VPN бесплатно на <b>3 дня</b> и убедитесь сами!\n\n"
        "👇 Выберите действие:",
        reply_markup=keyboard_start(),
        disable_web_page_preview=True
    )
