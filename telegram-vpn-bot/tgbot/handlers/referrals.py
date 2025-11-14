import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from loader import bot, config
import db_manager
from marzban.client import create_user, get_user_links
import aiosqlite

router = Router()
logger = logging.getLogger(__name__)

from db_manager import DB_PATH


# === 1️⃣ /ref — получить свою реферальную ссылку ===
@router.message(F.text.in_({"/ref", "Реферальная ссылка"}))
async def get_ref_link(message: Message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await bot.me()).username}?start=ref_{user_id}"
    await message.answer(
        f"👥 Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        f"🔹 За каждого друга, оплатившего VPN — вы получаете 1 балл.\n"
        f"🔹 За 3 оплаты вы получаете <b>1 месяц бесплатного VPN!</b>"
    )


@router.callback_query(F.data == "/ref_call")
async def get_ref_link_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    ref_link = f"https://t.me/{(await bot.me()).username}?start=ref_{user_id}"

    await callback.message.answer(
        f"👥 Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        f"🔹 За каждого друга, оплатившего VPN — вы получаете 1 балл.\n"
        f"🔹 За 3 оплаты вы получаете <b>1 месяц бесплатного VPN!</b>"
    )
    await callback.answer()




# === 2️⃣ Пользователь пришёл по реферальной ссылке ===
@router.message(F.text.startswith("/start ref_"))
async def handle_ref_start(message: Message):
    referrer_id = int(message.text.split("_")[1])
    referred_id = message.from_user.id

    if referrer_id == referred_id:
        await message.answer("😅 Нельзя пригласить самого себя.")
        return

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, не был ли этот пользователь уже зарегистрирован как приглашённый
            check = await db.execute("SELECT id FROM referrals WHERE referred_id = ?", (referred_id,))
            exists = await check.fetchone()
            if exists:
                await message.answer("⚠️ Вы уже были зарегистрированы в реферальной системе.")
                return

            await db.execute(
                "INSERT INTO referrals (referrer_id, referred_id, paid) VALUES (?, ?, 0)",
                (referrer_id, referred_id)
            )
            await db.commit()

        await message.answer("🎉 Вы зарегистрированы по реферальной ссылке!\nТеперь оформите VPN, чтобы помочь другу получить бонус 💪")

        # Уведомляем пригласившего
        await bot.send_message(
            chat_id=referrer_id,
            text=f"👤 Новый пользователь <code>{referred_id}</code> зарегистрировался по вашей ссылке!"
        )

    except Exception as e:
        logger.error(f"Ошибка регистрации реферала: {e}")
        await message.answer("⚠️ Ошибка при регистрации. Попробуйте позже.")


# === 3️⃣ Помечаем реферала как оплатившего ===
async def mark_referral_paid(user_id: int):
    """
    Вызывается после успешной оплаты (например, из payments.py)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Найдём кто пригласил этого пользователя
        result = await db.execute("SELECT referrer_id FROM referrals WHERE referred_id = ? AND paid = 0", (user_id,))
        ref = await result.fetchone()

        if not ref:
            return  # пользователь не реферал или уже помечен как оплативший

        referrer_id = ref[0]

        # Помечаем как оплатившего
        await db.execute("UPDATE referrals SET paid = 1 WHERE referred_id = ?", (user_id,))
        await db.commit()

        # Считаем количество успешных оплат по рефералу
        count_res = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND paid = 1", (referrer_id,))
        count = (await count_res.fetchone())[0]

        # Если 3 оплаты — дарим месяц VPN
        if count >= 3:
            logger.info(f"🎁 Реферальный бонус: {referrer_id} получает бесплатный месяц VPN")

            sub_id = str(uuid.uuid4())
            expiry_date = datetime.now() + timedelta(days=30)

            await create_user(sub_id, expiry_date)
            links = await get_user_links(sub_id)
            await db_manager.record_trial_usage(referrer_id, sub_id, expiry_date)

            await bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎁 Поздравляем! Трое ваших друзей оплатили VPN!\n\n"
                    f"Вы получили <b>1 месяц бесплатного VPN</b> 🔥\n\n"
                    f"🔑 Ваши VPN ключи:\n{links}"
                )
            )
