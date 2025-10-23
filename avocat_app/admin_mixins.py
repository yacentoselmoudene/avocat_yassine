# admin_mixins.py
from django.contrib import admin
from django.utils.html import format_html

class SoftDeleteAdminMixin(admin.ModelAdmin):
    list_display = ("__str__", "is_deleted", "created_at", "updated_at")
    list_filter = ("is_deleted",)
    readonly_fields = ("created_at", "updated_at")

    actions = ["action_soft_delete", "action_restore", "action_hard_delete"]

    def get_queryset(self, request):
        # superuser voit tout; autres: seulement actifs
        qs = self.model.all_objects.get_queryset() if request.user.is_superuser else self.model.objects.get_queryset()
        return qs

    @admin.action(description="حذف (وسم كمحذوف)")
    def action_soft_delete(self, request, queryset):
        queryset.update(is_deleted=True)

    @admin.action(description="استعادة")
    def action_restore(self, request, queryset):
        queryset.update(is_deleted=False)

    @admin.action(description="حذف نهائي (لا يمكن التراجع)")
    def action_hard_delete(self, request, queryset):
        for obj in queryset:
            obj.hard_delete()
