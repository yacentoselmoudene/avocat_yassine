# avocat_app/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte, Expert,
    Avertissement, TypeAvertissement, CodeCategorieAffaire,
    TypeDepense, TypeRecette, RoleUtilisateur, StatutTache, TypeAlerte,
    TypeAffaire, StatutAffaire, TypeMesure, TypeAudience,
    TypeExecution, StatutExecution,
    StatutMesure, StatutRecours, ResultatAudience, TypeRecours, Barreau, TypeJuridiction, DegreJuridiction
)

# ---------- Base mixin: RTL + Bootstrap + تنظيف مدخلات ----------
class ArabicBootstrapFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                if 'js-select2' not in css:
                    field.widget.attrs["class"] = (css + " form-select js-select2").strip()
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = (css + " form-check-input").strip()
            else:
                field.widget.attrs["class"] = (css + " form-control").strip()
            field.widget.attrs.setdefault("dir", "rtl")
            if isinstance(field.widget, (forms.DateInput, forms.DateTimeInput)):
                field.widget.attrs.setdefault("type", "date")

    def clean(self):
        cleaned = super().clean()
        # تنميط نصوص: إزالة مسافات زائدة
        for k, v in cleaned.items():
            if isinstance(v, str):
                cleaned[k] = v.strip()
        return cleaned

from django.utils.translation import gettext_lazy as _

