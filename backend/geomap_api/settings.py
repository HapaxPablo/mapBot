import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / '.env')


SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1'
).split(',')
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    ''
).split(',')
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework.authtoken',
    'corsheaders',
    'django_minio_backend',
    'rest_framework',
    'channels',
    'users',
    'points',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'geomap_api.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'geomap_api.wsgi.application'
ASGI_APPLICATION = 'geomap_api.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# ------------------------------- DATABASE ---------------------------------- #
# По умолчанию sqlite для лёгкого старта, можно переключить на postgres из .env
if os.environ.get('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB'),
            'HOST': os.environ.get('POSTGRES_HOST'),
            'USER': os.environ.get('POSTGRES_USER'),
            'PORT': os.environ.get('POSTGRES_PORT', 5432),
            'PASSWORD': os.environ.get('POSTGRES_PASS'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Krasnoyarsk'
USE_I18N = True
USE_TZ = False
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# --------------------------------- MINIO ------------------------------------ #
# Хранилище фото точек, отдельный бакет от rmc_rest_api, но тот же MinIO-инстанс
# можно переиспользовать (см. MINIO_ENDPOINT в .env главного проекта).
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'files:9000')
MINIO_ACCESS_KEY = os.environ.get('MINIO_STORAGE_ACCESS_KEY')
MINIO_SECRET_KEY = os.environ.get('MINIO_STORAGE_SECRET_KEY')
MINIO_USE_HTTPS = os.environ.get('MINIO_HTTPS', 'false').lower() == 'true'
MINIO_EXTERNAL_ENDPOINT = os.environ.get('MINIO_EXTERNAL_ENDPOINT')
MINIO_EXTERNAL_ENDPOINT_USE_HTTPS = os.environ.get('MINIO_EXTERNAL_HTTPS', 'true').lower() == 'true'
MINIO_REGION = os.environ.get('MINIO_REGION', 'us-east-1')

MINIO_PUBLIC_BUCKETS = []
MINIO_PRIVATE_BUCKETS = ['geomap-media']

STORAGES = {
    'default': {
        'BACKEND': 'django_minio_backend.models.MinioBackend',
        'OPTIONS': {
            'MINIO_ENDPOINT': MINIO_ENDPOINT,
            'MINIO_ACCESS_KEY': MINIO_ACCESS_KEY,
            'MINIO_SECRET_KEY': MINIO_SECRET_KEY,
            'MINIO_USE_HTTPS': MINIO_USE_HTTPS,
            'MINIO_REGION': MINIO_REGION,
            'MINIO_EXTERNAL_ENDPOINT': MINIO_EXTERNAL_ENDPOINT,
            'MINIO_EXTERNAL_ENDPOINT_USE_HTTPS': MINIO_EXTERNAL_ENDPOINT_USE_HTTPS,
            'MINIO_PRIVATE_BUCKETS': MINIO_PRIVATE_BUCKETS,
            'MINIO_PUBLIC_BUCKETS': MINIO_PUBLIC_BUCKETS,
            'MINIO_URL_EXPIRY_HOURS': timedelta(days=7),
            'MINIO_CONSISTENCY_CHECK_ON_START': False,
        }
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# ------------------------------- REST / CORS -------------------------------- #
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'points.authentication.TokenAuthenticationWithoutApiKey',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
}

# WebApp читает карту из браузера Telegram — открыт для всех источников.
CORS_ALLOW_ALL_ORIGINS = True

# Секретный ключ, которым бот подписывает свои запросы на запись (создание точек,
# лайки/дизлайки, загрузка фото). Обычные GET-запросы (для карты) открыты всем.
BOT_API_KEY = os.environ.get('BOT_API_KEY', 'change-me')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
TELEGRAM_INIT_DATA_MAX_AGE = int(os.environ.get('TELEGRAM_INIT_DATA_MAX_AGE', 86400))
TELEGRAM_ADMIN_IDS = {
    int(value.strip())
    for value in os.environ.get(
        'TELEGRAM_ADMIN_IDS', os.environ.get('ADMIN_ID', '')
    ).split(',')
    if value.strip().isdigit()
}
