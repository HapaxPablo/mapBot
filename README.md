# GeoMapBot 2.0 — структура

```
geomap/
├── docker-compose.yml        # geomap_db + geomap_backend + geomap_bot
├── backend/                  # Django-сервис (по образцу rmc_rest_api)
│   ├── geomap_api/settings.py, urls.py, wsgi.py
│   ├── points/                # модель Point (title, lat, lng, photo в MinIO, likes/dislikes)
│   │   ├── models.py serializers.py permissions.py views.py urls.py admin.py
│   │   └── migrations/0001_initial.py   ← уже сгенерирована и проверена
│   ├── static/map.html        # Telegram WebApp: Leaflet-карта поверх tileserver-gl
│   ├── api_helpers.py         # presigned-ссылки MinIO (как File.url в rmc_rest_api)
│   ├── requirements.txt / Dockerfile / .env.example
└── bot/                       # aiogram 3, FSM
    ├── bot.py config.py api_client.py
    └── requirements.txt / Dockerfile / .env.example
```

## Как это работает

1. **Бэкенд** — отдельный Django-проект (не залезает в модели `brands` из
   основного rmc_rest_api, чтобы не путать «бренды» рекламодателей с точками
   на карте). Модель `Point`: `title`, `lat`, `lng`, `photo` (MinIO,
   presigned-ссылка на 7 дней — как у `File.url`), `likes`/`dislikes`,
   `telegram_user_id`, мягкое удаление через `is_active`.
2. **Запись** (создание точки, лайк/дизлайк, фото) защищена заголовком
   `Authorization: Api-Key <BOT_API_KEY>` — это делает только бот.
   **Чтение** (`GET /api/points/`) открыто всем — карта в WebApp дёргает его
   напрямую из браузера Telegram без авторизации.
3. **Бот** (aiogram 3, FSM): кнопка «➕ Добавить точку» → заголовок → геолокация
   → опциональное фото. Кнопка «🗺 Карта» — это `WebAppInfo`, открывающая
   `static/map.html` прямо внутри Telegram.
4. **Карта** — Leaflet, тайлы берутся с уже поднятого `tileserver` из
   `prod.yml` (`https://api1.krasrm.com/maps/...`), маркеры — из
   `GET /api/points/`.

## Что нужно проверить/поправить перед деплоем

- **Точный URL тайлов**. `tileserver-gl` отдаёт растровые тайлы вида
  `/styles/<имя_стиля>/{z}/{x}/{y}.png`. Имя стиля зависит от конфига
  `maptiler/tileserver-gl` (`--file siberian-fed-district.mbtiles`) — зайдите
  на `https://api1.krasrm.com/maps/` и посмотрите список стилей/эндпоинтов,
  затем поправьте `TILE_STYLE` в `backend/static/map.html`. Если сервер отдаёт
  только векторные тайлы — потребуется MapLibre GL JS вместо Leaflet
  (raster-подложка проще для WebApp, поэтому взял её по умолчанию).
- **Имя docker-сети** в `docker-compose.yml` (`rmc_rest_api_default`) — нужно
  подставить реальное имя сети из `docker compose ls`/`docker network ls` у
  основного проекта, чтобы `geomap_backend` мог достучаться до MinIO
  (`files:9000`) и, если нужно, до `gateway`.
- **MinIO**: бэкенд переиспользует тот же инстанс, что и rmc_rest_api
  (бакет `geomap-media` создастся сам при первой загрузке фото — либо
  добавьте создание бакета так же, как `files/minio_setup.py` в основном
  проекте).
- **Домен/nginx**: сейчас `geomap_backend` слушает `8010` напрямую и `map.html`
  отдаётся как статика того же контейнера (`/static/map.html`). Для прод —
  either добавить `location /geomap/` в `nginx/nginx.conf`, либо поднять
  отдельный домен (`geomap.krasrm.com`), выставленный в `.env.example`.
- Миграция `points/migrations/0001_initial.py` сгенерирована и синтаксически
  проверена (`makemigrations` + `py_compile`), но не прогонялась на реальной
  БД/MinIO — сделайте это перед первым релизом.

## Запуск локально (без Docker)

```bash
cd backend
cp .env.example .env   # заполнить MinIO/Postgres
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8010

cd ../bot
cp .env.example .env   # заполнить BOT_TOKEN и BOT_API_KEY (тот же, что в backend/.env)
pip install -r requirements.txt
python bot.py
```
