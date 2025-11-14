# tgbot/handlers/payments.py
import logging
import uuid
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, ContentType
)
from loader import bot, config
from marzban.client import create_user, get_user_links
import db_manager

payments_router = Router()
logger = logging.getLogger(__name__)

# 🔹 База тарифов (должна совпадать с tariffs.py)
TARIFFS = {
    "basic": {"name": "💼 Базовый", "days": 30, "price": 79},
    "premium": {"name": "🚀 Премиум", "days": 90, "price": 199},
    "vip": {"name": "👑 VIP", "days": 365, "price": 749},
}

# 🔹 Пользователи, ожидающие отправки скриншота
pending_screenshots = {}


# 🟢 Пользователь нажал “Купить тариф” (универсальный handler для pay_*)
@payments_router.callback_query(F.data.startswith("pay_"))
async def handle_buy_callback(callback: CallbackQuery):
    logger.info("CALLBACK (pay_*) raw: %s user=%s", callback.data, callback.from_user.id)

    # Надёжный разбор tariff_id — берём последний сегмент
    tariff_id = callback.data.split("_")[-1]
    logger.info("Parsed tariff_id=%s", tariff_id)

    tariff = TARIFFS.get(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден ❌", show_alert=True)
        logger.error("Tariff not found for id=%s", tariff_id)
        return

    # Выбор способа оплаты
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить через ЮKassa", callback_data=f"yookassa_{tariff_id}")],
        [InlineKeyboardButton(text="💸 Ручная оплата", callback_data=f"manual_{tariff_id}")]
    ])

    await callback.message.answer(
        f"Вы выбрали тариф <b>{tariff['name']}</b>\n\n"
        f"💰 Цена: <b>{tariff['price']}₽</b>\n"
        f"⏱ Срок: {tariff['days']} дней\n\n"
        f"Выберите способ оплаты 👇",
        reply_markup=keyboard
    )
    await callback.answer()


# 💳 Оплата через ЮKassa (Telegram Payments fallback)
@payments_router.callback_query(F.data.startswith("yookassa_"))
async def handle_yookassa_payment(callback: CallbackQuery):
    logger.info("CALLBACK (yookassa_) raw: %s user=%s", callback.data, callback.from_user.id)
    tariff_id = callback.data.split("_")[-1]
    tariff = TARIFFS.get(tariff_id)

    if not tariff:
        await callback.answer("Ошибка: тариф не найден.", show_alert=True)
        return

    try:
        prices = [LabeledPrice(label=tariff["name"], amount=int(tariff["price"] * 100))]

        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Оплата тарифа {tariff['name']}",
            description=f"Подписка на {tariff['days']} дней",
            payload=tariff_id,
            provider_token=getattr(config.tg_bot, "provider_token", None),
            currency="RUB",
            prices=prices,
            start_parameter=f"vpn_{tariff_id}_{uuid.uuid4().hex[:8]}",
        )

        await callback.answer()

    except Exception as e:
        logger.exception("Ошибка при создании счёта ЮKassa (Telegram invoice): %s", e)
        await callback.answer("Ошибка при создании счёта. Попробуйте позже.", show_alert=True)


# ✅ Telegram подтверждает платёж (pre_checkout_query)
@payments_router.pre_checkout_query(lambda q: True)
async def process_pre_checkout_query(pre_checkout_q):
    try:
        await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
    except Exception:
        await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=False, error_message="Ошибка при проверке платежа.")


# 💰 Успешная оплата через Telegram Payments (ЮKassa как провайдер)
@payments_router.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    tariff_id = message.successful_payment.invoice_payload
    tariff = TARIFFS.get(tariff_id)

    if not tariff:
        logger.error(f"Успешная оплата, но тариф {tariff_id} не найден")
        await message.answer("Ошибка: тариф не найден. Свяжитесь с поддержкой.")
        return

    logger.info(f"Пользователь {user_id} оплатил {tariff['name']} через ЮKassa")

    sub_id = str(uuid.uuid4())
    expiry_date = datetime.now() + timedelta(days=tariff["days"])

    try:
        await create_user(sub_id, expiry_date)
        links = await get_user_links(sub_id)
        await db_manager.record_trial_usage(user_id, sub_id, expiry_date)

    # ...
        await create_user(sub_id, expiry_date)
        links = await get_user_links(sub_id)
        await db_manager.record_trial_usage(user_id, sub_id, expiry_date)

        from tgbot.handlers.referrals import mark_referral_paid
        await mark_referral_paid(int(user_id))



        await message.answer(
            f"✅ Оплата подтверждена через ЮKassa!\n\n"
            f"Тариф: <b>{tariff['name']}</b>\n"
            f"Срок: {tariff['days']} дней\n\n"
            f"🔑 Ваши VPN ключи:\n\n{links}"
        )

        # Уведомление админу
        await bot.send_message(
            chat_id=config.tg_bot.admin_id,
            text=f"💳 Новый платёж через ЮKassa:\nПользователь: {user_id}\nТариф: {tariff['name']} ({tariff['price']}₽)"
        )

    except Exception as e:
        logger.exception("Ошибка при активации подписки:")
        await message.answer("Ошибка при активации. Свяжитесь с поддержкой.")


