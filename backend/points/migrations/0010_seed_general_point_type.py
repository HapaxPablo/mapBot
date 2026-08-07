from django.db import migrations


def create_general_point_type(apps, schema_editor):
    PointType = apps.get_model('points', 'PointType')
    PointType.objects.get_or_create(name='general')


class Migration(migrations.Migration):
    dependencies = [
        ('points', '0009_pointtype_icon_name'),
    ]

    operations = [
        migrations.RunPython(create_general_point_type, migrations.RunPython.noop),
    ]
