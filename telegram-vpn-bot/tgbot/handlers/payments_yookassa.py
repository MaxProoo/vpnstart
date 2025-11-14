# tgbot/handlers/payments_yookassa.py
import uuid
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loader import bot, config
from marzban.client import create_user, get_user_links
import db_manager
from fastapi import Request, APIRouter
from yookassa import Configuration, Payment

# Роутеры
payments_yookassa_router = Router()
webhook_router = APIRouter()

# Настройка YooKassa SDK (использует значения из config.yookassa)
Configuration.account_id = config.yookassa.shop_id
Configuration.secret_key = config.yookassa.api_key

# Тарифы
TARIFFS = {
    "basic": {"name": "💼 Базовый", "days": 30, "price": 79},
    "premium": {"name": "🚀 Премиум", "days": 90, "price": 199},
    "vip": {"name": "👑 VIP", "days": 365, "price": 749},
}


@payments_yookassa_router.callback_query(F.data.startswith("pay_yookassa_"))
async def pay_yookassa(callback: CallbackQuery):
    tariff_id = callback.data.split("_", 2)[-1]
    tariff = TARIFFS.get(tariff_id)
    if not tariff:
        await callback.answer("Ошибка: тариф не найден ❌", show_alert=True)
        return

    # Создаём платёж через YooKassa API (redirect)
    payment = Payment.create({
        "amount": {"value": f"{tariff['price']}.00", "currency": "RUB"},
        "confirmation": {
            "type": "redirect",
            # верни url на тот, который у тебя валиден; можно telegram username return to bot
            "return_url": f"https://t.me/{(await bot.get_me()).username}"
        },
        "capture": True,
        "description": f"Оплата тарифа {tariff['name']} пользователем {callback.from_user.id}",
        "metadata": {
            "user_id": str(callback.from_user.id),
            "tariff_id": tariff_id
        }
    })

    payment_url = payment.confirmation.confirmation_url

    await callback.message.answer(
        f"💳 Для оплаты тарифа <b>{tariff['name']}</b> нажмите кнопку ниже 👇\n\n"
        f"После оплаты VPN будет выдан автоматически 🔐",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оплатить через YooKassa", url=payment_url)]
        ])
    )
    await callback.answer()


# Webhook от YooKassa — настрой URL в YOO merchant panel на этот endpoint
@webhook_router.post("/yookassa/webhook")
async def yookassa_webhook(request: Request):
    """
    Ожидает JSON вида от YooKassa.
    Если event == "payment.succeeded" — активирует подписку и запускает реферальную обработку.
    """
    body = await request.json()
    event = body.get("event")
    obj = body.get("object", {})
    if event != "payment.succeeded":
        return {"status": "ignored"}

    metadata = obj.get("metadata", {}) or {}
    user_id_raw = metadata.get("user_id")
    tariff_id = metadata.get("tariff_id")

    if not user_id_raw or not tariff_id:
        return {"status": "error", "message": "Missing metadata"}

    try:
        user_id = int(user_id_raw)
    except Exception:
        return {"status": "error", "message": "Invalid user_id"}

    tariff = TARIFFS.get(tariff_id)
    if not tariff:
        return {"status": "error", "message": "Tariff not found"}

    # Создаём VPN-подписку
    sub_id = str(uuid.uuid4())
    expiry_date = datetime.now() + timedelta(days=tariff["days"])

    try:
        await create_user(sub_id, expiry_date)
        links = await get_user_links(sub_id)
        await db_manager.record_trial_usage(user_id, sub_id, expiry_date)

        # Отправляем пользователю ключи
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 Оплата подтверждена!\n\n"
                f"Тариф: <b>{tariff['name']}</b>\n"
                f"⏱ Срок: {tariff['days']} дней\n\n"
                f"🔑 Ваши VPN ключи:\n\n{links}"
            ),
        )

        # --- Реферальная логика: отмечаем оплату и проверяем награду ---
        try:
            referrer_id = await db_manager.mark_referral_paid(user_id)  # возвращает referrer_id или None
            if referrer_id:
                # проверяем, достиг ли реферер порога и не награждался ли уже
                should_reward = await db_manager.should_reward_referrer(referrer_id)
                if should_reward:
                    # выдаём бесплатный месяц и помечаем, что награда выдана
                    bonus_sub = str(uuid.uuid4())
                    bonus_expiry = datetime.now() + timedelta(days=30)
                    await create_user(bonus_sub, bonus_expiry)
                    bonus_links = await get_user_links(bonus_sub)
                    await db_manager.mark_referrer_rewarded(referrer_id)
                    await db_manager.record_trial_usage(referrer_id, bonus_sub, bonus_expiry)
                    await bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            f"🎁 Поздравляем! Трое ваших приглашённых оплатили подписку.\n"
                            f"Вы получили 1 месяц бесплатного доступа.\n\n🔑 Ключи:\n{bonus_links}"
                        )
                    )
        except Exception as e:
            # логируем, но НЕ ломаем основной поток
            logger = __import__("logging").getLogger(__name__)
            logger.exception("Ошибка при реферальной обработке: %s", e)

        return {"status": "success"}
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Ошибка при обработке webhook YooKassa: %s", e)
        return {"status": "error", "message": "internal error"}
