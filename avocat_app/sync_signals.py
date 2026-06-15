"""Local-write capture for desktop mode.

When `settings.DESKTOP_MODE` is True, every save/delete on a registered core
model writes a row in `SyncOutbox`. The desktop sync engine drains that queue
and POSTs `/api/sync/push/` on the central server.

The capture is bypassed when `suppress_outbox()` is active — the sync engine
uses it while applying server payloads to local DB (otherwise pulls would
immediately push themselves back).
"""
import json
import threading
from contextlib import contextmanager

from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

_local = threading.local()


@contextmanager
def suppress_outbox():
    prev = getattr(_local, "suppressed", False)
    _local.suppressed = True
    try:
        yield
    finally:
        _local.suppressed = prev


def _is_suppressed() -> bool:
    return getattr(_local, "suppressed", False)


def _make_handler(table_name: str):
    def _post_save(sender, instance, created, update_fields=None, **kwargs):  # noqa: ARG001
        if not getattr(settings, "DESKTOP_MODE", False) or _is_suppressed():
            return
        from .models import SyncOutbox
        is_soft_delete = (
            update_fields is not None
            and "is_deleted" in set(update_fields)
            and getattr(instance, "is_deleted", False)
        )
        op = SyncOutbox.DELETE if is_soft_delete else SyncOutbox.UPSERT
        fields = None
        if op == SyncOutbox.UPSERT and update_fields is not None:
            fields = sorted(set(update_fields) - {"updated_at"})
        SyncOutbox.objects.create(
            table_name=table_name,
            entity_id=str(instance.pk),
            op=op,
            changed_fields=json.dumps(fields) if fields else None,
            client_updated_at=getattr(instance, "updated_at", None) or timezone.now(),
        )

    def _post_delete(sender, instance, **kwargs):  # noqa: ARG001
        if not getattr(settings, "DESKTOP_MODE", False) or _is_suppressed():
            return
        from .models import SyncOutbox
        SyncOutbox.objects.create(
            table_name=table_name,
            entity_id=str(instance.pk),
            op=SyncOutbox.DELETE,
            client_updated_at=getattr(instance, "updated_at", None) or timezone.now(),
        )

    return _post_save, _post_delete


def register_outbox_signals():
    """Wire post_save/post_delete on every core sync table."""
    from .api.registry import CORE_TABLES
    for name, model in CORE_TABLES:
        ps, pd = _make_handler(name)
        post_save.connect(ps, sender=model, weak=False,
                          dispatch_uid=f"outbox_save_{name}")
        post_delete.connect(pd, sender=model, weak=False,
                            dispatch_uid=f"outbox_delete_{name}")
