from aiogram.types import Message

import api_client
from keyboards.common import main_keyboard
from runtime import ADMIN_ROLES, logger


async def profile_keyboard(telegram_user_id: int):
    try:
        profile = await api_client.get_telegram_profile(telegram_user_id)
    except Exception:
        logger.exception("Не удалось получить роль Telegram-пользователя")
        return main_keyboard()
    return main_keyboard(profile.get("role") if profile else None)


async def require_admin(message: Message) -> dict | None:
    try:
        profile = await api_client.get_telegram_profile(message.from_user.id)
    except Exception:
        logger.exception("Не удалось проверить права администратора")
        await message.answer("⚠️ Не удалось проверить права доступа. Попробуйте позже.")
        return None
    if not profile or profile.get("role") not in ADMIN_ROLES:
        await message.answer(
            "⛔ Админка доступна только администраторам.",
            reply_markup=main_keyboard(profile.get("role") if profile else None),
        )
        return None
    return profile


async def require_admin_callback(callback) -> bool:
    try:
        profile = await api_client.get_telegram_profile(callback.from_user.id)
    except Exception:
        logger.exception("Не удалось проверить права администратора")
        await callback.answer("Не удалось проверить права доступа.", show_alert=True)
        return False
    if not profile or profile.get("role") not in ADMIN_ROLES:
        await callback.answer("Админка доступна только администраторам.", show_alert=True)
        return False
    return True
