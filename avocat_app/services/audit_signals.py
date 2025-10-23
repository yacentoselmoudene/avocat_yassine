# avocat_app/services/audit_signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from django.db.models import Model
from django.conf import settings

from ..models import AuditLog, AuditAction
from .audit_utils import diff_instances
from ..middleware.request_local import get_current_request
from ..utils.audit import is_migration_command

# ذاكرة مؤقتة قبل الحفظ لمقارنة old/new
_BEFORE = {}

def _key(inst: Model):
    return f"{inst._meta.label_lower}:{inst.pk or 'new'}"

def _should_audit(inst: Model) -> bool:
    # لا تسجل نفسك ولا موديلات التدقيق
    return inst.__class__ is not AuditLog

@receiver(pre_save)
def _capture_before_save(sender, instance, **kwargs):
    if is_migration_command() or not settings.AUDIT_ENABLED:
        return
    if not _should_audit(instance): return
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _BEFORE[_key(instance)] = old
        except sender.DoesNotExist:
            _BEFORE[_key(instance)] = None

@receiver(post_save)
def _audit_after_save(sender, instance, created, **kwargs):
    if is_migration_command() or not settings.AUDIT_ENABLED:
        return
    if not _should_audit(instance): return
    if not getattr(settings, "AUDIT_ENABLED", True): return
    request = get_current_request()

    old = _BEFORE.pop(_key(instance), None)
    action = AuditAction.CREATE if created else AuditAction.UPDATE
    changes = diff_instances(old, instance)

    # لو UPDATE بلا تغييرات (مثل حفظ غير مؤثر)، يمكن التخلّي عنه
    if action == AuditAction.UPDATE and not changes:
        return

    AuditLog.objects.create(
        actor=getattr(request, "user", None) if request and getattr(request, "user", None) and request.user.is_authenticated else None,
        action=action,
        app_label=instance._meta.app_label,
        model=instance._meta.model_name,
        object_pk=str(instance.pk),
        object_repr=str(instance),
        changes=changes,
        path=getattr(request, "path", "") if request else "",
        method=getattr(request, "method", "") if request else "",
        status_code=getattr(request, "status_code", None),  # غالبًا غير متاح هنا
        ip=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT")[:256] if request else None,
        session_key=getattr(request, "session", None).session_key if request and getattr(request, "session", None) else None,
        token_id=str(getattr(request, "auth_token_id", "") or "") if request else None,
    )

@receiver(post_delete)
def _audit_after_delete(sender, instance, **kwargs):
    if is_migration_command() or not settings.AUDIT_ENABLED:
        return
    if not _should_audit(instance): return
    if not getattr(settings, "AUDIT_ENABLED", True): return
    request = get_current_request()
    AuditLog.objects.create(
        actor=getattr(request, "user", None) if request and getattr(request, "user", None) and request.user.is_authenticated else None,
        action=AuditAction.DELETE,
        app_label=instance._meta.app_label,
        model=instance._meta.model_name,
        object_pk=str(instance.pk) if instance.pk else None,
        object_repr=str(instance),
        changes=None,
        path=getattr(request, "path", "") if request else "",
        method=getattr(request, "method", "") if request else "",
        status_code=getattr(request, "status_code", None),
        ip=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT")[:256] if request else None,
        session_key=getattr(request, "session", None).session_key if request and getattr(request, "session", None) else None,
        token_id=str(getattr(request, "auth_token_id", "") or "") if request else None,
    )
