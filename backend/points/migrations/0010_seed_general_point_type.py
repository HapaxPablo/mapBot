"""Миграция схемы данных серверной части GeoMap."""

from django.db import migrations


def create_general_point_type(apps, schema_editor):
    """Добавляет базовый тип точки, если он ещё отсутствует."""
    PointType = apps.get_model('points', 'PointType')
    PointType.objects.get_or_create(name='general')


class Migration(migrations.Migration):
    """Описывает операции миграции базы данных."""
    dependencies = [
        ('points', '0009_pointtype_icon_name'),
    ]

    operations = [
        migrations.RunPython(create_general_point_type, migrations.RunPython.noop),
    ]
