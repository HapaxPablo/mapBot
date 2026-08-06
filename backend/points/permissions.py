from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission
from users.models import TelegramProfile

class BotOrReadOnly(BasePermission):
    """
    GET/HEAD/OPTIONS доступны всем (карта в WebApp читает точки без авторизации).
    Запись (создание точки, лайк/дизлайк, загрузка фото) — только с валидным
    заголовком Authorization: Api-Key <BOT_API_KEY>, который подставляет бот.
    """

    message = 'Требуется корректный Api-Key.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Api-Key '):
            return False

        token = auth.removeprefix('Api-Key ').strip()
        if token != settings.BOT_API_KEY:
            return False

        return True


class CanDeactivatePoint(BasePermission):
    message = 'Недостаточно прав для деактивации точки.'

    def has_permission(self, request, view):
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
