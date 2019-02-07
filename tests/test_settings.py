from swiftbrowser.settings import *  # NOQA
SECRET_KEY = "DONT_USE_THIS_IN_PRODUCTION"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
