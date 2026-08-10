import os

from .test import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "starter_test"),
        "USER": os.environ.get("POSTGRES_USER", "starter"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "starter"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
        "CONN_MAX_AGE": 0,
    }
}
