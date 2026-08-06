from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from points.models import Point, PointType


def notify_points_changed():
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            'points',
            {'type': 'points.changed'},
        )


@receiver(post_save, sender=Point)
def point_saved(**kwargs):
    notify_points_changed()


@receiver(m2m_changed, sender=Point.allowed_users.through)
def point_access_changed(**kwargs):
    notify_points_changed()


@receiver(post_save, sender=PointType)
def point_type_saved(**kwargs):
    notify_points_changed()
