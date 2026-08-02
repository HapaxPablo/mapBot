import httpx

import config

_headers = {"Authorization": f"Api-Key {config.BOT_API_KEY}"}


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
        resp.raise_for_status()
        return resp.json()


async def upload_photo(point_id: str, photo_bytes: bytes, filename: str) -> dict:
    async with httpx.AsyncClient(base_url=config.BACKEND_URL, timeout=30) as client:
        resp = await client.post(
            f"/api/points/{point_id}/photo/",
            headers=_headers,
            files={"photo": (filename, photo_bytes, "image/jpeg")},
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