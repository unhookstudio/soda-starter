import os

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "test-only-secret-key-that-is-long-enough-for-hs256"
NINJA_JWT = {
    **NINJA_JWT,  # noqa: F405
    "SIGNING_KEY": "test-only-jwt-signing-key-that-is-long-enough-for-hs256",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "django_db"),
        "USER": os.environ.get("POSTGRES_USER", "django_user"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "django_pass"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
        "CONN_MAX_AGE": 0,
    }
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": BASE_DIR / ".test_media",  # noqa: F405
            "base_url": "/media/",
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN = False
