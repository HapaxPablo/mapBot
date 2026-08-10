import re
from html import escape

from aiogram import F, Router

import api_client
from keyboards.points import point_vote_keyboard
from runtime import logger


router = Router()


@router.callback_query(F.data.startswith("point:"))
async def point_info(callback):
    point_id = callback.data.split(":", 1)[1]
    try:
        point = await api_client.get_point(point_id, callback.from_user.id)
    except Exception:
        logger.exception("Не удалось загрузить точку %s", point_id)
        await callback.answer("Точка недоступна или была скрыта.", show_alert=True)
        return

    text = (
        f"📍 <b>{escape(str(point['title']))}</b>\n"
        f"📄 {escape(str(point.get('description') or '—'))}\n"
        f"🌍 Координаты: <code>{point['lat']}, {point['lng']}</code>"
    )
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=point_vote_keyboard(point_id, point["likes"], point["dislikes"]),
    )
    if point.get("photo_url"):
        await callback.message.answer_photo(point["photo_url"], caption="📷 Фото точки")
    await callback.answer()


@router.callback_query(F.data.startswith("vote:"))
async def point_vote(callback):
    _, vote_type, point_id = callback.data.split(":", 2)
    try:
        result = await api_client.vote(
            point_id=point_id,
            telegram_user_id=callback.from_user.id,
            vote_type=vote_type,
        )
    except Exception:
        logger.exception("Не удалось сохранить голос за точку %s", point_id)
        await callback.answer("Не удалось сохранить голос. Попробуйте позже.", show_alert=True)
        return
    if result.get("already_voted"):
        await callback.answer("Вы уже голосовали за эту точку.", show_alert=True)
        return

    message_text = callback.message.text or ""
    message_text = re.sub(r"❤️\s*\d+", f"❤️ {result['likes']}", message_text)
    message_text = re.sub(r"👎\s*\d+", f"👎 {result['dislikes']}", message_text)
    await callback.message.edit_text(
        message_text,
        parse_mode="HTML",
        reply_markup=point_vote_keyboard(point_id, result["likes"], result["dislikes"]),
    )
    await callback.answer("Ваш голос учтён!")
