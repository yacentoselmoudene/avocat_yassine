"""Binary file sync for PieceJointe — runs after the metadata sync.

Pull phase  — for every PieceJointe row pointing at a file we don't have
              locally, GET /api/files/<uuid>/ and write it under MEDIA_ROOT.
Push phase  — for every locally-present file the central server hasn't seen
              yet (or has at a stale path), POST the binary.

State is tracked in a single small SQLite table inside the local DB so it
survives across launches.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import requests
from django.conf import settings
from django.db import connection

from avocat_app.models import PieceJointe

log = logging.getLogger("desktop")


def _ensure_state_table():
    with connection.cursor() as cx:
        cx.execute("""
            CREATE TABLE IF NOT EXISTS desktop_file_state (
                piece_id           TEXT PRIMARY KEY,
                last_uploaded_path TEXT,
                last_uploaded_mtime REAL,
                last_downloaded_path TEXT
            )
        """)


def _media_path(rel_path: str) -> Path:
    return Path(settings.MEDIA_ROOT) / rel_path


def _ledger_get(piece_id: str) -> dict | None:
    _ensure_state_table()
    with connection.cursor() as cx:
        cx.execute(
            "SELECT last_uploaded_path, last_uploaded_mtime, last_downloaded_path "
            "FROM desktop_file_state WHERE piece_id=%s",
            [piece_id],
        )
        row = cx.fetchone()
    if not row:
        return None
    return {"upload_path": row[0], "upload_mtime": row[1], "download_path": row[2]}


def _ledger_record_upload(piece_id: str, path: str, mtime: float):
    _ensure_state_table()
    with connection.cursor() as cx:
        cx.execute(
            "INSERT INTO desktop_file_state(piece_id, last_uploaded_path, last_uploaded_mtime) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT(piece_id) DO UPDATE SET "
            "  last_uploaded_path=excluded.last_uploaded_path, "
            "  last_uploaded_mtime=excluded.last_uploaded_mtime",
            [piece_id, path, mtime],
        )


def _ledger_record_download(piece_id: str, path: str):
    _ensure_state_table()
    with connection.cursor() as cx:
        cx.execute(
            "INSERT INTO desktop_file_state(piece_id, last_downloaded_path) "
            "VALUES (%s, %s) "
            "ON CONFLICT(piece_id) DO UPDATE SET "
            "  last_downloaded_path=excluded.last_downloaded_path",
            [piece_id, path],
        )


# ---------------------------------------------------------------------------
# Pull
# ---------------------------------------------------------------------------

def pull_files(token: str) -> dict:
    """Download every PieceJointe binary we know about but don't have yet."""
    headers = {"Authorization": f"Bearer {token}"}
    summary = {"downloaded": 0, "skipped": 0, "errors": 0}

    qs = PieceJointe.all_objects.exclude(fichier="").exclude(fichier__isnull=True)
    for piece in qs:
        rel_path = piece.fichier.name
        if not rel_path:
            continue
        local = _media_path(rel_path)
        if local.exists() and local.stat().st_size > 0:
            summary["skipped"] += 1
            continue
        local.parent.mkdir(parents=True, exist_ok=True)
        url = f"{settings.DESKTOP_REMOTE_API}/files/{piece.pk}/"
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=120)
            if r.status_code == 404:
                # Server has the metadata but the file was never uploaded.
                summary["skipped"] += 1
                continue
            r.raise_for_status()
            tmp = local.with_suffix(local.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            tmp.replace(local)
            _ledger_record_download(str(piece.pk), rel_path)
            summary["downloaded"] += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("file pull failed piece=%s err=%s", piece.pk, exc)
            summary["errors"] += 1
    return summary


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------

def push_files(token: str) -> dict:
    """Upload binaries the server hasn't seen at the current local mtime."""
    headers = {"Authorization": f"Bearer {token}"}
    summary = {"uploaded": 0, "skipped": 0, "errors": 0}

    qs = PieceJointe.all_objects.exclude(fichier="").exclude(fichier__isnull=True)
    for piece in qs:
        rel_path = piece.fichier.name
        local = _media_path(rel_path)
        if not local.exists():
            summary["skipped"] += 1
            continue
        mtime = local.stat().st_mtime
        state = _ledger_get(str(piece.pk))
        if state and state.get("upload_path") == rel_path and state.get("upload_mtime") == mtime:
            summary["skipped"] += 1
            continue
        url = f"{settings.DESKTOP_REMOTE_API}/files/{piece.pk}/"
        try:
            with open(local, "rb") as fh:
                r = requests.post(url, headers=headers,
                                  files={"file": (os.path.basename(rel_path), fh)},
                                  timeout=180)
            if r.status_code == 404:
                # Server has no row yet — metadata push must run first; we'll
                # try again on the next cycle.
                summary["skipped"] += 1
                continue
            r.raise_for_status()
            _ledger_record_upload(str(piece.pk), rel_path, mtime)
            summary["uploaded"] += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("file push failed piece=%s err=%s", piece.pk, exc)
            summary["errors"] += 1
    return summary
