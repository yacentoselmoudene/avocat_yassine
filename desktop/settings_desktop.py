"""Desktop overrides — bundled .exe / .app reads/writes a LOCAL SQLite mirror.

Import via:  DJANGO_SETTINGS_MODULE=desktop.settings_desktop

What we change vs the base settings:
  - DATABASES → SQLite at  ~/.avocat_desktop/local.sqlite3  (user-writable, survives upgrades)
  - DESKTOP_MODE = True (used in views/templates to show the sync button)
  - DESKTOP_REMOTE_API → central server URL the sync engine talks to
  - DESKTOP_USER / DESKTOP_PASSWORD → cached JWT credentials for the engine (first launch wizard sets them)
  - axes disabled (no brute-force concern on a single-user device)
"""
import os
import secrets
from pathlib import Path

# The packaged .app/.exe has no .env file shipped, so seed any vars the base
# settings would otherwise read from the environment BEFORE importing it.
_DATA_DIR = Path(os.getenv("AVOCAT_DESKTOP_DATA", str(Path.home() / ".avocat_desktop")))
_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _persistent_secret(name: str) -> str:
    """Read a per-install secret from disk, generating it on first launch.
    Same value across reboots, different per machine."""
    f = _DATA_DIR / f"{name}.key"
    if f.exists():
        return f.read_text().strip()
    value = secrets.token_urlsafe(64)
    f.write_text(value)
    try:
        f.chmod(0o600)
    except OSError:
        pass
    return value


os.environ.setdefault("SECRET_KEY", _persistent_secret("secret"))
os.environ.setdefault("PORTAIL_COOKIE_SECRET", _persistent_secret("portail"))
# The base settings declares env('DB_PASSWORD') with no default — even though
# DATABASES gets overridden below, the lookup fires during the import. Seed
# any other no-default vars the same way so the base import never raises.
os.environ.setdefault("DB_PASSWORD", "_unused_desktop_uses_sqlite_")
os.environ.setdefault("DEBUG", "False")
# Tell django-environ to skip looking for a non-existent .env file.
os.environ.setdefault("DJANGO_READ_DOT_ENV_FILE", "False")

from avocat_yassine.settings import *  # noqa: E402,F401,F403

DESKTOP_MODE = True

DESKTOP_DATA_DIR = Path(os.getenv("AVOCAT_DESKTOP_DATA",
                                  str(Path.home() / ".avocat_desktop")))
DESKTOP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DESKTOP_DATA_DIR / "local.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}

DESKTOP_REMOTE_API = os.getenv("AVOCAT_REMOTE_API", "http://127.0.0.1:8003/api")
DESKTOP_CREDENTIALS_PATH = DESKTOP_DATA_DIR / "credentials.json"

INSTALLED_APPS = [a for a in INSTALLED_APPS if a != "axes"]  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if "axes" not in m]      # noqa: F405
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

MEDIA_ROOT = str(DESKTOP_DATA_DIR / "media")
STATIC_ROOT = str(DESKTOP_DATA_DIR / "static")

DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# The desktop launcher serves over plain HTTP on localhost; flipping the
# Secure flags off lets session, csrf and auth_token cookies survive the
# embedded webview round-trip. The exposure is local to the device only.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
AUTH_TOKEN_COOKIE_SECURE = False

for _t in TEMPLATES:  # noqa: F405
    _ctx = _t.setdefault("OPTIONS", {}).setdefault("context_processors", [])
    if "desktop.context_processors.desktop_flag" not in _ctx:
        _ctx.append("desktop.context_processors.desktop_flag")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": str(DESKTOP_DATA_DIR / "desktop.log"),
        },
    },
    "loggers": {
        "desktop": {"handlers": ["file"], "level": "INFO"},
        "django.request": {"handlers": ["file"], "level": "WARNING"},
    },
}
