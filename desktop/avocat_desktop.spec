# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — bundles the Django desktop app into a single binary.

Build:
    cd /Users/yassineelmoudene/Desktop/Devs/avocat_yassine
    /Users/Shared/Venv/bin/pyinstaller desktop/avocat_desktop.spec --clean --noconfirm

Output:
    dist/AvocatDesktop.app          (macOS, double-clickable)
    dist/AvocatDesktop/             (Windows/Linux, ./AvocatDesktop)

On first launch the binary writes its SQLite + media to
    ~/.avocat_desktop/
and POSTs sync calls to AVOCAT_REMOTE_API (defaults to http://127.0.0.1:8003/api).
"""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
)

PROJECT_ROOT = Path(SPECPATH).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Make sure Django can resolve settings at analysis time (PyInstaller imports
# the settings module to walk INSTALLED_APPS).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "desktop.settings_desktop")

# ---------------------------------------------------------------------------
# Data files — templates, static, locale, migrations.
# Django loads these at RUNTIME so PyInstaller doesn't see them via imports.
# ---------------------------------------------------------------------------
def _walk_tree(src: Path, dest: str) -> list[tuple[str, str]]:
    """Mirror src/ into the bundle at dest/, preserving subdirectories."""
    out = []
    if not src.exists():
        return out
    for p in src.rglob("*"):
        if p.is_file():
            rel_dir = str(p.relative_to(src).parent)
            target = dest if rel_dir == "." else f"{dest}/{rel_dir}"
            out.append((str(p), target))
    return out


datas = []
datas += _walk_tree(PROJECT_ROOT / "templates", "templates")
datas += _walk_tree(PROJECT_ROOT / "static", "static")
datas += _walk_tree(PROJECT_ROOT / "locale", "locale")
datas += _walk_tree(PROJECT_ROOT / "avocat_app" / "migrations", "avocat_app/migrations")
datas += _walk_tree(PROJECT_ROOT / "avocat_app" / "templates", "avocat_app/templates")

# Django + DRF + simplejwt ship template/static/locale files of their own.
for pkg in (
    "django",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
):
    datas += collect_data_files(pkg)

# ---------------------------------------------------------------------------
# Hidden imports — Django apps and runtime-loaded modules PyInstaller misses.
# ---------------------------------------------------------------------------
hiddenimports = []

# Every avocat_app submodule (signals, services, middleware, views_*…).
hiddenimports += collect_submodules("avocat_app")
hiddenimports += collect_submodules("desktop")
hiddenimports += collect_submodules("rest_framework")
hiddenimports += collect_submodules("rest_framework_simplejwt")
hiddenimports += collect_submodules("corsheaders")
hiddenimports += collect_submodules("django_extensions")
hiddenimports += collect_submodules("django_filters")
hiddenimports += collect_submodules("environ")
hiddenimports += collect_submodules("requests")
hiddenimports += collect_submodules("avocat_yassine")
hiddenimports += [
    "avocat_yassine.wsgi",
    "avocat_yassine.urls",
    "avocat_yassine.settings",
]
# DRF auth backends that show up by string name.
hiddenimports += [
    "rest_framework.authentication",
    "rest_framework.permissions",
    "rest_framework.renderers",
    "rest_framework.parsers",
    "rest_framework_simplejwt.authentication",
    "rest_framework_simplejwt.token_blacklist",
]

# Django pieces that get imported by string name (settings, apps registry…).
hiddenimports += [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.db.backends.sqlite3",
    "django.template.loaders.filesystem",
    "django.template.loaders.app_directories",
    "django.template.defaulttags",
    "django.template.defaultfilters",
    "django.middleware.clickjacking",
    "django.middleware.common",
    "django.middleware.csrf",
    "django.middleware.security",
]

# PyWebView's native backend on macOS is loaded by string.
binaries = []
webview_all = collect_all("webview")
datas += webview_all[0]
binaries += webview_all[1]
hiddenimports += webview_all[2]

# pyobjc — macOS native bridge for PyWebView.
if sys.platform == "darwin":
    for pkg in ("objc", "Cocoa", "WebKit", "Foundation", "AppKit"):
        try:
            pkg_all = collect_all(pkg)
            datas += pkg_all[0]
            binaries += pkg_all[1]
            hiddenimports += pkg_all[2]
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Excludes — keep the binary lean by dropping things we don't ship.
# ---------------------------------------------------------------------------
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "mysqlclient",
    "MySQLdb",
    "psycopg2",
    "psycopg",
    "axes",
]

# ---------------------------------------------------------------------------
# Analysis / Build
# ---------------------------------------------------------------------------
block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / "desktop" / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AvocatDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # no terminal window — the webview IS the UI
    disable_windowed_traceback=False,
    icon=str(PROJECT_ROOT / "static" / "pwa" / "icon.icns"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AvocatDesktop",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AvocatDesktop.app",
        icon=str(PROJECT_ROOT / "static" / "pwa" / "icon.icns"),
        bundle_identifier="ma.avocatyassine.desktop",
        info_plist={
            "CFBundleName": "Avocat Desktop",
            "CFBundleDisplayName": "مكتب المحاماة",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1",
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.business",
            "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
        },
    )
