"""Desktop sync engine.

Runs INSIDE the Django process (.exe) and talks to the central API server.

Pull side:
  - For each table in the registry, GET /api/sync/pull/?table=&since=&limit=
  - Apply incoming rows via Django ORM under `suppress_outbox()` so the
    capture signals don't re-queue them.
  - Persist `last_pulled_since` per table in DesktopSyncState (also stored in
    SQLite so it survives across launches).

Push side:
  - Drain SyncOutbox where pushed_at IS NULL, grouped by row (last op wins
    for a given (table, entity_id)).
  - POST /api/sync/push/ in chunks of SYNC_PUSH_MAX_BATCH.
  - For 'ok' results: mark outbox rows pushed_at=now.
  - For 'conflict' results: overwrite local row with server payload, mark
    outbox rows pushed_at=now (server wins, LWW).
  - For 'error' results: bump attempts, store last_error, leave for retry.
"""
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.utils import timezone as djtz

from avocat_app.api.registry import CORE_TABLES, SYNC_TABLES, get_model
from avocat_app.models import SyncOutbox
from avocat_app.sync_signals import suppress_outbox

log = logging.getLogger("desktop")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _credentials() -> dict:
    p = settings.DESKTOP_CREDENTIALS_PATH
    if not p.exists():
        raise RuntimeError(
            "Desktop not configured — set credentials via /desktop/setup/ or "
            f"by writing JSON {{username, password}} to {p}"
        )
    return json.loads(p.read_text())


