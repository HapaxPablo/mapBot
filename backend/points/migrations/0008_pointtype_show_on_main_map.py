from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('points', '0007_point_type_relation'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointtype',
            name='show_on_main_map',
            field=models.BooleanField(
                default=True,
                help_text='Если выключено, точки этого типа доступны только в специальном слое.',
                verbose_name='Показывать на общей карте',
            ),
        ),
    ]
