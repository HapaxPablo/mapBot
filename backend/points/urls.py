from django.urls import include, path
from rest_framework.routers import SimpleRouter

from points.views import PointViewSet, current_user, telegram_auth, telegram_webapp_auth

router = SimpleRouter()
router.register('points', PointViewSet, basename='points')

urlpatterns = [
    path('auth/telegram/', telegram_auth, name='telegram-auth'),
    path('auth/telegram/webapp/', telegram_webapp_auth, name='telegram-webapp-auth'),
    path('auth/me/', current_user, name='current-user'),
    path('', include(router.urls)),
]
