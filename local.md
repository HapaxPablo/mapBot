# Локальный запуск GeoMapBot

Пошаговая инструкция для проверки на своей машине, без хостинга и домена.

## 0. Что понадобится

- Docker + Docker Compose
- Токен бота от [@BotFather](https://t.me/BotFather)
- [ngrok](https://ngrok.com/download) — для публичного https-адреса под Telegram WebApp
  (можно пропустить, если пока не тестируете карту — см. п.7)

---

## 1. Распаковать архив и подготовить `.env`

```bash
cd geomap-bot
cp .env.example .env
```

Откройте `.env` и впишите:

```env
SECRET_KEY=local-dev-secret
DEBUG=true
ALLOWED_HOSTS=*

POSTGRES_DB=geomap
POSTGRES_USER=geomap
POSTGRES_PASS=geomap
POSTGRES_HOST=db
POSTGRES_PORT=5432

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_ENDPOINT=minio:9000
MINIO_EXTERNAL_ENDPOINT=localhost:9000
MINIO_HTTPS=false
MINIO_EXTERNAL_HTTPS=false
MINIO_REGION=us-east-1

BOT_API_KEY=local-dev-key

BOT_TOKEN=<токен от BotFather>
BACKEND_API_URL=http://backend:8000/api
WEBAPP_URL=https://example.com
ADMIN_ID=0
```

`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` и `WEBAPP_URL` заполним чуть позже — сначала нужны сами сервисы.

---

## 2. Поднять базу и MinIO

```bash
docker compose up -d db minio
```

Подождите ~10 секунд, пока пройдут healthcheck'и:

```bash
docker compose ps
```

Оба должны быть `healthy`.

---

## 3. Создать ключ доступа MinIO

1. Откройте консоль MinIO: **http://localhost:9001**
2. Войдите как `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` (`minioadmin` / `minioadmin123`)
3. Слева **Access Keys → Create access key**
4. Скопируйте `Access Key` и `Secret Key` в `.env`:

```env
MINIO_ACCESS_KEY=<полученный access key>
MINIO_SECRET_KEY=<полученный secret key>
```

---

## 4. Собрать и поднять backend

```bash
docker compose up -d --build backend
```

При старте контейнер сам выполнит `migrate`. Проверьте логи:

```bash
docker compose logs -f backend
```

Должно быть видно `Starting gunicorn` без ошибок подключения к БД/MinIO. Остановите просмотр логов `Ctrl+C` (сам контейнер продолжит работать).

Проверка, что API отвечает:

```bash
curl http://localhost:8010/api/points/
```

Ожидаемый ответ — пустой список: `{"count":0,"next":null,"previous":null,"results":[]}`

---

## 5. Создать суперпользователя для админки

```bash
docker exec -it geomap_backend python manage.py createsuperuser
```

Админка будет доступна на **http://localhost:8010/admin/** — там же видны все созданные точки, можно смотреть/чистить руками во время тестов.

---

## 6. Поднять nginx (отдаёт webapp + проксирует `/api`)

```bash
docker compose up -d --build nginx
```

Проверка:

```bash
curl http://localhost:8080/api/points/
```

Должен вернуть то же самое, что и в п.4 — значит проксирование работает.

---

## 7. Публичный https-адрес для карты (WebApp)

Telegram открывает WebApp только по `https`, поэтому нужен туннель до вашего `localhost:8080`.

```bash
ngrok http 8080
```

В выводе будет строка вида:

```
Forwarding  https://a1b2c3d4.ngrok-free.app -> http://localhost:8080
```

Скопируйте `https://a1b2c3d4.ngrok-free.app` в `.env`:

```env
WEBAPP_URL=https://a1b2c3d4.ngrok-free.app
```

**Важно:** ngrok-адрес меняется при каждом перезапуске (на бесплатном тарифе) — после рестарта туннеля нужно обновлять `WEBAPP_URL` и перезапускать бота (п.8).

Если карту пока не тестируете — можно пропустить этот пункт, оставить `WEBAPP_URL` заглушкой и просто не нажимать кнопку «🗺 Карта» (остальной функционал бота работает без неё).

---

## 8. Поднять бота

```bash
docker compose up -d --build bot
docker compose logs -f bot
```

Должно появиться `🚀 GeoMapBot запущен`. Если меняли `WEBAPP_URL` после первого запуска:

```bash
docker compose up -d --build bot
```

---

## 9. Проверка в Telegram

1. Найдите своего бота в Telegram, нажмите **/start**
2. **➕ Добавить точку** → введите название → отправьте геолокацию (📎 → Геопозиция) →
   отправьте фото или напишите «Пропустить»
3. Проверьте, что точка появилась:
   - в админке: http://localhost:8010/admin/points/point/
   - через API: `curl http://localhost:8080/api/points/`
4. **🗺 Карта** (если настроен ngrok) — должна открыться карта с меткой

---

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| Бот не отвечает | Проверьте `BOT_TOKEN`, посмотрите `docker compose logs bot` |
| `❌ Не удалось добавить точку` | Проверьте `docker compose logs backend` — скорее всего не совпадает `BOT_API_KEY` в `.env` (он используется и ботом, и backend'ом из одного файла, но если меняли на лету — нужен рестарт обоих: `docker compose up -d --build backend bot`) |
| Кнопка «Карта» не открывается / белый экран | `WEBAPP_URL` не https, ngrok-туннель уже не активен, либо не пересобирали бота после смены `WEBAPP_URL` |
| На карте нет тайлов (пустой фон) | Это ожидаемо локально — тайлы грузятся с `https://api1.krasrm.com/maps/`, а не с вашей машины. Если и там тайлы не подгружаются — проверьте актуальный `TILESET_ID` в `webapp/index.html` (см. `README.md`) |
| Фото не открывается по `photo_url` | `MINIO_EXTERNAL_ENDPOINT` должен быть адресом, доступным из браузера — `localhost:9000` подходит только если открываете webapp тоже локально; при открытии через ngrok фото с `localhost:9000` браузер пользователя не увидит (это его локальный адрес, не ваш). Для полноценной проверки фото тоже нужно тунелировать MinIO либо временно тестировать без фото |

---

## Полная остановка / чистый перезапуск

```bash
docker compose down          # остановить всё
docker compose down -v       # + удалить volumes (полностью чистая БД и MinIO)
```