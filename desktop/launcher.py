"""PyWebView launcher — bundles the Django app inside a native window.

Boot sequence:
  1. Force DJANGO_SETTINGS_MODULE=desktop.settings_desktop (local SQLite).
  2. Ensure data dir exists, run migrations on first launch.
  3. Start Django on a free localhost port in a background thread.
  4. Open a PyWebView window pointing at it (no URL bar, native chrome).

Run dev:
    ~/Desktop/Devs/Venv/bin/python -m desktop.launcher

Bundle (later phase):
    pyinstaller desktop/avocat_desktop.spec
"""
import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desktop.settings_desktop")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False


def _bootstrap_django():
    """Apply migrations on first launch, ensure auth user table exists."""
    import django
    django.setup()
    from django.conf import settings
    log_path = settings.DESKTOP_DATA_DIR / "launcher.log"
    logging.basicConfig(filename=str(log_path), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("desktop.launcher")
    log.info("data dir: %s", settings.DESKTOP_DATA_DIR)
    log.info("db: %s", settings.DATABASES["default"]["NAME"])

    from django.core.management import call_command
    call_command("migrate", verbosity=0, interactive=False)
    log.info("migrations OK")


def _run_django(port: int):
    """Start Django's runserver in-process (no autoreload, --insecure so static still serves)."""
    from django.core.management import call_command
    call_command("runserver", f"127.0.0.1:{port}",
                 use_reloader=False, use_threading=True, insecure_serving=True, verbosity=0)


def main():
    _bootstrap_django()
    port = _find_free_port()

    t = threading.Thread(target=_run_django, args=(port,), daemon=True)
    t.start()

    if not _wait_for_port("127.0.0.1", port):
        print(f"FATAL: Django did not start on 127.0.0.1:{port}", file=sys.stderr)
        sys.exit(1)

    url = f"http://127.0.0.1:{port}/"
    print(f"→ launcher: opening {url}")

    import webview
    webview.create_window(
        title="مكتب المحاماة — Desktop",
        url=url,
        width=1280,
        height=820,
        min_size=(900, 600),
        confirm_close=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
