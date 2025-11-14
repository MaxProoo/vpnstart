import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)


def keyboard_start():
    builder = InlineKeyboardBuilder()
    builder.button(text='🎁 Получить пробный доступ', callback_data='trial')
    builder.button(text="💬 Поддержка", url="https://t.me/workerswy")
    builder.button(text='💰 Тарифы', callback_data='show_tariffs')
    builder.button(text="о нас", callback_data="about")
    builder.button(text='впн на месяц бесплатно', callback_data='/ref_call')
    builder.adjust(2)
    return builder.as_markup()



def keyboard_cancel():
    builder = InlineKeyboardBuilder()
    builder.button(text='❌Выйти из меню', callback_data='cancel')
    return builder.as_markup()


def keyboard_about():
    builder = InlineKeyboardBuilder()
    builder.button(text="📞 Поддержка", url="https://t.me/workerswy")
    builder.button(text="💰 Тарифы", callback_data="show_tariffs")
    return builder.as_markup()


