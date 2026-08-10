from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import api_client
from keyboards.admin import (
    admin_point_actions_keyboard,
    admin_point_edit_keyboard,
    admin_point_keyboard,
    admin_type_actions_keyboard,
    admin_type_edit_keyboard,
    admin_type_keyboard,
    admin_user_keyboard,
    admin_user_roles_keyboard,
    role_label,
)
from keyboards.common import admin_keyboard, main_keyboard
from runtime import (
    ADMIN_BACK_BUTTON,
    ADMIN_BUTTON,
    ADMIN_POINTS_BUTTON,
    ADMIN_TYPES_BUTTON,
    ADMIN_USERS_BUTTON,
    ADMIN_VOTES_BUTTON,
    bot,
    logger,
)
from services.access import require_admin, require_admin_callback
from states import Admin
from utils import api_error_text


router = Router()


@router.message(F.text == ADMIN_BUTTON)
async def admin_start(message: Message, state: FSMContext):
    if not await require_admin(message):
        return
    await state.clear()
    await state.set_state(Admin.menu)
    await message.answer(
        "⚙️ Админка\nВыберите раздел:",
        reply_markup=admin_keyboard(),
    )


@router.message(StateFilter(Admin.menu), F.text == ADMIN_BACK_BUTTON)
async def admin_back(message: Message, state: FSMContext):
    profile = await require_admin(message)
    if not profile:
        await state.clear()
        return
    await state.clear()
    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_keyboard(profile.get("role")),
    )


@router.message(StateFilter(Admin.menu), F.text == ADMIN_USERS_BUTTON)
async def admin_users_start(message: Message, state: FSMContext):
    if not await require_admin(message):
        return
    try:
        users = await api_client.admin_list_users(message.from_user.id)
    except Exception as exc:
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось загрузить пользователей.')}")
        return
    await state.set_state(Admin.users)
    await message.answer(
        f"👥 Пользователи: {len(users)}\nВыберите пользователя:",
        reply_markup=admin_user_keyboard(users),
    )


@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user_selected(callback):
    if not await require_admin_callback(callback):
        return
    telegram_id = int(callback.data.split(":", 2)[2])
    try:
        users = await api_client.admin_list_users(callback.from_user.id)
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось загрузить пользователя."), show_alert=True)
        return
    user = next((item for item in users if item["telegram_id"] == telegram_id), None)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")])) or "Без имени"
    text = (
        f"👤 <b>{escape(name)}</b>\n"
        f"Username: @{escape(user.get('username') or '—')}\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Роль: <b>{role_label(user['role'])}</b>\n\n"
        "Выберите новую роль:"
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=admin_user_roles_keyboard(telegram_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:user-role:"))
async def admin_user_role_selected(callback):
    if not await require_admin_callback(callback):
        return
    _, _, telegram_id, role = callback.data.split(":", 3)
    try:
        await api_client.admin_change_user_role(callback.from_user.id, int(telegram_id), role)
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось изменить роль."), show_alert=True)
        return
    await callback.answer("Роль изменена")
    await callback.message.answer(
        f"✅ Для пользователя {telegram_id} установлена роль «{role_label(role)}»."
    )


@router.message(StateFilter(Admin.menu), F.text == ADMIN_TYPES_BUTTON)
async def admin_types_start(message: Message, state: FSMContext):
    if not await require_admin(message):
        return
    try:
        point_types = await api_client.admin_list_point_types(message.from_user.id)
    except Exception as exc:
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось загрузить типы точек.')}")
        return
    await message.answer(
        f"🗂 Типы точек: {len(point_types)}",
        reply_markup=admin_type_keyboard(point_types),
    )


@router.callback_query(F.data == "admin:type-add")
async def admin_type_add(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    await state.set_state(Admin.type_name)
    await callback.answer()
    await callback.message.answer("Введите название нового типа точки:")


@router.message(StateFilter(Admin.type_name))
async def admin_type_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(type_name=name)
    await state.set_state(Admin.type_icon)
    await message.answer("Введите имя Lucide-иконки или напишите «Пропустить»:")


@router.message(StateFilter(Admin.type_icon))
async def admin_type_icon(message: Message, state: FSMContext):
    icon_name = (message.text or "").strip()
    if icon_name.casefold() == "пропустить" or not icon_name:
        icon_name = "MapPin"
    await state.update_data(type_icon=icon_name)
    await state.set_state(Admin.type_visibility)
    await message.answer(
        "Показывать этот тип на общей карте?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да", callback_data="admin:type-visibility:1"),
            InlineKeyboardButton(text="Нет", callback_data="admin:type-visibility:0"),
        ]]),
    )


