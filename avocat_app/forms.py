# =============================================================
# FILE: forms.py  (نماذج عربية لكل النماذج — RTL + رسائل عربية)
# =============================================================
from django import forms
from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte
)

ARABIC_INPUT_CSS_CLASS = 'arabic-input'

class BaseArabicForm(forms.ModelForm):
    """تهيئة عامة للـwidgets والرسائل بالعربية + اتجاه RTL."""
    default_error_messages = {
        'required': 'هذا الحقل إجباري.',
        'invalid': 'القيمة غير صالحة.',
        'max_length': 'النص أطول من المسموح.',
        'min_length': 'النص أقصر من المسموح.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.error_messages = {**self.default_error_messages, **field.error_messages}
            css = field.widget.attrs.get('class', '')
            attrs = {'dir': 'rtl', 'class': f"{css} {ARABIC_INPUT_CSS_CLASS}".strip()}
            # عناصر التاريخ والوقت بنمط HTML5
            if isinstance(field.widget, (forms.DateInput, forms.DateTimeInput)):
                attrs['type'] = 'date' if isinstance(field.widget, forms.DateInput) else 'datetime-local'
            field.widget.attrs.update(attrs)


# --- نماذج أساسية لكل Model ---
class JuridictionForm(BaseArabicForm):
    class Meta:
        model = Juridiction
        fields = '__all__'

class AvocatForm(BaseArabicForm):
    class Meta:
        model = Avocat
        fields = '__all__'

class AffaireForm(BaseArabicForm):
    class Meta:
        model = Affaire
        fields = '__all__'
        widgets = {
            'objet': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'date_ouverture': forms.DateInput(attrs={'type': 'date'}),
        }

class PartieForm(BaseArabicForm):
    class Meta:
        model = Partie
        fields = '__all__'
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 2}),
        }

class AffairePartieForm(BaseArabicForm):
    class Meta:
        model = AffairePartie
        fields = '__all__'

class AffaireAvocatForm(BaseArabicForm):
    class Meta:
        model = AffaireAvocat
        fields = '__all__'

class AudienceForm(BaseArabicForm):
    class Meta:
        model = Audience
        fields = '__all__'
        widgets = {
            'date_audience': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'proces_verbal': forms.Textarea(attrs={'rows': 3}),
        }

class MesureForm(BaseArabicForm):
    class Meta:
        model = Mesure
        fields = '__all__'
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class ExpertiseForm(BaseArabicForm):
    class Meta:
        model = Expertise
        fields = '__all__'
        widgets = {
            'date_ordonnee': forms.DateInput(attrs={'type': 'date'}),
            'date_depot': forms.DateInput(attrs={'type': 'date'}),
        }

class DecisionForm(BaseArabicForm):
    class Meta:
        model = Decision
        fields = '__all__'
        widgets = {
            'date_prononce': forms.DateInput(attrs={'type': 'date'}),
            'resumé': forms.Textarea(attrs={'rows': 3}),
        }

class NotificationForm(BaseArabicForm):
    class Meta:
        model = Notification
        fields = '__all__'
        widgets = {
            'date_depot_demande': forms.DateInput(attrs={'type': 'date'}),
            'date_remise_huissier': forms.DateInput(attrs={'type': 'date'}),
            'date_signification': forms.DateInput(attrs={'type': 'date'}),
        }

class VoieDeRecoursForm(BaseArabicForm):
    class Meta:
        model = VoieDeRecours
        fields = '__all__'
        widgets = {
            'date_depot': forms.DateInput(attrs={'type': 'date'}),
        }

class ExecutionForm(BaseArabicForm):
    class Meta:
        model = Execution
        fields = '__all__'
        widgets = {
            'date_demande': forms.DateInput(attrs={'type': 'date'}),
            'date_demande_liquidation': forms.DateInput(attrs={'type': 'date'}),
            'date_pv_refus': forms.DateInput(attrs={'type': 'date'}),
            'date_contrainte': forms.DateInput(attrs={'type': 'date'}),
        }

class DepenseForm(BaseArabicForm):
    class Meta:
        model = Depense
        fields = '__all__'
        widgets = {
            'date_depense': forms.DateInput(attrs={'type': 'date'}),
        }

class RecetteForm(BaseArabicForm):
    class Meta:
        model = Recette
        fields = '__all__'
        widgets = {
            'date_recette': forms.DateInput(attrs={'type': 'date'}),
        }

class PieceJointeForm(BaseArabicForm):
    class Meta:
        model = PieceJointe
        fields = '__all__'

class UtilisateurForm(BaseArabicForm):
    class Meta:
        model = Utilisateur
        fields = '__all__'

class TacheForm(BaseArabicForm):
    class Meta:
        model = Tache
        fields = '__all__'
        widgets = {
            'echeance': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

class AlerteForm(BaseArabicForm):
    class Meta:
        model = Alerte
        fields = '__all__'
        widgets = {
            'date_alerte': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'message': forms.Textarea(attrs={'rows': 2}),
        }
