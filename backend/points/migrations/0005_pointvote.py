"""Миграция схемы данных серверной части GeoMap."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Описывает операции миграции базы данных."""
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('points', '0004_move_telegramprofile_to_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='PointVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vote_type', models.CharField(choices=[('like', 'Лайк'), ('dislike', 'Дизлайк')], max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('point', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='points.point')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_votes', to='auth.user')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('point', 'user'), name='unique_point_vote_per_user')],
            },
        ),
    ]
