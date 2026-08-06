from django.contrib import admin

from users.models import TelegramProfile


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name', 'user__username')
    readonly_fields = ('telegram_id', 'created_at', 'updated_at')
