# avocat_app/urls_ref.py
from django.urls import path
from . import views_ref as v

app_name = "cabinet"

urlpatterns = [
    # TypeDepense
    path("typedepenses/", v.TypeDepenseList.as_view(), name="typedepense_list"),
    path("typedepenses/new/", v.TypeDepenseCreate.as_view(), name="typedepense_create"),
    path("typedepenses/<uuid:pk>/edit/", v.TypeDepenseUpdate.as_view(), name="typedepense_update"),
    path("typedepenses/<uuid:pk>/delete/", v.TypeDepenseDelete.as_view(), name="typedepense_delete"),

    # TypeRecette
    path("typerecettes/", v.TypeRecetteList.as_view(), name="typerecette_list"),
    path("typerecettes/new/", v.TypeRecetteCreate.as_view(), name="typerecette_create"),
    path("typerecettes/<uuid:pk>/edit/", v.TypeRecetteUpdate.as_view(), name="typerecette_update"),
    path("typerecettes/<uuid:pk>/delete/", v.TypeRecetteDelete.as_view(), name="typerecette_delete"),

    # RoleUtilisateur
    path("roles/", v.RoleUtilisateurList.as_view(), name="roleutilisateur_list"),
    path("roles/new/", v.RoleUtilisateurCreate.as_view(), name="roleutilisateur_create"),
    path("roles/<uuid:pk>/edit/", v.RoleUtilisateurUpdate.as_view(), name="roleutilisateur_update"),
    path("roles/<uuid:pk>/delete/", v.RoleUtilisateurDelete.as_view(), name="roleutilisateur_delete"),

    # StatutTache
    path("statuts-tache/", v.StatutTacheList.as_view(), name="statuttache_list"),
    path("statuts-tache/new/", v.StatutTacheCreate.as_view(), name="statuttache_create"),
    path("statuts-tache/<uuid:pk>/edit/", v.StatutTacheUpdate.as_view(), name="statuttache_update"),
    path("statuts-tache/<uuid:pk>/delete/", v.StatutTacheDelete.as_view(), name="statuttache_delete"),

    # TypeAlerte
    path("types-alerte/", v.TypeAlerteList.as_view(), name="typealerte_list"),
    path("types-alerte/new/", v.TypeAlerteCreate.as_view(), name="typealerte_create"),
    path("types-alerte/<uuid:pk>/edit/", v.TypeAlerteUpdate.as_view(), name="typealerte_update"),
    path("types-alerte/<uuid:pk>/delete/", v.TypeAlerteDelete.as_view(), name="typealerte_delete"),
]
