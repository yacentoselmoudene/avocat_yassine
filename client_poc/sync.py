"""Pull + push + full sync orchestrator."""
from datetime import datetime, timezone

import requests

from . import auth, config, storage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pull
# ---------------------------------------------------------------------------

def pull_table(table: str) -> dict:
    since = storage.get_since(table)
    total = 0
    pages = 0
    next_since = since
    while True:
        params = {"table": table, "since": next_since, "limit": config.PULL_PAGE_SIZE}
        r = requests.get(
            f"{config.API_BASE}/sync/pull/",
            headers=auth.auth_headers(),
            params=params,
            timeout=config.HTTP_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        items = data["items"]
        storage.upsert_from_server(table, items)
        total += len(items)
        pages += 1
        next_since = data["next_since"]
        if not data["has_more"]:
            break
    storage.set_since(table, next_since)
    return {"table": table, "fetched": total, "pages": pages, "until": next_since}


def pull_all() -> list[dict]:
    return [pull_table(t) for t in config.TABLES]


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------

def _push_batch(changes: list[dict]) -> list[dict]:
    r = requests.post(
        f"{config.API_BASE}/sync/push/",
        headers={**auth.auth_headers(), "Content-Type": "application/json"},
        json={"changes": changes},
        timeout=config.HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["results"]


def push_table(table: str) -> dict:
    changes = storage.pending_changes(table)
    summary = {"table": table, "sent": len(changes), "ok": 0, "conflict": 0, "error": 0}
    if not changes:
        return summary

    for i in range(0, len(changes), config.PUSH_BATCH_SIZE):
        chunk = changes[i : i + config.PUSH_BATCH_SIZE]
        results = _push_batch(chunk)
        for res in results:
            rid = str(res.get("id")) if res.get("id") is not None else None
            st = res.get("status")
            if st == "ok":
                storage.clear_dirty(table, rid, res.get("server_updated_at"))
                summary["ok"] += 1
            elif st == "conflict":
                storage.replace_with_server(table, res["server_payload"])
                summary["conflict"] += 1
            else:
                summary["error"] += 1
    return summary


def push_all() -> list[dict]:
    return [push_table(t) for t in config.TABLES]


# ---------------------------------------------------------------------------
# Full sync: pull → push → pull (final pull picks up server_updated_at echoes)
# ---------------------------------------------------------------------------

def full_sync() -> dict:
    return {
        "pull_pre": pull_all(),
        "push": push_all(),
        "pull_post": pull_all(),
        "finished_at": _now_iso(),
    }
