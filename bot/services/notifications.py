"""Компонент Telegram-бота GeoMap."""

import asyncio

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import api_client
from runtime import bot, logger


async def notification_loop():
    """Выполняет операцию компонента Telegram-бота."""
    while True:
        try:
            notifications = await api_client.get_pending_notifications()
            sent_ids = []
            for notification in notifications:
                try:
                    await bot.send_message(notification["telegram_id"], notification["message"])
                except TelegramForbiddenError:
                    logger.warning(
                        "Пользователь %s заблокировал бота, уведомление %s удалено",
                        notification["telegram_id"], notification["id"],
                    )
                    sent_ids.append(notification["id"])
                except TelegramBadRequest:
                    logger.warning(
                        "Некорректное уведомление %s для пользователя %s удалено",
                        notification["id"], notification["telegram_id"],
                    )
                    sent_ids.append(notification["id"])
                except Exception:
                    logger.exception(
                        "Не удалось отправить уведомление %s пользователю %s",
                        notification["id"], notification["telegram_id"],
                    )
                else:
                    sent_ids.append(notification["id"])
            await api_client.acknowledge_notifications(sent_ids)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка фоновой отправки уведомлений")
        await asyncio.sleep(5)
