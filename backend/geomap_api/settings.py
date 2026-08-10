import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / '.env')


SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
APP_ENV = os.environ.get('APP_ENV', 'development').strip().lower()
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    '',
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
    'geomap_api.middleware.AllowLocalNullOriginMiddleware',
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

REDIS_URL = os.environ.get('REDIS_URL', '').strip()
if REDIS_URL:
    # RedisChannelLayer uses a blocking BZPOPMIN read while a WebSocket waits
    # for a group event. A finite socket read timeout turns an idle socket into
    # a disconnect, so keep the read timeout unlimited and limit only connect.
    redis_host = {
        'address': REDIS_URL,
        'socket_connect_timeout': 5,
        'socket_timeout': None,
        'health_check_interval': 30,
    }
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [redis_host],
                'prefix': 'geomap',
                'expiry': 60,
                'group_expiry': 86400,
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ------------------------------- DATABASE ---------------------------------- #
# По умолчанию sqlite для лёгкого старта, можно переключить на postgres из .env.
# Test mode deliberately ignores production database variables so CI can run
# without a PostgreSQL service.
if os.environ.get('TESTING', '').lower() in {'1', 'true', 'yes'}:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
elif os.environ.get('POSTGRES_DB'):
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
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# --------------------------------- MINIO ------------------------------------ #
# Хранилище фото точек, отдельный бакет
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
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/minute',
        'user': '240/minute',
    },
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024



# Секретный ключ, которым бот подписывает свои запросы на запись (создание точек,
# лайки/дизлайки, загрузка фото). Обычные GET-запросы (для карты) открыты всем.
BOT_API_KEY = os.environ.get('BOT_API_KEY', 'change-me')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
TOKEN_MAX_AGE_SECONDS = int(os.environ.get('TOKEN_MAX_AGE_SECONDS', 2592000))
TELEGRAM_INIT_DATA_MAX_AGE = int(os.environ.get('TELEGRAM_INIT_DATA_MAX_AGE', 86400))
TELEGRAM_INIT_DATA_CLOCK_SKEW_SECONDS = int(
    os.environ.get('TELEGRAM_INIT_DATA_CLOCK_SKEW_SECONDS', 60)
)
TELEGRAM_ADMIN_IDS = {
    int(value.strip())
    for value in os.environ.get(
        'TELEGRAM_ADMIN_IDS', os.environ.get('ADMIN_ID', '')
    ).split(',')
    if value.strip().isdigit()
}

if APP_ENV == 'production':
    if DEBUG:
        raise RuntimeError('DEBUG must be false in production.')
    if SECRET_KEY == 'dev-secret-key':
        raise RuntimeError('SECRET_KEY must be configured in production.')
    if BOT_API_KEY in {'', 'change-me'}:
        raise RuntimeError('BOT_API_KEY must be configured in production.')
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN must be configured in production.')
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise RuntimeError('ALLOWED_HOSTS must be restricted in production.')
    if not REDIS_URL:
        raise RuntimeError('REDIS_URL must be configured in production.')

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SECURE = True
