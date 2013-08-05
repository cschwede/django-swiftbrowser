from settings import *

# make tests faster
SOUTH_TESTS_MIGRATE = False
DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3'}
