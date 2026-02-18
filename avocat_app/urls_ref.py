# avocat_app/urls_ref.py
from django.urls import path
from . import views_ref as v
from .views_ref_generic import RefList, RefCreate, RefUpdate, RefDelete


app_name = "cabinet_ref"

urlpatterns = [
    path("<slug:refname>/", RefList.as_view(), name="ref_list"),
    path("<slug:refname>/new/", RefCreate.as_view(), name="ref_create"),
    path("<slug:refname>/<int:pk>/edit/", RefUpdate.as_view(), name="ref_update"),
    path("<slug:refname>/<int:pk>/delete/", RefDelete.as_view(), name="ref_delete"),
]

"""
urlpatternssss = [
    # TypeDepense
    path("typedepenses/", v.TypeDepenseList.as_view(), name="typedepense_list"),
    path("typedepenses/new/", v.TypeDepenseCreate.as_view(), name="typedepense_create"),
    path("typedepenses/<int:pk>/edit/", v.TypeDepenseUpdate.as_view(), name="typedepense_update"),
    path("typedepenses/<int:pk>/delete/", v.TypeDepenseDelete.as_view(), name="typedepense_delete"),

    # TypeRecette
    path("typerecettes/", v.TypeRecetteList.as_view(), name="typerecette_list"),
    path("typerecettes/new/", v.TypeRecetteCreate.as_view(), name="typerecette_create"),
    path("typerecettes/<int:pk>/edit/", v.TypeRecetteUpdate.as_view(), name="typerecette_update"),
    path("typerecettes/<int:pk>/delete/", v.TypeRecetteDelete.as_view(), name="typerecette_delete"),

    # RoleUtilisateur
    path("roles/", v.RoleUtilisateurList.as_view(), name="roleutilisateur_list"),
    path("roles/new/", v.RoleUtilisateurCreate.as_view(), name="roleutilisateur_create"),
    path("roles/<int:pk>/edit/", v.RoleUtilisateurUpdate.as_view(), name="roleutilisateur_update"),
    path("roles/<int:pk>/delete/", v.RoleUtilisateurDelete.as_view(), name="roleutilisateur_delete"),

    # StatutTache
    path("statuts-execution/", v.StatutExecutionList.as_view(), name="statutexecution_list"),
    path("statuts-execution/new/", v.StatutExecutionCreate.as_view(), name="statutexecution_create"),
    path("statuts-execution/<int:pk>/edit/", v.StatutExecutionUpdate.as_view(), name="statutexecution_update"),
    path("statuts-execution/<int:pk>/delete/", v.StatutExecutionDelete.as_view(), name="statutexecution_delete"),

    # StatutTache
    path("statuts-recours/", v.StatutRecoursList.as_view(), name="statutrecours_list"),
    path("statuts-recours/new/", v.StatutRecoursCreate.as_view(), name="statutrecours_create"),
    path("statuts-recours/<int:pk>/edit/", v.StatutRecoursUpdate.as_view(), name="statutrecours_update"),
    path("statuts-recours/<int:pk>/delete/", v.StatutRecoursDelete.as_view(), name="statutrecours_delete"),

    path("statuts-tache/", v.StatutTacheList.as_view(), name="statuttache_list"),
    path("statuts-tache/new/", v.StatutTacheCreate.as_view(), name="statuttache_create"),
    path("statuts-tache/<int:pk>/edit/", v.StatutTacheUpdate.as_view(), name="statuttache_update"),
    path("statuts-tache/<int:pk>/delete/", v.StatutTacheDelete.as_view(), name="statuttache_delete"),

    # StatutTache
    path("statuts-affaire/", v.StatutAffaireList.as_view(), name="statutaffaire_list"),
    path("statuts-affaire/new/", v.StatutAffaireCreate.as_view(), name="statutaffaire_create"),
    path("statuts-affaire/<int:pk>/edit/", v.StatutAffaireUpdate.as_view(), name="statutaffaire_update"),
    path("statuts-affaire/<int:pk>/delete/", v.StatutAffaireDelete.as_view(), name="statutaffaire_delete"),

    path("types-audience/", v.TypeAudienceList.as_view(), name="typeaudience_list"),
    path("types-audience/new/", v.TypeAudienceCreate.as_view(), name="typeaudience_create"),
    path("types-audience/<int:pk>/edit/", v.TypeAudienceUpdate.as_view(), name="typeaudience_update"),
    path("types-audience/<int:pk>/delete/", v.TypeAudienceDelete.as_view(), name="typeaudience_delete"),


path("types-affaire/", v.TypeAffaireList.as_view(), name="typeaffaire_list"),
    path("types-affaire/new/", v.TypeAffaireCreate.as_view(), name="typeaffaire_create"),
    path("types-affaire/<int:pk>/edit/", v.TypeAffaireUpdate.as_view(), name="typeaffaire_update"),
    path("types-affaire/<int:pk>/delete/", v.TypeAffaireDelete.as_view(), name="typeaffaire_delete"),

    path("types-recours/", v.TypeRecoursList.as_view(), name="typerecours_list"),
    path("types-recours/new/", v.TypeRecoursCreate.as_view(), name="typerecours_create"),
    path("types-recours/<int:pk>/edit/", v.TypeRecoursUpdate.as_view(), name="typerecours_update"),
    path("types-recours/<int:pk>/delete/", v.TypeRecoursDelete.as_view(), name="typerecours_delete"),

    path("types-execution/", v.TypeExecutionList.as_view(), name="typeexecution_list"),
    path("types-execution/new/", v.TypeExecutionCreate.as_view(), name="typeexecution_create"),
    path("types-execution/<int:pk>/edit/", v.TypeExecutionUpdate.as_view(), name="typeexecution_update"),
    path("types-execution/<int:pk>/delete/", v.TypeExecutionDelete.as_view(), name="typeexecution_delete"),

    path("resultataudience/", v.ResultatAudienceList.as_view(), name="resultataudience_list"),
    path("resultataudience/new/", v.ResultatAudienceCreate.as_view(), name="resultataudience_create"),
    path("resultataudience/<int:pk>/edit/", v.ResultatAudienceUpdate.as_view(), name="resultataudience_update"),
    path("resultataudience/<int:pk>/delete/", v.ResultatAudienceDelete.as_view(), name="resultataudience_delete"),

    # TypeAlerte
    path("types-alerte/", v.TypeAlerteList.as_view(), name="typealerte_list"),
    path("types-alerte/new/", v.TypeAlerteCreate.as_view(), name="typealerte_create"),
    path("types-alerte/<int:pk>/edit/", v.TypeAlerteUpdate.as_view(), name="typealerte_update"),
    path("types-alerte/<int:pk>/delete/", v.TypeAlerteDelete.as_view(), name="typealerte_delete"),

    path("types-juridiction/", v.TypeJuridictionList.as_view(), name="typejuridiction_list"),
    path("types-juridiction/new/", v.TypeJuridictionCreate.as_view(), name="typejuridiction_create"),
    path("types-juridiction/<int:pk>/edit/", v.TypeJuridictionUpdate.as_view(), name="typejuridiction_update"),
    path("types-juridiction/<int:pk>/delete/", v.TypeJuridictionDelete.as_view(), name="typejuridiction_delete"),

    path("degres-juridiction/", v.DegreJuridictionList.as_view(), name="degrejuridiction_list"),
    path("degres-juridiction/new/", v.DegreJuridictionCreate.as_view(), name="degrejuridiction_create"),
    path("degres-juridiction/<int:pk>/edit/", v.DegreJuridictionUpdate.as_view(), name="degrejuridiction_update"),
    path("degres-juridiction/<int:pk>/delete/", v.DegreJuridictionDelete.as_view(), name="degrejuridiction_delete"),

]
"""