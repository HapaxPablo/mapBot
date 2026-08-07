import asyncio

import httpx

import config

_headers = {"Authorization": f"Api-Key {config.BOT_API_KEY}"}
_client: httpx.AsyncClient | None = None


class RetryingAsyncClient(httpx.AsyncClient):
    async def request(self, method, url, *args, **kwargs):
        method = method.upper()
        attempts = 3 if method == 'GET' else 1
        for attempt in range(attempts):
            try:
                response = await super().request(method, url, *args, **kwargs)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 >= attempts:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            if response.status_code not in {502, 503, 504} or attempt + 1 >= attempts:
                return response
            await asyncio.sleep(0.5 * (attempt + 1))
        raise RuntimeError('HTTP request retry loop exited unexpectedly.')


def _get_client() -> RetryingAsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = RetryingAsyncClient(
            base_url=config.BACKEND_URL,
            timeout=30,
        )
    return _client


class _ClientContext:
    async def __aenter__(self):
        return _get_client()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


def _client_context():
    return _ClientContext()


async def close():
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


async def authenticate_telegram_user(telegram_id: int, username: str | None,
                                     first_name: str | None, last_name: str | None) -> dict:
    async with _client_context() as client:
        resp = await client.post(
            "/api/auth/telegram/",
            headers=_headers,
            json={
                "telegram_id": telegram_id,
                "username": username or "",
                "first_name": first_name or "",
                "last_name": last_name or "",
            },
        )
        if resp.status_code == 409:
            return {"already_registered": True}
        resp.raise_for_status()
        return resp.json()


async def create_point(title: str, lat: float, lng: float,
                        telegram_user_id: int, username: str | None,
                        description: str | None = None,
                        point_type: str | None = None,
                        photo_bytes: bytes | None = None,
                        filename: str = 'point.jpg') -> dict:
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

    async with _client_context() as client:
        request_kwargs = {'headers': _headers}
        if photo_bytes is None:
            request_kwargs['json'] = payload
        else:
            request_kwargs['data'] = payload
            request_kwargs['files'] = {
                'photo': (filename, photo_bytes, 'image/jpeg'),
            }
        resp = await client.post("/api/points/", **request_kwargs)
        if resp.status_code == 403:
            try:
                detail = resp.json().get("detail", "Недостаточно прав для создания точки.")
            except ValueError:
                detail = "Недостаточно прав для создания точки."
            return {"forbidden": True, "detail": detail}
        resp.raise_for_status()
        return resp.json()


async def list_point_types() -> list[dict]:
    async with _client_context() as client:
        resp = await client.get("/api/point-types/")
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data) if isinstance(data, dict) else data


