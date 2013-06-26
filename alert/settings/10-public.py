# Celery imports
import djcelery
djcelery.setup_loader()
# Needed by Celery to avoid using relative path imports. See:
# http://docs.celeryq.org/en/latest/userguide/tasks.html#automatic-naming-and-relative-imports
import os
import sys
sys.path.append(os.getcwd())

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False


# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.messages.context_processors.messages',
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'alert.urls'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.humanize',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    'djcelery',
    'south',
    'alerts',
    'casepage',
    'citations',
    'contact',
    'coverage',
    'custom_filters',
    'favorites',
    'honeypot',
    'lib',
    'maintenance_warning',
    'pinger',
    'scrapers',
    'search',
    'userHandling',
]


# This is where the @login_required decorator redirects. By default it's /accounts/login.
# Also where users are redirected after they login. Default: /account/profile
LOGIN_URL = "/sign-in/"
LOGIN_REDIRECT_URL = "/"

# Per documentation, we need this to extend the User model
# (http://docs.djangoproject.com/en/dev/topics/auth/#storing-additional-information-about-users)
AUTH_PROFILE_MODULE = 'userHandling.UserProfile'

# These remap some of the the messages constants to correspond with blueprint
from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.DEBUG : 'notice',
    message_constants.INFO : 'notice',
    message_constants.WARNING : 'error',
}

# Solr settings
SOLR_URL = 'http://127.0.0.1:8983/solr'


# Public celery settings
# Rate limits aren't used, so disable them across the board for better performance
CELERY_DISABLE_RATE_LIMITS = True
CELERY_SEND_TASK_ERROR_EMAILS = True



# email settings
SERVER_EMAIL = 'noreply@courtlistener.com'
DEFAULT_FROM_EMAIL = 'noreply@courtlistener.com'

SITEMAP_PING_URLS = (
    'http://search.yahooapis.com/SiteExplorerService/V1/ping',
    'http://www.google.com/webmasters/tools/ping',
    'http://www.bing.com/webmaster/ping.aspx',
)

# Disabled b/c there are issues with how CACHE_MIDDLEWARE_ANONYMOUS_ONLY is implemented.
#CACHE_MIDDLEWARE_SECONDS = (60*15)
#CACHE_MIDDLEWARE_KEY_PREFIX = "alert"
#CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

DEFAULT_CHARSET = 'utf-8'

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
