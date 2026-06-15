"""POC CLI — login / pull / push / sync / show / demo.

Usage:
  python -m client_poc.cli login <user> <pass>
  python -m client_poc.cli pull
  python -m client_poc.cli push
  python -m client_poc.cli sync
  python -m client_poc.cli show <table> [--all]
  python -m client_poc.cli reset
  python -m client_poc.cli demo
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from . import auth, storage, sync


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def cmd_login(args):
    data = auth.login(args.user, args.password)
    print(f"OK — token cached at {auth.config.TOKEN_PATH}")
    print(f"access (60c): {data['access'][:60]}...")


def cmd_pull(args):
    storage.init_db()
    _print(sync.pull_all())


def cmd_push(args):
    storage.init_db()
    _print(sync.push_all())


def cmd_sync(args):
    storage.init_db()
    _print(sync.full_sync())


def cmd_show(args):
    storage.init_db()
    rows = storage.list_rows(args.table, include_deleted=args.all_rows)
    print(f"{args.table}: {len(rows)} row(s)")
    for r in rows[: args.limit]:
        payload = json.loads(r["payload"])
        flags = []
        if r["is_deleted"]:
            flags.append("DELETED")
        if r["dirty"]:
            flags.append(f"DIRTY({r['local_op']})")
        flags_s = f"  [{', '.join(flags)}]" if flags else ""
        label = payload.get("libelle") or payload.get("reference_interne") or ""
        print(f"  {r['id']}  {r['updated_at']}  {label}{flags_s}")


def cmd_reset(args):
    storage.reset_db()
    print(f"local DB reset at {auth.config.DB_PATH}")


def cmd_demo(args):
    """Scripted scenario asserting LWW + tombstones + conflict.

    Steps:
      1. reset local DB
      2. pull   -> local mirror populated
      3. pick a tache, modify locally, push, pull -> assert change is on server
      4. delete it locally, push, pull -> assert tombstone propagated
      5. conflict: push an upsert with very old client_updated_at -> assert conflict + server wins
    """
    storage.reset_db()
    print("→ pull initial")
    _print(sync.pull_all())

    taches = storage.list_rows("tache")
    if not taches:
        print("⚠ no tache rows on server — demo needs at least 1 tache (run fixtures first)")
        sys.exit(2)

    # Step 3: modify a single field (echeance) — push only that field so untouched
    # text fields don't re-trigger their Arabic-only validator.
    target = taches[0]
    payload = json.loads(target["payload"])
    new_echeance = "2030-12-31T23:59:00+00:00"
    payload["echeance"] = new_echeance
    storage.mark_local_upsert(
        "tache", payload, datetime.now(timezone.utc).isoformat(),
        changed_fields=["echeance"],
    )
    print(f"\n→ local edit on tache {target['id']}: echeance -> {new_echeance}")
    push_res = sync.push_all()
    _print(push_res)
    tache_res = next(r for r in push_res if r["table"] == "tache")
    assert tache_res["error"] == 0, f"server upsert errored: re-run with debug to inspect"
    assert tache_res["ok"] == 1, "expected exactly 1 ok"

    # Wipe local row + re-pull from epoch to truly verify server state
    storage.reset_db()
    sync.pull_table("tache")
    fresh = storage.get_row("tache", target["id"])
    assert fresh is not None, "row vanished after sync"
    assert json.loads(fresh["payload"]).get("echeance", "").startswith("2030-12-31"), \
        "echeance did NOT round-trip via server"
    print("✓ edit round-tripped via server — LWW upsert OK")

    # Step 4: delete
    print(f"\n→ local DELETE on tache {target['id']}")
    storage.mark_local_delete("tache", target["id"], datetime.now(timezone.utc).isoformat())
    _print(sync.push_all())
    storage.set_since("tache", "1970-01-01T00:00:00+00:00")
    sync.pull_table("tache")
    after_del = storage.get_row("tache", target["id"])
    assert after_del is not None and after_del["is_deleted"] == 1, "tombstone did NOT propagate"
    print("✓ tombstone propagated — soft delete OK")

    # Step 5: conflict (force an old client_updated_at)
    print("\n→ conflict test — staging an upsert dated 1990")
    payload2 = json.loads(after_del["payload"])
    payload2["libelle"] = "[POC-OUTDATED-WRITE] should be rejected"
    payload2["is_deleted"] = False
    storage.mark_local_upsert("tache", payload2, "1990-01-01T00:00:00+00:00")
    res = sync.push_all()
    _print(res)
    tache_summary = next(r for r in res if r["table"] == "tache")
    assert tache_summary["conflict"] >= 1, "expected at least 1 conflict"
    after_conflict = storage.get_row("tache", target["id"])
    assert json.loads(after_conflict["payload"]).get("libelle") != "[POC-OUTDATED-WRITE] should be rejected", \
        "server payload did NOT overwrite local on conflict"
    print("✓ conflict detected, server payload restored locally — LWW conflict OK")

    print("\n🎉 demo passed: pull / push (upsert + delete) / conflict resolution all verified.")


def main():
    parser = argparse.ArgumentParser(prog="client_poc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("login"); p.add_argument("user"); p.add_argument("password"); p.set_defaults(func=cmd_login)
    sub.add_parser("pull").set_defaults(func=cmd_pull)
    sub.add_parser("push").set_defaults(func=cmd_push)
    sub.add_parser("sync").set_defaults(func=cmd_sync)
    sub.add_parser("reset").set_defaults(func=cmd_reset)
    sub.add_parser("demo").set_defaults(func=cmd_demo)

    p = sub.add_parser("show")
    p.add_argument("table"); p.add_argument("--all", dest="all_rows", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_show)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
