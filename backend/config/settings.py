"""Django settings for the AeonX backend.

Twelve-factor: every environment-specific value comes from the environment, so the
same image runs locally (docker compose + MinIO) and on AWS (EC2 + S3) with nothing
changed but the env file. See .env.example for the full list.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, str(default))).strip().lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [v.strip() for v in env(key, default).split(",") if v.strip()]


# ---------------------------------------------------------------- core

SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,api")

# Behind a load balancer / reverse proxy that terminates TLS, Django must be told
# the original request was HTTPS or it will build http:// URLs and redirect-loop.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF needs the scheme-qualified origin of anything that POSTs to the admin.
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "investors",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------- database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "aeonx"),
        "USER": env("POSTGRES_USER", "aeonx"),
        "PASSWORD": env("POSTGRES_PASSWORD", "aeonx"),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------- i18n

LANGUAGE_CODE = "en-in"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------- storage

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Documents go to S3-compatible object storage: MinIO locally, real S3 on AWS.
# Identical code path in both, so the S3 behaviour is exercised in development
# rather than first meeting it on deploy.
USE_S3 = env_bool("USE_S3", True)

if USE_S3:
    _s3_options = {
        "bucket_name": env("AWS_STORAGE_BUCKET_NAME", "aeonx-documents"),
        "region_name": env("AWS_S3_REGION_NAME", "ap-south-1"),
        "default_acl": None,
        "file_overwrite": False,
        # Investor filings are public records that regulators, exchanges and
        # shareholders bookmark and cite. A presigned URL expires and would turn
        # every one of those saved links into an error, so object URLs are
        # unsigned and permanent, and the bucket is fronted by a public-read
        # policy (see backend/README.md).
        "querystring_auth": False,
        # Filings are immutable once published; a year of browser caching is safe
        # because a corrected document is uploaded under a new key.
        "object_parameters": {"CacheControl": "public, max-age=31536000, immutable"},
    }
    _endpoint = env("AWS_S3_ENDPOINT_URL")
    if _endpoint:
        _s3_options["endpoint_url"] = _endpoint
    _custom_domain = env("AWS_S3_CUSTOM_DOMAIN")
    if _custom_domain:
        _s3_options["custom_domain"] = _custom_domain
        # django-storages assumes https for a custom domain. Local MinIO is plain
        # http, and getting this wrong yields URLs that look right and never load.
        _s3_options["url_protocol"] = env("AWS_S3_URL_PROTOCOL", "https:")
    # MinIO needs path-style addressing; virtual-hosted style assumes a real
    # AWS-shaped DNS name and fails against a bare host:port endpoint.
    if env_bool("AWS_S3_PATH_STYLE", bool(_endpoint)):
        _s3_options["addressing_style"] = "path"

    DEFAULT_FILE_STORAGE_OPTIONS = _s3_options
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": _s3_options,
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    # boto3 reads these from the environment; set explicitly so a stray shell
    # profile cannot silently point uploads at the wrong account.
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")
else:
    MEDIA_URL = "media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# Filings are occasionally large scanned PDFs. Stream anything over 5 MB to a temp
# file instead of buffering it in the worker's memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------------------------------------------------------------- api

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

# The document list is public data read by the static marketing site, which is
# served from a different origin (Vercel for staging, CloudFront in production).
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGIN_REGEXES = env_list("CORS_ALLOWED_ORIGIN_REGEXES")
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)
# GET-only public API: no cookies cross-origin, so no credentialed CORS.
CORS_ALLOW_CREDENTIALS = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
