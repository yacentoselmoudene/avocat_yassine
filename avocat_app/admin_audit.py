from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "app_label", "model", "object_pk", "ip")
    list_filter = ("action", "app_label", "model")
    search_fields = ("object_pk", "object_repr", "actor__username", "actor__email", "ip", "user_agent", "path")
    date_hierarchy = "timestamp"
