from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

import api_client
from keyboards.common import main_keyboard, registration_keyboard
from runtime import logger


router = Router()


@router.message(Command("start"))
async def start(message: Message):
    try:
        profile = await api_client.get_telegram_profile(message.from_user.id)
    except Exception:
        logger.exception("Не удалось проверить регистрацию Telegram-пользователя")
        profile = None
    if profile:
        await message.answer(
            "🌌 С возвращением в GeoMapBot!",
            reply_markup=main_keyboard(profile.get("role")),
        )
        return
    await message.answer(
        "🌌 Добро пожаловать в GeoMapBot!\n\n"
        "Для регистрации нажмите кнопку ниже.",
        reply_markup=registration_keyboard(),
    )


@router.message(F.text == "✅ Зарегистрироваться")
async def register_user(message: Message):
    try:
        auth = await api_client.authenticate_telegram_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    except Exception:
        logger.exception("Не удалось зарегистрировать Telegram-пользователя")
        await message.answer(
            "⚠️ Не удалось выполнить регистрацию. Попробуйте ещё раз позже.",
            reply_markup=registration_keyboard(),
        )
        return

    if auth.get("already_registered"):
        profile = await api_client.get_telegram_profile(message.from_user.id)
        role = profile.get("role") if profile else None
    else:
        role = auth["user"]["role"]
    logger.info("Telegram user %s registered with role %s", message.from_user.id, role)
    await message.answer(
        (
            "✅ Регистрация успешно завершена!\n\n"
            if not auth.get("already_registered")
            else "✅ Вы уже зарегистрированы.\n\n"
        )
        + "Теперь можно пользоваться ботом.",
        reply_markup=main_keyboard(role),
    )
