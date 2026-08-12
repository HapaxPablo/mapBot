"""Миграция схемы данных серверной части GeoMap."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Описывает операции миграции базы данных."""
    dependencies = [
        ('points', '0008_pointtype_show_on_main_map'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointtype',
            name='icon_name',
            field=models.CharField(
                blank=True,
                default='MapPin',
                help_text='Например: MapPin, Warehouse, Home, Flag.',
                max_length=64,
                verbose_name='Lucide-иконка',
            ),
        ),
    ]
