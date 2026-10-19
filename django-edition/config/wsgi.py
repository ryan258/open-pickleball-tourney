import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# The served (gunicorn) entrypoint is production by default; local manage.py/./tour keep their debug-friendly defaults.
os.environ.setdefault("DEBUG", "0")
os.environ.setdefault("ALLOW_ORGANIZER_SIGNUP", "0")
application = get_wsgi_application()
