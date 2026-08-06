from rest_framework.authentication import TokenAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed


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