# 💸 Ручная оплата — показываем кнопку "Я оплатил", потом ожидаем фото
@payments_router.callback_query(F.data.startswith("manual_") | F.data.startswith("pay_manual_"))
async def handle_manual_payment(callback: CallbackQuery):
    logger.info("CALLBACK (manual) raw: %s user=%s", callback.data, callback.from_user.id)
    tariff_id = callback.data.split("_")[-1]
    tariff = TARIFFS.get(tariff_id)

    if not tariff:
        await callback.answer("Ошибка: тариф не найден.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Я оплатил", callback_data=f"paid_{tariff_id}")]
    ])

    await callback.message.answer(
        f"🧾 <b>Ручная оплата</b>\n\n"
        f"💰 Сумма: <b>{tariff['price']}₽</b>\n"
        f"⏱ Срок: {tariff['days']} дней\n\n"
        f"Переведите оплату администратору: @{config.tg_bot.admin_id}\n\n"
        f"После оплаты нажмите кнопку <b>«Я оплатил 💸»</b> и отправьте скриншот.",
        reply_markup=keyboard
    )
    await callback.answer()


# 💸 Пользователь нажал "Я оплатил" — просим фото
@payments_router.callback_query(F.data.startswith("paid_"))
async def handle_paid(callback: CallbackQuery):
    user_id = callback.from_user.id
    tariff_id = callback.data.split("_")[-1]
    tariff = TARIFFS.get(tariff_id)

    if not tariff:
        await callback.answer("Ошибка: тариф не найден.", show_alert=True)
        return

    pending_screenshots[user_id] = tariff_id
    await callback.message.answer("📸 Отправьте, пожалуйста, скриншот, подтверждающий оплату.")
    await callback.answer()


# 📷 Пользователь отправил фото
@payments_router.message(F.content_type == ContentType.PHOTO)
async def handle_payment_screenshot(message: Message):
    user_id = message.from_user.id

    if user_id not in pending_screenshots:
        return

    tariff_id = pending_screenshots.pop(user_id)
    tariff = TARIFFS.get(tariff_id)
    admin_id = config.tg_bot.admin_id
    photo_id = message.photo[-1].file_id

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_{user_id}_{tariff_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}_{tariff_id}")
        ]
    ])

    await bot.send_photo(
        chat_id=admin_id,
        photo=photo_id,
        caption=(
            f"📥 Новая ручная оплата:\n\n"
            f"👤 Пользователь: <code>{user_id}</code>\n"
            f"💳 Тариф: <b>{tariff['name']}</b>\n"
            f"💰 Сумма: {tariff['price']}₽"
        ),
        reply_markup=keyboard
    )

    await message.answer("✅ Скриншот отправлен администратору. Ожидайте подтверждения.")


# ✅ Подтверждение админом (ручная оплата)
@payments_router.callback_query(F.data.startswith("confirm_"))
async def handle_confirm(callback: CallbackQuery):
    _, user_id_str, tariff_id = callback.data.split("_")
    user_id = int(user_id_str)
    tariff = TARIFFS.get(tariff_id)

    sub_id = str(uuid.uuid4())
    expiry_date = datetime.now() + timedelta(days=tariff["days"])

    await create_user(sub_id, expiry_date)
    links = await get_user_links(sub_id)
    await db_manager.record_trial_usage(user_id, sub_id, expiry_date)

    await bot.send_message(
        chat_id=user_id,
        text=(f"🎉 Оплата подтверждена!\n\n"
              f"Тариф: <b>{tariff['name']}</b>\n"
              f"Срок: {tariff['days']} дней\n\n"
              f"🔑 Ваши VPN ключи:\n\n{links}")
    )

    await callback.message.edit_caption(
        caption=f"✅ Оплата от {user_id} подтверждена.\nТариф: {tariff['name']}"
    )
    from tgbot.handlers.referrals import mark_referral_paid
    await mark_referral_paid(int(user_id))
    await callback.answer("Оплата подтверждена ✅")


# ❌ Админ отклонил оплату
@payments_router.callback_query(F.data.startswith("reject_"))
async def handle_reject(callback: CallbackQuery):
    _, user_id_str, tariff_id = callback.data.split("_")
    user_id = int(user_id_str)
    tariff = TARIFFS.get(tariff_id)

    await bot.send_message(
        chat_id=user_id,
        text=(
            f"❌ Оплата за тариф <b>{tariff['name']}</b> отклонена.\n"
            f"Свяжитесь с администратором: @{config.tg_bot.admin_id}"
        )
    )

    await callback.message.edit_caption(
        caption=f"🚫 Оплата пользователя <code>{user_id}</code> отклонена.\nТариф: {tariff['name']}"
    )
    await callback.answer("Оплата отклонена ❌")
