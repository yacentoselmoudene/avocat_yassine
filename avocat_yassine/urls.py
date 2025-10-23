# project/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth (واجهة عربية جميلة عبر django.contrib.auth + قوالبك)
    path("auth/", include(("avocat_app.auth_urls", "authui"), namespace="authui")),
    # يمكن تخصيص قوالب تسجيل الدخول/الخروج عبر:
    # templates/registration/login.html
    # templates/registration/logged_out.html
    path("ref/", include("avocat_app.urls_ref")),  # toutes les pages référentiel sous /ref/

    # تطبيق المكتب (كل صفحات CRUD والمودالات HTMX…)
    path("", include(("avocat_app.urls", "cabinet"), namespace="cabinet")),
]

# ملفات MEDIA أثناء التطوير فقط
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# =============================================
# FILE: admin.py  (إضافة CSS الـRTL بسهولة لكل ModelAdmin)
# =============================================
# في ملف admin.py الحالي، أضِف mixin صغيرًا:

class RtlAdminMixin:
    class Media:
        css = {
            'all': ('admin_rtl.css',)  # تأكد من جمع staticfiles
        }

# ثم اجعل جميع ModelAdmin ترث منه، مثال:
# class AffaireAdmin(RtlAdminMixin, admin.ModelAdmin):
#     ...

# يمكنك أيضًا تفعيل اللغة العربية عمومًا عبر settings (انظر أدناه)

# =============================================
# FILE: settings.py (مقاطع لإضافتها)
# =============================================



# =============================================
# FILE: templates/admin/base_site.html (اختياري لتعريب العناوين)
# =============================================
"""
{% extends "admin/base_site.html" %}
{% block title %}لوحة إدارة المكتب{% endblock %}
{% block branding %}<h1 id="site-name">إدارة مكتب المحاماة</h1>{% endblock %}
{% block extrastyle %}{{ block.super }}
<link rel="stylesheet" href="{% static 'admin_rtl.css' %}">
{% endblock %}
"""




