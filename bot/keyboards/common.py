from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.types import WebAppInfo

import config
from runtime import ADMIN_BUTTON, ADMIN_ROLES, ADMIN_USERS_BUTTON, ADMIN_TYPES_BUTTON
from runtime import ADMIN_POINTS_BUTTON, ADMIN_VOTES_BUTTON, ADMIN_BACK_BUTTON


def main_keyboard(role: str | None = None) -> ReplyKeyboardMarkup:
    keyboard = [[
        KeyboardButton(text="📍 Список точек"),
        KeyboardButton(text="➕ Добавить точку"),
    ]]
    if role in ADMIN_ROLES:
        keyboard.append([KeyboardButton(text=ADMIN_BUTTON)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_USERS_BUTTON), KeyboardButton(text=ADMIN_TYPES_BUTTON)],
            [KeyboardButton(text=ADMIN_POINTS_BUTTON), KeyboardButton(text=ADMIN_VOTES_BUTTON)],
            [KeyboardButton(text=ADMIN_BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


def map_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗺 Открыть карту", web_app=WebAppInfo(url=config.WEBAPP_URL)),
    ]])


def registration_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Зарегистрироваться")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
