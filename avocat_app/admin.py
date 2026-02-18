# =============================
# FILE: admin.py
# Admin en FR + libelles AR pour les colonnes affichees
# =============================
from pathlib import Path

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte, TypeDepense,
    TypeRecette, RoleUtilisateur, StatutTache, TypeAlerte, StatutAffaire, TypeAffaire, TypeMesure,
    TypeRecours, TypeExecution, TypeRecette, TypeAlerte, StatutRecours, StatutExecution,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---- Personnalisation globale de l'admin (FR) ----
admin.site.site_header = "Gestion du Cabinet d'Avocats — Administration"
admin.site.site_title = "Administration — Cabinet d'Avocats"
admin.site.index_title = "Tableau de bord (Administration)"


# ---- Mixins utiles ----
class ArabicListDisplayMixin:
    """Mixin pour fournir des short_description en AR sur les propriétés list_display."""
    pass


# ---- Inlines ----
class AffairePartieInline(admin.TabularInline):
    model = AffairePartie
    extra = 0

class AffaireAvocatInline(admin.TabularInline):
    model = AffaireAvocat
    extra = 0

class AudienceInline(admin.TabularInline):
    model = Audience
    extra = 0

class DecisionInline(admin.TabularInline):
    model = Decision
    extra = 0

class PieceJointeInline(admin.TabularInline):
    model = PieceJointe
    extra = 0


# ---- ModelAdmins ----
@admin.register(Juridiction)
class JuridictionAdmin(admin.ModelAdmin):
    list_display = ("nomtribunal_ar", "villetribunal_ar", "type")
    search_fields = ("nomtribunal_ar", "villetribunal_ar")
    list_filter = ("type", "villetribunal_ar")


@admin.register(Avocat)
class AvocatAdmin(admin.ModelAdmin):
    list_display = ("nom", "barreau", "telephone", "email")
    search_fields = ("nom", "barreau")


@admin.register(Partie)
class PartieAdmin(admin.ModelAdmin):
    list_display = ("nom_complet", "type_partie", "cin_ou_rc", "telephone", "email")
    list_filter = ("type_partie",)
    search_fields = ("nom_complet", "cin_ou_rc")


@admin.register(Affaire)
class AffaireAdmin(admin.ModelAdmin):
    inlines = [AffairePartieInline, AffaireAvocatInline, AudienceInline, DecisionInline, PieceJointeInline]
    list_display = (
        "reference_interne",
        "type_affaire",
        "statut_affaire",
        "juridiction",
        "date_ouverture",
        "_client_principal",
        "_resume_objet",
    )
    list_filter = ("type_affaire", "statut_affaire", "juridiction__villetribunal_ar")
    search_fields = ("reference_interne", "reference_tribunal", "objet")
    date_hierarchy = "date_ouverture"

    @admin.display(description="العميل/المدعي")
    def _client_principal(self, obj: Affaire):
        ap = AffairePartie.objects.filter(affaire=obj, role_dans_affaire__libelle__in=["Demandeur", "Plagnant", "Appelant"]).select_related("partie").first()
        return ap.partie.nom_complet if ap else "—"

    @admin.display(description="موضوع مختصر")
    def _resume_objet(self, obj: Affaire):
        if not obj.objet:
            return "—"
        return (obj.objet[:40] + "…") if len(obj.objet) > 40 else obj.objet


@admin.register(Audience)
class AudienceAdmin(admin.ModelAdmin):
    list_display = ("affaire", "type_audience", "date_audience", "_resultat_ar")
    list_filter = ("type_audience",)
    search_fields = ("affaire__reference_interne",)
    date_hierarchy = "date_audience"

    @admin.display(description="النتيجة")
    def _resultat_ar(self, obj: Audience):
        return obj.resultat or "—"


@admin.register(Mesure)
class MesureAdmin(admin.ModelAdmin):
    list_display = ("audience", "type_mesure", "statut", "_notes")
    list_filter = ("type_mesure", "statut")

    @admin.display(description="ملاحظات")
    def _notes(self, obj: Mesure):
        return (obj.notes[:30] + "…") if obj.notes and len(obj.notes) > 30 else (obj.notes or "—")


@admin.register(Expertise)
class ExpertiseAdmin(admin.ModelAdmin):
    list_display = ("affaire", "expert_nom", "date_ordonnee", "date_depot", "contre_expertise")
    list_filter = ("contre_expertise",)


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("affaire", "numero_decision", "date_prononce", "susceptible_recours", "_resume")
    search_fields = ("numero_decision", "affaire__reference_interne")

    @admin.display(description="ملخص الحكم")
    def _resume(self, obj: Decision):
        return (obj.resumé[:42] + "…") if obj.resumé and len(obj.resumé) > 42 else (obj.resumé or "—")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "decision", "demande_numero", "date_depot_demande",
        "huissier_nom", "date_remise_huissier", "date_signification", "_echeance_appel"
    )
    date_hierarchy = "date_signification"
    search_fields = ("demande_numero", "decision__numero_decision")

    @admin.display(description="أجل الاستئناف")
    def _echeance_appel(self, obj: Notification):
        from services.alerts import compute_appeal_deadline
        if not obj.date_signification:
            return "—"
        return compute_appeal_deadline(obj.date_signification)


