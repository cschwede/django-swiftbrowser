""" Settings for Django project """
import os

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

USE_L10N = True
USE_TZ = True

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIRS = (os.path.join(PROJECT_PATH, 'templates'),)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)

ROOT_URLCONF = 'swiftbrowser.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'swiftbrowser',
)

SWIFT_AUTH_URL = 'http://127.0.0.1:8080/auth/v1.0'
SWIFT_AUTH_VERSION = 1  # 2 for keystone
STORAGE_URL = 'http://127.0.0.1:8080/v1/'
BASE_URL = 'http://127.0.0.1:8000'  # default if using built-in runserver
SWAUTH_URL = 'http://127.0.0.1:8080/auth/v2'

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'
SECRET_KEY = 'DONT_USE_THIS_IN_PRODUCTION'
STATIC_URL = "http://cdnjs.cloudflare.com/ajax/libs/"

ALLOWED_HOSTS = ['127.0.0.1', 'insert_your_hostname_here']
