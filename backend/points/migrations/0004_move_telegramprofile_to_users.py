from django.db import migrations


def move_profiles(apps, schema_editor):
    OldProfile = apps.get_model('points', 'TelegramProfile')
    NewProfile = apps.get_model('users', 'TelegramProfile')

    for old in OldProfile.objects.all().iterator():
        profile, created = NewProfile.objects.get_or_create(
            telegram_id=old.telegram_id,
            defaults={
                'user_id': old.user_id,
                'username': old.username,
                'first_name': old.first_name,
                'last_name': old.last_name,
                'phone_number': old.phone_number,
                'role': old.role,
            },
        )
        if not created:
            continue
        user = profile.user
        user.is_staff = profile.role in {'admin', 'superuser'}
        user.is_superuser = profile.role == 'superuser'
        user.save(update_fields=('is_staff', 'is_superuser'))


class Migration(migrations.Migration):
    dependencies = [
        ('points', '0003_telegramprofile_phone_number'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(move_profiles, migrations.RunPython.noop),
        migrations.DeleteModel(name='TelegramProfile'),
    ]
