from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.authtoken.models import Token

from points.models import Point
from points.serializers import PointSerializer
from users.models import TelegramProfile


class PointConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        query = parse_qs(self.scope.get('query_string', b'').decode())
        token_key = query.get('token', [None])[0]
        self.profile = await self.get_profile(token_key)
        await self.channel_layer.group_add('points', self.channel_name)
        await self.accept()
        await self.send_points(scope='all')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('points', self.channel_name)

    async def points_changed(self, event):
        await self.send_points(scope='all')
        if self.profile is not None and self.profile.role in {
            TelegramProfile.Role.ADMIN,
            TelegramProfile.Role.SUPERUSER,
            TelegramProfile.Role.OLD_MEMBER,
        }:
            await self.send_points(scope='personal')

    async def receive_json(self, content, **kwargs):
        scope = content.get('scope', 'all')
        if scope == 'personal' and self.profile is None:
            await self.send_json({'type': 'error', 'detail': 'Authentication required.'})
            return
        await self.send_points(scope, content.get('point_type'))

    async def send_points(self, scope='all', point_type=None):
        points = await self.get_points(scope, point_type)
        await self.send_json({
            'type': 'points',
            'scope': scope,
            'point_type': point_type,
            'points': points,
        })

    @database_sync_to_async
    def get_profile(self, token_key):
        if not token_key:
            return None
        token = Token.objects.select_related('user__telegram_profile').filter(key=token_key).first()
        return token.user.telegram_profile if token else None

    @database_sync_to_async
    def get_points(self, scope, point_type):
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
        return PointSerializer(queryset.distinct(), many=True).data
