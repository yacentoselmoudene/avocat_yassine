"""Local SQLite store — one table per synced entity + sync_state.

Row columns:
  id            : UUID (PK, mirrors server)
  updated_at    : ISO-8601 (server stamp, or local touch when dirty)
  is_deleted    : tombstone flag
  dirty         : 1 when there's a local change waiting to be pushed
  local_op      : 'upsert' or 'delete' when dirty=1
  dirty_fields  : JSON array of field names actually edited locally (NULL = push full payload)
  payload       : canonical row state (server snapshot, or merged after local edit)
"""
import json
import sqlite3
from contextlib import contextmanager
from typing import Iterable

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS {tbl} (
    id            TEXT PRIMARY KEY,
    updated_at    TEXT NOT NULL,
    is_deleted    INTEGER NOT NULL DEFAULT 0,
    dirty         INTEGER NOT NULL DEFAULT 0,
    local_op      TEXT,
    dirty_fields  TEXT,
    payload       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_{tbl}_dirty ON {tbl}(dirty);
CREATE INDEX IF NOT EXISTS idx_{tbl}_updated ON {tbl}(updated_at);
"""

STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_state (
    table_name        TEXT PRIMARY KEY,
    last_pulled_since TEXT NOT NULL DEFAULT '1970-01-01T00:00:00+00:00'
);
"""


def _conn():
    cx = sqlite3.connect(str(config.DB_PATH))
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys=ON;")
    return cx


def init_db():
    with _conn() as cx:
        cx.executescript(STATE_SCHEMA)
        for t in config.TABLES:
            cx.executescript(SCHEMA.format(tbl=t))


def reset_db():
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    init_db()


@contextmanager
def cursor():
    cx = _conn()
    try:
        yield cx
        cx.commit()
    finally:
        cx.close()


# ---------- sync_state ----------

def get_since(table: str) -> str:
    with cursor() as cx:
        row = cx.execute("SELECT last_pulled_since FROM sync_state WHERE table_name=?", (table,)).fetchone()
        if row:
            return row["last_pulled_since"]
        cx.execute("INSERT INTO sync_state(table_name) VALUES (?)", (table,))
        return "1970-01-01T00:00:00+00:00"


def set_since(table: str, ts: str):
    with cursor() as cx:
        cx.execute(
            "INSERT INTO sync_state(table_name, last_pulled_since) VALUES (?, ?) "
            "ON CONFLICT(table_name) DO UPDATE SET last_pulled_since=excluded.last_pulled_since",
            (table, ts),
        )


# ---------- table rows ----------

def upsert_from_server(table: str, items: Iterable[dict]):
    """Apply incoming server rows. Local dirty rows are NOT clobbered (LWW handled on push)."""
    with cursor() as cx:
        for it in items:
            rid = str(it["id"])
            updated = it["updated_at"]
            deleted = 1 if it.get("is_deleted") else 0
            payload = json.dumps(it, ensure_ascii=False)
            row = cx.execute(f"SELECT updated_at, dirty FROM {table} WHERE id=?", (rid,)).fetchone()
            if row and row["dirty"]:
                if row["updated_at"] >= updated:
                    continue
            cx.execute(
                f"INSERT INTO {table}(id, updated_at, is_deleted, dirty, local_op, dirty_fields, payload) "
                f"VALUES (?, ?, ?, 0, NULL, NULL, ?) "
                f"ON CONFLICT(id) DO UPDATE SET "
                f"  updated_at=excluded.updated_at, "
                f"  is_deleted=excluded.is_deleted, "
                f"  dirty=0, local_op=NULL, dirty_fields=NULL, payload=excluded.payload",
                (rid, updated, deleted, payload),
            )


def list_rows(table: str, include_deleted=False) -> list[dict]:
    sql = f"SELECT id, updated_at, is_deleted, dirty, local_op, dirty_fields, payload FROM {table}"
    if not include_deleted:
        sql += " WHERE is_deleted=0"
    with cursor() as cx:
        return [dict(r) for r in cx.execute(sql).fetchall()]


def get_row(table: str, rid: str) -> dict | None:
    with cursor() as cx:
        r = cx.execute(
            f"SELECT id, updated_at, is_deleted, dirty, local_op, dirty_fields, payload FROM {table} WHERE id=?",
            (rid,),
        ).fetchone()
        return dict(r) if r else None


def mark_local_upsert(table: str, payload: dict, now_iso: str, changed_fields: list[str] | None = None):
    """Stage a local upsert.

    `changed_fields` is the subset of fields the user actually edited.
    When provided, only those fields (+ id/updated_at/is_deleted) are pushed —
    correct sync semantics, avoids re-validating untouched fields server-side.
    When omitted, the FULL payload is pushed (e.g. brand-new rows).
    """
    rid = str(payload["id"])
    canonical = {**payload, "updated_at": now_iso, "is_deleted": False}
    df_json = json.dumps(changed_fields) if changed_fields is not None else None
    with cursor() as cx:
        cx.execute(
            f"INSERT INTO {table}(id, updated_at, is_deleted, dirty, local_op, dirty_fields, payload) "
            f"VALUES (?, ?, 0, 1, 'upsert', ?, ?) "
            f"ON CONFLICT(id) DO UPDATE SET "
            f"  updated_at=excluded.updated_at, "
            f"  is_deleted=0, dirty=1, local_op='upsert', "
            f"  dirty_fields=excluded.dirty_fields, payload=excluded.payload",
            (rid, now_iso, df_json, json.dumps(canonical, ensure_ascii=False)),
        )


def mark_local_delete(table: str, rid: str, now_iso: str):
    """Stage a local delete (tombstone)."""
    with cursor() as cx:
        cx.execute(
            f"UPDATE {table} SET is_deleted=1, dirty=1, local_op='delete', dirty_fields=NULL, updated_at=? WHERE id=?",
            (now_iso, rid),
        )


def pending_changes(table: str) -> list[dict]:
    with cursor() as cx:
        rows = cx.execute(
            f"SELECT id, updated_at, is_deleted, local_op, dirty_fields, payload FROM {table} WHERE dirty=1",
        ).fetchall()
    out = []
    for r in rows:
        full = json.loads(r["payload"])
        if r["local_op"] == "upsert" and r["dirty_fields"]:
            keep = set(json.loads(r["dirty_fields"])) | {"id", "updated_at", "is_deleted"}
            push_payload = {k: v for k, v in full.items() if k in keep}
        else:
            push_payload = full
        out.append({
            "table": table,
            "op": r["local_op"],
            "client_updated_at": r["updated_at"],
            "payload": push_payload,
        })
    return out


def clear_dirty(table: str, rid: str, server_updated_at: str | None = None):
    with cursor() as cx:
        if server_updated_at:
            cx.execute(
                f"UPDATE {table} SET dirty=0, local_op=NULL, dirty_fields=NULL, updated_at=? WHERE id=?",
                (server_updated_at, rid),
            )
        else:
            cx.execute(
                f"UPDATE {table} SET dirty=0, local_op=NULL, dirty_fields=NULL WHERE id=?",
                (rid,),
            )


def replace_with_server(table: str, item: dict):
    """On conflict, server wins: overwrite local row, clear dirty flags."""
    rid = str(item["id"])
    with cursor() as cx:
        cx.execute(
            f"INSERT INTO {table}(id, updated_at, is_deleted, dirty, local_op, dirty_fields, payload) "
            f"VALUES (?, ?, ?, 0, NULL, NULL, ?) "
            f"ON CONFLICT(id) DO UPDATE SET "
            f"  updated_at=excluded.updated_at, "
            f"  is_deleted=excluded.is_deleted, "
            f"  dirty=0, local_op=NULL, dirty_fields=NULL, payload=excluded.payload",
            (rid, item["updated_at"], 1 if item.get("is_deleted") else 0,
             json.dumps(item, ensure_ascii=False)),
        )