async def get_telegram_profile(telegram_user_id: int) -> dict | None:
    async with _client_context() as client:
        resp = await client.get(
            "/api/auth/telegram/profile/",
            headers=_headers,
            params={"telegram_user_id": telegram_user_id},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


async def get_pending_notifications() -> list[dict]:
    async with _client_context() as client:
        resp = await client.get("/api/bot/notifications/", headers=_headers)
        resp.raise_for_status()
        return resp.json()


async def acknowledge_notifications(notification_ids: list[int]) -> None:
    if not notification_ids:
        return
    async with _client_context() as client:
        resp = await client.post(
            "/api/bot/notifications/ack/",
            headers=_headers,
            json={"ids": notification_ids},
        )
        resp.raise_for_status()


async def _admin_request(method: str, path: str, telegram_user_id: int, **kwargs):
    if method == "GET":
        params = dict(kwargs.pop("params", {}))
        params["telegram_user_id"] = telegram_user_id
        kwargs["params"] = params
    else:
        payload = dict(kwargs.pop("json", {}))
        payload["telegram_user_id"] = telegram_user_id
        kwargs["json"] = payload

    async with _client_context() as client:
        resp = await client.request(method, path, headers=_headers, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()


async def admin_list_users(telegram_user_id: int, search: str | None = None) -> list[dict]:
    params = {"search": search} if search else {}
    return await _admin_request("GET", "/api/admin/users/", telegram_user_id, params=params)


async def admin_change_user_role(
        telegram_user_id: int, target_telegram_id: int, role: str) -> dict:
    return await _admin_request(
        "POST",
        f"/api/admin/users/{target_telegram_id}/role/",
        telegram_user_id,
        json={"role": role},
    )


async def admin_list_point_types(telegram_user_id: int) -> list[dict]:
    return await _admin_request("GET", "/api/admin/point-types/", telegram_user_id)


async def admin_create_point_type(
        telegram_user_id: int, name: str, icon_name: str, show_on_main_map: bool) -> dict:
    return await _admin_request(
        "POST",
        "/api/admin/point-types/",
        telegram_user_id,
        json={
            "name": name,
            "icon_name": icon_name,
            "show_on_main_map": show_on_main_map,
        },
    )


async def admin_update_point_type(
        telegram_user_id: int, point_type_id: int, changes: dict) -> dict:
    return await _admin_request(
        "PATCH",
        f"/api/admin/point-types/{point_type_id}/",
        telegram_user_id,
        json=changes,
    )


async def admin_delete_point_type(telegram_user_id: int, point_type_id: int):
    return await _admin_request(
        "DELETE",
        f"/api/admin/point-types/{point_type_id}/",
        telegram_user_id,
    )


async def admin_list_points(
        telegram_user_id: int, search: str | None = None,
        is_active: bool | None = None, point_type: str | None = None) -> list[dict]:
    params = {}
    if search:
        params["search"] = search
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    if point_type:
        params["point_type"] = point_type
    return await _admin_request("GET", "/api/admin/points/", telegram_user_id, params=params)


async def admin_update_point(
        telegram_user_id: int, point_id: str, changes: dict) -> dict:
    return await _admin_request(
        "PATCH",
        f"/api/admin/points/{point_id}/",
        telegram_user_id,
        json=changes,
    )


async def admin_upload_point_photo(
        telegram_user_id: int, point_id: str, photo_bytes: bytes, filename: str) -> dict:
    async with _client_context() as client:
        resp = await client.post(
            f"/api/admin/points/{point_id}/photo/",
            headers=_headers,
            files={"photo": (filename, photo_bytes, "image/jpeg")},
            data={"telegram_user_id": str(telegram_user_id)},
        )
        resp.raise_for_status()
        return resp.json()


async def admin_list_votes(telegram_user_id: int) -> list[dict]:
    return await _admin_request("GET", "/api/admin/votes/", telegram_user_id)


async def upload_photo(point_id: str, photo_bytes: bytes, filename: str,
                       telegram_user_id: int) -> dict:
    async with _client_context() as client:
        resp = await client.post(
            f"/api/points/{point_id}/photo/",
            headers=_headers,
            files={"photo": (filename, photo_bytes, "image/jpeg")},
            data={"telegram_user_id": str(telegram_user_id)},
        )
        resp.raise_for_status()
        return resp.json()


async def list_points(
        scope: str = "common", telegram_user_id: int | None = None) -> list[dict]:
    async with _client_context() as client:
        params = {}
        if scope == "personal":
            params["scope"] = "personal"
            if telegram_user_id is not None:
                params["telegram_user_id"] = telegram_user_id
        resp = await client.get("/api/points/", headers=_headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data)

async def get_point(point_id: str, telegram_user_id: int | None = None):

    async with _client_context() as client:


        params = {}
        if telegram_user_id is not None:
            params['telegram_user_id'] = telegram_user_id
        response = await client.get(
            f"/api/points/{point_id}/",
            headers=_headers,
            params=params,
        )


        response.raise_for_status()


        return response.json()


async def vote(point_id: str, telegram_user_id: int, vote_type: str) -> dict:
    async with _client_context() as client:
        response = await client.post(
            f"/api/points/{point_id}/{vote_type}/",
            headers=_headers,
            json={"telegram_user_id": telegram_user_id},
        )
        if response.status_code == 409:
            return {"already_voted": True}
        response.raise_for_status()
        return response.json()
