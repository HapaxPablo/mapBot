import uuid
from datetime import timedelta as td

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django_minio_backend import MinioBackend


def photo_path(instance, filename):
    return f'points/{instance.id}/{filename}'


class Point(models.Model):
    """Метка на карте, добавленная через Telegram-бота."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
        verbose_name='Идентификатор',
    )
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    point_type = models.ForeignKey(
        'points.PointType', on_delete=models.PROTECT,
        related_name='points', verbose_name='Тип точки',
    )
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    lat = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        verbose_name='Широта',
    )
    lng = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        verbose_name='Долгота',
    )
    photo = models.FileField(
        upload_to=photo_path,
        storage=MinioBackend(bucket_name='geomap-media'),
        null=True, blank=True,
        verbose_name='Фото',
    )
    telegram_user_id = models.BigIntegerField(verbose_name='Telegram ID автора')
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name='Автор')
    allowed_users = models.ManyToManyField(
        'users.TelegramProfile', blank=True, related_name='accessible_points',
        verbose_name='Пользователи с доступом',
    )
    likes = models.PositiveIntegerField(default=0, verbose_name='Лайки')
    dislikes = models.PositiveIntegerField(default=0, verbose_name='Дизлайки')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        db_table = 'points'
        ordering = ('-created',)
        verbose_name = 'Точка'
        verbose_name_plural = 'Точки'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['telegram_user_id']),
            models.Index(fields=['lat', 'lng'], name='point_lat_lng_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(lat__gte=-90, lat__lte=90),
                name='point_latitude_range',
            ),
            models.CheckConstraint(
                condition=Q(lng__gte=-180, lng__lte=180),
                name='point_longitude_range',
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def photo_url(self):
        if not self.photo:
            return None
        from api_helpers import get_minio_client
        client = get_minio_client(external=True)
        return client.get_presigned_url(
            'GET', 'geomap-media', str(self.photo), expires=td(days=7),
        )
