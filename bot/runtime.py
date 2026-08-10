import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

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

POINTS_COMMON_BUTTON = "🌍 Общие"
POINTS_PERSONAL_BUTTON = "🗺 Мои"
POINTS_BACK_BUTTON = "⬅️ Назад"