@admin.register(VoieDeRecours)
class VoieDeRecoursAdmin(admin.ModelAdmin):
    list_display = ("decision", "type_recours", "date_depot", "juridiction", "statut")
    list_filter = ("type_recours", "statut")


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ("decision", "type_execution", "date_demande", "statut", "depot_caisse_barreau")
    list_filter = ("type_execution", "statut")


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ("affaire", "type_depense", "montant", "date_depense", "beneficiaire")
    list_filter = ("type_depense",)
    date_hierarchy = "date_depense"
    search_fields = ("affaire__reference_interne", "beneficiaire")


@admin.register(Recette)
class RecetteAdmin(admin.ModelAdmin):
    list_display = ("affaire", "type_recette", "montant", "date_recette", "source")
    list_filter = ("type_recette",)
    date_hierarchy = "date_recette"


@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ("affaire", "titre", "type_piece", "date_ajout")
    list_filter = ("type_piece",)
    date_hierarchy = "date_ajout"


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("nom_complet", "role", "email", "actif")
    list_filter = ("role", "actif")
    search_fields = ("nom_complet", "email")


@admin.register(Tache)
class TacheAdmin(admin.ModelAdmin):
    list_display = ("titre", "affaire", "echeance", "assigne_a", "statut")
    list_filter = ("statut",)
    date_hierarchy = "echeance"


@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ("type_alerte", "reference_id", "date_alerte", "moyen", "destinataire", "_message")
    list_filter = ("type_alerte", "moyen")
    date_hierarchy = "date_alerte"

    @admin.display(description="نص التنبيه")
    def _message(self, obj: Alerte):
        return (obj.message[:40] + "…") if len(obj.message) > 40 else obj.message



# =============================================
# FILE: settings.py (مقاطع لإضافتها)
# =============================================

# --- اللغة و الـRTL ---
LANGUAGE_CODE = 'ar'
USE_I18N = True

LOCALE_PATHS = [BASE_DIR / 'locale']

# --- ملفات ثابتة ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # ضع admin_rtl.css داخل static/


# --- البريد الإلكتروني (مثال SMTP بسيط) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yourprovider.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'no-reply@yourdomain.tld'
EMAIL_HOST_PASSWORD = '***'
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'no-reply@yourdomain.tld'

# --- Twilio SMS ---
TWILIO_ACCOUNT_SID = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_AUTH_TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_FROM = '+1234567890'

# --- قنوات التنبيه ---
ALERTE_CHANNELS = ['InApp', 'Email', 'SMS']

# --- قواعد أجل الاستئناف حسب نوع القضية ---
APPEAL_RULES = {
    'Civil': 30,
    'Famille': 15,
    'Social': 30,
    'Commercial': 30,
    'Location': 30,
    'Pénal': 10,
    'Pénal-Routier': 10,
    'Pénal-Contravention': 10,
    'Pénal-Flagrant': 10,
}
# =============================
# FILE: management/commands/generate_appeal_alerts.py
# أمر دوري اختياري لإنشاء التنبيهات (مثلاً عبر cron) في حال تعطّل الإشارات
# =============================

# admin.py
from .admin_mixins import SoftDeleteAdminMixin

@admin.register(RoleUtilisateur)
class RoleUtilisateurAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(StatutTache)
class StatutTacheAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(StatutAffaire)
class StatutAffaireAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeAffaire)
class TypeAffaireAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeMesure)
class TypeMesureAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeRecours)
class TypeRecoursAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeExecution)
class TypeExecutionAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeRecette)
class TypeRecetteAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeAlerte)
class TypeAlerteAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(StatutRecours)
class StatutRecoursAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(StatutExecution)
class StatutExecutionAdmin(SoftDeleteAdminMixin):
    pass

@admin.register(TypeDepense)
class TypeDepenseAdmin(SoftDeleteAdminMixin):
    pass


""""Commande Django pour générer les alertes d'échéance 
d'appel pour toutes les notifications signifiées."""

"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from models import Notification
from services.alerts import create_appeal_alerts_for_notification

class Command(BaseCommand):
    help = "Génère les alertes d'échéance d'appel pour toutes les notifications signifiées."

    def handle(self, *args, **options):
        today = date.today()
        count_total = 0
        qs = Notification.objects.exclude(date_signification__isnull=True)
        for notif in qs.iterator():
            count_total += create_appeal_alerts_for_notification(notif)
        self.stdout.write(self.style.SUCCESS(f"Alertes créées/mises à jour: {count_total}"))     
"""

