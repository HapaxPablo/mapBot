"""Компонент Telegram-бота GeoMap."""

from .client import HEADERS, client_context


async def _admin_request(method: str, path: str, telegram_user_id: int, **kwargs):
    """Выполняет операцию компонента Telegram-бота."""
    if method == "GET":
        params = dict(kwargs.pop("params", {}))
        params["telegram_user_id"] = telegram_user_id
        kwargs["params"] = params
    else:
        payload = dict(kwargs.pop("json", {}))
        payload["telegram_user_id"] = telegram_user_id
        kwargs["json"] = payload

    async with client_context() as client:
        response = await client.request(method, path, headers=HEADERS, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        return response.json()


async def admin_list_users(telegram_user_id: int, search: str | None = None) -> list[dict]:
    """Выполняет операцию компонента Telegram-бота."""
    params = {"search": search} if search else {}
    return await _admin_request("GET", "/api/admin/users/", telegram_user_id, params=params)


async def admin_change_user_role(
    telegram_user_id: int,
    target_telegram_id: int,
    role: str,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request(
        "POST",
        f"/api/admin/users/{target_telegram_id}/role/",
        telegram_user_id,
        json={"role": role},
    )


async def admin_list_point_types(telegram_user_id: int) -> list[dict]:
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request("GET", "/api/admin/point-types/", telegram_user_id)


async def admin_create_point_type(
    telegram_user_id: int,
    name: str,
    icon_name: str,
    show_on_main_map: bool,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request(
        "POST",
        "/api/admin/point-types/",
        telegram_user_id,
        json={"name": name, "icon_name": icon_name, "show_on_main_map": show_on_main_map},
    )


async def admin_update_point_type(
    telegram_user_id: int,
    point_type_id: int,
    changes: dict,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request(
        "PATCH",
        f"/api/admin/point-types/{point_type_id}/",
        telegram_user_id,
        json=changes,
    )


async def admin_delete_point_type(telegram_user_id: int, point_type_id: int):
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request(
        "DELETE",
        f"/api/admin/point-types/{point_type_id}/",
        telegram_user_id,
    )


async def admin_list_points(
    telegram_user_id: int,
    search: str | None = None,
    is_active: bool | None = None,
    point_type: str | None = None,
) -> list[dict]:
    """Выполняет операцию компонента Telegram-бота."""
    params = {}
    if search:
        params["search"] = search
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    if point_type:
        params["point_type"] = point_type
    return await _admin_request("GET", "/api/admin/points/", telegram_user_id, params=params)


async def admin_update_point(
    telegram_user_id: int,
    point_id: str,
    changes: dict,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request(
        "PATCH",
        f"/api/admin/points/{point_id}/",
        telegram_user_id,
        json=changes,
    )


async def admin_upload_point_photo(
    telegram_user_id: int,
    point_id: str,
    photo_bytes: bytes,
    filename: str,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        response = await client.post(
            f"/api/admin/points/{point_id}/photo/",
            headers=HEADERS,
            files={"photo": (filename, photo_bytes, "image/jpeg")},
            data={"telegram_user_id": str(telegram_user_id)},
        )
        response.raise_for_status()
        return response.json()


async def admin_list_votes(telegram_user_id: int) -> list[dict]:
    """Выполняет операцию компонента Telegram-бота."""
    return await _admin_request("GET", "/api/admin/votes/", telegram_user_id)
