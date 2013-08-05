""" Settings for Django project """
import os

DATABASES = { }

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIRS = (os.path.join(PROJECT_PATH, 'templates'), )

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)

ROOT_URLCONF = 'swiftbrowser.urls'

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'swiftbrowser', 
)


# Adapt the following settings to your needs


DEBUG = True
USE_L10N = True
USE_TZ = True


SWIFT_AUTH_URL = 'http://127.0.0.1:8080/auth/v1.0'
STORAGE_URL = 'http://127.0.0.1:8080/v1/'

SECRET_KEY = "DONT_USE_THIS_IN_PRODUCTION"
STATIC_URL = "/static/"
STATIC_ROOT = "/home/cschwede/myproj/static/"

try:
    from local_settings import *
except ImportError:
    pass
