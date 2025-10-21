# avocat_app/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte
)

# ---------- Base mixin: RTL + Bootstrap + تنظيف مدخلات ----------
class ArabicBootstrapFormMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
            field.widget.attrs.setdefault("dir", "rtl")
            # عناصر Boolean/Checkbox
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = (css + " form-check-input").strip()
            # تواريخ
            if isinstance(field.widget, (forms.DateInput, forms.DateTimeInput)):
                field.widget.attrs.setdefault("type", "date")

    def clean(self):
        cleaned = super().clean()
        # تنميط نصوص: إزالة مسافات زائدة
        for k, v in cleaned.items():
            if isinstance(v, str):
                cleaned[k] = v.strip()
        return cleaned

# داخل avocat_app/forms.py


# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import AffairePartie, AffaireAvocat, Partie, Avocat

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
        fields = "__all__"
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
        fields = "__all__"
        labels = {
            "reference_interne": "المرجع الداخلي",
            "reference_tribunal": "مرجع المحكمة",
            "type_affaire": "نوع القضية",
            "statut_affaire": "الحالة",
            "juridiction": "المحكمة",
            "date_ouverture": "تاريخ الفتح",
            "objet": "موضوع موجز",
            "avocat_responsable": "المحامي المسؤول",
        }
        widgets = {
            "date_ouverture": forms.DateInput(attrs={"type": "date"}),
            "objet": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        # مثال تحقق بسيط: مرجع داخلي مطلوب ومميز (اعتمد القيد unique بالموديل أيضًا)
        if not cleaned.get("reference_interne"):
            raise ValidationError("المرجع الداخلي مطلوب.")
        return cleaned


# ---------- أمثلة مختصرة لنماذج أخرى بنفس النمط ----------
class JuridictionForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Juridiction
        fields = "__all__"
        labels = {"nom": "الاسم", "ville": "المدينة", "type": "النوع"}

class PartieForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Partie
        fields = "__all__"
        labels = {
            "nom_complet": "الاسم الكامل",
            "type_partie": "الصفة",
            "cin_ou_rc": "البطاقة/السجل",
            "adresse": "العنوان",
            "telephone": "الهاتف",
            "email": "البريد",
        }

class AudienceForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Audience
        fields = "__all__"
        labels = {
            "affaire": "القضية",
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
        labels = {"audience": "الجلسة", "type_mesure": "نوع الإجراء", "statut": "الحالة", "notes": "ملاحظات"}

class ExpertiseForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Expertise
        fields = "__all__"
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
        fields = "__all__"
        labels = {
            "affaire": "القضية", "numero_decision": "رقم الحكم",
            "date_prononce": "تاريخ النطق", "resumé": "ملخص", "susceptible_recours": "قابل للطعن",
        }
        widgets = {"date_prononce": forms.DateInput(attrs={"type": "date"})}

class NotificationForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Notification
        fields = "__all__"
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
        labels = {"decision": "الحكم", "type_recours": "نوع الطعن", "date_depot": "تاريخ الإيداع", "juridiction": "المحكمة", "statut": "الحالة"}
        widgets = {"date_depot": forms.DateInput(attrs={"type": "date"})}

class ExecutionForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Execution
        fields = "__all__"
        labels = {"decision": "الحكم", "type_execution": "نوع التنفيذ", "date_demande": "تاريخ الطلب", "statut": "الحالة", "depot_caisse_barreau": "إحالة للهيئة"}
        widgets = {"date_demande": forms.DateInput(attrs={"type": "date"})}

class DepenseForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Depense
        fields = "__all__"
        labels = {"affaire": "القضية", "type_depense": "النوع", "montant": "المبلغ", "date_depense": "التاريخ", "beneficiaire": "المستفيد"}
        widgets = {"date_depense": forms.DateInput(attrs={"type": "date"})}

class RecetteForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Recette
        fields = "__all__"
        labels = {"affaire": "القضية", "type_recette": "النوع", "montant": "المبلغ", "date_recette": "التاريخ", "source": "المصدر"}
        widgets = {"date_recette": forms.DateInput(attrs={"type": "date"})}

class PieceJointeForm(ArabicBootstrapFormMixin):
    class Meta:
        model = PieceJointe
        fields = "__all__"
        labels = {"affaire": "القضية", "titre": "العنوان", "type_piece": "النوع", "fichier": "الملف", "date_ajout": "تاريخ الإضافة"}
        widgets = {"date_ajout": forms.DateInput(attrs={"type": "date"})}

class UtilisateurForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Utilisateur
        fields = "__all__"
        labels = {"nom_complet": "الاسم", "role": "الدور", "email": "البريد", "actif": "نشط"}

class TacheForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Tache
        fields = "__all__"
        labels = {"titre": "العنوان", "description": "الوصف", "affaire": "القضية", "assigne_a": "المكلّف", "echeance": "الأجل", "statut": "الحالة"}
        widgets = {"echeance": forms.DateInput(attrs={"type": "date"})}

class AlerteForm(ArabicBootstrapFormMixin):
    class Meta:
        model = Alerte
        fields = "__all__"
        labels = {"type_alerte": "النوع", "reference_id": "المعرّف", "date_alerte": "التاريخ", "moyen": "القناة", "destinataire": "المرسل إليه", "message": "النص"}
        widgets = {"date_alerte": forms.DateInput(attrs={"type": "date"})}
