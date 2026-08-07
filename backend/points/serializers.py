from rest_framework import serializers

from points.models import Point, PointType
from users.models import TelegramProfile


MAX_POINT_PHOTO_SIZE = 10 * 1024 * 1024
ALLOWED_POINT_PHOTO_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def validate_point_photo(photo):
    if photo.size > MAX_POINT_PHOTO_SIZE:
        raise serializers.ValidationError('Фото не должно быть больше 10 МБ.')
    if getattr(photo, 'content_type', None) not in ALLOWED_POINT_PHOTO_TYPES:
        raise serializers.ValidationError('Разрешены только JPG, PNG и WebP.')
    header = photo.read(12)
    photo.seek(0)
    valid_signature = (
        header.startswith(b'\xff\xd8\xff')
        or header.startswith(b'\x89PNG\r\n\x1a\n')
        or (header.startswith(b'RIFF') and header[8:12] == b'WEBP')
    )
    if not valid_signature:
        raise serializers.ValidationError('Файл не похож на корректное изображение.')
    return photo


class PointTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointType
        fields = ('id', 'name')
        read_only_fields = fields


class AdminPointTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointType
        fields = ('id', 'name', 'icon_name', 'show_on_main_map')


class AdminPointSerializer(serializers.ModelSerializer):
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=5000,
    )
    allowed_user_ids = serializers.SerializerMethodField()
    allowed_users = serializers.ListField(
        child=serializers.IntegerField(min_value=1), write_only=True, required=False,
    )
    point_type = serializers.SlugRelatedField(
        slug_field='name', queryset=PointType.objects.all(),
    )

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng', 'point_type',
            'username', 'telegram_user_id', 'likes', 'dislikes',
            'is_active', 'created', 'allowed_user_ids', 'allowed_users',
        )
        read_only_fields = (
            'id', 'username', 'telegram_user_id', 'likes',
            'dislikes', 'created', 'allowed_user_ids',
        )

    def get_allowed_user_ids(self, obj):
        return list(obj.allowed_users.values_list('telegram_id', flat=True))

    def validate_allowed_users(self, value):
        profiles = TelegramProfile.objects.filter(telegram_id__in=value)
        if profiles.count() != len(set(value)):
            raise serializers.ValidationError('Один или несколько пользователей не найдены.')
        return value

    def update(self, instance, validated_data):
        allowed_user_ids = validated_data.pop('allowed_users', None)
        instance = super().update(instance, validated_data)
        if allowed_user_ids is not None:
            profiles = TelegramProfile.objects.filter(telegram_id__in=allowed_user_ids)
            instance.allowed_users.set(profiles)
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = TelegramProfile
        fields = (
            'user_id', 'telegram_id', 'username', 'first_name', 'last_name',
            'role', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'user_id', 'telegram_id', 'username', 'first_name', 'last_name',
            'created_at', 'updated_at',
        )


class TelegramAuthSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField(min_value=1)
    username = serializers.CharField(required=False, allow_blank=True, max_length=255)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=255)


class TelegramWebAppAuthSerializer(serializers.Serializer):
    init_data = serializers.CharField(max_length=4096)


class TelegramUserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = TelegramProfile
        fields = ('user_id', 'telegram_id', 'username', 'first_name', 'last_name', 'role')
        read_only_fields = fields


class PointSerializer(serializers.ModelSerializer):
    photo_url = serializers.ReadOnlyField()
    point_type = serializers.CharField(source='point_type.name', read_only=True)
    point_type_icon = serializers.CharField(source='point_type.icon_name', read_only=True)

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng', 'point_type', 'point_type_icon',
            'photo_url',
            'likes', 'dislikes', 'created',
        )
        read_only_fields = (
            'id', 'photo_url', 'likes', 'dislikes', 'created',
        )


class PointCreateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=5000,
    )
    point_type = serializers.SlugRelatedField(
        slug_field='name', queryset=PointType.objects.all(),
        required=False,
    )
    photo = serializers.FileField(write_only=True, required=True)

    def validate_photo(self, value):
        return validate_point_photo(value)

    class Meta:
        model = Point
        fields = (
            'id', 'title', 'description', 'lat', 'lng', 'point_type',
            'telegram_user_id', 'username', 'photo',
        )
        read_only_fields = ('id',)
