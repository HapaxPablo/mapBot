"""Миграция схемы данных серверной части GeoMap."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Описывает операции миграции базы данных."""
    dependencies = [
        ('points', '0011_point_coordinate_validators'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='point',
            index=models.Index(fields=['lat', 'lng'], name='point_lat_lng_idx'),
        ),
    ]
