"""Компонент Telegram-бота GeoMap."""

from .client import HEADERS, client_context


async def create_point(
    title: str,
    lat: float,
    lng: float,
    telegram_user_id: int,
    username: str | None,
    description: str | None = None,
    point_type: str | None = None,
    photo_bytes: bytes | None = None,
    filename: str = "point.jpg",
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    payload = {
        "title": title,
        "lat": lat,
        "lng": lng,
        "telegram_user_id": telegram_user_id,
        "username": username,
    }
    if description is not None:
        payload["description"] = description
    if point_type is not None:
        payload["point_type"] = point_type

    async with client_context() as client:
        request_kwargs = {"headers": HEADERS}
        if photo_bytes is None:
            request_kwargs["json"] = payload
        else:
            request_kwargs["data"] = payload
            request_kwargs["files"] = {"photo": (filename, photo_bytes, "image/jpeg")}
        response = await client.post("/api/points/", **request_kwargs)
        if response.status_code == 403:
            try:
                detail = response.json().get("detail", "Недостаточно прав для создания точки.")
            except ValueError:
                detail = "Недостаточно прав для создания точки."
            return {"forbidden": True, "detail": detail}
        response.raise_for_status()
        return response.json()

async def list_point_types() -> list[dict]:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        response = await client.get("/api/point-types/")
        response.raise_for_status()
        data = response.json()
        return data.get("results", data) if isinstance(data, dict) else data


async def upload_photo(
    point_id: str,
    photo_bytes: bytes,
    filename: str,
    telegram_user_id: int,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        response = await client.post(
            f"/api/points/{point_id}/photo/",
            headers=HEADERS,
            files={"photo": (filename, photo_bytes, "image/jpeg")},
            data={"telegram_user_id": str(telegram_user_id)},
        )
        response.raise_for_status()
        return response.json()


async def list_points(
    scope: str = "common",
    telegram_user_id: int | None = None,
) -> list[dict]:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        params = {}
        if scope == "personal":
            params["scope"] = "personal"
            if telegram_user_id is not None:
                params["telegram_user_id"] = telegram_user_id
        response = await client.get("/api/points/", headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results", data)


async def get_point(point_id: str, telegram_user_id: int | None = None) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        params = {}
        if telegram_user_id is not None:
            params["telegram_user_id"] = telegram_user_id
        response = await client.get(
            f"/api/points/{point_id}/",
            headers=HEADERS,
            params=params,
        )
        response.raise_for_status()
        return response.json()


async def vote(point_id: str, telegram_user_id: int, vote_type: str) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        response = await client.post(
            f"/api/points/{point_id}/{vote_type}/",
            headers=HEADERS,
            json={"telegram_user_id": telegram_user_id},
        )
        if response.status_code == 409:
            return {"already_voted": True}
        response.raise_for_status()
        return response.json()
