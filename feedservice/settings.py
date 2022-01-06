# -*- coding: utf-8 -*-

import os, os.path


def bool_env(val, default):
    """Replaces string based environment values with Python booleans"""

    if not val in os.environ:
        return default

    return True if os.environ.get(val) == 'True' else False


DEBUG = bool_env('MYGPOFS_DEBUG', True)

ADMINS = (
    ('Stefan Kögl', 'stefan@skoegl.net'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True


# Static asset configuration
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'htdocs', 'media'),
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.getenv('MYGPOFS_SECRET_KEY', '')

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'feedservice.urls'

WSGI_APPLICATION = 'feedservice.wsgi.application'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
        },
    }
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_extensions',
    'feedservice.parse',
    'feedservice.webservice',
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

BASE_URL='http://localhost:8080/'

import dj_database_url
DATABASES = {'default': dj_database_url.config()}

SOUNDCLOUD_CONSUMER_KEY = os.getenv('MYGPOFS_SOUNDCLOUD_CONSUMER_KEY', '')

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')

ALLOWED_HOSTS = [_f for _f in os.getenv('MYGPOFS_ALLOWED_HOSTS', '').split(';') if _f]


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')


FETCH_TIMEOUT = int(os.getenv('FETCH_TIMEOUT', 20))

# Need to monkey patch here or requests will fail
import eventlet
eventlet.monkey_patch()

### Sentry

try:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    # Sentry Data Source Name (DSN)
    sentry_dsn = os.getenv('SENTRY_DSN', '')
    if not sentry_dsn:
        raise ValueError('Could not set up sentry because ' 'SENTRY_DSN is not set')

    sentry_sdk.init(dsn=sentry_dsn, integrations=[DjangoIntegration()], send_default_pii=True)

except (ImportError, ValueError):
    pass




