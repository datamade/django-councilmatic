import sys
import os
from importlib.util import find_spec

import dj_database_url

from .test_config_jurisdiction import *  # noqa


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "replacethiswithsomethingsecret"

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

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "opencivicdata.core",
    "opencivicdata.legislative",
    "councilmatic_core",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
]

# The search and CMS layers are optional. Enable each one when its
# extra is installed, e.g. pip install -e .[search] or .[cms]

if find_spec("haystack"):
    INSTALLED_APPS += [
        "haystack",
        "councilmatic_search",
    ]

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "haystack.backends.simple_backend.SimpleEngine",
        },
    }

if find_spec("wagtail"):
    INSTALLED_APPS += [
        "wagtail.contrib.forms",
        "wagtail.contrib.redirects",
        "wagtail.contrib.typed_table_block",
        "wagtail.embeds",
        "wagtail.sites",
        "wagtail.users",
        "wagtail.snippets",
        "wagtail.documents",
        "wagtail.images",
        "wagtail.search",
        "wagtail.admin",
        "wagtail",
        "modelcluster",
        "taggit",
        "councilmatic_cms",
    ]

    MIDDLEWARE += [
        "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    ]

    WAGTAIL_SITE_NAME = "Chicago Councilmatic"
    WAGTAILADMIN_BASE_URL = "http://localhost:8000"

ROOT_URLCONF = "tests.urls"

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
