from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed


def token_is_valid(token):
    if not token.created:
        return True
    max_age = timedelta(seconds=settings.TOKEN_MAX_AGE_SECONDS)
    return timezone.now() - token.created <= max_age


class TokenAuthenticationWithoutApiKey(TokenAuthentication):
    """Do not treat the bot's Authorization: Api-Key header as a DRF token."""

    def authenticate(self, request):
        header = get_authorization_header(request)
        if header and not header.lower().startswith(b'token '):
            return None
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            raise

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if not token_is_valid(token):
            token.delete()
            raise AuthenticationFailed('Token has expired.')
        return user, token
