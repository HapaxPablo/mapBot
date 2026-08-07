from django.urls import include, path
from rest_framework.routers import SimpleRouter

from points.views import (
    PointViewSet, admin_point_detail, admin_point_type_detail, admin_point_types,
    admin_point_photo, admin_points, admin_user_role, admin_users, admin_votes, bot_notifications,
    bot_notifications_ack, current_user, health, point_types, telegram_auth, telegram_profile,
    telegram_webapp_auth,
)

router = SimpleRouter()
router.register('points', PointViewSet, basename='points')

urlpatterns = [
    path('auth/telegram/', telegram_auth, name='telegram-auth'),
    path('auth/telegram/webapp/', telegram_webapp_auth, name='telegram-webapp-auth'),
    path('auth/telegram/profile/', telegram_profile, name='telegram-profile'),
    path('auth/me/', current_user, name='current-user'),
    path('bot/notifications/', bot_notifications, name='bot-notifications'),
    path('bot/notifications/ack/', bot_notifications_ack, name='bot-notifications-ack'),
    path('point-types/', point_types, name='point-types'),
    path('health/', health, name='health'),
    path('admin/users/', admin_users, name='admin-users'),
    path('admin/users/<int:telegram_id>/role/', admin_user_role, name='admin-user-role'),
    path('admin/point-types/', admin_point_types, name='admin-point-types'),
    path('admin/point-types/<int:pk>/', admin_point_type_detail, name='admin-point-type-detail'),
    path('admin/points/', admin_points, name='admin-points'),
    path('admin/points/<uuid:pk>/', admin_point_detail, name='admin-point-detail'),
    path('admin/points/<uuid:pk>/photo/', admin_point_photo, name='admin-point-photo'),
    path('admin/votes/', admin_votes, name='admin-votes'),
    path('', include(router.urls)),
]
