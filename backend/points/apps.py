"""Компонент серверной части GeoMap."""

from django.apps import AppConfig


class PointsConfig(AppConfig):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'points'
    verbose_name = 'Точки карты'

    def ready(self):
        """Выполняет операцию серверного компонента GeoMap."""
        import points.signals  # noqa: F401
