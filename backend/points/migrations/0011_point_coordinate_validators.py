from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ('points', '0010_seed_general_point_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='point',
            name='lat',
            field=models.FloatField(
                validators=[MinValueValidator(-90), MaxValueValidator(90)],
                verbose_name='Широта',
            ),
        ),
        migrations.AlterField(
            model_name='point',
            name='lng',
            field=models.FloatField(
                validators=[MinValueValidator(-180), MaxValueValidator(180)],
                verbose_name='Долгота',
            ),
        ),
        migrations.AddConstraint(
            model_name='point',
            constraint=models.CheckConstraint(
                condition=Q(lat__gte=-90, lat__lte=90),
                name='point_latitude_range',
            ),
        ),
        migrations.AddConstraint(
            model_name='point',
            constraint=models.CheckConstraint(
                condition=Q(lng__gte=-180, lng__lte=180),
                name='point_longitude_range',
            ),
        ),
    ]
