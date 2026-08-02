from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


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
        return token == settings.BOT_API_KEY
