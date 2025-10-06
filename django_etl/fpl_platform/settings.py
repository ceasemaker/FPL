from pathlib import Path
import os

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", os.getenv("DJANGO_SECRET_KEY", "insecure-default-secret-key-change-me"))
DEBUG = env_bool("DEBUG", default=env_bool("DJANGO_DEBUG", default=False))
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", os.getenv("DJANGO_ALLOWED_HOSTS", "*")).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "etl",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add WhiteNoise for static files
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fpl_platform.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "fpl_platform.wsgi.application"
ASGI_APPLICATION = "fpl_platform.asgi.application"

from typing import Any


def _postgres_database() -> dict[str, Any]:
    # Support Render's DATABASE_URL format
    database_url = os.getenv("DATABASE_URL")
    print(f"DEBUG: DATABASE_URL exists: {bool(database_url)}")
    if database_url:
        print(f"DEBUG: DATABASE_URL value (masked): {database_url[:20]}...")
        # Parse DATABASE_URL (format: postgresql://user:password@host:port/dbname)
        try:
            from urllib.parse import urlparse
            result = urlparse(database_url)
            print(f"DEBUG: Parsed scheme: {result.scheme}, hostname: {result.hostname}")
            if result.scheme in ['postgresql', 'postgres']:
                config = {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": result.path[1:],  # Remove leading '/'
                    "USER": result.username,
                    "PASSWORD": result.password,
                    "HOST": result.hostname,
                    "PORT": result.port or 5432,
                }
                print(f"DEBUG: Using parsed DATABASE_URL with host: {config['HOST']}")
                return config
        except Exception as e:
            print(f"ERROR: Failed to parse DATABASE_URL: {e}")
            # Fall through to individual env vars
    
    # Fallback to individual environment variables
    print("DEBUG: Using individual environment variables")
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "fpl_db"),
        "USER": os.getenv("POSTGRES_USER", "fpl_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "fpl_password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
    print(f"DEBUG: Fallback config host: {config['HOST']}")
    return config


def _sqlite_database() -> dict[str, Any]:
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


print(f"DEBUG: Checking database config - DATABASE_URL: {bool(os.getenv('DATABASE_URL'))}, POSTGRES_HOST: {bool(os.getenv('POSTGRES_HOST'))}, USE_POSTGRES: {env_bool('USE_POSTGRES', default=False)}")

if os.getenv("DATABASE_URL") or os.getenv("POSTGRES_HOST") or env_bool("USE_POSTGRES", default=False):
    print("DEBUG: Using PostgreSQL")
    DATABASES = {"default": _postgres_database()}
else:
    print("DEBUG: Using SQLite")
    DATABASES = {"default": _sqlite_database()}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TZ", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis Configuration
# Support both REDIS_URL (Render format) and individual components (local dev)
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB = os.getenv("REDIS_DB", "0")
    
    # Build Redis URL with optional password
    if REDIS_PASSWORD:
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "fpl",
        "TIMEOUT": 1800,  # 30 minutes default
    }
}

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/London'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1 hour max per task
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
