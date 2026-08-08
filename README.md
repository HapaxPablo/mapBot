# GeoMapBot 2.0

Telegram-бот и Telegram WebApp для добавления геоточек, просмотра их на карте и голосования. Проект состоит из Django API, aiogram-бота и React-приложения на MapLibre.

## Структура проекта

```text
.
├── backend/              # Django API, WebSocket, пользователи и точки
├── bot/                  # Telegram-бот на aiogram 3 и FSM
├── webapp/               # React + MapLibre Telegram WebApp
├── nginx/                # reverse proxy для WebApp, API, WebSocket и фото
├── docker-compose.yml    # локальный стек
└── README.md             # общая и локальная документация
```

Основные сервисы Docker Compose:

| Сервис | Назначение | Локальный адрес |
|---|---|---|
| `geomap-nginx` | единая точка входа | `http://localhost:8080` |
| `geomap-webapp` | собранная карта | `http://localhost:8080/geomap/` |
| `geomap-backend` | Django API и WebSocket | `http://localhost:8010` |
| `geomap-db` | PostgreSQL | только Docker-сеть |
| `geomap-redis` | Redis для Channels и фоновых задач | только Docker-сеть |
| `geomap-minio` | хранилище фотографий | `http://localhost:9010`, консоль `http://localhost:9011` |
| `geomap-bot` | Telegram-бот | — |

## Как это работает

1. Бот собирает данные для точки: тип, название, описание, геолокацию и фотографию.
2. Backend хранит точки в PostgreSQL, фотографии — в приватном бакете MinIO, а для фото выдаёт временные presigned-ссылки.
3. Чтение точек (`GET /api/points/`) открыто для карты. Запись, голосование и загрузка фото защищены `Authorization: Api-Key <BOT_API_KEY>` или Telegram WebApp-аутентификацией.
4. WebApp получает точки по WebSocket `/ws/points/` и использует HTTP fallback через `/api/points/`.
5. Nginx маршрутизирует `/geomap/` в WebApp, `/api/`, `/admin/`, `/static/` и `/ws/` в backend, а `/geomap-media/` — в MinIO.

Пользователи с ролью `admin` или `superuser` получают в боте раздел администрирования: пользователи, типы точек, точки, голоса и уведомления. Django Admin для основного пользовательского сценария не используется.

## Локальный запуск через Docker

### Что понадобится