def _login() -> str:
    creds = _credentials()
    r = requests.post(
        f"{settings.DESKTOP_REMOTE_API}/auth/token/",
        json={"username": creds["username"], "password": creds["password"]},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Per-table sync state — kept in a tiny table inside the local SQLite.
# ---------------------------------------------------------------------------

from django.db import connection


def _ensure_state_table():
    with connection.cursor() as cx:
        cx.execute("""
            CREATE TABLE IF NOT EXISTS desktop_sync_state (
                table_name        TEXT PRIMARY KEY,
                last_pulled_since TEXT NOT NULL DEFAULT '1970-01-01T00:00:00+00:00',
                last_run_at       TEXT
            )
        """)


def _get_since(table: str) -> str:
    _ensure_state_table()
    with connection.cursor() as cx:
        cx.execute("SELECT last_pulled_since FROM desktop_sync_state WHERE table_name=%s", [table])
        row = cx.fetchone()
        if row:
            return row[0]
        cx.execute("INSERT INTO desktop_sync_state(table_name) VALUES (%s)", [table])
        return "1970-01-01T00:00:00+00:00"


def _set_since(table: str, ts: str):
    _ensure_state_table()
    with connection.cursor() as cx:
        cx.execute(
            "INSERT INTO desktop_sync_state(table_name, last_pulled_since, last_run_at) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT(table_name) DO UPDATE SET "
            "  last_pulled_since=excluded.last_pulled_since, "
            "  last_run_at=excluded.last_run_at",
            [table, ts, _now_iso()],
        )


# ---------------------------------------------------------------------------
# Pull
# ---------------------------------------------------------------------------

def _apply_server_row(model, item: dict):
    """Upsert a row from the server INTO the local DB without triggering outbox."""
    pk_field = model._meta.pk.attname
    pk_value = item.get("id") or item.get(pk_field)
    data = dict(item)
    data.pop("created_at", None)
    fk_fields = {f.name: f for f in model._meta.fields if f.is_relation and not f.many_to_many}
    cleaned = {}
    for k, v in data.items():
        if k in fk_fields:
            cleaned[fk_fields[k].attname] = v
        else:
            cleaned[k] = v
    with suppress_outbox():
        model.all_objects.update_or_create(pk=pk_value, defaults=cleaned)


def pull_table(table: str, token: str, page_size: int = 200) -> dict:
    model = get_model(table)
    if model is None:
        return {"table": table, "error": "unknown table"}
    since = _get_since(table)
    total = 0
    pages = 0
    next_since = since
    while True:
        r = requests.get(
            f"{settings.DESKTOP_REMOTE_API}/sync/pull/",
            headers={"Authorization": f"Bearer {token}"},
            params={"table": table, "since": next_since, "limit": page_size},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        for it in data["items"]:
            try:
                _apply_server_row(model, it)
                total += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("apply failed table=%s id=%s err=%s", table, it.get("id"), exc)
        pages += 1
        next_since = data["next_since"]
        if not data["has_more"]:
            break
    _set_since(table, next_since)
    return {"table": table, "applied": total, "pages": pages, "until": next_since}


@contextmanager
def _fk_disabled():
    """SQLite-only: disable FK enforcement so we can apply server rows in any
    order without dancing the dependency DAG. Server data is already consistent;
    once pull_all() finishes, the local mirror is too. No-op on other vendors.
    PRAGMA must be set outside any transaction (silent no-op inside one)."""
    if connection.vendor != "sqlite":
        yield
        return
    with connection.cursor() as cx:
        cx.execute("PRAGMA foreign_keys = OFF")
    try:
        yield
    finally:
        with connection.cursor() as cx:
            cx.execute("PRAGMA foreign_keys = ON")


def pull_all(token: str) -> list[dict]:
    with _fk_disabled():
        return [pull_table(name, token) for name, _ in SYNC_TABLES]


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------

def _collapse_outbox(rows: list[SyncOutbox]) -> dict[tuple[str, str], SyncOutbox]:
    """Keep only the latest outbox row per (table, entity_id)."""
    latest: dict[tuple[str, str], SyncOutbox] = {}
    for row in rows:
        key = (row.table_name, row.entity_id)
        if key not in latest or row.created_at > latest[key].created_at:
            latest[key] = row
    return latest


def _build_change(outbox_row: SyncOutbox) -> dict | None:
    model = get_model(outbox_row.table_name)
    if model is None:
        return None
    instance = model.all_objects.filter(pk=outbox_row.entity_id).first()

    if outbox_row.op == SyncOutbox.DELETE:
        return {
            "table": outbox_row.table_name,
            "op": "delete",
            "client_updated_at": outbox_row.client_updated_at.isoformat(),
            "payload": {"id": outbox_row.entity_id},
        }
    if instance is None:
        return None

    from avocat_app.api.serializers import get_serializer
    Serializer = get_serializer(outbox_row.table_name)
    full = Serializer(instance).data

    if outbox_row.changed_fields:
        keep = set(json.loads(outbox_row.changed_fields)) | {"id", "updated_at", "is_deleted"}
        payload = {k: v for k, v in full.items() if k in keep}
    else:
        payload = dict(full)
    return {
        "table": outbox_row.table_name,
        "op": "upsert",
        "client_updated_at": outbox_row.client_updated_at.isoformat(),
        "payload": payload,
    }


def push_all(token: str, batch_size: int | None = None) -> dict:
    pending = list(SyncOutbox.objects.filter(pushed_at__isnull=True).order_by("created_at"))
    if not pending:
        return {"sent": 0, "ok": 0, "conflict": 0, "error": 0, "skipped": 0}

    collapsed = _collapse_outbox(pending)
    superseded_ids = [r.id for r in pending if (r.table_name, r.entity_id) in collapsed and collapsed[(r.table_name, r.entity_id)].id != r.id]
    SyncOutbox.objects.filter(id__in=superseded_ids).update(pushed_at=djtz.now())

    keepers = list(collapsed.values())
    changes_and_rows: list[tuple[dict, SyncOutbox]] = []
    skipped = 0
    for row in keepers:
        ch = _build_change(row)
        if ch is None:
            row.pushed_at = djtz.now()
            row.last_error = "row not found locally"
            row.save(update_fields=["pushed_at", "last_error"])
            skipped += 1
            continue
        changes_and_rows.append((ch, row))

    batch_size = batch_size or getattr(settings, "SYNC_PUSH_MAX_BATCH", 500)
    summary = {"sent": len(changes_and_rows), "ok": 0, "conflict": 0, "error": 0, "skipped": skipped}

    for i in range(0, len(changes_and_rows), batch_size):
        chunk = changes_and_rows[i : i + batch_size]
        body = {"changes": [c for c, _ in chunk]}
        r = requests.post(
            f"{settings.DESKTOP_REMOTE_API}/sync/push/",
            headers=_headers(token),
            json=body,
            timeout=120,
        )
        r.raise_for_status()
        results = r.json()["results"]
        for res, (_, row) in zip(results, chunk):
            status = res.get("status")
            if status == "ok":
                row.pushed_at = djtz.now()
                row.last_error = None
                row.save(update_fields=["pushed_at", "last_error"])
                summary["ok"] += 1
            elif status == "conflict":
                server_payload = res.get("server_payload") or {}
                model = get_model(row.table_name)
                if model is not None and server_payload:
                    try:
                        _apply_server_row(model, server_payload)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("conflict apply failed: %s", exc)
                row.pushed_at = djtz.now()
                row.last_error = "conflict — server payload applied locally"
                row.save(update_fields=["pushed_at", "last_error"])
                summary["conflict"] += 1
            else:
                row.attempts = (row.attempts or 0) + 1
                row.last_error = res.get("detail") or "unknown error"
                row.save(update_fields=["attempts", "last_error"])
                summary["error"] += 1
    return summary


# ---------------------------------------------------------------------------
# Entry point — full pull -> push -> pull
# ---------------------------------------------------------------------------

def full_sync() -> dict:
    """Full round-trip: metadata pull → file pull → metadata push → file push → metadata pull.

    Order matters:
      1. Metadata pull first so PieceJointe rows exist before we try to download.
      2. File pull next — we have the local rows pointing at relative paths.
      3. Metadata push — sends any local edits.
      4. File push — must come AFTER metadata push so the server has a row
         to attach the binary to (otherwise files endpoint 404s).
      5. Metadata pull again to absorb the updated_at the server bumped during
         the upload (so we don't re-push the same file every cycle).
    """
    from .sync_files import pull_files, push_files

    token = _login()
    return {
        "pull_pre": pull_all(token),
        "files_pull": pull_files(token),
        "push": push_all(token),
        "files_push": push_files(token),
        "pull_post": pull_all(token),
        "finished_at": _now_iso(),
    }
