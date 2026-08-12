"""Миграция схемы данных серверной части GeoMap."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Описывает операции миграции базы данных."""
    dependencies = [
        ('points', '0002_telegramprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramprofile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
