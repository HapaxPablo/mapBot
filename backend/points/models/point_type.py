"""Компонент серверной части GeoMap."""

from django.db import models


class PointType(models.Model):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
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
        """Класс, инкапсулирующий логику серверного компонента GeoMap."""
        ordering = ('name',)
        verbose_name = 'Тип точки'
        verbose_name_plural = 'Типы точек'

    def __str__(self):
        """Выполняет операцию серверного компонента GeoMap."""
        return self.name
