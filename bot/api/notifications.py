from .client import HEADERS, client_context


async def get_pending_notifications() -> list[dict]:
    async with client_context() as client:
        response = await client.get("/api/bot/notifications/", headers=HEADERS)
        response.raise_for_status()
        return response.json()


async def acknowledge_notifications(notification_ids: list[int]) -> None:
    if not notification_ids:
        return
    async with client_context() as client:
        response = await client.post(
            "/api/bot/notifications/ack/",
            headers=HEADERS,
            json={"ids": notification_ids},
        )
        response.raise_for_status()
