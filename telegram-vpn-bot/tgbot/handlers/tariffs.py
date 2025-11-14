import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

tariffs_router = Router()

# 🔹 База тарифов
TARIFFS = [
    {
        "id": "basic",
        "name": "💼 Базовый",
        "duration_days": 30,
        "price": 79,
        "description": "30 дней доступа, 1 устройство, без ограничений по скорости."
    },
    {
        "id": "premium",
        "name": "🚀 Премиум",
        "duration_days": 90,
        "price": 199,
        "description": "90 дней, до 3 устройств, приоритетная поддержка."
    },
    {
        "id": "vip",
        "name": "👑 VIP",
        "duration_days": 365,
        "price": 749,
        "description": "1 год доступа, без ограничений, поддержка 24/7."
    }
]


# 🔹 Команда /tariffs
@tariffs_router.message(F.text.in_({"/tariffs", "Тарифы"}))
async def show_tariffs(message: Message):
    """Отображает список тарифов пользователю"""
    for tariff in TARIFFS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Купить за {tariff['price']}₽",
                callback_data=f"pay_{tariff['id']}"
            )]
        ])
        await message.answer(
            f"<b>{tariff['name']}</b>\n\n"
            f"{tariff['description']}\n\n"
            f"⏱ Срок: {tariff['duration_days']} дней\n"
            f"💰 Цена: {tariff['price']}₽",
            reply_markup=keyboard
        )

@tariffs_router.callback_query(F.data == 'show_tariffs')
async def help_callback_handler(callback: CallbackQuery):
    for tariff in TARIFFS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Купить за {tariff['price']}₽",
                callback_data=f"pay_{tariff['id']}"
            )]
        ])
        await callback.message.answer(
            f"<b>{tariff['name']}</b>\n\n"
            f"{tariff['description']}\n\n"
            f"⏱ Срок: {tariff['duration_days']} дней\n"
            f"💰 Цена: {tariff['price']}₽",
            reply_markup=keyboard
        )


# 🔹 Пользователь нажал "Купить"
@tariffs_router.callback_query(F.data.startswith("buy_"))
async def select_payment_method(callback: CallbackQuery):
    """Показывает выбор способа оплаты"""
    tariff_id = callback.data.split("_", 1)[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Ручная оплата", callback_data=f"pay_manual_{tariff_id}")
        ],
        [
            InlineKeyboardButton(text="💳 Оплата через ЮKassa", callback_data=f"pay_yookassa_{tariff_id}")
        ]
    ])

    await callback.message.answer(
        "Выберите способ оплаты 💰:",
        reply_markup=keyboard
    )
    await callback.answer()
