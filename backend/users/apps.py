"""Компонент серверной части GeoMap."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Пользователи'