# ========= تنسيق عربي عام للنماذج =========
class ArabicModelForm(forms.ModelForm):
    """أساس لكل النماذج لتطبيق تنسيق عربي وحقول RTL"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
            field.widget.attrs.setdefault("dir", "rtl")
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 3)

# ========= 1) نموذج ربط القضية بالأطراف =========
class AffairePartieForm(ArabicModelForm):
    class Meta:
        model = AffairePartie
        fields = ["affaire", "partie", "role_dans_affaire"]
        labels = {
            "affaire": "القضية",
            "partie": "الطرف",
            "role_dans_affaire": "الدور في القضية",

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ترتيب الحقول حسب الحاجة
        self.fields["affaire"].widget = forms.HiddenInput()  # غالبًا نمررها من الـview
        self.fields["partie"].queryset = Partie.objects.all().order_by("nom_complet")
        self.fields["role_dans_affaire"].widget.attrs.update({
            "class": "form-select",
        })

    def clean(self):
        cleaned = super().clean()
        partie = cleaned.get("partie")
        affaire = cleaned.get("affaire")
        if partie and affaire:
            exists = AffairePartie.objects.filter(affaire=affaire, partie=partie).exists()
            if exists and not self.instance.pk:
                raise forms.ValidationError("هذا الطرف مسجّل بالفعل في نفس القضية.")
        return cleaned

# ========= 2) نموذج ربط القضية بالمحامين =========
class AffaireAvocatForm(ArabicModelForm):
    class Meta:
        model = AffaireAvocat
        fields = ["affaire", "avocat", "role"]
        labels = {
            "affaire": "القضية",
            "avocat": "المحامي",
            "role": "دور المحامي في القضية",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["affaire"].widget = forms.HiddenInput()
        self.fields["avocat"].queryset = Avocat.objects.all().order_by("nom")
        self.fields["role"].widget.attrs.update({"class": "form-select"})

    def clean(self):
        cleaned = super().clean()
        avocat = cleaned.get("avocat")
        affaire = cleaned.get("affaire")
        if avocat and affaire:
            exists = AffaireAvocat.objects.filter(affaire=affaire, avocat=avocat).exists()
            if exists and not self.instance.pk:
                raise forms.ValidationError("هذا المحامي مسجّل بالفعل في نفس القضية.")
        return cleaned


class ArabicLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "اسم المستخدم أو البريد الإلكتروني"
        self.fields["password"].label = "كلمة المرور"
        for f in self.fields.values():
            classes = f.widget.attrs.get("class", "")
            f.widget.attrs["class"] = (classes + " form-control").strip()
            f.widget.attrs.setdefault("dir", "rtl")


# ---------- Avocat ----------
class AvocatForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Avocat
        # fileds "__all__" without created_at, updated_at et is_deleted
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {
            "nom": "الاسم الكامل",
            "barreau": "هيئة الانتماء",
            "telephone": "الهاتف",
            "email": "البريد الإلكتروني",
        }
        help_texts = {
            "email": "اكتب بريدًا صحيحًا لتلقي الإشعارات.",
        }


# ---------- Affaire ----------
class AffaireForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Affaire
        fields = [
            "reference_interne",
            "numero_dossier", "code_categorie", "annee_dossier",
            "type_affaire", "statut_affaire", "phase",
            "juridiction", "avocat_responsable",
            "date_ouverture", "priorite",
            "valeur_litige", "objet", "notes",
        ]
        labels = {
            "reference_interne": "المرجع الداخلي",
            "numero_dossier": "رقم الملف",
            "code_categorie": "صنف القضية",
            "annee_dossier": "السنة",
            "type_affaire": "نوع القضية",
            "statut_affaire": "حالة القضية",
            "phase": "المرحلة",
            "juridiction": "المحكمة",
            "date_ouverture": "تاريخ الفتح",
            "objet": "موضوع الدعوى",
            "avocat_responsable": "المحامي المسؤول",
            "valeur_litige": "قيمة النزاع (د.م.)",
            "priorite": "الأولوية",
            "notes": "ملاحظات",
        }
        widgets = {
            "date_ouverture": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "objet": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "priorite": forms.Select(attrs={"class": "form-select"}),
            "phase": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholders
        self.fields["reference_interne"].widget.attrs["placeholder"] = "مثال: AFF-2026-001"
        self.fields["numero_dossier"].widget.attrs["placeholder"] = "مثال: 1234"
        self.fields["annee_dossier"].widget.attrs["placeholder"] = "مثال: 2026"
        self.fields["valeur_litige"].widget.attrs["placeholder"] = "0.00"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("reference_interne"):
            raise ValidationError("المرجع الداخلي مطلوب.")
        return cleaned


# ---------- أمثلة مختصرة لنماذج أخرى بنفس النمط ----------
class JuridictionForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Juridiction
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"nomtribunal_ar": "الاسم", "villetribunal_ar": "المدينة", "type": "النوع"}

class PartieForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Partie
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {
            "nom_complet": "الاسم الكامل",
            "type_partie": "الصفة",
            "cin_ou_rc": "البطاقة/السجل",
            "adresse": "العنوان",
            "telephone": "الهاتف",
            "email": "البريد",
        }

class BarreauForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Barreau
        fields = ["nom", "juridiction_appel"]
        labels = {
            "nom": "الاسم الكامل",
            "juridiction_appel": "محكمة الاستئناف",
        }

class AudienceForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Audience
        fields = ["type_audience", "date_audience", "resultat"]  # pas "affaire" ici
        labels = {
            "type_audience": "نوع الجلسة",
            "date_audience": "تاريخ الجلسة",
            "resultat": "النتيجة",
            "proces_verbal": "محضر",
        }
        widgets = {"date_audience": forms.DateInput(attrs={"type": "date"})}

class MesureForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Mesure
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"audience": "الجلسة", "type_mesure": "نوع الإجراء", "statut": "الحالة", "notes": "ملاحظات", "date_ordonnee": "تاريخ الأمر"}
        widgets = {"date_ordonnee": forms.DateInput(attrs={"type": "date"})}

class ExpertiseForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Expertise
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {
            "affaire": "القضية", "expert_nom": "اسم الخبير",
            "date_ordonnee": "تاريخ الأمر", "date_depot": "تاريخ الإيداع",
            "contre_expertise": "خبرة مضادة",
        }
        widgets = {
            "date_ordonnee": forms.DateInput(attrs={"type": "date"}),
            "date_depot": forms.DateInput(attrs={"type": "date"}),
        }

class DecisionForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Decision
        fields = ["numero_decision", "date_prononce", "resumé", "susceptible_recours"]
        labels = {
            "numero_decision": "رقم الحكم",
            "date_prononce": "تاريخ النطق", "resumé": "ملخص", "susceptible_recours": "قابل للطعن",
        }
        widgets = {"date_prononce": forms.DateInput(attrs={"type": "date"})}

class NotificationForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Notification
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {
            "decision": "الحكم", "demande_numero": "رقم طلب التبليغ",
            "date_depot_demande": "تاريخ إيداع الطلب", "huissier_nom": "اسم المفوض",
            "date_remise_huissier": "تاريخ التسليم للمفوض", "date_signification": "تاريخ التبليغ",
        }
        widgets = {
            "date_depot_demande": forms.DateInput(attrs={"type": "date"}),
            "date_remise_huissier": forms.DateInput(attrs={"type": "date"}),
            "date_signification": forms.DateInput(attrs={"type": "date"}),
        }

class VoieDeRecoursForm(ArabicBootstrapFormMixin):
    class Meta:
        model = VoieDeRecours
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"decision": "الحكم", "type_recours": "نوع الطعن", "date_depot": "تاريخ الإيداع", "juridiction": "المحكمة", "statut": "الحالة"}
        widgets = {"date_depot": forms.DateInput(attrs={"type": "date"})}

class ExecutionForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Execution
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"decision": "الحكم", "type_execution": "نوع التنفيذ", "date_demande": "تاريخ الطلب", "statut": "الحالة", "depot_caisse_barreau": "إحالة للهيئة"}
        widgets = {
            "date_demande": forms.DateInput(attrs={"type": "date"}),
            "date_demande_liquidation": forms.DateInput(attrs={"type": "date"}),
            "date_pv_refus": forms.DateInput(attrs={"type": "date"}),
            "date_contrainte": forms.DateInput(attrs={"type": "date"}),
        }

class DepenseForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Depense
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"affaire": "القضية", "type_depense": "النوع", "montant": "المبلغ", "date_depense": "التاريخ", "beneficiaire": "المستفيد"}
        widgets = {"date_depense": forms.DateInput(attrs={"type": "date"})}

class RecetteForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Recette
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"affaire": "القضية", "type_recette": "النوع", "montant": "المبلغ", "date_recette": "التاريخ", "source": "المصدر"}
        widgets = {"date_recette": forms.DateInput(attrs={"type": "date"})}

class PieceJointeForm(ArabicBootstrapFormMixin):
    class Meta:
        model = PieceJointe
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"affaire": "القضية", "titre": "العنوان", "type_piece": "النوع", "fichier": "الملف", "date_ajout": "تاريخ الإضافة"}
        widgets = {"date_ajout": forms.DateInput(attrs={"type": "date"})}

class UtilisateurForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Utilisateur
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"nom_complet": "الاسم", "role": "الدور", "email": "البريد", "actif": "نشط"}

class TacheForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Tache
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"titre": "العنوان", "description": "الوصف", "affaire": "القضية", "assigne_a": "المكلّف", "echeance": "الأجل", "statut": "الحالة"}
        widgets = {"echeance": forms.DateInput(attrs={"type": "date"})}

class ExpertForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Expert
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"nom_complet": "الاسم", "email": "البريد", "telephone": "الهاتف", "specialite": "التخصص", "adresse": "العنوان"}

class AlerteForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Alerte
        fields = "__all__"
        exclude = ["created_at", "updated_at", "is_deleted"]
        labels = {"type_alerte": "النوع", "reference_id": "المعرّف", "date_alerte": "التاريخ", "moyen": "القناة", "destinataire": "المرسل إليه", "message": "النص"}
        widgets = {"date_alerte": forms.DateInput(attrs={"type": "date"})}

class LibelleForm(ArabicModelForm):
    class Meta:
        fields = ["libelle"]
        labels = {"libelle": "الاسم"}

# Spécifiques (tous identiques mais explicitement typés si besoin d’extensions futures)
class TypeDepenseForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeDepense

class TypeRecetteForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeRecette

class RoleUtilisateurForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = RoleUtilisateur

class StatutTacheForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = StatutTache

class TypeAlerteForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeAlerte
class TypeAffaireForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeAffaire
class StatutAffaireForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = StatutAffaire

class TypeMesureForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeMesure
class TypeAudienceForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeAudience

class TypeExecutionForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeExecution
class StatutExecutionForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = StatutExecution
class StatutMesureForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = StatutMesure


class StatutRecoursForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = StatutRecours

class ResultatAudienceForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = ResultatAudience

class TypeRecoursForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeRecours

class TypeJuridictionForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeJuridiction

class DegreJuridictionForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = DegreJuridiction


class AvertissementForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Avertissement
        fields = [
            "type_avertissement", "date_envoi", "destinataire_nom",
            "destinataire_adresse", "moyen_envoi", "numero_suivi",
            "resultat", "date_reponse", "objet_avertissement",
            "document", "preuve_envoi", "notes_reponse",
        ]
        labels = {
            "type_avertissement": "نوع الإنذار",
            "date_envoi": "تاريخ الإرسال",
            "destinataire_nom": "اسم المرسل إليه",
            "destinataire_adresse": "العنوان",
            "moyen_envoi": "وسيلة الإرسال",
            "numero_suivi": "رقم التتبع",
            "resultat": "النتيجة",
            "date_reponse": "تاريخ الرد",
            "objet_avertissement": "موضوع الإنذار",
            "document": "نسخة الإنذار",
            "preuve_envoi": "إثبات الإرسال",
            "notes_reponse": "ملاحظات على الرد",
        }
        widgets = {
            "date_envoi": forms.DateInput(attrs={"type": "date"}),
            "date_reponse": forms.DateInput(attrs={"type": "date"}),
            "moyen_envoi": forms.Select(attrs={"class": "form-select"}),
            "resultat": forms.Select(attrs={"class": "form-select"}),
            "objet_avertissement": forms.Textarea(attrs={"rows": 3}),
            "destinataire_adresse": forms.Textarea(attrs={"rows": 2}),
            "notes_reponse": forms.Textarea(attrs={"rows": 2}),
        }


class TypeAvertissementForm(LibelleForm):
    class Meta(LibelleForm.Meta):
        model = TypeAvertissement
