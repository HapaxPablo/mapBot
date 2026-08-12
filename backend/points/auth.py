"""Компонент серверной части GeoMap."""

import hashlib
import hmac
import time
from urllib.parse import parse_qsl

from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
from rest_framework.authtoken.models import Token

from users.models import TelegramProfile
from users.notifications import notify_admins


def telegram_webapp_user(init_data: str) -> dict:
    """Выполняет операцию серверного компонента GeoMap."""
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop('hash', '')
    if not received_hash or not settings.BOT_TOKEN:
        raise ValueError('Invalid Telegram WebApp init data.')

    data_check_string = '\n'.join(
        f'{key}={value}' for key, value in sorted(values.items())
    )
    secret_key = hmac.new(
        b'WebAppData', settings.BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError('Invalid Telegram WebApp init data.')

    try:
        auth_date = int(values.get('auth_date', '0'))
    except (TypeError, ValueError) as exc:
        raise ValueError('Telegram WebApp auth date is invalid.') from exc
    now = time.time()
    if (
        auth_date <= 0
        or now - auth_date > settings.TELEGRAM_INIT_DATA_MAX_AGE
        or auth_date - now > settings.TELEGRAM_INIT_DATA_CLOCK_SKEW_SECONDS
    ):
        raise ValueError('Telegram WebApp init data has expired.')

    import json
    try:
        user = json.loads(values['user'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Telegram user is missing from WebApp init data.') from exc
    if not isinstance(user, dict) or not user.get('id'):
        raise ValueError('Telegram user is invalid.')
    return user


@transaction.atomic
def authenticate_telegram_user(*, telegram_id: int, username: str = '',
                               first_name: str = '', last_name: str = '',
                               rotate_token: bool = False):
    """Выполняет операцию серверного компонента GeoMap."""
    profile = TelegramProfile.objects.select_for_update().filter(telegram_id=telegram_id).first()
    if profile is None:
        user = User.objects.create_user(
            username=f'tg_{telegram_id}',
            first_name=first_name[:150],
            last_name=last_name[:150],
        )
        user.set_unusable_password()
        user.save(update_fields=('password',))
        profile = TelegramProfile.objects.create(
            user=user, telegram_id=telegram_id, username=username[:255],
            first_name=first_name[:255], last_name=last_name[:255],
            role=(TelegramProfile.Role.ADMIN
                  if telegram_id in settings.TELEGRAM_ADMIN_IDS
                  else TelegramProfile.Role.NEW_MEMBER),
        )
        notify_admins(
            f"👤 Зарегистрировался пользователь: {username or telegram_id} "
            f"(роль: {profile.get_role_display()})."
        )
    else:
        user = profile.user
        profile.username = username[:255]
        profile.first_name = first_name[:255]
        profile.last_name = last_name[:255]
        update_fields = ['username', 'first_name', 'last_name', 'updated_at']
        profile.save(update_fields=update_fields)

    if rotate_token:
        Token.objects.filter(user=user).delete()
    token, _ = Token.objects.get_or_create(user=user)
    return profile, token
