"""Компонент серверной части GeoMap."""

from django.contrib import admin

from points.models import Point, PointType, PointVote


@admin.register(PointType)
class PointTypeAdmin(admin.ModelAdmin):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    list_display = ('name', 'icon_name', 'show_on_main_map')
    list_filter = ('show_on_main_map',)
    search_fields = ('name',)


@admin.register(Point)
class PointAdmin(admin.ModelAdmin):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    list_display = ('id', 'title', 'point_type', 'username', 'lat', 'lng', 'likes', 'dislikes', 'is_active', 'created')
    list_filter = ('point_type', 'is_active', 'created')
    search_fields = ('title', 'point_type', 'username', 'telegram_user_id')
    filter_horizontal = ('allowed_users',)
    readonly_fields = ('id', 'created')


@admin.register(PointVote)
class PointVoteAdmin(admin.ModelAdmin):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    list_display = ('point', 'user', 'vote_type', 'created_at')
    list_filter = ('vote_type', 'created_at')
    search_fields = ('point__title', 'user__username', 'user__telegram_profile__telegram_id')
    readonly_fields = ('point', 'user', 'vote_type', 'created_at')
