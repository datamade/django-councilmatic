import sys
import os

import dj_database_url

from .test_config_jurisdiction import *  # noqa


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "replacethiswithsomethingsecret"
USING_NOTIFICATIONS = False

DEBUG = True

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {}

DATABASES["default"] = dj_database_url.parse(
    f"postgres://postgres:postgres@localhost:{os.getenv('PG_PORT', 5432)}/django_councilmatic",
    conn_max_age=600,
    ssl_require=True if os.getenv("POSTGRES_REQUIRE_SSL") else False,
    engine="django.contrib.gis.db.backends.postgis",
)

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "haystack.backends.simple_backend.SimpleEngine",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

FLUSH_KEY = "super secret junk"

DISQUS_SHORTNAME = None

ANALYTICS_TRACKING_CODE = ""

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "opencivicdata.core",
    "opencivicdata.legislative",
    "councilmatic_core",
    "haystack",
    "adv_cache_tag",
)

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
)

ROOT_URLCONF = "councilmatic_core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "councilmatic_core.views.city_context",
            ],
        },
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/Chicago"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

ADV_CACHE_INCLUDE_PK = True

AWS_KEY = ""
AWS_SECRET = ""

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": sys.stdout,
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
