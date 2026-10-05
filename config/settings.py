"""Small-install defaults; production deliberately requires explicit configuration."""
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse, unquote

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("TOURNEY_DATA_DIR", BASE_DIR / ".data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEBUG = os.environ.get("DEBUG", "1") == "1"
DEMO_MODE = DEBUG and os.environ.get("DEMO_MODE", "0") == "1"
secret_path = DATA_DIR / "secret.key"
if not os.environ.get("SECRET_KEY") and DEBUG:
    if not secret_path.exists():
        fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(secrets.token_urlsafe(64))
    SECRET_KEY = secret_path.read_text().strip()
else:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    if not SECRET_KEY:
        raise RuntimeError("Set SECRET_KEY for a production installation.")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "tourney",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "tourney.middleware.BoundaryMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages",
                  "tourney.context.common"]}}]
WSGI_APPLICATION = "config.wsgi.application"
db_url = os.environ.get("DATABASE_URL", "")
if db_url:
    db = urlparse(db_url)
    if db.scheme not in ("postgres", "postgresql"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL.")
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": db.path.lstrip("/"),
        "USER": unquote(db.username or ""), "PASSWORD": unquote(db.password or ""),
        "HOST": db.hostname, "PORT": db.port or 5432, "CONN_MAX_AGE": 60}}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA_DIR / "tourney.sqlite3",
        "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"}}}
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 12
CSRF_COOKIE_HTTPONLY = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
CSRF_TRUSTED_ORIGINS = [SITE_URL]
# Behind a TLS-terminating proxy, opt in to trusting its headers. Never enable on a directly exposed server.
if os.environ.get("TRUST_PROXY_SSL", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUST_FORWARDED_FOR = os.environ.get("TRUST_FORWARDED_FOR", "0") == "1"  # rate limits use the proxy-supplied client address
ENABLE_EXPERIMENTAL_FORMATS = os.environ.get("ENABLE_EXPERIMENTAL_FORMATS", "0") == "1"  # pools / double elimination are not release-gated
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
EMAIL_FILE_PATH = DATA_DIR / "mail"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "events@localhost")
ALLOW_ORGANIZER_SIGNUP = os.environ.get("ALLOW_ORGANIZER_SIGNUP", "1") == "1"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

