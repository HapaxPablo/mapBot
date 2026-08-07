from users.models import Notification, TelegramProfile


def notify_admins(message: str):
    recipients = TelegramProfile.objects.filter(
        role__in=(TelegramProfile.Role.ADMIN, TelegramProfile.Role.SUPERUSER),
    )
    Notification.objects.bulk_create([
        Notification(recipient=profile, message=message)
        for profile in recipients
    ])


def notify_map_users(profiles, message: str):
    recipients = profiles.exclude(role=TelegramProfile.Role.NEW_MEMBER)
    Notification.objects.bulk_create([
        Notification(recipient=profile, message=message)
        for profile in recipients
    ])
