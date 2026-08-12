"""Компонент серверной части GeoMap."""

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, parser_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response

from points.auth import authenticate_telegram_user, telegram_webapp_user
from points.geo import filter_by_bounds, parse_bounds
from points.models import Point, PointType, PointVote
from points.permissions import BotOrReadOnly, CanDeactivatePoint, CanVotePoint
from points.serializers import (
    AdminPointSerializer, AdminPointTypeSerializer, AdminUserSerializer,
    PointCreateSerializer, PointSerializer, PointTypeSerializer,
    validate_point_photo,
)
from points.serializers import TelegramAuthSerializer, TelegramUserSerializer, TelegramWebAppAuthSerializer
from points.authentication import TokenAuthenticationWithoutApiKey
from users.models import Notification, TelegramProfile


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def telegram_auth(request):
    """Выполняет операцию серверного компонента GeoMap."""
    auth = request.headers.get('Authorization', '')
    if auth != f'Api-Key {settings.BOT_API_KEY}':
        return Response({'detail': 'Требуется корректный Api-Key.'}, status=status.HTTP_401_UNAUTHORIZED)
    serializer = TelegramAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile, token = authenticate_telegram_user(**serializer.validated_data)
    return Response(
        {'user': TelegramUserSerializer(profile).data, 'token': token.key},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def telegram_webapp_auth(request):
    """Выполняет операцию серверного компонента GeoMap."""
    serializer = TelegramWebAppAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        tg_user = telegram_webapp_user(serializer.validated_data['init_data'])
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

    profile, token = authenticate_telegram_user(
        telegram_id=int(tg_user['id']),
        username=tg_user.get('username', ''),
        first_name=tg_user.get('first_name', ''),
        last_name=tg_user.get('last_name', ''),
        rotate_token=True,
    )
    return Response({'user': TelegramUserSerializer(profile).data, 'token': token.key})


@api_view(['GET'])
@authentication_classes([TokenAuthenticationWithoutApiKey])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Выполняет операцию серверного компонента GeoMap."""
    profile = TelegramProfile.objects.get(user=request.user)
    return Response(TelegramUserSerializer(profile).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def point_types(request):
    """Выполняет операцию серверного компонента GeoMap."""
    return Response(PointTypeSerializer(PointType.objects.all(), many=True).data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    """Выполняет операцию серверного компонента GeoMap."""
    try:
        connection.ensure_connection()
    except Exception:
        return Response(
            {'status': 'unavailable', 'checks': {'database': 'failed'}},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({'status': 'ok', 'checks': {'database': 'ok'}})


def _require_bot_key(request):
    """Выполняет операцию серверного компонента GeoMap."""
    if request.headers.get('Authorization', '') != f'Api-Key {settings.BOT_API_KEY}':
        return Response(
            {'detail': 'Требуется корректный Api-Key.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return None


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def bot_notifications(request):
    """Выполняет операцию серверного компонента GeoMap."""
    error = _require_bot_key(request)
    if error:
        return error
    notifications = Notification.objects.select_related('recipient').order_by('created_at')[:100]
    return Response([{
        'id': notification.id,
        'telegram_id': notification.recipient.telegram_id,
        'message': notification.message,
    } for notification in notifications])


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def bot_notifications_ack(request):
    """Выполняет операцию серверного компонента GeoMap."""
    error = _require_bot_key(request)
    if error:
        return error
    notification_ids = request.data.get('ids', [])
    if not isinstance(notification_ids, list):
        return Response({'detail': 'Поле ids должно быть списком.'}, status=status.HTTP_400_BAD_REQUEST)
    Notification.objects.filter(id__in=notification_ids).delete()
    return Response({'deleted': len(notification_ids)})


def _admin_actor(request):
    """Выполняет операцию серверного компонента GeoMap."""
    auth = request.headers.get('Authorization', '')
    if auth != f'Api-Key {settings.BOT_API_KEY}':
        return None, Response(
            {'detail': 'Требуется корректный Api-Key.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    telegram_user_id = request.data.get('telegram_user_id') or request.query_params.get('telegram_user_id')
    try:
        telegram_user_id = int(telegram_user_id)
    except (TypeError, ValueError):
        return None, Response(
            {'detail': 'Не указан Telegram ID администратора.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = TelegramProfile.objects.filter(telegram_id=telegram_user_id).first()
    if profile is None or profile.role not in {
        TelegramProfile.Role.ADMIN,
        TelegramProfile.Role.SUPERUSER,
    }:
        return None, Response(
            {'detail': 'Доступ разрешён только администраторам.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return profile, None


def _without_actor(data):
    """Выполняет операцию серверного компонента GeoMap."""
    data = data.copy()
    data.pop('telegram_user_id', None)
    return data


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def telegram_profile(request):
    """Выполняет операцию серверного компонента GeoMap."""
    auth = request.headers.get('Authorization', '')
    if auth != f'Api-Key {settings.BOT_API_KEY}':
        return Response(
            {'detail': 'Требуется корректный Api-Key.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    telegram_user_id = request.query_params.get('telegram_user_id')
    try:
        telegram_user_id = int(telegram_user_id)
    except (TypeError, ValueError):
        return Response(
            {'detail': 'Не указан Telegram ID пользователя.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    profile = TelegramProfile.objects.filter(telegram_id=telegram_user_id).first()
    if profile is None:
        return Response(
            {'detail': 'Пользователь не зарегистрирован.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(TelegramUserSerializer(profile).data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_users(request):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    queryset = TelegramProfile.objects.select_related('user').all()
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(telegram_id__icontains=search)
        )
    return Response(AdminUserSerializer(queryset, many=True).data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_user_role(request, telegram_id):
    """Выполняет операцию серверного компонента GeoMap."""
    actor, error = _admin_actor(request)
    if error:
        return error
    profile = TelegramProfile.objects.filter(telegram_id=telegram_id).first()
    if profile is None:
        return Response({'detail': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
    role = request.data.get('role')
    valid_roles = {choice[0] for choice in TelegramProfile.Role.choices}
    if role not in valid_roles:
        return Response({'detail': 'Некорректная роль пользователя.'}, status=status.HTTP_400_BAD_REQUEST)
    if actor.role == TelegramProfile.Role.ADMIN and role == TelegramProfile.Role.SUPERUSER:
        return Response(
            {'detail': 'Только superuser может назначать роль superuser.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    profile.role = role
    profile.save(update_fields=('role', 'updated_at'))
    return Response(AdminUserSerializer(profile).data)


@api_view(['GET', 'POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_point_types(request):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    if request.method == 'GET':
        return Response(AdminPointTypeSerializer(PointType.objects.all(), many=True).data)

    serializer = AdminPointTypeSerializer(data=_without_actor(request.data))
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_point_type_detail(request, pk):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    point_type = PointType.objects.filter(pk=pk).first()
    if point_type is None:
        return Response({'detail': 'Тип точки не найден.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(AdminPointTypeSerializer(point_type).data)
    if request.method == 'DELETE':
        try:
            point_type.delete()
        except ProtectedError:
            return Response(
                {'detail': 'Нельзя удалить тип, к которому привязаны точки.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = AdminPointTypeSerializer(
        point_type, data=_without_actor(request.data), partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_points(request):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    queryset = Point.objects.all().select_related('point_type').prefetch_related('allowed_users')
    search = request.query_params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(username__icontains=search)
            | Q(telegram_user_id__icontains=search)
        )
    is_active = request.query_params.get('is_active')
    if is_active in {'true', 'false'}:
        queryset = queryset.filter(is_active=is_active == 'true')
    point_type = request.query_params.get('point_type', '').strip()
    if point_type:
        queryset = queryset.filter(point_type__name=point_type)
    return Response(AdminPointSerializer(queryset, many=True).data)


@api_view(['GET', 'PATCH'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_point_detail(request, pk):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    point = Point.objects.select_related('point_type').filter(pk=pk).first()
    if point is None:
        return Response({'detail': 'Точка не найдена.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(AdminPointSerializer(point).data)

    serializer = AdminPointSerializer(
        point, data=_without_actor(request.data), partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser])
def admin_point_photo(request, pk):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    point = Point.objects.filter(pk=pk).first()
    if point is None:
        return Response({'detail': 'Точка не найдена.'}, status=status.HTTP_404_NOT_FOUND)
    photo = request.FILES.get('photo')
    if not photo:
        return Response({'detail': 'Файл photo обязателен.'}, status=status.HTTP_400_BAD_REQUEST)
    validate_point_photo(photo)
    point.photo = photo
    point.save(update_fields=['photo'])
    return Response(AdminPointSerializer(point).data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def admin_votes(request):
    """Выполняет операцию серверного компонента GeoMap."""
    _, error = _admin_actor(request)
    if error:
        return error
    votes = PointVote.objects.select_related('point', 'user').order_by('-created_at')
    result = [{
        'id': vote.id,
        'point_id': str(vote.point_id),
        'point_title': vote.point.title,
        'telegram_user_id': getattr(getattr(vote.user, 'telegram_profile', None), 'telegram_id', None),
        'username': vote.user.username,
        'vote_type': vote.get_vote_type_display(),
        'created_at': vote.created_at,
    } for vote in votes]
    return Response(result)


class PointViewSet(viewsets.ModelViewSet):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""

    queryset = Point.objects.filter(is_active=True)
    permission_classes = [BotOrReadOnly]
    authentication_classes = [TokenAuthenticationWithoutApiKey]
    parser_classes = [JSONParser, MultiPartParser]
    http_method_names = ['get', 'post']

    def _request_profile(self):
        """Выполняет операцию серверного компонента GeoMap."""
        if self.request.user.is_authenticated:
            return TelegramProfile.objects.filter(user=self.request.user).first()
        if self.request.headers.get('Authorization', '') != f'Api-Key {settings.BOT_API_KEY}':
            return None
        telegram_user_id = (
            self.request.query_params.get('telegram_user_id')
            or self.request.data.get('telegram_user_id')
        )
        return TelegramProfile.objects.filter(telegram_id=telegram_user_id).first()

    def get_queryset(self):
        """Выполняет операцию серверного компонента GeoMap."""
        queryset = super().get_queryset().select_related('point_type')
        profile = self._request_profile()

        if self.action != 'list':
            public_queryset = queryset.filter(point_type__show_on_main_map=True)
            if profile and profile.role in {
                TelegramProfile.Role.ADMIN,
                TelegramProfile.Role.SUPERUSER,
            }:
                return queryset
            if profile and profile.role == TelegramProfile.Role.OLD_MEMBER:
                return queryset.filter(
                    Q(point_type__show_on_main_map=True) | Q(allowed_users=profile),
                ).distinct()
            return public_queryset

        if self.request.query_params.get('scope') != 'personal':
            queryset = queryset.filter(point_type__show_on_main_map=True)
            point_type = self.request.query_params.get('point_type')
            if point_type:
                queryset = queryset.filter(point_type__name=point_type)
            bounds = parse_bounds(self.request.query_params.get('bbox'))
            return filter_by_bounds(queryset, bounds) if bounds else queryset

        if profile is None or profile.role not in {
            TelegramProfile.Role.ADMIN,
            TelegramProfile.Role.SUPERUSER,
            TelegramProfile.Role.OLD_MEMBER,
        }:
            return queryset.none()

        if profile.role == TelegramProfile.Role.OLD_MEMBER:
            queryset = queryset.filter(allowed_users=profile)
        queryset = queryset.filter(point_type__show_on_main_map=False)

        point_type = self.request.query_params.get('point_type')
        if point_type:
            queryset = queryset.filter(point_type__name=point_type)
        bounds = parse_bounds(self.request.query_params.get('bbox'))
        if bounds:
            queryset = filter_by_bounds(queryset, bounds)
        return queryset.distinct()

    def get_serializer_class(self):
        """Выполняет операцию серверного компонента GeoMap."""
        if self.action == 'create':
            return PointCreateSerializer
        return PointSerializer

    def get_permissions(self):
        """Выполняет операцию серверного компонента GeoMap."""
        if self.action == 'deactivate':
            return [CanDeactivatePoint()]
        if self.action in {'like', 'dislike'}:
            return [CanVotePoint()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Выполняет операцию серверного компонента GeoMap."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.setdefault(
            'point_type',
            PointType.objects.get_or_create(name='general')[0],
        )
        profile = self._request_profile()
        if profile is None or profile.telegram_id != serializer.validated_data['telegram_user_id']:
            return Response({'detail': 'Пользователь не зарегистрирован.'}, status=status.HTTP_403_FORBIDDEN)
        if profile.role == TelegramProfile.Role.NEW_MEMBER:
            return Response({'detail': 'Новые участники не могут создавать точки.'}, status=status.HTTP_403_FORBIDDEN)
        point = serializer.save()
        return Response(PointSerializer(point).data, status=status.HTTP_201_CREATED)

    def _get_voter(self, request):
        """Выполняет операцию серверного компонента GeoMap."""
        profile = self._request_profile()
        return profile.user if profile else None

    def _vote(self, request, point, vote_type):
        """Выполняет операцию серверного компонента GeoMap."""
        user = self._get_voter(request)
        if user is None:
            return Response({'detail': 'Для голосования нужно зарегистрироваться.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            with transaction.atomic():
                # Lock the point so changing a vote cannot race with another
                # request and leave the counters out of sync.
                point = Point.objects.select_for_update().get(pk=point.pk)
                existing_vote = PointVote.objects.filter(
                    point=point,
                    user=user,
                ).first()

                if existing_vote is not None:
                    if existing_vote.vote_type == vote_type:
                        return Response(
                            {'detail': 'Вы уже поставили такую реакцию на эту точку.'},
                            status=status.HTTP_409_CONFLICT,
                        )

                    old_field = 'likes' if existing_vote.vote_type == PointVote.VoteType.LIKE else 'dislikes'
                    existing_vote.delete()
                    Point.objects.filter(pk=point.pk).update(**{old_field: F(old_field) - 1})

                PointVote.objects.create(point=point, user=user, vote_type=vote_type)

                field = 'likes' if vote_type == PointVote.VoteType.LIKE else 'dislikes'
                Point.objects.filter(pk=point.pk).update(**{field: F(field) + 1})
        except IntegrityError:
            return Response({'detail': 'Вы уже голосовали за эту точку.'}, status=status.HTTP_409_CONFLICT)

        point.refresh_from_db(fields=('likes', 'dislikes'))
        return Response({'likes': point.likes, 'dislikes': point.dislikes})

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser], url_path='photo')
    def upload_photo(self, request, pk=None):
        """Выполняет операцию серверного компонента GeoMap."""
        point = self.get_object()
        profile = self._request_profile()
        if profile is None:
            return Response({'detail': 'Пользователь не зарегистрирован.'}, status=status.HTTP_403_FORBIDDEN)
        if profile.role == TelegramProfile.Role.NEW_MEMBER:
            return Response({'detail': 'Новые участники не могут загружать фотографии.'}, status=status.HTTP_403_FORBIDDEN)
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'detail': 'Файл photo обязателен.'}, status=status.HTTP_400_BAD_REQUEST)
        validate_point_photo(photo)
        point.photo = photo
        point.save(update_fields=['photo'])
        return Response(PointSerializer(point).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Выполняет операцию серверного компонента GeoMap."""
        point = self.get_object()
        if point.point_type.show_on_main_map:
            return Response(
                {'detail': 'Деактивировать можно только точку специального типа.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        point.is_active = False
        point.save(update_fields=['is_active'])
        return Response({'id': str(point.id), 'is_active': False})

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Выполняет операцию серверного компонента GeoMap."""
        point = self.get_object()
        return self._vote(request, point, PointVote.VoteType.LIKE)

    @action(detail=True, methods=['post'])
    def dislike(self, request, pk=None):
        """Выполняет операцию серверного компонента GeoMap."""
        point = self.get_object()
        return self._vote(request, point, PointVote.VoteType.DISLIKE)
