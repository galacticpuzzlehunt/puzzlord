from settings.base import *

DEBUG = True

EMAIL_SUBJECT_PREFIX = "[\u2708\u2708\u2708DEVELOPMENT\u2708\u2708\u2708] "

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "django-file": {
            "format": "%(asctime)s [%(levelname)s] %(module)s\n%(message)s"
        },
        "puzzles-file": {"format": "%(asctime)s [%(levelname)s] %(message)s"},
        "django-console": {
            "format": "\033[34;1m%(asctime)s \033[35;1m[%(levelname)s] \033[34;1m%(module)s\033[0m\n%(message)s"
        },
        "puzzles-console": {
            "format": "\033[36;1m%(asctime)s \033[35;1m[%(levelname)s] \033[36;1m%(name)s\033[0m %(message)s"
        },
    },
    "handlers": {
        "django": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "./logs/django.log",
            "formatter": "django-file",
        },
        "puzzle": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "./logs/puzzle.log",
            "formatter": "puzzles-file",
        },
        "request": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "./logs/request.log",
            "formatter": "puzzles-file",
        },
        "django-console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "django-console",
        },
        "puzzles-console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "puzzles-console",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["django", "django-console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.db.backends": {
            "level": "DEBUG",
            "handlers": ["django"],
            "propagate": False,
        },
        "django.server": {
            "level": "DEBUG",
            "handlers": ["django"],
            "propagate": False,
        },
        "django.utils.autoreload": {
            "level": "INFO",
            "propagate": True,
        },
        "puzzles": {
            "handlers": ["puzzles-console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "puzzles.puzzle": {
            "handlers": ["puzzle", "puzzles-console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "puzzles.request": {
            "handlers": ["request", "puzzles-console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
