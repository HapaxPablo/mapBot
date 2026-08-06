from rest_framework import serializers

from points.models import Point, PointType
from users.models import TelegramProfile


class TelegramAuthSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField(min_value=1)
    username = serializers.CharField(required=False, allow_blank=True, max_length=255)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=32)


class TelegramWebAppAuthSerializer(serializers.Serializer):
    init_data = serializers.CharField()


class TelegramUserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = TelegramProfile
        fields = ('user_id', 'telegram_id', 'username', 'first_name', 'last_name', 'phone_number', 'role')
        read_only_fields = fields


class PointSerializer(serializers.ModelSerializer):
    photo_url = serializers.ReadOnlyField()
    point_type = serializers.CharField(source='point_type.name', read_only=True)
    point_type_icon = serializers.CharField(source='point_type.icon_name', read_only=True)

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng', 'point_type', 'point_type_icon',
            'photo_url', 'username', 'telegram_user_id',
            'likes', 'dislikes', 'created',
        )
        read_only_fields = (
            'id', 'photo_url', 'likes', 'dislikes', 'created',
        )


class PointCreateSerializer(serializers.ModelSerializer):
    point_type = serializers.SlugRelatedField(
        slug_field='name', queryset=PointType.objects.all(),
        required=False,
    )

    """То, что реально присылает бот при создании точки: без фото."""

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng', 'point_type',
            'telegram_user_id', 'username',
        )
        read_only_fields = ('id',)
