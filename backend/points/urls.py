from django.urls import include, path
from rest_framework.routers import SimpleRouter

from points.views import PointViewSet

router = SimpleRouter()
router.register('points', PointViewSet, basename='points')

urlpatterns = [
    path('', include(router.urls)),
]
