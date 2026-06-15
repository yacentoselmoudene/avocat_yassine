# مكتب المحاماة — Desktop (.app / .exe)

Standalone desktop bundle. The whole Django app + a SQLite mirror runs
inside the process; the UI is a PyWebView window. The sync engine talks to
the central API (default `http://127.0.0.1:8003/api`, overridable via the
`AVOCAT_REMOTE_API` env var).

## Per-install data
First launch writes to `~/.avocat_desktop/`:
- `local.sqlite3` — the local mirror
- `media/` — pulled binaries (PieceJointe attachments)
- `secret.key`, `portail.key` — per-install secrets, generated once
- `credentials.json` — JWT login credentials (set via `/desktop/setup/` on
   first run, or written manually as `{"username": "...", "password": "..."}`)
- `launcher.log`, `desktop.log` — runtime logs

## Build on macOS
```
cd /Users/yassineelmoudene/Desktop/Devs/avocat_yassine
/Users/Shared/Venv/bin/pyinstaller desktop/avocat_desktop.spec --clean --noconfirm
```
Output: `dist/AvocatDesktop.app` (≈110 MB).
Double-click to launch, or:
```
dist/AvocatDesktop.app/Contents/MacOS/AvocatDesktop
```

## Build on Windows
Same spec works — PyInstaller picks up the `if sys.platform == "darwin"`
branches automatically. Install Python 3.13, then:
```
pip install -r requirements.txt
pip install pyinstaller pywebview
pyinstaller desktop\avocat_desktop.spec --clean --noconfirm
```
Output: `dist\AvocatDesktop\AvocatDesktop.exe` (folder bundle, ≈110 MB).
For a single-file `.exe`, change `EXE(... exclude_binaries=False ...)` and
drop the `COLLECT` step in the spec — note this slows cold-start by ~3 s
since the bundle unpacks to a temp dir.

## Build on Linux
```
pip install -r requirements.txt pyinstaller pywebview[gtk]
pyinstaller desktop/avocat_desktop.spec --clean --noconfirm
```
Needs `libgtk-3-dev` + `libwebkit2gtk-4.0-dev` system packages.

## Distribution
- macOS: zip the `.app` or wrap into a `.dmg` (`hdiutil create`).
- Windows: zip `dist\AvocatDesktop\`, or wrap with NSIS/Inno Setup for an
  installer.
- Code signing recommended (notarization on macOS, Authenticode on Windows)
  so users don't get a "developer not verified" warning.

## Troubleshooting
- Crash on launch: `~/.avocat_desktop/launcher.log` + `desktop.log` carry
  the trace.
- White screen in webview: the embedded Django might not have come up yet.
  Wait 5 s and re-open; the launcher waits up to 20 s before opening the
  window.
- "Already running": port collision. The launcher picks a free port at
  random — close the prior instance.
