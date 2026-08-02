from rest_framework import serializers

from points.models import Point


class PointSerializer(serializers.ModelSerializer):
    photo_url = serializers.ReadOnlyField()

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng',
            'photo_url', 'username', 'telegram_user_id',
            'likes', 'dislikes', 'created',
        )
        read_only_fields = (
            'id', 'photo_url', 'likes', 'dislikes', 'created',
        )


class PointCreateSerializer(serializers.ModelSerializer):
    """То, что реально присылает бот при создании точки: без фото."""

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng',
            'telegram_user_id', 'username',
        )
        read_only_fields = ('id',)
