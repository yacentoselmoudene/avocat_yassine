# avocat_app/models_audit.py
from django.db import models
from django.conf import settings

class AuditAction(models.TextChoices):
    CREATE = "CREATE", "إنشاء"
    UPDATE = "UPDATE", "تعديل"
    DELETE = "DELETE", "حذف"
    LOGIN  = "LOGIN",  "دخول"
    LOGOUT = "LOGOUT", "خروج"
    ATTACH = "ATTACH", "إرفاق ملف"
    EMAIL  = "EMAIL",  "إرسال بريد"
    SMS    = "SMS",    "إرسال SMS"
    EXPORT = "EXPORT", "تصدير"
    IMPORT = "IMPORT", "استيراد"
    OTHER  = "OTHER",  "أخرى"

class AuditLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_entries")
    action = models.CharField(max_length=16, choices=AuditAction.choices)
    app_label = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    object_pk = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(blank=True, null=True)   # {field: [old, new]}
    path = models.CharField(max_length=255, blank=True)
    method = models.CharField(max_length=8, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    token_id = models.IntegerField(null=True, blank=True)  # من AuthToken لو متاح

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=["app_label", "model", "object_pk"]),
            models.Index(fields=["actor", "action", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.action} {self.app_label}.{self.model}#{self.object_pk}"
