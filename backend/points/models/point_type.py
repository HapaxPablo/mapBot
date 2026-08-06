from django.db import models


class PointType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название типа')
    icon_name = models.CharField(
        max_length=64,
        blank=True,
        default='MapPin',
        verbose_name='Lucide-иконка',
        help_text='Например: MapPin, Warehouse, Home, Flag.',
    )
    show_on_main_map = models.BooleanField(
        default=True,
        verbose_name='Показывать на общей карте',
        help_text='Если выключено, точки этого типа доступны только в специальном слое.',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тип точки'
        verbose_name_plural = 'Типы точек'

    def __str__(self):
        return self.name
