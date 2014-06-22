import os, sys
from django.conf import settings

DIRNAME = os.path.dirname(__file__)
settings.configure(DEBUG=True,
    DATABASES={
        'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    ROOT_URLCONF='swiftbrowser.urls',
    SWIFT_AUTH_URL = 'http://127.0.0.1:8080/auth/v1.0',
    STORAGE_URL = 'http://127.0.0.1:8080/v1/', 
    STATIC_URL = '/static/',
    SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies',
    INSTALLED_APPS=(
        'django.contrib.sessions',
        'django.contrib.staticfiles',
        'swiftbrowser',
        'swiftbrowser.tests',
        'icons_mimetypes'),
        THUMBNAIL_USER = 'sw_thumbnails:sw_thumbnails',
        THUMBNAIL_AUTH_KEY = 'sw_thumbnails',
        THUMBNAIL_DURABILITY= '3600',
        THUMBNAIL_SIZE = (32, 32),
        TRASH_USER = 'sw_trash:sw_trash',
        TRASH_AUTH_KEY = 'sw_trash',
        TRASH_DURABILITY= '3600',
        SWIFT_AUTH_VERSION = 1)


from django.test.simple import DjangoTestSuiteRunner
test_runner = DjangoTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(['swiftbrowser', ])
if failures:
    sys.exit(failures)
