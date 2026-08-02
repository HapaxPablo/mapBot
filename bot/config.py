import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

TOKEN = os.environ["BOT_TOKEN"]

# URL geomap-бэкенда (points API), поднятого по образцу rmc_rest_api
BACKEND_URL = os.environ.get("BACKEND_URL", "https://geomap.krasrm.com")
BOT_API_KEY = os.environ["BOT_API_KEY"]  # должен совпадать с BOT_API_KEY бэкенда

# Страница карты (Telegram WebApp), см. backend/static/map.html
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://geomap.krasrm.com/geomap/")

ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
