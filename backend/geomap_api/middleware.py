from django.conf import settings


class AllowLocalNullOriginMiddleware:
    """Allow local development clients with an opaque browser origin.

    Some embedded/desktop browser contexts send ``Origin: null`` even when
    the page was opened through localhost. The normal CSRF token check is
    still performed by Django; this only skips the origin comparison for
    local HTTP development and is disabled when DEBUG is false.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':', 1)[0].lower()
        if (
            settings.DEBUG
            and request.META.get('HTTP_ORIGIN') == 'null'
            and host in {'localhost', '127.0.0.1'}
            and request.scheme == 'http'
        ):
            request.META.pop('HTTP_ORIGIN', None)
        return self.get_response(request)
