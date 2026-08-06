from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('points', '0005_pointvote'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='point',
            name='point_type',
            field=models.CharField(
                db_index=True,
                default='general',
                help_text='Например: склад, маршрут, закрытая зона.',
                max_length=100,
                verbose_name='Тип точки',
            ),
        ),
        migrations.AddField(
            model_name='point',
            name='allowed_users',
            field=models.ManyToManyField(
                blank=True,
                related_name='accessible_points',
                to='users.telegramprofile',
                verbose_name='Пользователи с доступом',
            ),
        ),
    ]
