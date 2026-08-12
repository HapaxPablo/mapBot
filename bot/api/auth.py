"""Компонент Telegram-бота GeoMap."""

from .client import HEADERS, client_context


async def authenticate_telegram_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> dict:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        response = await client.post(
            "/api/auth/telegram/",
            headers=HEADERS,
            json={
                "telegram_id": telegram_id,
                "username": username or "",
                "first_name": first_name or "",
                "last_name": last_name or "",
            },
        )
        if response.status_code == 409:
            return {"already_registered": True}
        response.raise_for_status()
        return response.json()

async def get_telegram_profile(telegram_user_id: int) -> dict | None:
    """Выполняет операцию компонента Telegram-бота."""
    async with client_context() as client:
        response = await client.get(
            "/api/auth/telegram/profile/",
            headers=HEADERS,
            params={"telegram_user_id": telegram_user_id},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