@router.callback_query(StateFilter(Admin.type_visibility), F.data.startswith("admin:type-visibility:"))
async def admin_type_visibility(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    data = await state.get_data()
    try:
        await api_client.admin_create_point_type(
            callback.from_user.id,
            data["type_name"],
            data["type_icon"],
            callback.data.endswith(":1"),
        )
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось создать тип."), show_alert=True)
        return
    await state.set_state(Admin.menu)
    await callback.answer("Тип создан")
    await callback.message.answer("✅ Тип точки создан.", reply_markup=admin_keyboard())


@router.callback_query(F.data.startswith("admin:type:"))
async def admin_type_selected(callback):
    if not await require_admin_callback(callback):
        return
    point_type_id = int(callback.data.split(":", 2)[2])
    try:
        point_types = await api_client.admin_list_point_types(callback.from_user.id)
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось загрузить тип."), show_alert=True)
        return
    point_type = next((item for item in point_types if item["id"] == point_type_id), None)
    if point_type is None:
        await callback.answer("Тип точки не найден.", show_alert=True)
        return
    text = (
        f"🗂 <b>{escape(point_type['name'])}</b>\n"
        f"Иконка: <code>{escape(point_type['icon_name'])}</code>\n"
        f"Общая карта: {'да' if point_type['show_on_main_map'] else 'нет'}"
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=admin_type_actions_keyboard(point_type_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:type-edit:"))
async def admin_type_edit(callback):
    if not await require_admin_callback(callback):
        return
    point_type_id = int(callback.data.split(":", 2)[2])
    await callback.answer()
    await callback.message.answer("Что изменить?", reply_markup=admin_type_edit_keyboard(point_type_id))


@router.callback_query(F.data.startswith("admin:type-toggle:"))
async def admin_type_toggle(callback):
    if not await require_admin_callback(callback):
        return
    point_type_id = int(callback.data.split(":", 2)[2])
    try:
        point_types = await api_client.admin_list_point_types(callback.from_user.id)
        point_type = next(item for item in point_types if item["id"] == point_type_id)
        await api_client.admin_update_point_type(
            callback.from_user.id,
            point_type_id,
            {"show_on_main_map": not point_type["show_on_main_map"]},
        )
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось изменить видимость типа."), show_alert=True)
        return
    await callback.answer("Видимость изменена")
    await callback.message.answer("✅ Настройка показа на общей карте изменена.")


@router.callback_query(F.data.startswith("admin:type-delete:"))
async def admin_type_delete(callback):
    if not await require_admin_callback(callback):
        return
    point_type_id = int(callback.data.split(":", 2)[2])
    try:
        await api_client.admin_delete_point_type(callback.from_user.id, point_type_id)
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось удалить тип."), show_alert=True)
        return
    await callback.answer("Тип удалён")
    await callback.message.answer("✅ Тип точки удалён.")


@router.callback_query(F.data.startswith("admin:type-edit-field:"))
async def admin_type_edit_field(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    _, _, point_type_id, field = callback.data.split(":", 3)
    await state.update_data(type_edit_id=int(point_type_id), type_edit_field=field)
    await state.set_state(Admin.type_edit_value)
    await callback.answer()
    await callback.message.answer("Введите новое значение:")


@router.message(StateFilter(Admin.type_edit_value))
async def admin_type_edit_value(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value:
        await message.answer("Значение не может быть пустым. Попробуйте ещё раз:")
        return
    data = await state.get_data()
    try:
        await api_client.admin_update_point_type(
            message.from_user.id,
            data["type_edit_id"],
            {data["type_edit_field"]: value},
        )
    except Exception as exc:
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось изменить тип.')}")
        return
    await state.set_state(Admin.menu)
    await message.answer("✅ Тип точки обновлён.", reply_markup=admin_keyboard())


@router.message(StateFilter(Admin.menu), F.text == ADMIN_POINTS_BUTTON)
async def admin_points_start(message: Message, state: FSMContext):
    if not await require_admin(message):
        return
    try:
        points = await api_client.admin_list_points(message.from_user.id)
    except Exception as exc:
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось загрузить точки.')}")
        return
    await state.set_state(Admin.points)
    await message.answer(
        f"📍 Точки: {len(points)}\nВыберите точку:",
        reply_markup=admin_point_keyboard(points),
    )


@router.callback_query(F.data.startswith("admin:point:"))
async def admin_point_selected(callback):
    if not await require_admin_callback(callback):
        return
    point_id = callback.data.split(":", 2)[2]
    try:
        points = await api_client.admin_list_points(callback.from_user.id)
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось загрузить точку."), show_alert=True)
        return
    point = next((item for item in points if str(item["id"]) == point_id), None)
    if point is None:
        await callback.answer("Точка не найдена.", show_alert=True)
        return
    text = (
        f"📍 <b>{escape(point['title'])}</b>\n"
        f"Тип: {escape(point['point_type'])}\n"
        f"Описание: {escape(point.get('description') or '—')}\n"
        f"Координаты: <code>{point['lat']}, {point['lng']}</code>\n"
        f"Доступ: {', '.join(map(str, point.get('allowed_user_ids', []))) or 'все разрешённые пользователи'}\n"
        f"Статус: {'активна' if point['is_active'] else 'скрыта'}\n"
        f"Лайки/дизлайки: {point['likes']}/{point['dislikes']}"
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=admin_point_actions_keyboard(point_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:point-toggle:"))
async def admin_point_toggle(callback):
    if not await require_admin_callback(callback):
        return
    point_id = callback.data.split(":", 2)[2]
    try:
        points = await api_client.admin_list_points(callback.from_user.id)
        point = next(item for item in points if str(item["id"]) == point_id)
        await api_client.admin_update_point(
            callback.from_user.id,
            point_id,
            {"is_active": not point["is_active"]},
        )
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось изменить статус точки."), show_alert=True)
        return
    await callback.answer("Статус изменён")
    await callback.message.answer("✅ Статус точки изменён.")


@router.callback_query(F.data.startswith("admin:point-edit:"))
async def admin_point_edit(callback):
    if not await require_admin_callback(callback):
        return
    point_id = callback.data.split(":", 2)[2]
    await callback.answer()
    await callback.message.answer("Что изменить?", reply_markup=admin_point_edit_keyboard(point_id))


@router.callback_query(F.data.startswith("admin:point-photo:"))
async def admin_point_photo_start(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    point_id = callback.data.split(":", 2)[2]
    await state.update_data(point_photo_id=point_id)
    await state.set_state(Admin.point_photo)
    await callback.answer()
    await callback.message.answer("Пришлите новое фото точки:")


@router.message(StateFilter(Admin.point_photo), F.photo)
async def admin_point_photo_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    photo = message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        await api_client.admin_upload_point_photo(
            message.from_user.id,
            data["point_photo_id"],
            file_bytes.read(),
            f"{photo.file_id}.jpg",
        )
    except Exception as exc:
        logger.exception("Не удалось заменить фото точки")
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось загрузить фото.')}")
        return
    await state.set_state(Admin.menu)
    await message.answer("✅ Фото точки обновлено.", reply_markup=admin_keyboard())


@router.message(StateFilter(Admin.point_photo))
async def admin_point_photo_invalid(message: Message):
    await message.answer("Пришлите именно фото точки.")


@router.callback_query(F.data.startswith("admin:pef:"))
async def admin_point_edit_field(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    _, _, point_id, field = callback.data.split(":", 3)
    if field == "point_type":
        try:
            point_types = await api_client.admin_list_point_types(callback.from_user.id)
        except Exception as exc:
            await callback.answer(api_error_text(exc, "Не удалось загрузить типы точек."), show_alert=True)
            return
        await callback.answer()
        await callback.message.answer(
            "Выберите новый тип:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=point_type["name"],
                    callback_data=f"admin:point-type:{point_id}:{point_type['id']}",
                )
            ] for point_type in point_types]),
        )
        return
    await state.update_data(point_edit_id=point_id, point_edit_field=field)
    await state.set_state(Admin.point_edit_value)
    await callback.answer()
    if field == "description":
        prompt = "Введите описание или «Пропустить»:"
    elif field == "allowed_users":
        prompt = "Введите Telegram ID пользователей через запятую или «Пропустить» для доступа всем:"
    else:
        prompt = "Введите новое значение:"
    await callback.message.answer(prompt)


@router.callback_query(F.data.startswith("admin:point-type:"))
async def admin_point_type_selected(callback):
    if not await require_admin_callback(callback):
        return
    _, _, point_id, point_type_id = callback.data.split(":", 3)
    try:
        point_types = await api_client.admin_list_point_types(callback.from_user.id)
        point_type = next(item for item in point_types if str(item["id"]) == point_type_id)
        await api_client.admin_update_point(
            callback.from_user.id,
            point_id,
            {"point_type": point_type["name"]},
        )
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось изменить тип точки."), show_alert=True)
        return
    await callback.answer("Тип изменён")
    await callback.message.answer("✅ Тип точки обновлён.")


@router.message(StateFilter(Admin.point_edit_value))
async def admin_point_edit_value(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    data = await state.get_data()
    field = data["point_edit_field"]
    changes = {}
    if field == "coordinates":
        try:
            lat, lng = [float(item.strip()) for item in value.split(",", 1)]
        except (ValueError, TypeError):
            await message.answer("Введите координаты в формате: 56.01, 92.87")
            return
        changes = {"lat": lat, "lng": lng}
    elif field == "description":
        changes = {"description": None if value.casefold() == "пропустить" else value}
    elif field == "allowed_users":
        if value.casefold() == "пропустить":
            changes = {"allowed_users": []}
        else:
            try:
                user_ids = [int(item.strip()) for item in value.split(",") if item.strip()]
            except ValueError:
                await message.answer("Введите Telegram ID через запятую, например: 123, 456")
                return
            changes = {"allowed_users": user_ids}
    elif value:
        changes = {field: value}
    else:
        await message.answer("Значение не может быть пустым. Попробуйте ещё раз:")
        return
    try:
        await api_client.admin_update_point(message.from_user.id, data["point_edit_id"], changes)
    except Exception as exc:
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось обновить точку.')}")
        return
    await state.set_state(Admin.menu)
    await message.answer("✅ Точка обновлена.", reply_markup=admin_keyboard())


@router.message(StateFilter(Admin.menu), F.text == ADMIN_VOTES_BUTTON)
async def admin_votes_start(message: Message):
    if not await require_admin(message):
        return
    try:
        votes = await api_client.admin_list_votes(message.from_user.id)
    except Exception as exc:
        await message.answer(f"⚠️ {api_error_text(exc, 'Не удалось загрузить голоса.')}")
        return
    if not votes:
        await message.answer("🗳 Голосов пока нет.")
        return
    lines = [f"🗳 Голоса: {len(votes)}"]
    for vote in votes[:50]:
        lines.append(
            f"{vote['vote_type']}: {vote['point_title']} — "
            f"{vote.get('username') or vote.get('telegram_user_id') or 'неизвестный пользователь'}"
        )
    await message.answer("\n".join(lines))
