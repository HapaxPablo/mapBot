"""Компонент серверной части GeoMap."""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.authtoken.models import Token

from points.models import Point
from points.serializers import PointSerializer
from points.authentication import token_is_valid
from points.geo import filter_by_bounds, parse_bounds
from users.models import TelegramProfile


class PointConsumer(AsyncJsonWebsocketConsumer):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    async def connect(self):
        """Выполняет операцию серверного компонента GeoMap."""
        self.profile = None
        self.scope = 'all'
        self.point_type = None
        self.bounds = None
        await self.channel_layer.group_add('points', self.channel_name)
        await self.accept()
        await self.send_points(scope='all')

    async def disconnect(self, close_code):
        """Выполняет операцию серверного компонента GeoMap."""
        await self.channel_layer.group_discard('points', self.channel_name)

    async def points_changed(self, event):
        """Выполняет операцию серверного компонента GeoMap."""
        await self.send_points(scope=self.scope, point_type=self.point_type)

    async def receive_json(self, content, **kwargs):
        """Выполняет операцию серверного компонента GeoMap."""
        if not isinstance(content, dict):
            await self.send_json({'type': 'error', 'detail': 'Invalid message.'})
            return

        if content.get('type') == 'auth':
            self.profile = await self.get_profile(content.get('token'))
            await self.send_json({'type': 'authenticated', 'authenticated': self.profile is not None})
            return

        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})
            return

        if content.get('type') == 'viewport':
            scope = content.get('scope', 'all')
            if scope not in {'all', 'personal'}:
                await self.send_json({'type': 'error', 'detail': 'Invalid points scope.'})
                return
            if scope == 'personal' and self.profile is None:
                await self.send_json({'type': 'error', 'detail': 'Authentication required.'})
                return
            bounds = parse_bounds(content.get('bounds'))
            if bounds is None:
                await self.send_json({'type': 'error', 'detail': 'Invalid map bounds.'})
                return
            point_type = content.get('point_type')
            if point_type is not None and not isinstance(point_type, str):
                await self.send_json({'type': 'error', 'detail': 'Invalid point type.'})
                return
            self.scope = scope
            self.point_type = point_type or None
            self.bounds = bounds
            await self.send_points(scope, self.point_type)
            return

        scope = content.get('scope', 'all')
        if scope == 'personal' and self.profile is None:
            await self.send_json({'type': 'error', 'detail': 'Authentication required.'})
            return
        await self.send_points(scope, content.get('point_type'))

    async def send_points(self, scope='all', point_type=None):
        """Выполняет операцию серверного компонента GeoMap."""
        points = await self.get_points(scope, point_type, self.bounds)
        await self.send_json({
            'type': 'points',
            'scope': scope,
            'point_type': point_type,
            'points': points,
        })

    @database_sync_to_async
    def get_profile(self, token_key):
        """Выполняет операцию серверного компонента GeoMap."""
        if not token_key:
            return None
        token = Token.objects.select_related('user__telegram_profile').filter(key=token_key).first()
        if token is not None and not token_is_valid(token):
            token.delete()
            return None
        return getattr(token.user, 'telegram_profile', None) if token else None

    @database_sync_to_async
    def get_points(self, scope, point_type, bounds=None):
        """Выполняет операцию серверного компонента GeoMap."""
        queryset = Point.objects.filter(is_active=True).select_related('point_type')
        if scope == 'personal':
            if self.profile is None:
                return []
            if self.profile.role == TelegramProfile.Role.OLD_MEMBER:
                queryset = queryset.filter(allowed_users=self.profile)
            elif self.profile.role not in {
                TelegramProfile.Role.ADMIN,
                TelegramProfile.Role.SUPERUSER,
            }:
                return []
            if point_type:
                queryset = queryset.filter(point_type__name=point_type)
            queryset = queryset.filter(point_type__show_on_main_map=False)
        else:
            queryset = queryset.filter(point_type__show_on_main_map=True)
        if point_type and scope == 'all':
            queryset = queryset.filter(point_type__name=point_type)
        if bounds:
            queryset = filter_by_bounds(queryset, bounds)
        return PointSerializer(queryset.distinct(), many=True).data
