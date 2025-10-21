# cabinet/urls.py
from django.urls import path
from . import views, views_audit

app_name = "cabinet"

urlpatterns = [
    # ====== الصفحة الرئيسية (يمكن جعلها لائحة القضايا) ======
    path("", views.AffaireList.as_view(), name="home"),

    # ====== Juridiction ======
    path("juridictions/", views.JuridictionList.as_view(), name="juridiction_list"),
    path("juridictions/create/", views.JuridictionCreate.as_view(), name="juridiction_create"),
    path("juridictions/<int:pk>/", views.JuridictionDetail.as_view(), name="juridiction_detail"),
    path("juridictions/<int:pk>/update/", views.JuridictionUpdate.as_view(), name="juridiction_update"),
    path("juridictions/<int:pk>/delete/", views.JuridictionDelete.as_view(), name="juridiction_delete"),

    # ====== Avocat ======
    path("avocats/", views.AvocatList.as_view(), name="avocat_list"),
    path("avocats/create/", views.AvocatCreate.as_view(), name="avocat_create"),
    path("avocats/<int:pk>/", views.AvocatDetail.as_view(), name="avocat_detail"),
    path("avocats/<int:pk>/update/", views.AvocatUpdate.as_view(), name="avocat_update"),
    path("avocats/<int:pk>/delete/", views.AvocatDelete.as_view(), name="avocat_delete"),

    # ====== Affaire (+ جزئي للتايملاين) ======
    path("affaires/", views.AffaireList.as_view(), name="affaire_list"),
    path("affaires/create/", views.AffaireCreate.as_view(), name="affaire_create"),
    path("affaires/<int:pk>/", views.AffaireDetail.as_view(), name="affaire_detail"),
    path("affaires/<int:pk>/update/", views.AffaireUpdate.as_view(), name="affaire_update"),
    path("affaires/<int:pk>/delete/", views.AffaireDelete.as_view(), name="affaire_delete"),
    # HTMX: تحديث جزء الـTimeline فقط
    path("affaires/<int:pk>/timeline/", views.affaire_timeline_partial, name="affaire_timeline"),


    # ====== Audience ======
    path("audiences/", views.AudienceList.as_view(), name="audience_list"),
    path("audiences/create/", views.AudienceCreate.as_view(), name="audience_create"),
    path("audiences/<int:pk>/", views.AudienceDetail.as_view(), name="audience_detail"),
    path("audiences/<int:pk>/update/", views.AudienceUpdate.as_view(), name="audience_update"),
    path("audiences/<int:pk>/delete/", views.AudienceDelete.as_view(), name="audience_delete"),

    path("audit/", views_audit.AuditLogList.as_view(), name="audit_list"),
    path("audit/<int:pk>/", views_audit.AuditLogDetail.as_view(), name="audit_detail"),
]
