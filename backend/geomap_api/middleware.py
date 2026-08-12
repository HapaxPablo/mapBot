"""Компонент серверной части GeoMap."""

from django.conf import settings


class AllowLocalNullOriginMiddleware:
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""

    def __init__(self, get_response):
        """Выполняет операцию серверного компонента GeoMap."""
        self.get_response = get_response

    def __call__(self, request):
        """Выполняет операцию серверного компонента GeoMap."""
        if (
            settings.DEBUG
            and settings.APP_ENV != 'production'
            and request.META.get('HTTP_ORIGIN') == 'null'
        ):
            request.META.pop('HTTP_ORIGIN', None)
        return self.get_response(request)
