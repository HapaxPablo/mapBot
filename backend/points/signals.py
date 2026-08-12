"""Компонент серверной части GeoMap."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from points.models import Point, PointType
from users.models import TelegramProfile
from users.notifications import notify_admins, notify_map_users


logger = logging.getLogger(__name__)


def safe_notify_admins(message):
    """Выполняет операцию серверного компонента GeoMap."""
    try:
        notify_admins(message)
    except Exception:
        logger.exception('Failed to enqueue admin notification')


def safe_notify_map_users(profiles, message):
    """Выполняет операцию серверного компонента GeoMap."""
    try:
        notify_map_users(profiles, message)
    except Exception:
        logger.exception('Failed to enqueue map user notification')


def notify_points_changed():
    """Выполняет операцию серверного компонента GeoMap."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                'points',
                {'type': 'points.changed'},
            )
    except Exception:
        logger.exception('Failed to broadcast point update')


@receiver(post_save, sender=Point)
def point_saved(sender, instance, created, **kwargs):
    """Выполняет операцию серверного компонента GeoMap."""
    transaction.on_commit(notify_points_changed)
    if created:
        message = (
            f"📍 Добавлена точка: «{instance.title}» "
            f"(тип: {instance.point_type.name})."
        )
    else:
        message = f"✏️ Изменена точка: «{instance.title}»."
    transaction.on_commit(lambda: safe_notify_admins(message))


@receiver(pre_save, sender=Point)
def delete_replaced_point_photo(sender, instance, **kwargs):
    """Выполняет операцию серверного компонента GeoMap."""
    if not instance.pk:
        return
    try:
        previous = Point.objects.only('photo').get(pk=instance.pk)
    except Point.DoesNotExist:
        return
    if not previous.photo or previous.photo.name == getattr(instance.photo, 'name', None):
        return

    previous_photo = previous.photo
    transaction.on_commit(lambda: previous_photo.storage.delete(previous_photo.name))


@receiver(m2m_changed, sender=Point.allowed_users.through)
def point_access_changed(action, instance, pk_set, **kwargs):
    """Выполняет операцию серверного компонента GeoMap."""
    transaction.on_commit(notify_points_changed)
    if action in {'post_add', 'post_remove', 'post_clear'}:
        transaction.on_commit(
            lambda: safe_notify_admins(f"✏️ Изменён доступ к точке «{instance.title}».")
        )
    if action == 'post_add' and pk_set:
        profile_ids = tuple(pk_set)
        transaction.on_commit(
            lambda: safe_notify_map_users(
                TelegramProfile.objects.filter(pk__in=profile_ids),
                f"🗺 Вам открыт доступ к точке «{instance.title}».",
            )
        )


@receiver(post_save, sender=PointType)
def point_type_saved(**kwargs):
    """Выполняет операцию серверного компонента GeoMap."""
    transaction.on_commit(notify_points_changed)
