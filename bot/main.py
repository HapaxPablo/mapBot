import asyncio

from aiogram.types import MenuButtonWebApp, WebAppInfo

import api_client
import config
from handlers import admin, common, points, voting
from runtime import bot, dp, logger
from services.notifications import notification_loop


_dispatcher_configured = False


def configure_dispatcher() -> None:
    global _dispatcher_configured
    if _dispatcher_configured:
        return
    dp.include_router(common.router)
    dp.include_router(points.router)
    dp.include_router(voting.router)
    dp.include_router(admin.router)
    _dispatcher_configured = True


async def main():
    configure_dispatcher()
    logger.info("🚀 GeoMapBot запущен")
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Карта",
            web_app=WebAppInfo(url=config.WEBAPP_URL),
        ),
    )
    notifications_task = asyncio.create_task(notification_loop())
    try:
        await dp.start_polling(bot)
    finally:
        notifications_task.cancel()
        await asyncio.gather(notifications_task, return_exceptions=True)
        await api_client.close()
        await dp.storage.close()


if __name__ == "__main__":
    asyncio.run(main())
