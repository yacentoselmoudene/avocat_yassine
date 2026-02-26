# -*- coding: utf-8 -*-
from __future__ import annotations

import django_filters
from django import forms

from .models import (
    Affaire, Audience, Depense, Recette, PieceJointe,
    TypeAffaire, StatutAffaire, Juridiction, Avocat,
    TypeDepense, TypeRecette, PhaseAffaire,
)


# ── Mixin: appliquer les classes Bootstrap RTL sur les widgets ──

class ArabicFilterMixin:
    """Applique automatiquement les classes Bootstrap RTL sur chaque widget du filtre."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.form.fields.items():
            widget = f.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = (css + " form-select form-select-sm js-select2").strip()
            else:
                widget.attrs["class"] = (css + " form-control form-control-sm").strip()
            widget.attrs.setdefault("dir", "rtl")


# ── Affaire ──

class AffaireFilter(ArabicFilterMixin, django_filters.FilterSet):
    phase = django_filters.ChoiceFilter(
        choices=PhaseAffaire.choices, label="المرحلة", empty_label="الكل",
    )
    type_affaire = django_filters.ModelChoiceFilter(
        queryset=TypeAffaire.objects.all(), label="نوع القضية", empty_label="الكل",
    )
    statut_affaire = django_filters.ModelChoiceFilter(
        queryset=StatutAffaire.objects.all(), label="الحالة", empty_label="الكل",
    )
    juridiction = django_filters.ModelChoiceFilter(
        queryset=Juridiction.objects.all(), label="المحكمة", empty_label="الكل",
    )
    avocat_responsable = django_filters.ModelChoiceFilter(
        queryset=Avocat.objects.all(), label="المحامي", empty_label="الكل",
    )
    priorite = django_filters.ChoiceFilter(
        choices=[('Haute', 'مرتفعة'), ('Normale', 'عادية'), ('Basse', 'منخفضة')],
        label="الأولوية", empty_label="الكل",
    )
    date_ouverture_min = django_filters.DateFilter(
        field_name="date_ouverture", lookup_expr="gte", label="من تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_ouverture_max = django_filters.DateFilter(
        field_name="date_ouverture", lookup_expr="lte", label="إلى تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Affaire
        fields = []


# ── Dépense ──

def _depense_year_choices():
    """Generate year choices from existing depense dates."""
    from django.utils import timezone
    current_year = timezone.localdate().year
    return [(str(y), str(y)) for y in range(current_year, current_year - 10, -1)]


class DepenseFilter(ArabicFilterMixin, django_filters.FilterSet):
    type_depense = django_filters.ModelChoiceFilter(
        queryset=TypeDepense.objects.all(), label="نوع المصروف", empty_label="الكل",
    )
    affaire = django_filters.ModelChoiceFilter(
        queryset=Affaire.objects.all(), label="القضية", empty_label="الكل",
    )
    annee = django_filters.ChoiceFilter(
        choices=_depense_year_choices, label="السنة", empty_label="الكل",
        method="filter_annee",
    )
    beneficiaire = django_filters.CharFilter(
        field_name="beneficiaire", lookup_expr="icontains", label="المستفيد",
    )
    date_depense_min = django_filters.DateFilter(
        field_name="date_depense", lookup_expr="gte", label="من تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_depense_max = django_filters.DateFilter(
        field_name="date_depense", lookup_expr="lte", label="إلى تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    montant_min = django_filters.NumberFilter(
        field_name="montant", lookup_expr="gte", label="المبلغ من",
    )
    montant_max = django_filters.NumberFilter(
        field_name="montant", lookup_expr="lte", label="المبلغ إلى",
    )

    def filter_annee(self, queryset, name, value):
        if value:
            return queryset.filter(date_depense__year=int(value))
        return queryset

    class Meta:
        model = Depense
        fields = []


# ── Recette ──

class RecetteFilter(ArabicFilterMixin, django_filters.FilterSet):
    type_recette = django_filters.ModelChoiceFilter(
        queryset=TypeRecette.objects.all(), label="نوع الإيراد", empty_label="الكل",
    )
    affaire = django_filters.ModelChoiceFilter(
        queryset=Affaire.objects.all(), label="القضية", empty_label="الكل",
    )
    date_recette_min = django_filters.DateFilter(
        field_name="date_recette", lookup_expr="gte", label="من تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_recette_max = django_filters.DateFilter(
        field_name="date_recette", lookup_expr="lte", label="إلى تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    montant_min = django_filters.NumberFilter(
        field_name="montant", lookup_expr="gte", label="المبلغ من",
    )
    montant_max = django_filters.NumberFilter(
        field_name="montant", lookup_expr="lte", label="المبلغ إلى",
    )

    class Meta:
        model = Recette
        fields = []


# ── PièceJointe ──

class PieceJointeFilter(ArabicFilterMixin, django_filters.FilterSet):
    type_piece = django_filters.ChoiceFilter(
        choices=[('PDF', 'PDF'), ('Image', 'صورة'), ('Doc', 'مستند'), ('Audio', 'صوت'), ('Autre', 'أخرى')],
        label="نوع الملف", empty_label="الكل",
    )
    affaire = django_filters.ModelChoiceFilter(
        queryset=Affaire.objects.all(), label="القضية", empty_label="الكل",
    )

    class Meta:
        model = PieceJointe
        fields = []


# ── Audience ──

class AudienceFilter(ArabicFilterMixin, django_filters.FilterSet):
    affaire = django_filters.ModelChoiceFilter(
        queryset=Affaire.objects.all(), label="القضية", empty_label="الكل",
    )
    date_audience_min = django_filters.DateFilter(
        field_name="date_audience", lookup_expr="gte", label="من تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_audience_max = django_filters.DateFilter(
        field_name="date_audience", lookup_expr="lte", label="إلى تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = Audience
        fields = []
