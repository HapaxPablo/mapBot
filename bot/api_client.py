import httpx

import config

_headers = {"Authorization": f"Api-Key {config.BOT_API_KEY}"}


async def authenticate_telegram_user(telegram_id: int, username: str | None,
                                     first_name: str | None, last_name: str | None,
                                     phone_number: str | None = None) -> dict:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=15) as client:
        resp = await client.post(
            "/api/auth/telegram/",
            headers=_headers,
            json={
                "telegram_id": telegram_id,
                "username": username or "",
                "first_name": first_name or "",
                "last_name": last_name or "",
                "phone_number": phone_number or "",
            },
        )
        if resp.status_code == 409:
            return {"already_registered": True}
        resp.raise_for_status()
        return resp.json()


async def create_point(title: str, lat: float, lng: float,
                        telegram_user_id: int, username: str | None) -> dict:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=15) as client:
        resp = await client.post(
            "/api/points/",
            headers=_headers,
            json={
                "title": title,
                "lat": lat,
                "lng": lng,
                "telegram_user_id": telegram_user_id,
                "username": username,
            },
        )
        if resp.status_code == 403:
            try:
                detail = resp.json().get("detail", "Недостаточно прав для создания точки.")
            except ValueError:
                detail = "Недостаточно прав для создания точки."
            return {"forbidden": True, "detail": detail}
        resp.raise_for_status()
        return resp.json()


async def upload_photo(point_id: str, photo_bytes: bytes, filename: str,
                       telegram_user_id: int) -> dict:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=30) as client:
        resp = await client.post(
            f"/api/points/{point_id}/photo/",
            headers=_headers,
            files={"photo": (filename, photo_bytes, "image/jpeg")},
            data={"telegram_user_id": str(telegram_user_id)},
        )
        resp.raise_for_status()
        return resp.json()


async def list_points() -> list[dict]:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=15) as client:
        resp = await client.get("/api/points/")
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data)

async def get_point(point_id: str):

    async with httpx.AsyncClient(
        base_url=config.BACKEND_URL,
        timeout=15
    ) as client:


        response = await client.get(
            f"/api/points/{point_id}/"
        )


        response.raise_for_status()


        return response.json()


async def vote(point_id: str, telegram_user_id: int, vote_type: str) -> dict:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=15) as client:
        response = await client.post(
            f"/api/points/{point_id}/{vote_type}/",
            headers=_headers,
            json={"telegram_user_id": telegram_user_id},
        )
        if response.status_code == 409:
            return {"already_voted": True}
        response.raise_for_status()
        return response.json()
