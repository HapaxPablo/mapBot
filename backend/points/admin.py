from django.contrib import admin

from points.models import Point


@admin.register(Point)
class PointAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'username', 'lat', 'lng', 'likes', 'dislikes', 'is_active', 'created')
    list_filter = ('is_active', 'created')
    search_fields = ('title', 'username', 'telegram_user_id')
    readonly_fields = ('id', 'created')
