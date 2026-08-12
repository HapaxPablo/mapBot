"""Компонент серверной части GeoMap."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed


def token_is_valid(token):
    """Выполняет операцию серверного компонента GeoMap."""
    if not token.created:
        return True
    max_age = timedelta(seconds=settings.TOKEN_MAX_AGE_SECONDS)
    return timezone.now() - token.created <= max_age


class TokenAuthenticationWithoutApiKey(TokenAuthentication):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""

    def authenticate(self, request):
        """Выполняет операцию серверного компонента GeoMap."""
        header = get_authorization_header(request)
        if header and not header.lower().startswith(b'token '):
            return None
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            raise

    def authenticate_credentials(self, key):
        """Выполняет операцию серверного компонента GeoMap."""
        user, token = super().authenticate_credentials(key)
        if not token_is_valid(token):
            token.delete()
            raise AuthenticationFailed('Token has expired.')
        return user, token
