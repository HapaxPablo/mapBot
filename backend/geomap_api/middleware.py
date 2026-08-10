from django.conf import settings


class AllowLocalNullOriginMiddleware:
    """Allow local development clients with an opaque browser origin.

    Some browser contexts send ``Origin: null`` for form submissions. The
    normal CSRF token check is still performed by Django; this only skips the
    origin comparison in development and is disabled in production.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.DEBUG
            and settings.APP_ENV != 'production'
            and request.META.get('HTTP_ORIGIN') == 'null'
        ):
            request.META.pop('HTTP_ORIGIN', None)
        return self.get_response(request)
