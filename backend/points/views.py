from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from points.auth import authenticate_telegram_user, telegram_webapp_user
from points.models import Point, PointType, PointVote
from points.permissions import BotOrReadOnly, CanDeactivatePoint
from points.serializers import PointCreateSerializer, PointSerializer
from points.serializers import TelegramAuthSerializer, TelegramUserSerializer, TelegramWebAppAuthSerializer
from points.authentication import TokenAuthenticationWithoutApiKey
from users.models import TelegramProfile


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def telegram_auth(request):
    """Register/login a Telegram user; only the trusted bot may call this."""
    auth = request.headers.get('Authorization', '')
    if auth != f'Api-Key {settings.BOT_API_KEY}':
        return Response({'detail': 'Требуется корректный Api-Key.'}, status=status.HTTP_401_UNAUTHORIZED)
    serializer = TelegramAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    if TelegramProfile.objects.filter(
        telegram_id=serializer.validated_data['telegram_id']
    ).exists():
        return Response(
            {'detail': 'Пользователь уже зарегистрирован.'},
            status=status.HTTP_409_CONFLICT,
        )
    profile, token = authenticate_telegram_user(**serializer.validated_data)
    return Response({'user': TelegramUserSerializer(profile).data, 'token': token.key})


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def telegram_webapp_auth(request):
    """Authenticate the user who opened this Telegram WebApp."""
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
    )
    return Response({'user': TelegramUserSerializer(profile).data, 'token': token.key})


@api_view(['GET'])
@authentication_classes([TokenAuthenticationWithoutApiKey])
@permission_classes([IsAuthenticated])
def current_user(request):
    profile = TelegramProfile.objects.get(user=request.user)
    return Response(TelegramUserSerializer(profile).data)


class PointViewSet(viewsets.ModelViewSet):
    """
    Точки карты.

    - GET  /api/points/            — список активных точек (для WebApp-карты)
    - GET  /api/points/{id}/       — одна точка
    - POST /api/points/            — создать точку (бот, Api-Key)
    - POST /api/points/{id}/photo/ — прикрепить фото (бот, Api-Key)
    - POST /api/points/{id}/like/  — лайк (бот, Api-Key)
    - POST /api/points/{id}/dislike/ — дизлайк (бот, Api-Key)
    """

    queryset = Point.objects.filter(is_active=True)
    permission_classes = [BotOrReadOnly]
    authentication_classes = [TokenAuthenticationWithoutApiKey]
    http_method_names = ['get', 'post']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset

        if self.request.query_params.get('scope') != 'personal':
            return queryset.filter(point_type__show_on_main_map=True)

        if not self.request.user.is_authenticated:
            return queryset.none()

        profile = TelegramProfile.objects.filter(user=self.request.user).first()
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
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return PointCreateSerializer
        return PointSerializer

    def get_permissions(self):
        if self.action == 'deactivate':
            return [CanDeactivatePoint()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.setdefault(
            'point_type',
            PointType.objects.get_or_create(name='general')[0],
        )
        profile = TelegramProfile.objects.filter(
            telegram_id=serializer.validated_data['telegram_user_id']
        ).first()
        if profile is None:
            return Response({'detail': 'Пользователь не зарегистрирован.'}, status=status.HTTP_403_FORBIDDEN)
        if profile.role == TelegramProfile.Role.NEW_MEMBER:
            return Response({'detail': 'Новые участники не могут создавать точки.'}, status=status.HTTP_403_FORBIDDEN)
        point = serializer.save()
        return Response(PointSerializer(point).data, status=status.HTTP_201_CREATED)

    def _get_voter(self, request):
        telegram_user_id = request.data.get('telegram_user_id')
        if telegram_user_id:
            profile = TelegramProfile.objects.filter(
                telegram_id=telegram_user_id
            ).select_related('user').first()
            if profile:
                return profile.user
        if request.user.is_authenticated:
            return request.user
        return None

    def _vote(self, request, point, vote_type):
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
        point = self.get_object()
        profile = TelegramProfile.objects.filter(
            telegram_id=request.data.get('telegram_user_id')
        ).first()
        if profile is None:
            return Response({'detail': 'Пользователь не зарегистрирован.'}, status=status.HTTP_403_FORBIDDEN)
        if profile.role == TelegramProfile.Role.NEW_MEMBER:
            return Response({'detail': 'Новые участники не могут загружать фотографии.'}, status=status.HTTP_403_FORBIDDEN)
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'detail': 'Файл photo обязателен.'}, status=status.HTTP_400_BAD_REQUEST)
        point.photo = photo
        point.save(update_fields=['photo'])
        return Response(PointSerializer(point).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
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
        point = self.get_object()
        return self._vote(request, point, PointVote.VoteType.LIKE)

    @action(detail=True, methods=['post'])
    def dislike(self, request, pk=None):
        point = self.get_object()
        return self._vote(request, point, PointVote.VoteType.DISLIKE)
