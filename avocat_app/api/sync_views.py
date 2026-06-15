"""Sync endpoints — pull (incremental delta) and push (LWW per row).

Protocol summary:
  GET  /api/sync/tables/                     -> list of synchronisable tables
  GET  /api/sync/pull/?table=&since=&limit=  -> rows updated_at > since (tombstones included)
  POST /api/sync/push/                       -> batch upsert/delete with LWW

Conflict resolution: last-write-wins on `updated_at`. The push payload MUST
carry `client_updated_at` for each item; if server's `updated_at` is newer,
the change is rejected as "conflict" and the server version is returned so
the client can reconcile.
"""
from datetime import datetime, timezone as dt_tz

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .registry import (
    SYNC_TABLES,
    get_model,
    get_role,
    is_pushable,
    list_table_names,
)
from .serializers import get_serializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EPOCH = datetime(1970, 1, 1, tzinfo=dt_tz.utc)


def _parse_since(raw: str | None):
    if not raw:
        return EPOCH
    ts = parse_datetime(raw)
    if ts is None:
        return None
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, dt_tz.utc)
    return ts


def _clamp_limit(raw: str | None) -> int:
    default = settings.SYNC_PULL_DEFAULT_LIMIT
    maximum = settings.SYNC_PULL_MAX_LIMIT
    try:
        n = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        n = default
    return max(1, min(maximum, n))


def _server_time_iso():
    return timezone.now().isoformat()


# ---------------------------------------------------------------------------
# GET /api/sync/tables/
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_tables(request):
    return Response({
        "server_time": _server_time_iso(),
        "tables": [
            {"name": name, "role": get_role(name), "pushable": is_pushable(name)}
            for name, _ in SYNC_TABLES
        ],
    })


# ---------------------------------------------------------------------------
# GET /api/sync/pull/
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sync_pull(request):
    table = request.query_params.get("table")
    if not table:
        return Response({"detail": "missing 'table' query param"}, status=400)

    model = get_model(table)
    if model is None:
        return Response({"detail": f"unknown table '{table}'"}, status=404)

    since = _parse_since(request.query_params.get("since"))
    if since is None:
        return Response({"detail": "invalid 'since' (ISO-8601 expected)"}, status=400)

    limit = _clamp_limit(request.query_params.get("limit"))

    qs = (model.all_objects
                .filter(updated_at__gt=since)
                .order_by("updated_at", "pk"))
    rows = list(qs[: limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]

    Serializer = get_serializer(table)
    items = Serializer(rows, many=True).data

    next_since = rows[-1].updated_at.isoformat() if rows else since.isoformat()

    return Response({
        "table": table,
        "server_time": _server_time_iso(),
        "since": since.isoformat(),
        "next_since": next_since,
        "has_more": has_more,
        "count": len(items),
        "items": items,
    })


# ---------------------------------------------------------------------------
# POST /api/sync/push/
# ---------------------------------------------------------------------------

def _process_change(item: dict) -> dict:
    table = item.get("table")
    op = item.get("op")
    payload = item.get("payload") or {}
    client_id = payload.get("id")

    if table is None or op not in {"upsert", "delete"}:
        return {"id": client_id, "table": table, "status": "error",
                "detail": "invalid 'table' or 'op'"}

    if not is_pushable(table):
        return {"id": client_id, "table": table, "status": "error",
                "detail": f"table '{table}' is not pushable from clients"}

    model = get_model(table)
    if not client_id:
        return {"id": None, "table": table, "status": "error",
                "detail": "payload.id is required"}

    raw_client_ts = item.get("client_updated_at") or payload.get("updated_at")
    client_ts = _parse_since(raw_client_ts) if raw_client_ts else timezone.now()
    if client_ts is None:
        return {"id": client_id, "table": table, "status": "error",
                "detail": "invalid client_updated_at"}

    existing = model.all_objects.filter(pk=client_id).first()

    if existing is not None and existing.updated_at > client_ts:
        Serializer = get_serializer(table)
        return {
            "id": str(client_id),
            "table": table,
            "status": "conflict",
            "server_updated_at": existing.updated_at.isoformat(),
            "server_payload": Serializer(existing).data,
        }

    Serializer = get_serializer(table)

    if op == "delete":
        if existing is None:
            return {"id": str(client_id), "table": table, "status": "ok",
                    "detail": "already absent"}
        existing.is_deleted = True
        existing.updated_at = timezone.now()
        existing.save(update_fields=["is_deleted", "updated_at"])
        return {"id": str(client_id), "table": table, "status": "ok",
                "server_updated_at": existing.updated_at.isoformat()}

    # op == "upsert"
    # `partial=True` so callers can send only the changed fields.
    # When existing is None (new row), DRF still enforces required fields.
    ser = Serializer(instance=existing, data=payload, partial=True)
    if not ser.is_valid():
        return {"id": str(client_id), "table": table, "status": "error",
                "detail": "validation failed", "errors": ser.errors}
    obj = ser.save()
    return {"id": str(obj.pk), "table": table, "status": "ok",
            "server_updated_at": obj.updated_at.isoformat()}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_push(request):
    changes = request.data.get("changes") if isinstance(request.data, dict) else None
    if not isinstance(changes, list):
        return Response({"detail": "body must be {'changes': [...]}"},
                        status=status.HTTP_400_BAD_REQUEST)

    if len(changes) > settings.SYNC_PUSH_MAX_BATCH:
        return Response(
            {"detail": f"batch too large (max {settings.SYNC_PUSH_MAX_BATCH})"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    results = []
    for item in changes:
        try:
            with transaction.atomic():
                results.append(_process_change(item))
        except Exception as exc:  # noqa: BLE001
            results.append({
                "id": (item or {}).get("payload", {}).get("id"),
                "table": (item or {}).get("table"),
                "status": "error",
                "detail": str(exc),
            })

    return Response({"server_time": _server_time_iso(), "results": results})
