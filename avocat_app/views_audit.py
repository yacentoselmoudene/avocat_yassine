from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from .models import AuditLog

class AuditLogList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "cabinet.view_auditlog"  # أنشئ صلاحية مخصصة لو أردت
    model = AuditLog
    paginate_by = 50
    ordering = "-timestamp"
    template_name = "audit/auditlog_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(object_repr__icontains=q)
        # فلاتر أخرى حسب الحاجة (action، user…)
        return qs

class AuditLogDetail(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "cabinet.view_auditlog"
    model = AuditLog
    template_name = "audit/auditlog_detail.html"
