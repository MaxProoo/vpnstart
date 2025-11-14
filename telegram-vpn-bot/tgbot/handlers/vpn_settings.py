import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from aiogram import Router, F
from aiogram.types import CallbackQuery
import uuid
from datetime import datetime, timedelta
import logging

from loader import bot
from marzban.client import create_user, get_user_links
import db_manager  # твой модуль для работы с базой

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

vpn_router = Router()


@vpn_router.message(Command("trial"))
async def trial_handler(message: Message):
    user_id = message.from_user.id
    logging.info(f"Обработка команды /vpn от пользователя {user_id}")

    # Проверка, использовал ли пользователь пробный период
    try:
        used_trial = await db_manager.has_user_used_trial(user_id)
    except Exception as e:
        logging.exception("Ошибка при проверке статуса пробника в БД:")
        await message.answer("Произошла ошибка при проверке вашего статуса. Попробуйте позже.")
        return

    if used_trial:
        await message.answer("Вы уже использовали свой пробный период.")
        return

    sub_id = str(uuid.uuid4())
    expiry_date = datetime.now() + timedelta(days=3)

    try:
        # Создание пользователя на Marzban
        result = await create_user(sub_id, expiry_date)
        if not result:
            raise RuntimeError("Marzban вернул пустой результат")

        # Получение ссылок
        keys = await get_user_links(sub_id)

        # Запись в БД
        await db_manager.record_trial_usage(user_id, sub_id, expiry_date)

        # Отправка пользователю
        await message.answer(
            f"✅ Ваш пробный VPN доступ активирован на 3 дня!\n\n"
            f"Ваши ключи для подключения:\n\n{keys}"
        )

        logging.info(f"Пользователь {user_id} получил пробный доступ {sub_id}")

    except Exception as e:
        logging.exception("Ошибка при создании пользователя в Marzban:")
        await message.answer("Произошла ошибка при выдаче доступа. Попробуйте позже.")


@vpn_router.callback_query(F.data == "trial")
async def trial_callback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    logging.info(f"Обработка КОЛБЕКА /trial от пользователя {user_id}")

    try:
        used_trial = await db_manager.has_user_used_trial(user_id)
    except Exception as e:
        logging.exception("Ошибка при проверке статуса пробника в БД:")
        await callback.answer("Ошибка при проверке статуса. Попробуйте позже.", show_alert=True)
        return

    if used_trial:
        await callback.answer("Вы уже использовали свой пробный период.", show_alert=True)
        return

    sub_id = str(uuid.uuid4())
    expiry_date = datetime.now() + timedelta(days=3)

    try:
        result = await create_user(sub_id, expiry_date)
        if not result:
            raise RuntimeError("Marzban вернул пустой результат")

        keys = await get_user_links(sub_id)
        await db_manager.record_trial_usage(user_id, sub_id, expiry_date)

        await callback.message.answer(
            f"✅ Ваш пробный VPN доступ активирован на 3 дня!\n\n"
            f"Ваши ключи для подключения:\n\n{keys}"
        )

        logging.info(f"Пользователь {user_id} получил пробный доступ {sub_id}")
        await callback.answer("Пробный доступ активирован!", show_alert=True)

    except Exception as e:
        logging.exception("Ошибка при создании пользователя в Marzban:")
        await callback.answer("Ошибка при выдаче доступа. Попробуйте позже.", show_alert=True)

