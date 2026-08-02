import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo,
                           InlineKeyboardMarkup, InlineKeyboardButton)

import api_client
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🗺 Карта", web_app=WebAppInfo(url=config.WEBAPP_URL)), ],
        [KeyboardButton(text="📍 Список точек"), KeyboardButton(text="➕ Добавить точку"), ], ], resize_keyboard=True, )


class AddPoint(StatesGroup):
    title = State()
    location = State()
    photo = State()


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("🌍 Добро пожаловать в GeoMapBot!\n\n"
                         "Нажмите «🗺 Карта», чтобы посмотреть точки, "
                         "или «➕ Добавить точку», чтобы отметить новое место.", reply_markup=main_keyboard(), )


@dp.message(F.text == "➕ Добавить точку")
async def add_point_start(message: Message, state: FSMContext):
    await state.set_state(AddPoint.title)
    await message.answer("📝 Введите заголовок точки:", reply_markup=ReplyKeyboardRemove(), )


@dp.message(StateFilter(AddPoint.title))
async def add_point_title(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Заголовок должен быть текстом. Попробуйте ещё раз:")
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AddPoint.location)
    await message.answer("📍 Теперь отправьте геолокацию точки "
                         "(Скрепка → Геопозиция), можно с обычного места на карте.")


@dp.message(StateFilter(AddPoint.location), F.location)
async def add_point_location(message: Message, state: FSMContext):
    data = await state.get_data()
    username = message.from_user.username or message.from_user.full_name

    try:
        point = await api_client.create_point(title=data["title"], lat=message.location.latitude,
            lng=message.location.longitude, telegram_user_id=message.from_user.id, username=username, )
    except Exception:
        logger.exception("Не удалось создать точку")
        await message.answer("⚠️ Не удалось сохранить точку, попробуйте позже.", reply_markup=main_keyboard(), )
        await state.clear()
        return

    await state.update_data(point_id=point["id"])
    await state.set_state(AddPoint.photo)
    await message.answer("✅ Точка сохранена!\n"
                         "📷 Пришлите фото для точки, либо напишите «Пропустить».")


@dp.message(StateFilter(AddPoint.location))
async def add_point_location_invalid(message: Message):
    await message.answer("Нужно отправить именно геолокацию (Скрепка → Геопозиция).")


@dp.message(StateFilter(AddPoint.photo), F.photo)
async def add_point_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    try:
        await api_client.upload_photo(point_id=data["point_id"], photo_bytes=file_bytes.read(),
            filename=f"{photo.file_id}.jpg", )
    except Exception:
        logger.exception("Не удалось загрузить фото")
        await message.answer("⚠️ Точка сохранена, но фото загрузить не удалось.")
    else:
        await message.answer("✅ Фото добавлено!")

    await state.clear()
    await message.answer("Готово. Точка появится на карте.", reply_markup=main_keyboard())


@dp.message(StateFilter(AddPoint.photo), F.text.lower() == "пропустить")
async def add_point_skip_photo(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Готово. Точка появится на карте без фото.", reply_markup=main_keyboard())


@dp.message(StateFilter(AddPoint.photo))
async def add_point_photo_invalid(message: Message):
    await message.answer("Пришлите фото или напишите «Пропустить».")


@dp.message(F.text == "📍 Список точек")
async def points_list(message: Message):
    points = await api_client.list_points()

    buttons = []

    for point in points:
        buttons.append([

            InlineKeyboardButton(

                text=point["title"],

                callback_data=f"point:{point['id']}"

            )

        ])

    await message.answer(

        "📍 Выберите точку:",

        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)

    )


@dp.callback_query(F.data.startswith("point:"))
async def point_info(callback):
    point_id = callback.data.split(":")[1]

    point = await api_client.get_point(point_id)

    text = f"""
                📍 <b>{point['title']}</b>
                
                📝 {point['description']}
                
                🌍 Координаты:
                
                {point['lat']}
                {point['lng']}
                
                ❤️ {point['likes']}
                👎 {point['dislikes']}
            """

    await callback.message.answer(text, parse_mode="HTML")

    if point.get("photo_url"):
        await callback.message.answer_photo(

            point["photo_url"],

            caption="📷 Фото точки"

        )

    await callback.answer()


async def main():
    logger.info("🚀 GeoMapBot запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
