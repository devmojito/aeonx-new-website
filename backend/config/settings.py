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

DEV_SECRET_KEY = "dev-only-insecure-key-change-me"
SECRET_KEY = env("DJANGO_SECRET_KEY", DEV_SECRET_KEY)
# Defaults to FALSE. Every .env in the project sets this explicitly, so the only
# way to reach the default is to forget the variable entirely -- and forgetting it
# on the instance must not silently produce a debug-mode production serving
# tracebacks, settings and SQL to the public internet.
DEBUG = env_bool("DJANGO_DEBUG", False)

# The dev key is published in this repository. With it, session cookies and CSRF
# tokens are forgeable, so a production process holding it is an authentication
# bypass waiting to be noticed. Refuse to start rather than run compromised.
if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is still the development key while DJANGO_DEBUG is "
        "false. Generate one: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )
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
    # HSTS cannot be withdrawn once a browser has cached it, and
    # includeSubDomains binds every subdomain of aeonx.digital, several of which
    # are outside this project and may not be HTTPS-ready. So both are env-driven
    # and start short: run an hour through cutover, confirm nothing on the domain
    # broke, then raise to 31536000 and turn includeSubDomains on deliberately.
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False)

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
    "contacts",
    "blog",
    "siteconfig",
    "manage_ui",
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

# DRF's rate throttling reads/writes the cache. The default LocMemCache is
# per-PROCESS, and gunicorn runs multiple worker processes -- each would keep
# its own separate count, so a caller hitting different workers across
# requests could exceed the configured rate by roughly the worker count before
# any single worker's counter crossed the limit. A shared cache is required
# for the limit to mean what it says; DatabaseCache reuses Postgres rather
# than adding Redis/Memcached for one small counter table.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        # Django's default MAX_ENTRIES is 300, and it culls a third of the table
        # once that is passed. The throttle is effectively the only tenant, so
        # every distinct visitor holds a row: past 300 callers in a window, real
        # counters get evicted and the rate limit silently stops applying to
        # whoever was culled. 10000 rows of counters is nothing on RDS.
        "OPTIONS": {"MAX_ENTRIES": 10000},
    }
}

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
STATICFILES_DIRS = [BASE_DIR / "static"]

# Send people to the custom admin, not Django's, after a login redirect.
LOGIN_URL = "/manage/login/"
LOGIN_REDIRECT_URL = "/manage/"

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
    # The public API is anonymous by design. DRF's default list would also enable
    # BasicAuthentication, which turns every endpoint into a password oracle that
    # answers before the throttle runs, and SessionAuthentication, whose CSRF
    # enforcement makes the contact form 403 for anyone holding a /manage/ session
    # now that the site and the API share one CloudFront origin.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    # CloudFront APPENDS the viewer address to whatever X-Forwarded-For the client
    # sent rather than replacing it, so only the LAST hop is trustworthy. Left
    # unset, DRF keys the throttle on the whole chain, and a caller who varies a
    # forged prefix mints a fresh bucket on every request. 1 = trust one proxy
    # (CloudFront) and key on the address it appended.
    "NUM_PROXIES": 1,
    "DEFAULT_THROTTLE_RATES": {
        # Generous enough that a real visitor never notices; tight enough that
        # a script cannot flood the inbox or the database. Per-IP, so one
        # aggressive caller cannot exhaust the budget for everyone else.
        "contact": env("CONTACT_THROTTLE_RATE", "10/hour"),
    },
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(
        "rest_framework.renderers.BrowsableAPIRenderer"
    )

# In production the static site and this API are served by the SAME CloudFront
# distribution, so every browser call is same-origin and CORS does not apply at
# all. These stay for local development, where the site is opened from a file or
# a different port. Production should set CORS_ALLOW_ALL_ORIGINS=false and leave
# the lists empty rather than naming an origin that never sends an Origin header.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGIN_REGEXES = env_list("CORS_ALLOWED_ORIGIN_REGEXES")
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", DEBUG)
# GET-only public API: no cookies cross-origin, so no credentialed CORS.
CORS_ALLOW_CREDENTIALS = False

# ---------------------------------------------------------------- email

# Local/staging default to the console backend so nothing tries to reach a
# real SMTP server that was never configured -- a submission still fails
# closed to "logged, not sent" rather than raising. Production sets
# EMAIL_BACKEND=django_ses.SESBackend, which signs with the EC2 instance role
# so no mail credentials ever sit on the box.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
# Must be an identity verified in AWS_SES_REGION_NAME. Only sales@aeonx.digital
# is verified, and SES rejects an unverified From outright, so this is not a
# cosmetic default.
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "sales@aeonx.digital")

# django-ses defaults the region to us-east-1, where nothing is verified, and
# fails with MessageRejected rather than anything that names the real cause.
# Both are set so the behaviour does not depend on which version pip resolves.
AWS_SES_REGION_NAME = env("AWS_SES_REGION_NAME", "ap-south-1")
AWS_SES_REGION_ENDPOINT = env(
    "AWS_SES_REGION_ENDPOINT", f"email.{AWS_SES_REGION_NAME}.amazonaws.com"
)
# django-ses defaults this to 0.5, which makes it call ses:GetSendQuota before
# every send to rate-limit itself. The EC2 instance role grants ses:SendEmail and
# nothing else, so that call raises AccessDenied and no mail goes out at all.
# 0 disables the check (the library documents 0/None as the off switch).
# Nothing is lost: the throttle assumes it is the only SES client and exists to
# stay under the account send rate, while this app sends contact-form
# notifications that DRF already caps at CONTACT_THROTTLE_RATE per IP -- orders
# of magnitude below any SES limit.
AWS_SES_AUTO_THROTTLE = 0

# Where a new contact-form lead is sent. Empty disables the notification (the
# submission is still saved -- see contacts/views.py) rather than raising, so
# a missing env var cannot take the whole endpoint down.
CONTACT_NOTIFY_EMAIL = env("CONTACT_NOTIFY_EMAIL", "sales@aeonx.digital")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
