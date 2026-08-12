"""Компонент серверной части GeoMap."""

from django.contrib.auth.models import User
from django.db import models


class TelegramProfile(models.Model):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    class Role(models.TextChoices):
        """Класс, инкапсулирующий логику серверного компонента GeoMap."""
        ADMIN = 'admin', 'Администратор'
        SUPERUSER = 'superuser', 'Суперпользователь'
        OLD_MEMBER = 'old_member', 'Старый участник'
        NEW_MEMBER = 'new_member', 'Новый участник'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='telegram_profile')
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.NEW_MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Класс, инкапсулирующий логику серверного компонента GeoMap."""
        ordering = ('telegram_id',)

    def save(self, *args, **kwargs):
        """Выполняет операцию серверного компонента GeoMap."""
        self.user.is_staff = self.role in {self.Role.ADMIN, self.Role.SUPERUSER}
        self.user.is_superuser = self.role == self.Role.SUPERUSER
        self.user.save(update_fields=('is_staff', 'is_superuser'))
        super().save(*args, **kwargs)

    def __str__(self):
        """Выполняет операцию серверного компонента GeoMap."""
        return f'{self.username or self.telegram_id} ({self.get_role_display()})'


class Notification(models.Model):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    recipient = models.ForeignKey(
        TelegramProfile, on_delete=models.CASCADE, related_name='notifications',
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Класс, инкапсулирующий логику серверного компонента GeoMap."""
        ordering = ('created_at',)

    def __str__(self):
        """Выполняет операцию серверного компонента GeoMap."""
        return f'{self.recipient.telegram_id}: {self.message[:50]}'
