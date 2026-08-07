# Локальный запуск GeoMapBot

Пошаговая инструкция для проверки на своей машине, без хостинга и домена.
Обновлено под текущий `docker-compose.yml`: свой собственный MinIO
(сервис `geomap_minio`), без nginx (карта отдаётся тем же контейнером,
что и API), один общий `.env` в корне проекта для backend и бота.

## 0. Что понадобится

- Docker + Docker Compose
- Токен бота от [@BotFather](https://t.me/BotFather)
- [ngrok](https://ngrok.com/download) — для публичного https-адреса под Telegram WebApp
  (можно пропустить, если пока не тестируете карту — см. п.8)

---

## 1. Подготовить `.env` в корне проекта

Один файл `.env` рядом с `docker-compose.yml` — его читают и backend, и
бот, и MinIO (через `env_file: ./.env` у каждого сервиса).

```env
# --- Django backend ---
APP_ENV=development
SECRET_KEY=local-dev-secret
DEBUG=true
ALLOWED_HOSTS=*

# --- Postgres ---
POSTGRES_DB=geomap
POSTGRES_USER=geomap
POSTGRES_PASS=geomap
POSTGRES_HOST=geomap-db
POSTGRES_PORT=5432

# --- MinIO (свой, поднимается тем же docker-compose) ---
MINIO_ROOT_USER=geomap_admin
MINIO_ROOT_PASSWORD=придумайте_надёжный_пароль
MINIO_ENDPOINT=geomap-minio:9000
MINIO_EXTERNAL_ENDPOINT=localhost:9010
MINIO_HTTPS=false
MINIO_EXTERNAL_HTTPS=false
MINIO_REGION=us-east-1
MINIO_STORAGE_ACCESS_KEY=geomap_admin
MINIO_STORAGE_SECRET_KEY=придумайте_надёжный_пароль

# --- Бот <-> backend ---
BOT_API_KEY=local-dev-key

# --- Бот ---
BOT_TOKEN=<токен от BotFather>
# внутри docker-сети бот стучится к backend по имени сервиса, не localhost
BACKEND_URL=http://geomap-backend:8010
WEBAPP_URL=https://example.com
ADMIN_ID=0
```

`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` и
`MINIO_STORAGE_ACCESS_KEY`/`MINIO_STORAGE_SECRET_KEY` здесь совпадают —
этого достаточно для локального теста. Отдельный ограниченный ключ можно
создать позже через консоль (п.4).

`WEBAPP_URL` заполним в п.8, когда поднимется ngrok.

---

## 2. Поднять базу и свой MinIO

```bash
docker compose up -d geomap-db geomap-minio geomap-redis
```

Подождите ~10 секунд, пока пройдут healthcheck'и:

```bash
docker compose ps
```

Оба сервиса должны быть `healthy`.

---

## 3. Собрать и поднять backend

```bash
docker compose up -d --build geomap-backend
```

При старте контейнер сам выполнит `migrate`, а `django-minio-backend`
(при `MINIO_CONSISTENCY_CHECK_ON_START: True` в `settings.py`) сам создаст
бакет `geomap-media` в вашем MinIO. Проверьте логи:

```bash
docker compose logs -f geomap-backend
```

Должно быть видно `Starting gunicorn` без ошибок подключения к БД/MinIO.
Остановите просмотр логов `Ctrl+C` (сам контейнер продолжит работать).

Проверка, что API отвечает:

```bash
curl http://localhost:8010/api/points/
```

Ожидаемый ответ — пустой список: `{"count":0,"next":null,"previous":null,"results":[]}`

---

## 4. (Опционально) Отдельный access key для MinIO

Если не хотите использовать root-креды напрямую:

1. Откройте консоль MinIO: **http://localhost:9011**
2. Войдите как `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` из `.env`
3. Слева **Access Keys → Create access key**
4. Скопируйте `Access Key` / `Secret Key` в `.env` вместо
   `MINIO_STORAGE_ACCESS_KEY` / `MINIO_STORAGE_SECRET_KEY` и пересоберите backend:

```bash
docker compose up -d --build geomap-backend
```

---

## 5. Создать суперпользователя для админки

```bash
docker exec -it geomap_backend python manage.py createsuperuser
```

Админка доступна на **http://localhost:8010/admin/** — там же видны все
созданные точки, можно смотреть/чистить руками во время тестов.

---

## 6. Проверить WebApp

Основная карта находится в React-приложении `webapp/`. В Docker она доступна
по адресу **http://localhost:8080/geomap/**. Для standalone-разработки:

```bash
cd webapp
npm ci
npm run dev
```

Проверьте `VITE_MAP_STYLE_URL`: JSON style должен быть доступен из браузера и
разрешать CORS. Точки загружаются через `/api/points/` и `/ws/points/`.

---

## 7. Поднять бота

```bash
docker compose up -d --build geomap-bot
docker compose logs -f geomap-bot
```

Должно появиться `🚀 GeoMapBot запущен`.

---

## 8. Публичный https-адрес для карты (WebApp)

Telegram открывает WebApp только по `https`, поэтому нужен туннель до
вашего `localhost:8010`.

```bash
ngrok http 8080
```

В выводе будет строка вида:

```
Forwarding  https://a1b2c3d4.ngrok-free.app -> http://localhost:8080
```

Скопируйте `https://a1b2c3d4.ngrok-free.app` в `.env`:

```env
WEBAPP_URL=https://a1b2c3d4.ngrok-free.app/geomap/
```

Пересоберите бота, чтобы новый `WEBAPP_URL` подхватился:

```bash
   docker compose up -d --build geomap-bot
```

**Важно:** ngrok-адрес меняется при каждом перезапуске (на бесплатном
тарифе) — после рестарта туннеля нужно обновлять `WEBAPP_URL` и
пересобирать бота заново.

### Фото и ngrok

По умолчанию `photo_url` строится из `MINIO_EXTERNAL_ENDPOINT=localhost:9010`
— это доступно только вам самим, но не телефону, который открывает карту
через ngrok. Если нужно проверить фото именно через Telegram WebApp:

1. Поднимите второй туннель для MinIO:
   ```bash
   ngrok http 9010
   ```
   (на бесплатном тарифе может понадобиться `ngrok.yml` с несколькими
   туннелями либо платный план — по умолчанию разрешён один туннель).
2. Впишите полученный домен в `.env`:
   ```env
   MINIO_EXTERNAL_ENDPOINT=xxxx.ngrok-free.app
   MINIO_EXTERNAL_HTTPS=true
   ```
3. Пересоберите backend:
   ```bash
   docker compose up -d --build geomap-backend
   ```

Если фото сейчас не критично для теста — проще пропустить этот раздел и
проверять точки с фото только локально через админку
(`http://localhost:8010/admin/points/point/`), а через Telegram/ngrok
тестировать только карту и создание точек без фото.

---

## 9. Проверка в Telegram

1. Найдите своего бота в Telegram, нажмите **/start**
2. **➕ Добавить точку** → выберите тип → введите название → введите описание или
   нажмите «Пропустить» → отправьте геолокацию (📎 → Геопозиция) → отправьте фото
3. Проверьте, что точка появилась:
   - в админке: http://localhost:8010/admin/points/point/
   - через API: `curl http://localhost:8010/api/points/`
4. Пользователь с ролью `admin` или `superuser` увидит кнопку **⚙️ Админка**.
   В ней доступны пользователи, типы точек, точки и голоса; ссылка на Django
   Admin для этого сценария не используется.
5. **🗺 Карта** (если настроен ngrok) — должна открыться карта с меткой

Уведомления отправляются фоновым процессом бота. После применения миграций
перезапустите backend и bot, чтобы он начал забирать очередь уведомлений:
уведомление о доступе к точке получают все зарегистрированные пользователи,
кроме `new_member`.

```bash
docker compose up -d --build geomap-backend geomap-bot
```

---

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| Бот не отвечает | Проверьте `BOT_TOKEN`, посмотрите `docker compose logs geomap-bot` |
| `❌ Не удалось добавить точку` | Проверьте `docker compose logs geomap-backend`. Т.к. `.env` теперь один и общий, несовпадения `BOT_API_KEY` быть не должно — но после изменения `.env` нужен рестарт обоих: `docker compose up -d --build geomap-backend geomap-bot` |
| Бот не может достучаться до backend | `BACKEND_URL` в `.env` должен быть `http://geomap-backend:8010` (имя docker-сервиса), а не `http://localhost:8010` — изнутри контейнера `localhost` указывает на сам контейнер бота, а не на backend |
| На карте нет точек, хотя в API они есть | Проверьте `/api/points/`, состояние WebSocket и `VITE_API_URL`; при недоступном WebSocket должен работать HTTP fallback |
| Кнопка «Карта» не открывается / белый экран | `WEBAPP_URL` не https, ngrok-туннель уже не активен, либо не пересобирали бота после смены `WEBAPP_URL` |
| На карте нет тайлов (пустой фон) | Проверьте доступность `VITE_MAP_STYLE_URL` из браузера Telegram и CORS для style/sprite/glyphs |
| Фото не открывается по `photo_url` | `MINIO_EXTERNAL_ENDPOINT` должен быть доступен из браузера, который открывает карту. `localhost:9010` подходит только если сами открываете карту с этой же машины; при доступе через ngrok нужен отдельный туннель для MinIO (см. раздел «Фото и ngrok») |
| Backend падает с ошибкой "bucket does not exist" | Проверьте, что в `settings.py` стоит `MINIO_CONSISTENCY_CHECK_ON_START: True`, и что `geomap_minio` был healthy до старта `geomap_backend` |
| После смены `.env` ничего не поменялось | `env_file` подхватывается только при пересоздании контейнера — `docker compose restart` не перечитывает `.env`, нужен `docker compose up -d --build <сервис>` |

---

## Полная остановка / чистый перезапуск

```bash
docker compose down          # остановить всё
docker compose down -v       # + удалить volumes (полностью чистая БД и MinIO)
```
