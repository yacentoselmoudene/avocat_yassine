# =============================================================
# FILE: urls.py  (روابط عربية الأسماء — app_name = 'cabinet')
# =============================================================
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


app_name = 'avoccat_app'

urlpatterns = [
    # Juridiction
    path('juridictions/', views.JuridictionList.as_view(), name='juridiction_list'),
    path('juridictions/new/', views.JuridictionCreate.as_view(), name='juridiction_create'),
    path('juridictions/<pk>/', views.JuridictionDetail.as_view(), name='juridiction_detail'),
    path('juridictions/<pk>/edit/', views.JuridictionUpdate.as_view(), name='juridiction_update'),
    path('juridictions/<pk>/delete/', views.JuridictionDelete.as_view(), name='juridiction_delete'),

    # Avocat
    path('avocats/', views.AvocatList.as_view(), name='avocat_list'),
    path('avocats/new/', views.AvocatCreate.as_view(), name='avocat_create'),
    path('avocats/<pk>/', views.AvocatDetail.as_view(), name='avocat_detail'),
    path('avocats/<pk>/edit/', views.AvocatUpdate.as_view(), name='avocat_update'),
    path('avocats/<pk>/delete/', views.AvocatDelete.as_view(), name='avocat_delete'),

    # Affaire
    path('affaires/', views.AffaireList.as_view(), name='affaire_list'),
    path('affaires/new/', views.AffaireCreate.as_view(), name='affaire_create'),
    path('affaires/<pk>/', views.AffaireDetail.as_view(), name='affaire_detail'),
    path('affaires/<pk>/edit/', views.AffaireUpdate.as_view(), name='affaire_update'),
    path('affaires/<pk>/delete/', views.AffaireDelete.as_view(), name='affaire_delete'),

    # Partie
    path('parties/', views.PartieList.as_view(), name='partie_list'),
    path('parties/new/', views.PartieCreate.as_view(), name='partie_create'),
    path('parties/<pk>/', views.PartieDetail.as_view(), name='partie_detail'),
    path('parties/<pk>/edit/', views.PartieUpdate.as_view(), name='partie_update'),
    path('parties/<pk>/delete/', views.PartieDelete.as_view(), name='partie_delete'),

    # AffairePartie
    path('affaire-parties/', views.AffairePartieList.as_view(), name='affairepartie_list'),
    path('affaire-parties/new/', views.AffairePartieCreate.as_view(), name='affairepartie_create'),
    path('affaire-parties/<pk>/', views.AffairePartieDetail.as_view(), name='affairepartie_detail'),
    path('affaire-parties/<pk>/edit/', views.AffairePartieUpdate.as_view(), name='affairepartie_update'),
    path('affaire-parties/<pk>/delete/', views.AffairePartieDelete.as_view(), name='affairepartie_delete'),

    # AffaireAvocat
    path('affaire-avocats/', views.AffaireAvocatList.as_view(), name='affaireavocat_list'),
    path('affaire-avocats/new/', views.AffaireAvocatCreate.as_view(), name='affaireavocat_create'),
    path('affaire-avocats/<pk>/', views.AffaireAvocatDetail.as_view(), name='affaireavocat_detail'),
    path('affaire-avocats/<pk>/edit/', views.AffaireAvocatUpdate.as_view(), name='affaireavocat_update'),
    path('affaire-avocats/<pk>/delete/', views.AffaireAvocatDelete.as_view(), name='affaireavocat_delete'),

    # Audience
    path('audiences/', views.AudienceList.as_view(), name='audience_list'),
    path('audiences/new/', views.AudienceCreate.as_view(), name='audience_create'),
    path('audiences/<pk>/', views.AudienceDetail.as_view(), name='audience_detail'),
    path('audiences/<pk>/edit/', views.AudienceUpdate.as_view(), name='audience_update'),
    path('audiences/<pk>/delete/', views.AudienceDelete.as_view(), name='audience_delete'),

    # Mesure
    path('mesures/', views.MesureList.as_view(), name='mesure_list'),
    path('mesures/new/', views.MesureCreate.as_view(), name='mesure_create'),
    path('mesures/<pk>/', views.MesureDetail.as_view(), name='mesure_detail'),
    path('mesures/<pk>/edit/', views.MesureUpdate.as_view(), name='mesure_update'),
    path('mesures/<pk>/delete/', views.MesureDelete.as_view(), name='mesure_delete'),

    # Expertise
    path('expertises/', views.ExpertiseList.as_view(), name='expertise_list'),
    path('expertises/new/', views.ExpertiseCreate.as_view(), name='expertise_create'),
    path('expertises/<pk>/', views.ExpertiseDetail.as_view(), name='expertise_detail'),
    path('expertises/<pk>/edit/', views.ExpertiseUpdate.as_view(), name='expertise_update'),
    path('expertises/<pk>/delete/', views.ExpertiseDelete.as_view(), name='expertise_delete'),

    # Decision
    path('decisions/', views.DecisionList.as_view(), name='decision_list'),
    path('decisions/new/', views.DecisionCreate.as_view(), name='decision_create'),
    path('decisions/<pk>/', views.DecisionDetail.as_view(), name='decision_detail'),
    path('decisions/<pk>/edit/', views.DecisionUpdate.as_view(), name='decision_update'),
    path('decisions/<pk>/delete/', views.DecisionDelete.as_view(), name='decision_delete'),

    # Notification
    path('notifications/', views.NotificationList.as_view(), name='notification_list'),
    path('notifications/new/', views.NotificationCreate.as_view(), name='notification_create'),
    path('notifications/<pk>/', views.NotificationDetail.as_view(), name='notification_detail'),
    path('notifications/<pk>/edit/', views.NotificationUpdate.as_view(), name='notification_update'),
    path('notifications/<pk>/delete/', views.NotificationDelete.as_view(), name='notification_delete'),

    # VoieDeRecours
    path('voies-de-recours/', views.VoieDeRecoursList.as_view(), name='voiederecours_list'),
    path('voies-de-recours/new/', views.VoieDeRecoursCreate.as_view(), name='voiederecours_create'),
    path('voies-de-recours/<pk>/', views.VoieDeRecoursDetail.as_view(), name='voiederecours_detail'),
    path('voies-de-recours/<pk>/edit/', views.VoieDeRecoursUpdate.as_view(), name='voiederecours_update'),
    path('voies-de-recours/<pk>/delete/', views.VoieDeRecoursDelete.as_view(), name='voiederecours_delete'),

    # Execution
    path('executions/', views.ExecutionList.as_view(), name='execution_list'),
    path('executions/new/', views.ExecutionCreate.as_view(), name='execution_create'),
    path('executions/<pk>/', views.ExecutionDetail.as_view(), name='execution_detail'),
    path('executions/<pk>/edit/', views.ExecutionUpdate.as_view(), name='execution_update'),
    path('executions/<pk>/delete/', views.ExecutionDelete.as_view(), name='execution_delete'),

    # Depense
    path('depenses/', views.DepenseList.as_view(), name='depense_list'),
    path('depenses/new/', views.DepenseCreate.as_view(), name='depense_create'),
    path('depenses/<pk>/', views.DepenseDetail.as_view(), name='depense_detail'),
    path('depenses/<pk>/edit/', views.DepenseUpdate.as_view(), name='depense_update'),
    path('depenses/<pk>/delete/', views.DepenseDelete.as_view(), name='depense_delete'),

    # Recette
    path('recettes/', views.RecetteList.as_view(), name='recette_list'),
    path('recettes/new/', views.RecetteCreate.as_view(), name='recette_create'),
    path('recettes/<pk>/', views.RecetteDetail.as_view(), name='recette_detail'),
    path('recettes/<pk>/edit/', views.RecetteUpdate.as_view(), name='recette_update'),
    path('recettes/<pk>/delete/', views.RecetteDelete.as_view(), name='recette_delete'),

    # PieceJointe
    path('pieces/', views.PieceJointeList.as_view(), name='piecejointe_list'),
    path('pieces/new/', views.PieceJointeCreate.as_view(), name='piecejointe_create'),
    path('pieces/<pk>/', views.PieceJointeDetail.as_view(), name='piecejointe_detail'),
    path('pieces/<pk>/edit/', views.PieceJointeUpdate.as_view(), name='piecejointe_update'),
    path('pieces/<pk>/delete/', views.PieceJointeDelete.as_view(), name='piecejointe_delete'),

    # Utilisateur
    path('utilisateurs/', views.UtilisateurList.as_view(), name='utilisateur_list'),
    path('utilisateurs/new/', views.UtilisateurCreate.as_view(), name='utilisateur_create'),
    path('utilisateurs/<pk>/', views.UtilisateurDetail.as_view(), name='utilisateur_detail'),
    path('utilisateurs/<pk>/edit/', views.UtilisateurUpdate.as_view(), name='utilisateur_update'),
    path('utilisateurs/<pk>/delete/', views.UtilisateurDelete.as_view(), name='utilisateur_delete'),

    # Tache
    path('taches/', views.TacheList.as_view(), name='tache_list'),
    path('taches/new/', views.TacheCreate.as_view(), name='tache_create'),
    path('taches/<pk>/', views.TacheDetail.as_view(), name='tache_detail'),
    path('taches/<pk>/edit/', views.TacheUpdate.as_view(), name='tache_update'),
    path('taches/<pk>/delete/', views.TacheDelete.as_view(), name='tache_delete'),

    # Alerte
    path('alertes/', views.AlerteList.as_view(), name='alerte_list'),
    path('alertes/new/', views.AlerteCreate.as_view(), name='alerte_create'),
    path('alertes/<pk>/', views.AlerteDetail.as_view(), name='alerte_detail'),
    path('alertes/<pk>/edit/', views.AlerteUpdate.as_view(), name='alerte_update'),
    path('alertes/<pk>/delete/', views.AlerteDelete.as_view(), name='alerte_delete'),
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)