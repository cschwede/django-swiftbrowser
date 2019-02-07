""" Settings for Django project """
import os

DEBUG = os.environ.get("DEBUG", False)

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

USE_L10N = True
USE_TZ = True

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
TEMPLATE_DIRS = (os.path.join(PROJECT_PATH, 'templates'),)

MIDDLEWARE = (
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

SWIFT_AUTH_URL = os.environ.get(
    'SWIFT_AUTH_URL', 'http://127.0.0.1:8080/auth/v1.0')
SWIFT_AUTH_VERSION = os.environ.get('SWIFT_AUTH_VERSION', 1)  # 2 for keystone
STORAGE_URL = os.environ.get('STORAGE_URL', 'http://127.0.0.1:8080/v1/')
BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'de-de'
SECRET_KEY = os.environ.get("SECRET_KEY")
STATIC_URL = "http://cdnjs.cloudflare.com/ajax/libs/"

ALLOWED_HOSTS = [os.environ.get("ALLOWED_HOSTS", "127.0.0.1"), ]
