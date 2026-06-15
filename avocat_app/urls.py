# avocat_app/urls.py
from django.urls import path
from . import views, views_audit, views_portail, views_cabinet_params, views_users, views_codes_affaire

app_name = "cabinet"

urlpatterns = [
    # ====== الصفحة الرئيسية (يمكن جعلها لائحة القضايا) ======
    path("", views.DashboardView.as_view(), name="dashboard"),

    # ====== Paramètres du cabinet ======
    path("parametres/cabinet/", views_cabinet_params.cabinet_params_view, name="cabinet_params"),

    # ====== Gestion des utilisateurs ======
    path("parametres/users/", views_users.user_list, name="user_list"),
    path("parametres/users/create/", views_users.user_create, name="user_create"),
    path("parametres/users/<int:user_id>/edit/", views_users.user_edit, name="user_edit"),
    path("parametres/users/<int:user_id>/delete/", views_users.user_delete, name="user_delete"),

    # ====== Recherche globale (HTMX autocomplete) ======
    path("search/", views.global_search, name="global_search"),

    # ====== Juridiction ======
    path("juridictions/", views.JuridictionList.as_view(), name="juridiction_list"),
    path("juridictions/create/", views.JuridictionCreate.as_view(), name="juridiction_create"),
    path("juridictions/<int:pk>/", views.JuridictionDetail.as_view(), name="juridiction_detail"),
    path("juridictions/<int:pk>/update/", views.JuridictionUpdate.as_view(), name="juridiction_update"),
    path("juridictions/<int:pk>/delete/", views.JuridictionDelete.as_view(), name="juridiction_delete"),

    # ====== Avocat ======
    path("avocats/", views.AvocatList.as_view(), name="avocat_list"),
    path("avocats/create/", views.AvocatCreate.as_view(), name="avocat_create"),
    path("avocats/<uuid:pk>/", views.AvocatDetail.as_view(), name="avocat_detail"),
    path("avocats/<uuid:pk>/update/", views.AvocatUpdate.as_view(), name="avocat_update"),
    path("avocats/<uuid:pk>/delete/", views.AvocatDelete.as_view(), name="avocat_delete"),

    # ====== Affaire (+ جزئي للتايملاين) ======
    path("affaires/", views.AffaireList.as_view(), name="affaire_list"),
    path("affaires/create/", views.AffaireCreate.as_view(), name="affaire_create"),
    path("affaires/<uuid:pk>/", views.AffaireDetail.as_view(), name="affaire_detail"),
    path("affaires/<uuid:pk>/update/", views.AffaireUpdate.as_view(), name="affaire_update"),
    path("affaires/<uuid:pk>/delete/", views.AffaireDelete.as_view(), name="affaire_delete"),
    # HTMX: تحديث جزء الـTimeline فقط
    path("affaires/<uuid:pk>/timeline/", views.affaire_timeline_partial, name="affaire_timeline"),

# ------ Créations imbriquées par Affaire ------
    path("affaires/<uuid:affaire_id>/audiences/new/", views.AudienceCreateForAffaire.as_view(), name="audience_create"),
    path("affaires/<uuid:affaire_id>/mesures/new/", views.MesureCreateForAffaire.as_view(), name="mesure_create"),
    path("affaires/<uuid:affaire_id>/expertises/new/", views.ExpertiseCreateForAffaire.as_view(), name="expertise_create"),
    path("affaires/<uuid:affaire_id>/decisions/new/", views.DecisionCreateForAffaire.as_view(), name="decision_create"),
    path("affaires/<uuid:affaire_id>/notifications/new/", views.NotificationCreateForAffaire.as_view(), name="notification_create"),
    path("affaires/<uuid:affaire_id>/recours/new/", views.RecoursCreateForAffaire.as_view(), name="voiederecours_create"),
    path("affaires/<uuid:affaire_id>/executions/new/", views.ExecutionCreateForAffaire.as_view(), name="execution_create"),
    path("affaires/<uuid:affaire_id>/avertissements/new/", views.AvertissementCreateForAffaire.as_view(), name="avertissement_create_for_affaire"),



    # ====== Audience ======
    path("audiences/", views.AudienceList.as_view(), name="audience_list"),
    path("audiences/create/", views.AudienceCreate.as_view(), name="audience_create"),
    path("audiences/<uuid:pk>/", views.AudienceDetail.as_view(), name="audience_detail"),
    path("audiences/<uuid:pk>/update/", views.AudienceUpdate.as_view(), name="audience_update"),
    path("audiences/<uuid:pk>/delete/", views.AudienceDelete.as_view(), name="audience_delete"),
    path("audiences/<uuid:pk>/set-result/", views.AudienceSetResult.as_view(), name="audience_set_result"),
    path("audiences/<uuid:pk>/row/", views.AudienceRow.as_view(), name="audience_row"),

    # API : juridictions adaptées à une catégorie d'affaire
    path("api/categories/<int:code_categorie_id>/juridictions/",
         views.api_juridictions_for_category, name="api_juridictions_for_category"),

    # === API : cascade mahakim.ma ===
    # GET /api/cours-appel/                  → liste des CA
    # GET /api/juridictions-by-ca/?ca=<id>   → PI rattachées à une CA
    # GET /api/codes-affaire/                → tous les code_type (chambres) groupés
    #                              ?sous_type=ابتدائي → codes filtrés par sous_type
    #                              ?code_type=1100    → codes d'une chambre donnée
    path("api/affaires/check-duplicate/", views.api_affaire_check_duplicate, name="api_affaire_check_duplicate"),
    path("api/cours-appel/",            views.api_cours_appel,        name="api_cours_appel"),
    path("api/juridictions-by-ca/",     views.api_juridictions_by_ca, name="api_juridictions_by_ca"),
    path("api/codes-affaire/",          views.api_codes_affaire,      name="api_codes_affaire"),
    path("api/code-types/",             views.api_code_types,         name="api_code_types"),

    # ====== Decision ======
    path("decisions/", views.DecisionList.as_view(), name="decision_list"),
    path("decisions/create/", views.DecisionCreate.as_view(), name="decision_create"),
    path("decisions/<uuid:pk>/", views.DecisionDetail.as_view(), name="decision_detail"),
    path("decisions/<uuid:pk>/update/", views.DecisionUpdate.as_view(), name="decision_update"),
    path("decisions/<uuid:pk>/delete/", views.DecisionDelete.as_view(), name="decision_delete"),

# ====== Notification ======
    path("notifications/", views.NotificationList.as_view(), name="notification_list"),
    path("notifications/create/", views.NotificationCreate.as_view(), name="notification_create"),
    path("notifications/<uuid:pk>/", views.NotificationDetail.as_view(), name="notification_detail"),
    path("notifications/<uuid:pk>/update/", views.NotificationUpdate.as_view(), name="notification_update"),
    path("notifications/<uuid:pk>/delete/", views.NotificationDelete.as_view(), name="notification_delete"),

    # ====== Partie ======
    path("parties/", views.PartieList.as_view(), name="partie_list"),
    path("parties/create/", views.PartieCreate.as_view(), name="partie_create"),
    path("parties/<uuid:pk>/", views.PartieDetail.as_view(), name="partie_detail"),
    path("parties/<uuid:pk>/update/", views.PartieUpdate.as_view(), name="partie_update"),
    path("parties/<uuid:pk>/delete/", views.PartieDelete.as_view(), name="partie_delete"),

    path("experts/", views.ExpertList.as_view(), name="expert_list"),
    path("experts/create/", views.ExpertCreate.as_view(), name="expert_create"),
    path("experts/<uuid:pk>/", views.ExpertDetail.as_view(), name="expert_detail"),
    path("experts/<uuid:pk>/update/", views.ExpertUpdate.as_view(), name="expert_update"),
    path("experts/<uuid:pk>/delete/", views.ExpertDelete.as_view(), name="expert_delete"),

    # ====== Relations Affaire-Partie / Affaire-Avocat ======
    path("affaire-parties/", views.AffairePartieList.as_view(), name="affairepartie_list"),
    path("affaire-parties/create/", views.AffairePartieCreate.as_view(), name="affairepartie_create"),
    path("affaire-parties/<uuid:pk>/", views.AffairePartieDetail.as_view(), name="affairepartie_detail"),
    path("affaire-parties/<uuid:pk>/update/", views.AffairePartieUpdate.as_view(), name="affairepartie_update"),
    path("affaire-parties/<uuid:pk>/delete/", views.AffairePartieDelete.as_view(), name="affairepartie_delete"),

    path("affaire-avocats/", views.AffaireAvocatList.as_view(), name="affaireavocat_list"),
    path("affaire-avocats/create/", views.AffaireAvocatCreate.as_view(), name="affaireavocat_create"),
    path("affaire-avocats/<uuid:pk>/", views.AffaireAvocatDetail.as_view(), name="affaireavocat_detail"),
    path("affaire-avocats/<uuid:pk>/update/", views.AffaireAvocatUpdate.as_view(), name="affaireavocat_update"),
    path("affaire-avocats/<uuid:pk>/delete/", views.AffaireAvocatDelete.as_view(), name="affaireavocat_delete"),

    # ====== Mesure ======
    path("mesures/", views.MesureList.as_view(), name="mesure_list"),
    path("mesures/create/", views.MesureCreate.as_view(), name="mesure_create"),
    path("mesures/<uuid:pk>/", views.MesureDetail.as_view(), name="mesure_detail"),
    path("mesures/<uuid:pk>/update/", views.MesureUpdate.as_view(), name="mesure_update"),
    path("mesures/<uuid:pk>/delete/", views.MesureDelete.as_view(), name="mesure_delete"),

    # ====== Expertise ======
    path("expertises/", views.ExpertiseList.as_view(), name="expertise_list"),
    path("expertises/create/", views.ExpertiseCreate.as_view(), name="expertise_create"),
    path("expertises/<uuid:pk>/", views.ExpertiseDetail.as_view(), name="expertise_detail"),
    path("expertises/<uuid:pk>/update/", views.ExpertiseUpdate.as_view(), name="expertise_update"),
    path("expertises/<uuid:pk>/delete/", views.ExpertiseDelete.as_view(), name="expertise_delete"),

    # ====== Voie de recours ======
    path("recours/", views.VoieDeRecoursList.as_view(), name="voiederecours_list"),
    path("recours/create/", views.VoieDeRecoursCreate.as_view(), name="voiederecours_create"),
    path("recours/<uuid:pk>/", views.VoieDeRecoursDetail.as_view(), name="voiederecours_detail"),
    path("recours/<uuid:pk>/update/", views.VoieDeRecoursUpdate.as_view(), name="voiederecours_update"),
    path("recours/<uuid:pk>/delete/", views.VoieDeRecoursDelete.as_view(), name="voiederecours_delete"),

    # ====== Execution ======
    path("executions/", views.ExecutionList.as_view(), name="execution_list"),
    path("executions/create/", views.ExecutionCreate.as_view(), name="execution_create"),
    path("executions/<uuid:pk>/", views.ExecutionDetail.as_view(), name="execution_detail"),
    path("executions/<uuid:pk>/update/", views.ExecutionUpdate.as_view(), name="execution_update"),
    path("executions/<uuid:pk>/delete/", views.ExecutionDelete.as_view(), name="execution_delete"),

    # ====== Dépenses / Recettes ======
    path("depenses/", views.DepenseList.as_view(), name="depense_list"),
    path("depenses/create/", views.DepenseCreate.as_view(), name="depense_create"),
    path("depenses/<uuid:pk>/", views.DepenseDetail.as_view(), name="depense_detail"),
    path("depenses/<uuid:pk>/update/", views.DepenseUpdate.as_view(), name="depense_update"),
    path("depenses/<uuid:pk>/delete/", views.DepenseDelete.as_view(), name="depense_delete"),

    path("recettes/", views.RecetteList.as_view(), name="recette_list"),
    path("recettes/create/", views.RecetteCreate.as_view(), name="recette_create"),
    path("recettes/<uuid:pk>/", views.RecetteDetail.as_view(), name="recette_detail"),
    path("recettes/<uuid:pk>/update/", views.RecetteUpdate.as_view(), name="recette_update"),
    path("recettes/<uuid:pk>/delete/", views.RecetteDelete.as_view(), name="recette_delete"),

    # ====== Pièces jointes ======
    path("pieces/", views.PieceJointeList.as_view(), name="piecejointe_list"),
    path("pieces/create/", views.PieceJointeCreate.as_view(), name="piecejointe_create"),
    path("pieces/<uuid:pk>/", views.PieceJointeDetail.as_view(), name="piecejointe_detail"),
    path("pieces/<uuid:pk>/update/", views.PieceJointeUpdate.as_view(), name="piecejointe_update"),
    path("pieces/<uuid:pk>/delete/", views.PieceJointeDelete.as_view(), name="piecejointe_delete"),

    # ====== Utilisateurs / Tâches / Alertes ======
    path("users/", views.UtilisateurList.as_view(), name="utilisateur_list"),
    path("users/create/", views.UtilisateurCreate.as_view(), name="utilisateur_create"),
    path("users/<uuid:pk>/", views.UtilisateurDetail.as_view(), name="utilisateur_detail"),
    path("users/<uuid:pk>/update/", views.UtilisateurUpdate.as_view(), name="utilisateur_update"),
    path("users/<uuid:pk>/delete/", views.UtilisateurDelete.as_view(), name="utilisateur_delete"),

    path("taches/", views.TacheList.as_view(), name="tache_list"),
    path("taches/create/", views.TacheCreate.as_view(), name="tache_create"),
    path("taches/<uuid:pk>/", views.TacheDetail.as_view(), name="tache_detail"),
    path("taches/<uuid:pk>/update/", views.TacheUpdate.as_view(), name="tache_update"),
    path("taches/<uuid:pk>/delete/", views.TacheDelete.as_view(), name="tache_delete"),

    path("alertes/", views.AlerteList.as_view(), name="alerte_list"),
    path("alertes/create/", views.AlerteCreate.as_view(), name="alerte_create"),
    path("alertes/<uuid:pk>/", views.AlerteDetail.as_view(), name="alerte_detail"),
    path("alertes/<uuid:pk>/update/", views.AlerteUpdate.as_view(), name="alerte_update"),
    path("alertes/<uuid:pk>/delete/", views.AlerteDelete.as_view(), name="alerte_delete"),

    path("barreaux/", views.BarreauList.as_view(), name="barreau_list"),
    path("barreaux/create/", views.BarreauCreate.as_view(), name="barreau_create"),

    path("barreaux/<slug:pk>/", views.BarreauDetail.as_view(), name="barreau_detail"),
    path("barreaux/<slug:pk>/update/", views.BarreauUpdate.as_view(), name="barreau_update"),
    path("barreaux/<slug:pk>/delete/", views.BarreauDelete.as_view(), name="barreau_delete"),

    # ====== Avertissement (إنذار) ======
    path("avertissements/", views.AvertissementList.as_view(), name="avertissement_list"),
    path("avertissements/create/", views.AvertissementCreate.as_view(), name="avertissement_create"),
    path("avertissements/<uuid:pk>/", views.AvertissementDetail.as_view(), name="avertissement_detail"),
    path("avertissements/<uuid:pk>/update/", views.AvertissementUpdate.as_view(), name="avertissement_update"),
    path("avertissements/<uuid:pk>/delete/", views.AvertissementDelete.as_view(), name="avertissement_delete"),

    # ====== Popups Personne ======
    path("parties/<uuid:pk>/popup/", views.PartiePopup.as_view(), name="partie_popup"),
    path("experts/<uuid:pk>/popup/", views.ExpertPopup.as_view(), name="expert_popup"),
    path("avocats/<uuid:pk>/popup/", views.AvocatPopup.as_view(), name="avocat_popup"),
    path("users/<uuid:pk>/popup/", views.UtilisateurPopup.as_view(), name="utilisateur_popup"),

    # ====== Mahakim.ma Sync (مزامنة محاكم) ======
    path("mahakim/", views.MahakimSyncListView.as_view(), name="mahakim_sync"),
    path("mahakim/sync-all/", views.sync_all_mahakim, name="mahakim_sync_all"),
    path("mahakim/preview-all/", views.mahakim_preview_all, name="mahakim_preview_all"),
    path("mahakim/fetch-ids/", views.fetch_mahakim_ids, name="mahakim_fetch_ids"),
    path("mahakim/fetch-ids-status/", views.fetch_mahakim_ids_status, name="mahakim_fetch_ids_status"),
    path("mahakim/fetch-ids-export/", views.fetch_mahakim_ids_export, name="mahakim_fetch_ids_export"),
    path("affaires/<uuid:pk>/sync-mahakim/", views.sync_affaire_mahakim, name="affaire_sync_mahakim"),
    path("affaires/<uuid:pk>/sync-preview/", views.mahakim_preview_single, name="mahakim_preview_single"),
    path("mahakim/sync-sessions/", views.sync_sessions_mahakim, name="mahakim_sync_sessions"),
    path("mahakim/preview-sessions/", views.mahakim_preview_sessions, name="mahakim_preview_sessions"),
    path("mahakim/tribunaux-pi/", views.get_tribunaux_pi, name="mahakim_tribunaux_pi"),

    # ====== المسطرة الغيابية (Contumace) ======
    path("contumace/", views.ContumaceListView.as_view(), name="contumace_list"),
    path("mahakim/sync-contumace/", views.sync_contumace_mahakim, name="mahakim_sync_contumace"),
    path("mahakim/sync-contumace-status/", views.contumace_sync_status, name="mahakim_sync_contumace_status"),
    path("mahakim/preview-contumace/", views.mahakim_preview_contumace, name="mahakim_preview_contumace"),

    # ====== حاسبة الرسوم القضائية (Tax Calculator — حساب محلي) ======
    path("tax-calculator/", views.TaxCalculatorView.as_view(), name="tax_calculator"),

    # ====== Document viewer & print ======
    path("viewer/", views.document_viewer, name="document_viewer"),
    path("print-docs/", views.print_documents, name="print_documents"),

    # ====== دليل الاستعمال ======
    path("guide/", views.user_guide, name="user_guide"),

    path("audit/", views_audit.AuditLogList.as_view(), name="audit_list"),
    path("audit/<uuid:pk>/", views_audit.AuditLogDetail.as_view(), name="audit_detail"),

    # ====== Carte des juridictions (Leaflet) ======
    path("map/", views.juridictions_map, name="juridictions_map"),

    # ====== Recherche jurisprudentielle (sémantique) ======
    path("search/jurisprudence/", views.jurisprudence_search, name="jurisprudence_search"),

    # ====== Portail client (magic link) ======
    path("parties/<uuid:partie_id>/portail-link/", views.portail_issue_link, name="portail_issue_link"),
    path("portail/login/", views_portail.portail_login, name="portail_login"),
    path("portail/access/<str:token>/", views_portail.portail_access, name="portail_access"),
    path("portail/logout/", views_portail.portail_logout, name="portail_logout"),
    path("portail/", views_portail.portail_dashboard, name="portail_dashboard"),
    path("portail/affaire/<uuid:pk>/", views_portail.portail_affaire_detail, name="portail_affaire_detail"),

    # ====== AI — Analyse de décision (Claude) ======
    path("decisions/<uuid:pk>/ai-analyze/", views.decision_ai_analyze, name="decision_ai_analyze"),

    # ====== WhatsApp Webhook entrant (Twilio) ======
    path("webhooks/twilio/whatsapp/", views.whatsapp_webhook, name="whatsapp_webhook"),

    # ====== WhatsApp (Twilio) ======
    path("whatsapp/templates/", views.WhatsAppTemplateList.as_view(), name="whatsapp_template_list"),
    path("whatsapp/templates/create/", views.WhatsAppTemplateCreate.as_view(), name="whatsapp_template_create"),
    path("whatsapp/templates/<uuid:pk>/update/", views.WhatsAppTemplateUpdate.as_view(), name="whatsapp_template_update"),
    path("whatsapp/templates/<uuid:pk>/delete/", views.WhatsAppTemplateDelete.as_view(), name="whatsapp_template_delete"),
    path("whatsapp/messages/", views.WhatsAppMessageList.as_view(), name="whatsapp_message_list"),
    path("audiences/<uuid:audience_id>/whatsapp-remind/", views.whatsapp_send_audience_reminder, name="whatsapp_send_audience_reminder"),
]
