"""Миграция схемы данных серверной части GeoMap."""

from django.db import migrations, models
import django.db.models.deletion


def move_point_types(apps, schema_editor):
    """Создаёт типы точек и переносит к ним существующие записи."""
    Point = apps.get_model('points', 'Point')
    PointType = apps.get_model('points', 'PointType')
    types = {}
    for old_name in Point.objects.values_list('point_type', flat=True).distinct():
        type_obj, _ = PointType.objects.get_or_create(name=old_name or 'general')
        types[old_name] = type_obj.pk
    for point in Point.objects.all().iterator():
        point.point_type_fk_id = types.get(point.point_type, types.get(None))
        point.save(update_fields=('point_type_fk',))


class Migration(migrations.Migration):
    """Описывает операции миграции базы данных."""
    dependencies = [
        ('points', '0006_point_type_and_allowed_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='PointType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название типа')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Тип точки',
                'verbose_name_plural': 'Типы точек',
            },
        ),
        migrations.AddField(
            model_name='point',
            name='point_type_fk',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='+', to='points.pointtype',
            ),
        ),
        migrations.RunPython(move_point_types, migrations.RunPython.noop),
        migrations.RemoveField(model_name='point', name='point_type'),
        migrations.RenameField(model_name='point', old_name='point_type_fk', new_name='point_type'),
        migrations.AlterField(
            model_name='point',
            name='point_type',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='points', to='points.pointtype',
                verbose_name='Тип точки',
            ),
        ),
    ]
