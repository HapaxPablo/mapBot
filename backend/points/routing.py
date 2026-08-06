from django.urls import re_path

from points.consumers import PointConsumer

websocket_urlpatterns = [
    re_path(r'^ws/points/$', PointConsumer.as_asgi()),
]
