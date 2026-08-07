import asyncio
import logging
import re
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo,
                           InlineKeyboardMarkup, InlineKeyboardButton, MenuButtonWebApp)

import api_client
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TOKEN)
storage = RedisStorage.from_url(config.REDIS_URL) if config.REDIS_URL else MemoryStorage()
dp = Dispatcher(storage=storage)

ADMIN_BUTTON = "⚙️ Админка"
ADMIN_USERS_BUTTON = "👥 Пользователи"
ADMIN_TYPES_BUTTON = "🗂 Типы точек"
ADMIN_POINTS_BUTTON = "📍 Управление точками"
ADMIN_VOTES_BUTTON = "🗳 Голоса"
ADMIN_BACK_BUTTON = "⬅️ Назад"
ADMIN_ROLES = {"admin", "superuser"}


def main_keyboard(role: str | None = None) -> ReplyKeyboardMarkup:
    keyboard = [[
        KeyboardButton(text="📍 Список точек"),
        KeyboardButton(text="➕ Добавить точку"),
    ]]
    if role in ADMIN_ROLES:
        keyboard.append([KeyboardButton(text=ADMIN_BUTTON)])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


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
    """Inline WebApp button: this launch mode includes Telegram initData."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🗺 Открыть карту",
            web_app=WebAppInfo(url=config.WEBAPP_URL),
        ),
    ]])


def registration_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Зарегистрироваться")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


class AddPoint(StatesGroup):
    point_type = State()
    title = State()
    description = State()
    location = State()
    photo = State()


class PointsList(StatesGroup):
    scope = State()


class Admin(StatesGroup):
    menu = State()
    users = State()
    type_name = State()
    type_icon = State()
    type_visibility = State()
    type_edit_value = State()
    points = State()
    point_edit_value = State()
    point_photo = State()


async def profile_keyboard(telegram_user_id: int) -> ReplyKeyboardMarkup:
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


@dp.message(Command("start"))
async def start(message: Message):
    try:
        profile = await api_client.get_telegram_profile(message.from_user.id)
    except Exception:
        logger.exception("Не удалось проверить регистрацию Telegram-пользователя")
        profile = None
    if profile:
        await message.answer(
            "🌍 С возвращением в GeoMapBot!",
            reply_markup=main_keyboard(profile.get("role")),
        )
        return
    await message.answer(
        "🌍 Добро пожаловать в GeoMapBot!\n\n"
        "Для регистрации нажмите кнопку ниже.",
        reply_markup=registration_keyboard(),
    )


@dp.message(F.text == "✅ Зарегистрироваться")
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
        ("✅ Регистрация успешно завершена!\n\n" if not auth.get("already_registered")
         else "✅ Вы уже зарегистрированы.\n\n")
        + "Теперь можно пользоваться ботом.",
        reply_markup=main_keyboard(role),
    )


def role_label(role: str) -> str:
    return {
        "admin": "Администратор",
        "superuser": "Суперпользователь",
        "old_member": "Старый участник",
        "new_member": "Новый участник",
    }.get(role, role)


def admin_user_keyboard(users: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=(user.get("username") or user.get("first_name") or str(user["telegram_id"]))[:60],
            callback_data=f"admin:user:{user['telegram_id']}",
        )
    ] for user in users])


def admin_type_keyboard(point_types: list[dict], include_add: bool = True) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(
            text=f"{point_type['name']} ({'общая карта' if point_type['show_on_main_map'] else 'спец. слой'})"[:64],
            callback_data=f"admin:type:{point_type['id']}",
        )
    ] for point_type in point_types]
    if include_add:
        rows.append([InlineKeyboardButton(text="➕ Добавить тип", callback_data="admin:type-add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_point_keyboard(points: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"{'✅' if point['is_active'] else '⛔'} {point['title']}"[:64],
            callback_data=f"admin:point:{point['id']}",
        )
    ] for point in points])


def admin_user_roles_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=label,
            callback_data=f"admin:user-role:{telegram_id}:{role}",
        )
    ] for role, label in (
        ("admin", "Администратор"),
        ("superuser", "Суперпользователь"),
        ("old_member", "Старый участник"),
        ("new_member", "Новый участник"),
    )])


def admin_type_actions_keyboard(point_type_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin:type-edit:{point_type_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:type-delete:{point_type_id}")],
    ])


def admin_type_edit_keyboard(point_type_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"admin:type-edit-field:{point_type_id}:name")],
        [InlineKeyboardButton(text="Иконка", callback_data=f"admin:type-edit-field:{point_type_id}:icon_name")],
        [InlineKeyboardButton(text="Показ на общей карте", callback_data=f"admin:type-toggle:{point_type_id}")],
    ])


def admin_point_actions_keyboard(point_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin:point-edit:{point_id}")],
        [InlineKeyboardButton(text="🔁 Изменить активность", callback_data=f"admin:point-toggle:{point_id}")],
        [InlineKeyboardButton(text="📷 Заменить фото", callback_data=f"admin:point-photo:{point_id}")],
    ])


def admin_point_edit_keyboard(point_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"admin:pef:{point_id}:title")],
        [InlineKeyboardButton(text="Описание", callback_data=f"admin:pef:{point_id}:description")],
        [InlineKeyboardButton(text="Тип", callback_data=f"admin:pef:{point_id}:point_type")],
        [InlineKeyboardButton(text="Координаты", callback_data=f"admin:pef:{point_id}:coordinates")],
        [InlineKeyboardButton(text="Доступ пользователей", callback_data=f"admin:pef:{point_id}:allowed_users")],
    ])


def api_error_text(exc: Exception, fallback: str) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
            if detail:
                return str(detail)
        except (ValueError, AttributeError):
            pass
    return fallback


@dp.message(F.text == ADMIN_BUTTON)
async def admin_start(message: Message, state: FSMContext):
    if not await require_admin(message):
        return
    await state.clear()
    await state.set_state(Admin.menu)
    await message.answer(
        "⚙️ Админка\nВыберите раздел:",
        reply_markup=admin_keyboard(),
    )


@dp.message(StateFilter(Admin.menu), F.text == ADMIN_BACK_BUTTON)
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


@dp.message(StateFilter(Admin.menu), F.text == ADMIN_USERS_BUTTON)
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


@dp.callback_query(F.data.startswith("admin:user:"))
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


@dp.callback_query(F.data.startswith("admin:user-role:"))
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
    await callback.message.answer(f"✅ Для пользователя {telegram_id} установлена роль «{role_label(role)}».")


@dp.message(StateFilter(Admin.menu), F.text == ADMIN_TYPES_BUTTON)
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


@dp.callback_query(F.data == "admin:type-add")
async def admin_type_add(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    await state.set_state(Admin.type_name)
    await callback.answer()
    await callback.message.answer("Введите название нового типа точки:")


@dp.message(StateFilter(Admin.type_name))
async def admin_type_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(type_name=name)
    await state.set_state(Admin.type_icon)
    await message.answer("Введите имя Lucide-иконки или напишите «Пропустить»:")


@dp.message(StateFilter(Admin.type_icon))
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


@dp.callback_query(StateFilter(Admin.type_visibility), F.data.startswith("admin:type-visibility:"))
async def admin_type_visibility(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    data = await state.get_data()
    show_on_main_map = callback.data.endswith(":1")
    try:
        await api_client.admin_create_point_type(
            callback.from_user.id,
            data["type_name"],
            data["type_icon"],
            show_on_main_map,
        )
    except Exception as exc:
        await callback.answer(api_error_text(exc, "Не удалось создать тип."), show_alert=True)
        return
    await state.set_state(Admin.menu)
    await callback.answer("Тип создан")
    await callback.message.answer("✅ Тип точки создан.", reply_markup=admin_keyboard())


@dp.callback_query(F.data.startswith("admin:type:"))
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


@dp.callback_query(F.data.startswith("admin:type-edit:"))
async def admin_type_edit(callback):
    if not await require_admin_callback(callback):
        return
    point_type_id = int(callback.data.split(":", 2)[2])
    await callback.answer()
    await callback.message.answer("Что изменить?", reply_markup=admin_type_edit_keyboard(point_type_id))


@dp.callback_query(F.data.startswith("admin:type-toggle:"))
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


@dp.callback_query(F.data.startswith("admin:type-delete:"))
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


@dp.callback_query(F.data.startswith("admin:type-edit-field:"))
async def admin_type_edit_field(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    _, _, point_type_id, field = callback.data.split(":", 3)
    await state.update_data(type_edit_id=int(point_type_id), type_edit_field=field)
    await state.set_state(Admin.type_edit_value)
    await callback.answer()
    await callback.message.answer("Введите новое значение:")


@dp.message(StateFilter(Admin.type_edit_value))
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


@dp.message(StateFilter(Admin.menu), F.text == ADMIN_POINTS_BUTTON)
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


@dp.callback_query(F.data.startswith("admin:point:"))
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


@dp.callback_query(F.data.startswith("admin:point-toggle:"))
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


@dp.callback_query(F.data.startswith("admin:point-edit:"))
async def admin_point_edit(callback):
    if not await require_admin_callback(callback):
        return
    point_id = callback.data.split(":", 2)[2]
    await callback.answer()
    await callback.message.answer("Что изменить?", reply_markup=admin_point_edit_keyboard(point_id))


@dp.callback_query(F.data.startswith("admin:point-photo:"))
async def admin_point_photo_start(callback, state: FSMContext):
    if not await require_admin_callback(callback):
        return
    point_id = callback.data.split(":", 2)[2]
    await state.update_data(point_photo_id=point_id)
    await state.set_state(Admin.point_photo)
    await callback.answer()
    await callback.message.answer("Пришлите новое фото точки:")


@dp.message(StateFilter(Admin.point_photo), F.photo)
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


@dp.message(StateFilter(Admin.point_photo))
async def admin_point_photo_invalid(message: Message):
    await message.answer("Пришлите именно фото точки.")


async def notification_loop():
    while True:
        try:
            notifications = await api_client.get_pending_notifications()
            sent_ids = []
            for notification in notifications:
                try:
                    await bot.send_message(notification["telegram_id"], notification["message"])
                except TelegramForbiddenError:
                    logger.warning(
                        "Пользователь %s заблокировал бота, уведомление %s удалено",
                        notification["telegram_id"], notification["id"],
                    )
                    sent_ids.append(notification["id"])
                except TelegramBadRequest:
                    logger.warning(
                        "Некорректное уведомление %s для пользователя %s удалено",
                        notification["id"],
                        notification["telegram_id"],
                    )
                    sent_ids.append(notification["id"])
                except Exception:
                    logger.exception(
                        "Не удалось отправить уведомление %s пользователю %s",
                        notification["id"], notification["telegram_id"],
                    )
                else:
                    sent_ids.append(notification["id"])
            await api_client.acknowledge_notifications(sent_ids)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка фоновой отправки уведомлений")
        await asyncio.sleep(5)


@dp.callback_query(F.data.startswith("admin:pef:"))
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


@dp.callback_query(F.data.startswith("admin:point-type:"))
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


@dp.message(StateFilter(Admin.point_edit_value))
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


@dp.message(StateFilter(Admin.menu), F.text == ADMIN_VOTES_BUTTON)
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


@dp.message(F.text == "➕ Добавить точку")
async def add_point_start(message: Message, state: FSMContext):
    try:
        point_types = await api_client.list_point_types()
    except Exception:
        logger.exception("Не удалось получить типы точек")
        await message.answer(
            "⚠️ Не удалось загрузить типы точек, попробуйте позже.",
            reply_markup=main_keyboard(),
        )
        return

    if not point_types:
        await message.answer(
            "⚠️ Пока не настроены типы точек. Обратитесь к администратору.",
            reply_markup=main_keyboard(),
        )
        return

    await state.update_data(
        point_types={str(point_type["id"]): point_type["name"] for point_type in point_types}
    )
    await state.set_state(AddPoint.point_type)
    await message.answer(
        "📌 Выберите тип точки:",
        reply_markup=point_type_keyboard(point_types),
    )


def point_type_keyboard(point_types: list[dict]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=point_type["name"],
                callback_data=f"add_point_type:{point_type['id']}",
            )
        ] for point_type in point_types]
    )


@dp.callback_query(StateFilter(AddPoint.point_type), F.data.startswith("add_point_type:"))
async def add_point_type(callback, state: FSMContext):
    type_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    point_type = data.get("point_types", {}).get(type_id)
    if point_type is None:
        await callback.answer("Тип точки устарел. Начните добавление заново.", show_alert=True)
        return

    await state.update_data(point_type=point_type)
    await state.set_state(AddPoint.title)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("📝 Введите название точки:", reply_markup=ReplyKeyboardRemove())


@dp.message(StateFilter(AddPoint.title))
async def add_point_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название должно быть непустым текстом. Попробуйте ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(AddPoint.description)
    await message.answer(
        "📝 Введите описание точки или нажмите «Пропустить»:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )


@dp.message(StateFilter(AddPoint.description), F.text.lower() == "пропустить")
async def add_point_skip_description(message: Message, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(AddPoint.location)
    await message.answer(
        "📍 Теперь отправьте геолокацию точки "
        "(Скрепка → Геопозиция), можно с обычного места на карте.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(StateFilter(AddPoint.description))
async def add_point_description(message: Message, state: FSMContext):
    description = (message.text or "").strip()
    if not description:
        await message.answer("Описание должно быть текстом или нажмите «Пропустить».")
        return
    await state.update_data(description=description)
    await state.set_state(AddPoint.location)
    await message.answer(
        "📍 Теперь отправьте геолокацию точки "
        "(Скрепка → Геопозиция), можно с обычного места на карте.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(StateFilter(AddPoint.location), F.location)
async def add_point_location(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(
        lat=message.location.latitude,
        lng=message.location.longitude,
    )
    await state.set_state(AddPoint.photo)
    await message.answer(
        "✅ Геолокация получена.\n📷 Теперь пришлите фото точки — она сохранится вместе с ним."
    )


@dp.message(StateFilter(AddPoint.location))
async def add_point_location_invalid(message: Message):
    await message.answer("Нужно отправить именно геолокацию (Скрепка → Геопозиция).")


@dp.message(StateFilter(AddPoint.photo), F.photo)
async def add_point_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > 10 * 1024 * 1024:
        await message.answer("вљ пёЏ Р¤РѕС‚Рѕ РЅРµ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ Р±РѕР»СЊС€Рµ 10 РњР‘. РџСЂРёС€Р»РёС‚Рµ С„РѕС‚Рѕ РјРµРЅСЊС€Рµ.")
        return
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    try:
        point = await api_client.create_point(
            title=data["title"],
            description=data.get("description"),
            lat=data["lat"],
            lng=data["lng"],
            telegram_user_id=message.from_user.id,
            username=message.from_user.username or message.from_user.full_name,
            point_type=data["point_type"],
            photo_bytes=file_bytes.read(),
            filename=f"{photo.file_id}.jpg",
        )
        if point.get("forbidden"):
            await message.answer(
                f"⚠️ {point['detail']}",
                reply_markup=await profile_keyboard(message.from_user.id),
            )
            await state.clear()
            return
    except Exception:
        logger.exception("Не удалось сохранить точку с фото")
        await message.answer("⚠️ Не удалось сохранить точку. Пришлите фото ещё раз.")
        return

    await state.clear()
    await message.answer(
        "✅ Готово. Точка сохранена и появится на карте.",
        reply_markup=await profile_keyboard(message.from_user.id),
    )


@dp.message(StateFilter(AddPoint.photo))
async def add_point_photo_invalid(message: Message):
    await message.answer("Пришлите фото точки.")


POINTS_COMMON_BUTTON = "🌍 Общие"
POINTS_PERSONAL_BUTTON = "🗺 Мои"
POINTS_BACK_BUTTON = "⬅️ Назад"


def points_scope_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=POINTS_PERSONAL_BUTTON),
                KeyboardButton(text=POINTS_COMMON_BUTTON),
            ],
            [KeyboardButton(text=POINTS_BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


@dp.message(F.text == "📍 Список точек")
async def points_list(message: Message, state: FSMContext):
    await state.set_state(PointsList.scope)
    await message.answer(
        "📍 Какой список точек открыть?",
        reply_markup=points_scope_keyboard(),
    )


async def send_points_list(message: Message, scope: str, telegram_user_id: int | None = None):
    points = await api_client.list_points(scope=scope, telegram_user_id=telegram_user_id)

    buttons = []

    for point in points:
        buttons.append([
            InlineKeyboardButton(
                text=point["title"],
                callback_data=f"point:{point['id']}"
            )
        ])

    await message.answer(
        "📍 Выберите точку:" if points else "📍 В этом списке пока нет точек.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.message(StateFilter(PointsList.scope), F.text == POINTS_COMMON_BUTTON)
async def common_points_list(message: Message):
    try:
        await send_points_list(message, "common")
    except Exception:
        logger.exception("Не удалось загрузить общие точки")
        await message.answer("⚠️ Не удалось загрузить список точек.")


@dp.message(StateFilter(PointsList.scope), F.text == POINTS_PERSONAL_BUTTON)
async def personal_points_list(message: Message):
    try:
        profile = await api_client.get_telegram_profile(message.from_user.id)
        if not profile or profile.get("role") == "new_member":
            await message.answer("Личные точки пока недоступны для вашей роли.")
            return
        await send_points_list(
            message,
            "personal",
            telegram_user_id=message.from_user.id,
        )
    except Exception:
        logger.exception("Не удалось загрузить личные точки")
        await message.answer("⚠️ Не удалось загрузить личные точки.")


@dp.message(StateFilter(PointsList.scope), F.text == POINTS_BACK_BUTTON)
async def points_list_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Главное меню.",
        reply_markup=await profile_keyboard(message.from_user.id),
    )


def point_vote_keyboard(point_id: str, likes: int, dislikes: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"❤️ ({likes})",
            callback_data=f"vote:like:{point_id}"
        ),
        InlineKeyboardButton(
            text=f"👎 ({dislikes})",
            callback_data=f"vote:dislike:{point_id}"
        ),
    ]])


@dp.callback_query(F.data.startswith("point:"))
async def point_info(callback):
    point_id = callback.data.split(":")[1]

    try:
        point = await api_client.get_point(point_id, callback.from_user.id)
    except Exception:
        logger.exception("Не удалось загрузить точку %s", point_id)
        await callback.answer("Точка недоступна или была скрыта.", show_alert=True)
        return

    text = f"""
                📍 <b>{escape(str(point['title']))}</b>
                📝 {escape(str(point.get('description') or '—'))}
                🌍 Координаты: <code>{point['lat']}, {point['lng']}</code>
            """

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=point_vote_keyboard(point_id, point['likes'], point['dislikes']),
    )

    if point.get("photo_url"):
        await callback.message.answer_photo(
            point["photo_url"],
            caption="📷 Фото точки"
        )

    await callback.answer()


@dp.callback_query(F.data.startswith("vote:"))
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
    # Обновляем счётчики в уже отправленном сообщении точки.
    message_text = callback.message.text or ""
    message_text = re.sub(
        r"\U00002764\ufe0f\s*\d+",
        f"\u2764\ufe0f {result['likes']}",
        message_text,
    )
    message_text = re.sub(
        r"\U0001f44e\s*\d+",
        f"\U0001f44e {result['dislikes']}",
        message_text,
    )
    await callback.message.edit_text(
        message_text,
        parse_mode="HTML",
        reply_markup=point_vote_keyboard(point_id, result["likes"], result["dislikes"]),
    )
    await callback.answer("Ваш голос учтён!")


async def main():
    logger.info("🚀 GeoMapBot запущен")
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Карта",
            web_app=WebAppInfo(url=config.WEBAPP_URL),
        ),
    )
    notifications_task = asyncio.create_task(notification_loop())
    try:
        await dp.start_polling(bot)
    finally:
        notifications_task.cancel()
        await asyncio.gather(notifications_task, return_exceptions=True)
        await api_client.close()
        await dp.storage.close()


if __name__ == "__main__":
    asyncio.run(main())
