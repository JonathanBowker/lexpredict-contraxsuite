# -*- coding: utf-8 -*-
"""
Copyright (C) 2017, ContraxSuite, LLC

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

You can also be released from the requirements of the license by purchasing
a commercial license from ContraxSuite, LLC. Buying such a license is
mandatory as soon as you develop commercial activities involving ContraxSuite
software without disclosing the source code of your own applications.  These
activities include: offering paid services to customers as an ASP or "cloud"
provider, processing documents on the fly in a web application,
or shipping ContraxSuite within a closed source product.

Django settings for contraxsuite_services project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
from __future__ import absolute_import, unicode_literals

# Standard imports
import datetime
import environ
import platform
import os
import re
import sys
import warnings
# import importlib

# Third-party imports
from celery.schedules import crontab
from kombu import Queue

# Django imports
from django.urls import reverse_lazy

# App imports
from contraxsuite_logging import prepare_log_dirs   # ContraxsuiteJSONFormatter
# from apps.common.db_cache.file_storage.local_file_access import ContraxsuiteLocalFileStorage

warnings.filterwarnings('ignore',
                        message='''Trying to unpickle estimator|The psycopg2 wheel package will be renamed|numpy.core.umath_tests''')

ROOT_DIR = environ.Path(__file__) - 2
PROJECT_DIR = ROOT_DIR.path('contraxsuite_services')
APPS_DIR = PROJECT_DIR.path('apps')

DEBUG = False
DEBUG_SQL = False
DEBUG_TEMPLATE = False

INTERNAL_IPS = ['127.0.0.1', '::1']

# APP CONFIGURATION
# ------------------------------------------------------------------------------
INSTALLED_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'suit',  # Admin
    'django.contrib.admin',

    # THIRD_PARTY_APPS
    'crispy_forms',  # Form layouts
    'allauth',  # registration
    'allauth.account',  # registration
    'allauth.socialaccount',  # registration
    'simple_history',  # historical records
    'django_celery_beat',  # task scheduling via DB
    'django_celery_results',  # for celery tasks
    'filebrowser',  # browse/upload documents
    'django_extensions',
    'pipeline',  # compressing js, css
    'ckeditor',  # editor
    # Useful template tags:
    'django.contrib.humanize',
    'dal',
    'dal_select2',
    # Configure the django-otp package
    'django_otp',
    'django_otp.plugins.otp_email',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    # Enable two-factor auth
    'allauth_2fa',
    'constance',  # django-constance
    'constance.backends.database',  # django-constance backend
    'corsheaders',  # inject CORS headers into response
    'django_json_widget',  # widget for json field for admin site

    # django-rest
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'rest_auth.registration',
    'rest_framework_swagger',
    'rest_framework_tracking',

    'channels',

    # LOCAL_APPS
    # 'apps.common',
    # 'apps.analyze',
    # 'apps.document',
    # 'apps.annotator',
    # 'apps.extract',
    # 'apps.project',
    # 'apps.deployment',
    # 'apps.task',
    # 'apps.users',
    # 'apps.employee',
    # 'apps.fields',
    # 'apps.lease',
    # 'apps.dump'
)

apps_dir = PROJECT_DIR('apps')
PROJECT_APPS = tuple('apps.%s' % name for name in os.listdir(apps_dir)
                     if os.path.isdir(os.path.join(apps_dir, name)) and '__' not in name)
INSTALLED_APPS += PROJECT_APPS


# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE = (
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # simple history middleware
    'simple_history.middleware.HistoryRequestMiddleware',
    # custom middleware
    # 'apps.common.middleware.AutoLoginMiddleware',
    'apps.common.middleware.LoginRequiredMiddleware',
    'apps.common.middleware.Response500ErrorMiddleware',
    'apps.common.middleware.Response404ErrorMiddleware',
    'apps.common.middleware.HttpResponseNotAllowedMiddleware',
    'apps.common.middleware.RequestUserMiddleware',
    'apps.common.middleware.AppEnabledRequiredMiddleware',
    'apps.common.middleware.CookieMiddleware',
    # django-pipeline middleware for minifying data
    'pipeline.middleware.MinifyHTMLMiddleware',
    # Configure the django-otp package. Note this must be after the
    # AuthenticationMiddleware.
    'django_otp.middleware.OTPMiddleware',
    # Reset login flow middleware. If this middleware is included, the login
    # flow is reset if another page is loaded between login and successfully
    # entering two-factor credentials.
    'allauth_2fa.middleware.AllauthTwoFactorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    PROJECT_DIR('fixtures'),
)

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
SITE_NAME = 'contraxsuite_services'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        # 'DIRS': [
        #     PROJECT_DIR('templates'),
        #     PROJECT_DIR('apps')
        # ],
        # 'APP_DIRS': True,
        'OPTIONS': {
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            'loaders': [
                'apps.common.loaders.Loader',
                # 'django.template.loaders.app_directories.Loader',
                # ('django.template.loaders.filesystem.Loader', [PROJECT_DIR('templates')])
            ],
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'constance.context_processors.config',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'apps.common.context_processors.common'
            ],
        },
    },
]

# email settings
DEFAULT_FROM_EMAIL = '"ContraxSuite" <support@contraxsuite.com>'
DEFAULT_REPLY_TO = '"ContraxSuite" <support@contraxsuite.com>'
SERVER_EMAIL = '"ContraxSuite" <support@contraxsuite.com>'

EMAIL_TIMEOUT = 30
EMAIL_PARALLEL_SEND = 8

# See: http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# https://demo.contraxsuite.com/${BASE_URL}/document/documents
# /api and /rest-auth are put to the root ignoring base path
# If using BASE_URL for calculating other params anywhere to the bottom of config file please
# put their definition after the local_settings is imported to allow re-configurin BASE_URL
# in local_settings.
BASE_URL = ''

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = PROJECT_DIR('staticfiles')

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    ROOT_DIR('static'),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = PROJECT_DIR('media')

# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'urls'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'wsgi.application'
ASGI_APPLICATION = 'routing.application'

# django-pipeline settings
# see: https://django-pipeline.readthedocs.io/en/latest/
STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'
PIPELINE_ENABLED = True
PIPELINE = {
    'CSS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'JS_COMPRESSOR': 'pipeline.compressors.yuglify.YuglifyCompressor',
    'STYLESHEETS': {
        'theme_css': {
            'source_filenames': (
                'theme/css/bootstrap.css',
                'theme/css/style.css',
                'theme/css/swiper.css',
                'theme/css/dark.css',
                'theme/css/font-icons.css',
                'theme/css/animate.css',
                'theme/css/magnific-popup.css',
                'theme/css/responsive.css',
            ),
            'output_filename': 'pipeline_theme.css',
        },
        'custom_css': {
            'source_filenames': (
                'css/project.css',
                'vendor/tagsinput/bootstrap-tagsinput.css',
            ),
            'output_filename': 'pipeline_custom.css',
        },
        'custom_jqwidgets_css': {
            'source_filenames': (
                'vendor/jqwidgets/styles/jqx.base.css',
            ),
            'output_filename': 'pipeline_custom_jqwidgets.css',
        },
    },
    'JAVASCRIPT': {
        'custom_js': {
            'source_filenames': (
                'vendor/tagsinput/bootstrap-tagsinput.js',
            ),
            'output_filename': 'pipeline_custom.js',
        },
    }
}

# PASSWORD VALIDATION
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
# ------------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# allauth settings
# http://django-allauth.readthedocs.io/en/latest/overview.html
ACCOUNT_LOGOUT_REDIRECT_URL = 'account_login'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_ALLOW_REGISTRATION = False
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 10
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 5
# ACCOUNT_ADAPTER = 'apps.users.adapters.AccountAdapter'
# Set the allauth adapter to be the 2FA adapter
# ACCOUNT_ADAPTER = 'allauth_2fa.adapter.OTPAdapter'
ACCOUNT_ADAPTER = 'apps.users.adapters.AccountAdapter'
ACCOUNT_FORMS = {'login': 'auth.CustomLoginForm'}
SOCIALACCOUNT_ADAPTER = 'apps.users.adapters.SocialAccountAdapter'

# Custom user app defaults
# Select the correct user model
AUTH_USER_MODEL = 'users.User'
LOGIN_REDIRECT_URL = 'users:redirect'
LOGIN_URL = reverse_lazy('account_login')

# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'

STATS_URLS = ['https://stats.contraxsuite.com/api/v1/stats/', 'http://52.200.197.133/api/v1/stats/']

# celery
# CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_BROKER_URL = 'amqp://contrax1:contrax1@localhost:5672/contrax1_vhost'
CELERY_BROKER_HEARTBEAT = 0
CELERY_RESULT_BACKEND = 'apps.task.celery_backend.database:DatabaseBackend'
CELERY_UPDATE_MAIN_TASK_ON_EACH_SUB_TASK = False
CELERY_RESULT_EXPIRES = 0
# CELERY_WORKER_HIJACK_ROOT_LOGGER = False

CELERY_QUEUE_SERIAL = 'serial'

TASK_NAME_AUTO_REINDEX = 'apps.rawdb.tasks.auto_reindex'

TASK_NAME_MANUAL_REINDEX = 'RawDB: Reindex'

TASK_NAME_UPDATE_PROJECT_DOCUMENTS = 'RawDB: Update project documents'

TASK_NAME_UPDATE_ASSIGNEE_FOR_DOCUMENTS = 'RawDB: Update assignee for documents'

TASK_NAME_UPDATE_STATUS_NAME_FOR_DOCUMENTS = 'RawDB: Update status name for documents'

TASK_NAME_IMANAGE_TRIGGER_SYNC = 'apps.imanage_integration.tasks.trigger_imanage_sync'

TASK_NAME_TRIGGER_DIGESTS = 'apps.notifications.tasks.trigger_digests'

CELERY_BEAT_SCHEDULE = {
    # Backend cleanup is disabled to not miss debug info after long loading
    # 'advanced_celery.backend_cleanup': {
    #     'task': 'advanced_celery.clean_tasks',
    #     'schedule': crontab(hour=7, minute=30, day_of_week='mon')
    # },
    'advanced_celery.track_tasks': {
        'task': 'advanced_celery.track_tasks',
        'schedule': 10.0,
        'options': {'queue': CELERY_QUEUE_SERIAL, 'expires': 10},
    },
    'advanced_celery.clean_sub_tasks': {
        'task': 'advanced_celery.clean_sub_tasks',
        'schedule': 60.0,
        'options': {'queue': CELERY_QUEUE_SERIAL, 'expires': 60},
    },
    'advanced_celery.retrain_dirty_fields': {
        'task': 'advanced_celery.retrain_dirty_fields',
        'schedule': 60.0,
        'options': {'queue': CELERY_QUEUE_SERIAL, 'expires': 60},
    },
    'advanced_celery.track_session_completed': {
        'task': 'advanced_celery.track_session_completed',
        'schedule': 120.0,
        'options': {'queue': CELERY_QUEUE_SERIAL, 'expires': 120},
    },
    'deployment.usage_stats': {
        'task': 'deployment.usage_stats',
        'schedule': 60 * 60 * 12,
        'options': {'queue': 'default', 'expires': 60 * 60 * 12},
    },
    'apps.rawdb.tasks.adapt_table_and_reindex_doc_type': {
        'task': TASK_NAME_AUTO_REINDEX,
        'schedule': 60,
        'options': {'queue': CELERY_QUEUE_SERIAL, 'expires': 60},
    },
    'apps.imanage_integration.tasks.trigger_imanage_sync': {
        'task': TASK_NAME_IMANAGE_TRIGGER_SYNC,
        'schedule': 60,
        'options': {'queue': 'serial', 'expires': 60},
    },
    'apps.notifications.trigger_digests': {
        'task': TASK_NAME_TRIGGER_DIGESTS,
        'schedule': 5,
        'options': {'queue': 'serial', 'expires': 5},
    }
}

EXCLUDE_FROM_TRACKING = {
    'celery.chord_unlock',
    'advanced_celery.track_tasks',
    'advanced_celery.track_session_completed',
    'advanced_celery.update_main_task',
    'advanced_celery.clean_sub_tasks',
    'advanced_celery.clean_dead_tasks',
    'advanced_celery.clean_tasks',
    'deployment.usage_stats',
    'advanced_celery.retrain_dirty_fields',
    'apps.rawdb.tasks.cache_document_fields_for_doc_ids_not_tracked',
    TASK_NAME_AUTO_REINDEX,
    TASK_NAME_IMANAGE_TRIGGER_SYNC,
    TASK_NAME_TRIGGER_DIGESTS
}

REMOVE_WHEN_READY = set()

USER_TASK_EXECUTION_DELAY = 24 * 60 * 60
REMOVE_SUB_TASKS_DELAY_IN_SEC = 60
REMOVE_READY_TASKS_DELAY_IN_SEC = 24 * 60 * 60

CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_CHORD_UNLOCK_MAX_RETRIES = 5
CELERY_CHORD_UNLOCK_DELAY_BETWEEN_RETRIES_IN_SEC = 3

CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# this needed on production. check
CELERY_IMPORTS = ('apps.task.tasks',)

CELERY_TASK_SERIALIZER = 'pickle'
CELERY_ACCEPT_CONTENT = ['json', 'pickle']

CELERY_TASK_QUEUES = (
    Queue('default', routing_key='task_default.#', queue_arguments={'max-priority': 10}),
    Queue('high_priority', routing_key='task_high_priority.#'),
    Queue('serial', routing_key='task_serial.#'),
    Queue('beat-db', routing_key='task_beat_db.#'),
    Queue('doc_load', routing_key='task_doc_load.#'),
)

CELERY_TASK_DEFAULT_QUEUE = 'default'

# Redis for Celery args caching
CELERY_CACHE_REDIS_URL = 'redis://127.0.0.1:6379/0'
CELERY_CACHE_REDIS_KEY_PREFIX = 'celery_task'

# django-excel
# http://django-excel.readthedocs.io/en/latest/
FILE_UPLOAD_HANDLERS = (
    "django_excel.ExcelMemoryFileUploadHandler",
    "django_excel.TemporaryExcelFileUploadHandler"
)

# elasticsearch integration
# https://elasticsearch-py.readthedocs.io/en/master/
ELASTICSEARCH_CONFIG = {
    'hosts': [{'host': '127.0.0.1', 'port': 9200}],
    'index': 'contraxsuite'
}

# django-ckeditor
CKEDITOR_CONFIGS = {
    'default': {
        # 'toolbar': 'full',
        'width': '100%',
    },
}

# django-filebrowser
# relative path in /media dir
FILEBROWSER_DIRECTORY = 'data/'

FILEBROWSER_DOCUMENTS_DIRECTORY = 'data/documents/'
# don't try to import a mis-installed PIL
STRICT_PIL = True
# Allowed extensions for file upload
FILEBROWSER_EXTENSIONS = {
    'Image': ['.jpg', '.jpeg', '.png', '.tif', '.tiff'],
    'Document': ['.pdf', '.doc', '.docx', '.rtf', '.txt', '.xls', '.xlsx', '.csv', '.html', '.json'],
    'Archive': ['.zip']
}
# Max. Upload Size in Bytes
FILEBROWSER_MAX_UPLOAD_SIZE = 300 * 1024 ** 2  # 300Mb
# replace spaces and convert to lowercase
FILEBROWSER_CONVERT_FILENAME = False
# remove non-alphanumeric chars (except for underscores, spaces & dashes)
FILEBROWSER_NORMALIZE_FILENAME = False
# Default sorting, options are: date, filesize, filename_lower, filetype_checked, mimetype
FILEBROWSER_DEFAULT_SORTING_BY = 'filename_lower'
# traverse all subdirectories when searching (this might take a while if many files)
FILEBROWSER_SEARCH_TRAVERSE = True
FILEBROWSER_LIST_PER_PAGE = 25

CONTRAX_FILE_STORAGE_TYPE = 'Local'
CONTRAX_FILE_STORAGE_LOCAL_ROOT_DIR = MEDIA_ROOT + '/' + FILEBROWSER_DIRECTORY
#CONTRAX_FILE_STORAGE_TYPE = 'WebDAV'
#CONTRAX_FILE_STORAGE_WEBDAV_ROOT_URL = 'http://localhost:8090/'
#CONTRAX_FILE_STORAGE_WEBDAV_USERNAME = 'user'
#CONTRAX_FILE_STORAGE_WEBDAV_PASSWORD = 'pass'
CONTRAX_FILE_STORAGE_DOCUMENTS_DIR = 'documents/'

# django-constance settings
# https://django-constance.readthedocs.io/en/latest/
REQUIRED_LOCATORS = (
    'geoentity',
    'party',
    'term',
    'date',
)
OPTIONAL_LOCATORS = (
    'amount',
    'citation',
    'copyright',
    'court',
    'currency',
    'definition',
    'distance',
    'duration',
    'percent',
    'ratio',
    'regulation',
    'trademark',
    'url'
)
LOCATOR_GROUPS = {
    'amount': ('amount', 'currency', 'distance', 'percent', 'ratio'),
    'other': ('citation', 'copyright', 'definition', 'regulation', 'trademark', 'url')
}
OPTIONAL_LOCATOR_CHOICES = [(i, i) for i in OPTIONAL_LOCATORS]
CONSTANCE_ADDITIONAL_FIELDS = {
    'app_multiselect': ['django.forms.fields.MultipleChoiceField', {
        'widget': 'django.forms.SelectMultiple',
        'choices': OPTIONAL_LOCATOR_CHOICES
    }],
}
CONSTANCE_CONFIG = {
    'standard_optional_locators': (OPTIONAL_LOCATORS,
                                   'Standard Optional Locators',
                                   'app_multiselect'),
    'auto_login': (False,
                   'Enable Auto Login',
                   bool),
    'data': ('{}',
             'Custom Config Data',
             str),
}
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

# django-rest-framework settings
# http://www.django-rest-framework.org/
# from rest_framework.authentication import SessionAuthentication
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ('v1',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'authenticator.CookieAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
        # 'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}
REST_AUTH_SERIALIZERS = {
    'TOKEN_SERIALIZER': 'authenticator.TokenSerializer',
    'PASSWORD_CHANGE_SERIALIZER': 'authenticator.CustomPasswordChangeSerializer',
}

# rest auth token settings
REST_AUTH_TOKEN_CREATOR = 'authenticator.token_creator'
REST_AUTH_TOKEN_EXPIRES_DAYS = 3
REST_AUTH_TOKEN_UPDATE_EXPIRATION_DATE = True

# swagger settings
SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': True,
    'JSON_EDITOR': True,
    'SHOW_REQUEST_HEADERS': True,
    'CUSTOM_HEADERS': {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
}
# tika settings (is not used for now)
# TIKA_VERSION = '1.14'
# TIKA_SERVER_JAR = ROOT_DIR('../libs/tika/tika-server-1.14.jar')
TIKA_DISABLE = False
TIKA_SERVER_ENDPOINT = None
JAR_BASE_PATH = PROJECT_DIR('jars')

JAI_JARS = ['jai-imageio-core.jar', 'jai-imageio-jpeg2000.jar']
TIKA_JARS = ['tika-app.jar', 'lexpredict-tika.jar'] + JAI_JARS

TEXTRACT_FIRST_FOR_EXTENSIONS = []
TIKA_TIMEOUT = 60 * 60

TEXTRACT_NON_OCR_EXTENSIONS = ['txt', 'doc', 'docx', 'rtf',
                               'md', 'odt', 'ott', 'odf']

# use jqWidgets' export, e.g. send data to jq OR handle it on client side
# FYI: http://www.jqwidgets.com/community/topic/jqxgrid-export-data/#}
JQ_EXPORT = False

# place dictionaries for GeoEntities, Terms, US Courts, etc.
DATA_ROOT = PROJECT_DIR('data/')
GIT_DATA_REPO_ROOT = 'https://raw.githubusercontent.com/' \
                     'LexPredict/lexpredict-legal-dictionary/1.0.7'

# logging
CELERY_LOG_FILE_PATH = PROJECT_DIR('logs/celery-{0}.log'.format(platform.node()))
LOG_FILE_PATH = PROJECT_DIR('logs/django-{0}.log'.format(platform.node()))
FRONT_LOG_FILE_PATH = PROJECT_DIR('logs/frontend-{0}.log'.format(platform.node()))
DB_LOG_FILE_PATH = PROJECT_DIR('logs/db-{0}.log'.format(platform.node()))

prepare_log_dirs(CELERY_LOG_FILE_PATH)
prepare_log_dirs(LOG_FILE_PATH)
prepare_log_dirs(FRONT_LOG_FILE_PATH)
prepare_log_dirs(DB_LOG_FILE_PATH)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)-7s %(asctime)s | %(message)s'
        },
        'json': {
            '()': 'contraxsuite_logging.ContraxsuiteJSONFormatter'
        }
    },
    'handlers': {
        'text_django': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'filename': LOG_FILE_PATH,
            'formatter': 'verbose',
        },
        'text_celery': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 5,
            'filename': CELERY_LOG_FILE_PATH,
            'formatter': 'verbose',
        },
        'text_db': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'filename': DB_LOG_FILE_PATH,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'filters': [],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stdout,
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'json_django': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'filename': LOG_FILE_PATH + '_json',
            'formatter': 'json',
        },
        'json_frontend': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'filename': FRONT_LOG_FILE_PATH + '_json',
            'formatter': 'json',
        },
        'json_celery': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'filename': CELERY_LOG_FILE_PATH + '_json',
            'formatter': 'json',
        },
        'json_db': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'filename': DB_LOG_FILE_PATH + '_json',
            'formatter': 'json',
        },
    },
    'loggers': {
        'apps.task.models': {
            'handlers': ['json_celery', 'text_celery'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'apps.task.tasks': {
            'handlers': ['json_celery', 'text_celery'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django': {
            'handlers': ['json_django', 'text_django'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'frontend': {
            'handlers': ['json_frontend'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['text_db', 'json_db'],  # Quiet by default!
            'propagate': False,
            'level': 'ERROR',
        },
        'django.template': {
            'handlers': ['json_django', 'text_django', 'mail_admins'],
            'level': 'INFO',
        },
    },
}

# Specifies where to search for Celery task logs.
# Index template should comply the index names to which filebeat writes logs.
# See filebeat.yml.template - output section.
LOGGING_ELASTICSEARCH_INDEX_TEMPLATE = 'filebeat*'

# django-extensions notebook
NOTEBOOK_ARGUMENTS = [
    '--ip=0.0.0.0',
    '--port=8000',
]

# django-cors-headers settings
# https://github.com/ottoyiu/django-cors-headers/
# CORS_ORIGIN_ALLOW_ALL = True
# CORS_ALLOW_CREDENTIALS = False
# CORS_URLS_REGEX = r'^.*$'

VERSION_NUMBER = '1.2.3'
VERSION_COMMIT = 'cdd28414'

NOTIFICATION_EMBEDDED_TEMPLATES_PATH = 'apps/notifications/notification_templates'
NOTIFICATION_CUSTOM_TEMPLATES_PATH_IN_MEDIA = 'notification_templates'


DATA_UPLOAD_MAX_NUMBER_FIELDS = None

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

CALCULATED_FIELDS_EVAL_LOCALS = {'datetime': datetime, 'len': len}

SCRIPTS_BASE_EVAL_LOCALS = {'datetime': datetime, 'len': len}

RETRAINING_DELAY_IN_SEC = 1 * 60 * 60

RETRAINING_TASK_EXECUTION_DELAY_IN_SEC = 1 * 60 * 60

TRAINED_AFTER_DOCUMENTS_NUMBER = 100

TEXT_UNITS_TO_PARSE_PACKAGE_SIZE = 50

ML_TRAIN_DATA_SET_GROUP_LEN = 10000

RAW_DB_FULL_TEXT_SEARCH_CUT_ABOVE_TEXT_LENGTH = 4 * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = 100*2621440

# Debugging Docker Deployments:
# CELERY_BROKER_URL = 'amqp://contrax1:contrax1@127.0.0.1:56720/contrax1_vhost'
# CELERY_CACHE_REDIS_URL = 'redis://127.0.0.1:63790/0'
# CONTRAX_FILE_STORAGE_TYPE = 'Nginx'
# CONTRAX_FILE_STORAGE_NGINX_ROOT_URL = 'http://127.0.0.1:800/media/data/documents/'
# TIKA_FOR_EXTENSIONS = ['pdf']

FRONTEND_ROOT_URL = None

try:
    from local_settings import *

    INSTALLED_APPS += LOCAL_INSTALLED_APPS
    MIDDLEWARE += LOCAL_MIDDLEWARE
except (ImportError, NameError):
    pass

try:
    from customer_settings import *

    if CUSTOMER_CELERY_BEAT_SCHEDULE:
        for task_name, schedule in CUSTOMER_CELERY_BEAT_SCHEDULE.items():
            CELERY_BEAT_SCHEDULE[task_name] = schedule
    if CUSTOMER_EXCLUDE_FROM_TRACKING:
        for task_name in CUSTOMER_EXCLUDE_FROM_TRACKING:
            EXCLUDE_FROM_TRACKING.add(task_name)
    if CUSTOMER_REMOVE_WHEN_READY:
        for task_name in CUSTOMER_REMOVE_WHEN_READY:
            REMOVE_WHEN_READY.add(task_name)
except (ImportError, NameError):
    pass

PIPELINE['PIPELINE_ENABLED'] = PIPELINE_ENABLED

BASE_URL = re.sub('^/+', '', BASE_URL)
BASE_URL = re.sub('/+$', '', BASE_URL)
if BASE_URL:
    BASE_URL += '/'

STATIC_URL = ('/' + BASE_URL if BASE_URL else '/') + 'static/'
MEDIA_URL = '/' + BASE_URL + 'media/'
# LoginRequiredMiddleware settings
LOGIN_EXEMPT_URLS = (
    r'^' + BASE_URL + 'accounts/',  # allow any URL under /accounts/*
    r'^rest-auth/',  # allow any URL under /rest-auth/*
    r'^api/v',  # allow any URL under /api/v*
    r'^' + BASE_URL + '__debug__/',  # allow debug toolbar
    r'^' + BASE_URL + 'extract/search/',
    r'^api/v\d+/logging/log_message/'
)

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG_TEMPLATE

if DEBUG_SQL:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(levelname)-7s %(asctime)s | %(message)s'
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'django.db.backends': {
                'level': 'DEBUG',
                'handlers': ['console'],
            },
        }
    }

if DEBUG:
    INSTALLED_APPS += (
        'debug_toolbar',
    )
    MIDDLEWARE += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

# settings for AutoLoginMiddleware
# urls available for unauthorized users,
# otherwise login as "test_user"
AUTOLOGIN_ALWAYS_OPEN_URLS = [
    reverse_lazy('account_login'),
]
# forbidden urls for "test user" (all account/* except login/logout)
AUTOLOGIN_TEST_USER_FORBIDDEN_URLS = [
    'accounts/(?!login|logout)',
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CELERY_CACHE_REDIS_URL],
        },
    },
}
