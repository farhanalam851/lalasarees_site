import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None):
    return os.environ.get(key, default)


ON_VERCEL = env("VERCEL") == "1"
INSECURE_DEFAULT_KEY = "dev-insecure-key-change-before-deploy"
SECRET_KEY = env("DJANGO_SECRET_KEY", INSECURE_DEFAULT_KEY)
# Safe by default: on Vercel, DEBUG is off unless you explicitly turn it on.
DEBUG = env("DJANGO_DEBUG", "0" if ON_VERCEL else "1") == "1"


def csv(key, default=""):
    return [x.strip() for x in env(key, default).split(",") if x.strip()]


ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = csv("DJANGO_CSRF_TRUSTED_ORIGINS")
if ON_VERCEL:
    # every *.vercel.app URL (production, preview, branch) plus the canonical custom domain
    ALLOWED_HOSTS += [".vercel.app"]
    CSRF_TRUSTED_ORIGINS += ["https://*.vercel.app"]
    ALLOWED_HOSTS += [h for h in csv("DJANGO_CANONICAL_HOST") if h not in ALLOWED_HOSTS]
for _host in ALLOWED_HOSTS:
    if _host not in ("localhost", "127.0.0.1") and not _host.startswith("."):
        _origin = f"https://{_host}"
        if _origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_origin)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "accounts",
    "shop",
    "orders",
    "dashboard",
]

MIDDLEWARE = [
    "lalasarees.middleware.CanonicalHostMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lalasarees.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.site",
                "dashboard.context.counts",
            ],
        },
    },
]

WSGI_APPLICATION = "lalasarees.wsgi.application"


def database_from_url(url):
    """Parse postgres://user:pass@host:port/dbname?sslmode=require (Neon, Supabase, Vercel Postgres...)."""
    u = urlparse(url)
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    options = {}
    if q.get("sslmode"):
        options["sslmode"] = q["sslmode"]
    elif u.hostname not in ("localhost", "127.0.0.1"):
        options["sslmode"] = "require"
    if q.get("connect_timeout"):
        options["connect_timeout"] = int(q["connect_timeout"])
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(u.path.lstrip("/")),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "",
        "PORT": u.port or 5432,
        "OPTIONS": options,
        # serverless: no long-lived connections; pooled (pgbouncer) URLs do not support server-side cursors
        "CONN_MAX_AGE": 0,
        "DISABLE_SERVER_SIDE_CURSORS": True,
    }


DATABASE_URL = env("DATABASE_URL") or env("POSTGRES_URL") or ""
if DATABASE_URL:
    DATABASES = {"default": database_from_url(DATABASE_URL)}
elif env("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER", ""),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Uploaded photos (products, categories, reviews). Vercel's disk is read-only and temporary, so on Vercel
# they MUST go to an S3-compatible bucket (Supabase Storage, Cloudflare R2, AWS S3, ...).
MEDIA_STORAGE_CONFIGURED = bool(env("AWS_STORAGE_BUCKET_NAME"))
if MEDIA_STORAGE_CONFIGURED:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL") or None          # blank for real AWS S3
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME") or None
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN") or None        # public host/path the browser loads images from
    AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", "path")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_QUERYSTRING_AUTH = False        # public, cacheable image URLs
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False       # never overwrite a customer's/admin's file with the same name
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "public, max-age=31536000, immutable"}
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN.strip('/')}/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024

# ---- Store / payments -------------------------------------------------
# True  -> listed prices already include GST (usual for retail)
# False -> listed prices are before GST and GST is added at checkout (usual for B2B)
PRICES_INCLUDE_GST = True

RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", "")

# ---- SEO / analytics / performance ----------------------------------
CANONICAL_HOST = env("DJANGO_CANONICAL_HOST", "")          # e.g. www.lalasarees.in (no scheme)
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID", "")           # e.g. G-XXXXXXXXXX; loads only after cookie consent
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0           # long cache for static files
SITEMAP_PROTOCOL = "http" if DEBUG else "https"

# ---- Logging: everything to stdout so it shows up in Vercel > Logs -------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler", "stream": sys.stdout}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}

# ---- Email ------------------------------------------------------------
if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_TIMEOUT = 10                  # never let a slow SMTP server hang a serverless request
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Lala Sarees <no-reply@lalasarees.in>")

# ---- Production hardening --------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_CONTENT_TYPE_NOSNIFF = True


def validate_production():
    """Called from wsgi.py when the site starts serving. Fails with a clear message instead of a mystery 500."""
    problems = []
    if not DEBUG and SECRET_KEY == INSECURE_DEFAULT_KEY:
        problems.append("DJANGO_SECRET_KEY is not set.")
    if ON_VERCEL and not DATABASE_URL:
        problems.append("DATABASE_URL is not set (Vercel cannot use SQLite).")
    if ON_VERCEL and not MEDIA_STORAGE_CONFIGURED:
        problems.append("AWS_STORAGE_BUCKET_NAME is not set (uploaded photos would be lost on Vercel).")
    if problems:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("Deployment settings missing: " + " ".join(problems))
