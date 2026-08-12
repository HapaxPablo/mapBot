"""Компонент серверной части GeoMap."""

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission
from users.models import TelegramProfile

class BotOrReadOnly(BasePermission):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""

    message = 'Требуется корректный Api-Key.'

    def has_permission(self, request, view):
        """Выполняет операцию серверного компонента GeoMap."""
        if request.method in SAFE_METHODS:
            return True

        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Api-Key '):
            return False

        token = auth.removeprefix('Api-Key ').strip()
        if token != settings.BOT_API_KEY:
            return False

        return True


class CanVotePoint(BotOrReadOnly):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""

    def has_permission(self, request, view):
        """Выполняет операцию серверного компонента GeoMap."""
        if request.user.is_authenticated:
            return True
        return super().has_permission(request, view)


class CanDeactivatePoint(BasePermission):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    message = 'Недостаточно прав для деактивации точки.'

    def has_permission(self, request, view):
        """Выполняет операцию серверного компонента GeoMap."""
        auth = request.headers.get('Authorization', '')
        if auth == f'Api-Key {settings.BOT_API_KEY}':
            return True

        if not request.user.is_authenticated:
            return False

        profile = TelegramProfile.objects.filter(user=request.user).first()
        return profile is not None and profile.role in {
            TelegramProfile.Role.ADMIN,
            TelegramProfile.Role.SUPERUSER,
            TelegramProfile.Role.OLD_MEMBER,
        }

    def has_object_permission(self, request, view, obj):
        """Выполняет операцию серверного компонента GeoMap."""
        auth = request.headers.get('Authorization', '')
        if auth == f'Api-Key {settings.BOT_API_KEY}':
            return True

        profile = TelegramProfile.objects.filter(user=request.user).first()
        if profile is None:
            return False
        if profile.role in {
            TelegramProfile.Role.ADMIN,
            TelegramProfile.Role.SUPERUSER,
        }:
            return True
        return profile.role == TelegramProfile.Role.OLD_MEMBER and obj.allowed_users.filter(
            pk=profile.pk,
        ).exists()
