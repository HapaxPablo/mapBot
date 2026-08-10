from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

import api_client
from keyboards.common import main_keyboard
from keyboards.points import point_type_keyboard, points_scope_keyboard
from runtime import (
    POINTS_BACK_BUTTON,
    POINTS_COMMON_BUTTON,
    POINTS_PERSONAL_BUTTON,
    bot,
    logger,
)
from services.access import profile_keyboard
from states import AddPoint, PointsList


router = Router()


@router.message(F.text == "➕ Добавить точку")
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
    await message.answer("📌 Выберите тип точки:", reply_markup=point_type_keyboard(point_types))


@router.callback_query(StateFilter(AddPoint.point_type), F.data.startswith("add_point_type:"))
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
    await callback.message.answer(
        "📄 Введите название точки:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(StateFilter(AddPoint.title))
async def add_point_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название должно быть непустым текстом. Попробуйте ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(AddPoint.description)
    await message.answer(
        "📄 Введите описание точки или нажмите «Пропустить»:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )


@router.message(StateFilter(AddPoint.description), F.text.lower() == "пропустить")
async def add_point_skip_description(message: Message, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(AddPoint.location)
    await message.answer(
        "📍 Теперь отправьте геолокацию точки "
        "(Скрепка → Геопозиция), можно с обычного места на карте.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(StateFilter(AddPoint.description))
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


@router.message(StateFilter(AddPoint.location), F.location)
async def add_point_location(message: Message, state: FSMContext):
    await state.update_data(
        lat=message.location.latitude,
        lng=message.location.longitude,
    )
    await state.set_state(AddPoint.photo)
    await message.answer(
        "✅ Геолокация получена.\n📷 Теперь пришлите фото точки — "
        "оно сохранится вместе с ней."
    )


@router.message(StateFilter(AddPoint.location))
async def add_point_location_invalid(message: Message):
    await message.answer("Нужно отправить именно геолокацию (Скрепка → Геопозиция).")


@router.message(StateFilter(AddPoint.photo), F.photo)
async def add_point_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > 10 * 1024 * 1024:
        await message.answer("⚠️ Фото не должно быть больше 10 МБ. Пришлите фото меньшего размера.")
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


@router.message(StateFilter(AddPoint.photo))
async def add_point_photo_invalid(message: Message):
    await message.answer("Пришлите фото точки.")


@router.message(F.text == "📍 Список точек")
async def points_list(message: Message, state: FSMContext):
    await state.set_state(PointsList.scope)
    await message.answer(
        "📍 Какой список точек открыть?",
        reply_markup=points_scope_keyboard(),
    )


async def send_points_list(message: Message, scope: str, telegram_user_id: int | None = None):
    points = await api_client.list_points(scope=scope, telegram_user_id=telegram_user_id)
    buttons = [[
        InlineKeyboardButton(
            text=point["title"],
            callback_data=f"point:{point['id']}",
        )
    ] for point in points]

    await message.answer(
        "📍 Выберите точку:" if points else "📍 В этом списке пока нет точек.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.message(StateFilter(PointsList.scope), F.text == POINTS_COMMON_BUTTON)
async def common_points_list(message: Message):
    try:
        await send_points_list(message, "common")
    except Exception:
        logger.exception("Не удалось загрузить общие точки")
        await message.answer("⚠️ Не удалось загрузить список точек.")


@router.message(StateFilter(PointsList.scope), F.text == POINTS_PERSONAL_BUTTON)
async def personal_points_list(message: Message):
    try:
        profile = await api_client.get_telegram_profile(message.from_user.id)
        if not profile or profile.get("role") == "new_member":
            await message.answer("Личные точки пока недоступны для вашей роли.")
            return
        await send_points_list(message, "personal", telegram_user_id=message.from_user.id)
    except Exception:
        logger.exception("Не удалось загрузить личные точки")
        await message.answer("⚠️ Не удалось загрузить личные точки.")


@router.message(StateFilter(PointsList.scope), F.text == POINTS_BACK_BUTTON)
async def points_list_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Главное меню.",
        reply_markup=await profile_keyboard(message.from_user.id),
    )