- Docker с Docker Compose;
- токен Telegram-бота от [@BotFather](https://t.me/BotFather);
- HTTPS-туннель, например [ngrok](https://ngrok.com/download), если нужно открывать WebApp из Telegram.

### 1. Создать `.env`

Создайте файл `.env` в корне проекта рядом с `docker-compose.yml`. Backend, бот, MinIO и WebApp используют этот общий файл.

```env
# Django
APP_ENV=development
SECRET_KEY=local-dev-secret
DEBUG=true
ALLOWED_HOSTS=*
# Для ngrok укажите актуальный домен, например:
# CSRF_TRUSTED_ORIGINS=https://example.ngrok-free.app

# PostgreSQL
POSTGRES_DB=geomap
POSTGRES_USER=geomap
POSTGRES_PASS=geomap
POSTGRES_HOST=geomap-db
POSTGRES_PORT=5432

# MinIO
MINIO_ROOT_USER=geomap_admin
MINIO_ROOT_PASSWORD=придумайте_надёжный_пароль
MINIO_ENDPOINT=geomap-minio:9000
MINIO_EXTERNAL_ENDPOINT=localhost:9010
MINIO_HTTPS=false
MINIO_EXTERNAL_HTTPS=false
MINIO_REGION=us-east-1
MINIO_STORAGE_ACCESS_KEY=geomap_admin
MINIO_STORAGE_SECRET_KEY=придумайте_надёжный_пароль

# Бот ↔ backend
BOT_API_KEY=local-dev-key
BOT_TOKEN=<токен от BotFather>
BACKEND_URL=http://geomap-backend:8010
WEBAPP_URL=https://example.com/geomap/
ADMIN_ID=0

# WebApp. Пустой VITE_API_URL означает текущий origin.
# Для локального запуска через nginx можно оставить пустым.
VITE_API_URL=
VITE_MAP_STYLE_URL=https://example.com/maps/styles/basic/style.json
```

`MINIO_ROOT_PASSWORD` и `MINIO_STORAGE_SECRET_KEY` должны совпадать для простого локального запуска. Позже можно создать отдельный access key в консоли MinIO (`http://localhost:9011`) и заменить только `MINIO_STORAGE_ACCESS_KEY` / `MINIO_STORAGE_SECRET_KEY`.

`VITE_MAP_STYLE_URL` должен быть доступен из браузера Telegram и разрешать CORS для style, sprite и glyphs.

### 2. Запустить инфраструктуру

```bash
docker compose up -d geomap-db geomap-minio geomap-redis
docker compose ps
```

Перед следующим шагом `geomap-db`, `geomap-minio` и `geomap-redis` должны перейти в состояние `healthy`.

### 3. Запустить backend, WebApp и nginx

```bash
docker compose up -d --build geomap-backend geomap-webapp nginx
docker compose logs -f geomap-backend
```

Контейнер backend выполняет миграции и сбор статики при старте. Проверка API:

```bash
curl http://localhost:8010/api/health/
curl http://localhost:8010/api/points/
```

Карта через nginx доступна по адресу `http://localhost:8080/geomap/`. В standalone-режиме WebApp можно запустить отдельно:

```bash
cd webapp
npm ci
npm run dev
```

### 4. Создать суперпользователя

```bash
docker exec -it geomap_backend python manage.py createsuperuser
```

Локальная Django Admin: `http://localhost:8010/admin/`.

### 5. Запустить бота

```bash
docker compose up -d --build geomap-bot
docker compose logs -f geomap-bot
```

После изменения `.env` пересоздавайте затронутые контейнеры через `docker compose up -d --build <сервис>`. Команда `docker compose restart` не перечитывает значения из `env_file`.

## Проверка в Telegram

Без HTTPS Telegram не откроет WebApp. Для локального тестирования:

```bash
ngrok http 8080
```

Скопируйте выданный адрес в `.env`:

```env
WEBAPP_URL=https://a1b2c3d4.ngrok-free.app/geomap/
CSRF_TRUSTED_ORIGINS=https://a1b2c3d4.ngrok-free.app
VITE_API_URL=
```

После этого пересоберите бота и WebApp, чтобы новые переменные попали в контейнеры:

```bash
docker compose up -d --build geomap-bot geomap-webapp nginx
```

Бесплатный адрес ngrok меняется после перезапуска туннеля — при каждой смене обновляйте `WEBAPP_URL` и пересобирайте бота.

Откройте бота и выполните:

1. `/start`;
2. **Добавить точку** → тип → название → описание или «Пропустить» → геолокация → фотография;
3. откройте **Карту**.

### Фотографии через ngrok

При `MINIO_EXTERNAL_ENDPOINT=localhost:9010` фотографии доступны только браузеру на этой же машине. Чтобы Telegram тоже мог их загрузить, поднимите второй туннель:

```bash
ngrok http 9010
```

Затем обновите `.env` и пересоберите backend:

```env
MINIO_EXTERNAL_ENDPOINT=xxxx.ngrok-free.app
MINIO_EXTERNAL_HTTPS=true
```

```bash
docker compose up -d --build geomap-backend
```

На бесплатном тарифе ngrok может потребоваться конфигурация нескольких туннелей или платный тариф.

## Частые проблемы

| Симптом | Что проверить |
|---|---|
| Бот не отвечает | `BOT_TOKEN` и `docker compose logs geomap-bot` |
| Не удаётся добавить точку | одинаковый `BOT_API_KEY` у бота и backend; после изменения `.env` пересоздайте оба сервиса |
| Бот не видит backend | внутри Docker `BACKEND_URL` должен быть `http://geomap-backend:8010`, не `localhost` |
| Карта пустая | `/api/points/`, WebSocket `/ws/points/`, `VITE_API_URL` и доступность `VITE_MAP_STYLE_URL` с CORS |
| Кнопка «Карта» не открывается | `WEBAPP_URL` должен быть HTTPS, содержать `/geomap/`, а бот нужно пересобрать после его изменения |
| Фото не открывается | `MINIO_EXTERNAL_ENDPOINT` должен быть доступен браузеру Telegram; для ngrok нужен отдельный туннель MinIO |
| Ошибка `bucket does not exist` | MinIO должен быть `healthy` до старта backend; при необходимости пересоздайте backend после запуска MinIO |
| Изменения `.env` не применились | используйте `docker compose up -d --build <сервис>`, а не только `docker compose restart` |

## Production перед деплоем

- установить `APP_ENV=production` и `DEBUG=false`;
- задать непредсказуемые `SECRET_KEY` и `BOT_API_KEY`;
- ограничить `ALLOWED_HOSTS` конкретными доменами;
- настроить `CSRF_TRUSTED_ORIGINS` и HTTPS;
- задать production-значения `VITE_MAP_STYLE_URL`, `VITE_API_URL`, `WEBAPP_URL` и внешнего MinIO;
- убедиться, что Redis, PostgreSQL и MinIO доступны backend;
- проверить миграции на копии production-базы.

## Соглашения по коммитам

Формат сообщения:

```text
<тип>[(контекст)]: <краткое описание>
```

Основные типы: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, `wip`. Описание начинается со строчной буквы, формулируется как продолжение фразы «после применения этого коммита будет…», не длиннее 72 символов и без точки в конце. Несовместимые изменения помечаются `!` после типа/контекста или отдельной строкой `BREAKING CHANGE:`.

