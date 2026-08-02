from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from points.models import Point
from points.permissions import BotOrReadOnly
from points.serializers import PointCreateSerializer, PointSerializer


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
    http_method_names = ['get', 'post']

    def get_serializer_class(self):
        if self.action == 'create':
            return PointCreateSerializer
        return PointSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        point = serializer.save()
        return Response(PointSerializer(point).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser], url_path='photo')
    def upload_photo(self, request, pk=None):
        point = self.get_object()
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'detail': 'Файл photo обязателен.'}, status=status.HTTP_400_BAD_REQUEST)
        point.photo = photo
        point.save(update_fields=['photo'])
        return Response(PointSerializer(point).data)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        point = self.get_object()
        point.likes += 1
        point.save(update_fields=['likes'])
        return Response({'likes': point.likes, 'dislikes': point.dislikes})

    @action(detail=True, methods=['post'])
    def dislike(self, request, pk=None):
        point = self.get_object()
        point.dislikes += 1
        point.save(update_fields=['dislikes'])
        return Response({'likes': point.likes, 'dislikes': point.dislikes})
