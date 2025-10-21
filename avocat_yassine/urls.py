"""
URL configuration for avocat_yassine project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('avocat_app.urls')),
    path('admin/', admin.site.urls),

]

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




