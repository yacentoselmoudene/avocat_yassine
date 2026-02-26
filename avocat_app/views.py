from __future__ import annotations

from typing import Any, Dict
from datetime import timedelta
import calendar

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView

from .views_mixins import (
    NoPostOnReadOnlyMixin, HTMXViewMixin, SoftDeleteQuerysetMixin,
    ModalCreateView, ModalUpdateView, ModalDeleteView, HTMXModalFormMixin,
)

from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte, Expert, Barreau,
    Avertissement, PhaseAffaire, DocumentRequirement, MahakimSyncResult,
)

from .filters import AffaireFilter, DepenseFilter, RecetteFilter, PieceJointeFilter, AudienceFilter

from .forms import (
    JuridictionForm, AvocatForm, AffaireForm, PartieForm, AffairePartieForm, AffaireAvocatForm,
    AudienceForm, MesureForm, ExpertiseForm, DecisionForm, NotificationForm, VoieDeRecoursForm,
    ExecutionForm, DepenseForm, RecetteForm, PieceJointeForm, UtilisateurForm, TacheForm, AlerteForm, ExpertForm,
    BarreauForm, AvertissementForm,
)

# -------------------------------------------------------------
# Utilitaires communs
# -------------------------------------------------------------
class SecureBase(LoginRequiredMixin, PermissionRequiredMixin):
    login_url = reverse_lazy('authui:login')
    raise_exception = False
    permission_required = ''

    def success_json(self, message=None, **payload):
        """
        JSON نجاح مرن يقبل أي مفاتيح إضافية:
        - redirect: URL
        - refreshTarget: CSS selector
        - refreshUrl: URL
        - html: HTML للاستخدام في Toast
        - message: نص مختصر
        """
        data = {"ok": True}
        if message:
            data["message"] = message
        # اندمج أي مفاتيح إضافية (refreshTarget/refreshUrl/redirect/html/...)
        data.update(payload)
        return JsonResponse(data)

# -------------------------------------------------------------
# Aide pour retrouver l'affaire liée à une étape (audience/mesure/…)
# -------------------------------------------------------------
def _affaire_pk_from_step(obj) -> int | None:
    if obj is None:
        return None
    if isinstance(obj, Audience):
        return obj.affaire_id
    if isinstance(obj, Mesure):
        return obj.audience.affaire_id if obj.audience_id else None
    if isinstance(obj, Expertise):
        return obj.affaire_id
    if isinstance(obj, Decision):
        return obj.affaire_id
    if isinstance(obj, Notification):
        return obj.decision.affaire_id if obj.decision_id else None
    if isinstance(obj, VoieDeRecours):
        return obj.decision.affaire_id if obj.decision_id else None
    if isinstance(obj, Execution):
        return obj.decision.affaire_id if obj.decision_id else None
    if isinstance(obj, Avertissement):
        return obj.affaire_id
    return None




class SearchListMixin:
    """Mixin générique pour filtrer via ?q= sur un ListView."""
    search_param = "q"
    search_fields: list[str] = []

    def get_search_query(self) -> str:
        return (self.request.GET.get(self.search_param) or "").strip()

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.get_search_query()
        if q and self.search_fields:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.get_search_query()
        return ctx


class DjangoFilterListMixin:
    """Mixin pour intégrer django-filter dans un ListView."""
    filterset_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if self.filterset_class:
            self.filterset = self.filterset_class(self.request.GET, queryset=qs)
            return self.filterset.qs
        self.filterset = None
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        fs = getattr(self, "filterset", None)
        ctx["filter"] = fs
        count = 0
        if fs and fs.form.is_bound:
            skip = {"q", "page", "view"}
            for name, val in fs.form.cleaned_data.items():
                if name not in skip and val not in (None, "", []):
                    count += 1
        ctx["active_filter_count"] = count
        return ctx


class HTMXPartialListMixin:
    """Si la requête est HTMX, ne renvoie que le partial du tableau."""
    partial_template_name: str = None  # à définir sur la vue

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request") and self.partial_template_name:
            return render(self.request, self.partial_template_name, context)
        return super().render_to_response(context, **response_kwargs)


# =============================================================
# POPUPS PERSONNE (Partie / Expert / Avocat / Utilisateur)
# =============================================================

class _PersonPopupBase(SecureBase, HTMXViewMixin, DetailView):
    """Base pour les popups read-only de personnes."""

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        ctx = self.build_popup_context()
        return self.render_modal("modals/_person_popup.html", ctx)

    def build_popup_context(self):
        raise NotImplementedError


class PartiePopup(_PersonPopupBase):
    model = Partie
    permission_required = "cabinet.view_partie"

    def build_popup_context(self):
        o = self.object
        return {
            "person_name": o.nom_complet,
            "person_badge": o.get_type_partie_display(),
            "icon": "bi-person-fill",
            "detail_url": o.get_absolute_url(),
            "person_fields": [
                {"label": "رقم التعريف", "value": o.cin_ou_rc},
                {"label": "العنوان", "value": o.adresse},
                {"label": "الهاتف", "value": o.telephone},
                {"label": "البريد", "value": o.email},
                {"label": "الممثل القانوني", "value": o.representant_legal},
                {"label": "المحامي", "value": str(o.avocat) if o.avocat else None},
            ],
        }


class ExpertPopup(_PersonPopupBase):
    model = Expert
    permission_required = "cabinet.view_expert"

    def build_popup_context(self):
        o = self.object
        return {
            "person_name": o.nom_complet,
            "person_badge": o.specialite,
            "icon": "bi-mortarboard-fill",
            "detail_url": o.get_absolute_url(),
            "person_fields": [
                {"label": "التخصص", "value": o.specialite},
                {"label": "الهاتف", "value": o.telephone},
                {"label": "البريد", "value": o.email},
                {"label": "العنوان", "value": o.adresse},
            ],
        }


class AvocatPopup(_PersonPopupBase):
    model = Avocat
    permission_required = "cabinet.view_avocat"

    def build_popup_context(self):
        o = self.object
        return {
            "person_name": o.nom,
            "person_badge": str(o.barreau),
            "icon": "bi-briefcase-fill",
            "detail_url": o.get_absolute_url(),
            "person_fields": [
                {"label": "الهيئة", "value": str(o.barreau)},
                {"label": "الهاتف", "value": o.telephone},
                {"label": "البريد", "value": o.email},
                {"label": "التعريفة/ساعة", "value": f"{o.taux_horaire} د.م." if o.taux_horaire else None},
            ],
        }


class UtilisateurPopup(_PersonPopupBase):
    model = Utilisateur
    permission_required = "cabinet.view_utilisateur"

    def build_popup_context(self):
        o = self.object
        return {
            "person_name": o.nom_complet,
            "person_badge": str(o.role),
            "icon": "bi-person-badge-fill",
            "detail_url": o.get_absolute_url(),
            "person_fields": [
                {"label": "الدور", "value": str(o.role)},
                {"label": "البريد", "value": o.email},
                {"label": "الهاتف", "value": o.telephone},
                {"label": "نشط", "value": "نعم" if o.actif else "لا"},
            ],
        }


# =============================================================
# DASHBOARD
# =============================================================

class DashboardView(SecureBase, TemplateView):
    template_name = "dashboard/index.html"
    permission_required = "cabinet.view_affaire"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        upcoming = today + timedelta(days=14)
        deadline_horizon = today + timedelta(days=7)

        ctx["stats"] = {
            "affaires_total": Affaire.objects.count(),
            "audiences_a_venir": Audience.objects.filter(date_audience__range=(today, upcoming)).count(),
        }

        ctx["next_audiences"] = (
            Audience.objects.select_related("affaire")
            .filter(date_audience__gte=today).order_by("date_audience")[:6]
        )
        ctx["recent_affaires"] = (
            Affaire.objects.select_related("juridiction")
            .order_by("-date_ouverture")[:6]
        )
        # Finance navigation: ?fy=year&fm=month
        ARABIC_MONTHS = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
            5: "ماي", 6: "يونيو", 7: "يوليوز", 8: "غشت",
            9: "شتنبر", 10: "أكتوبر", 11: "نونبر", 12: "دجنبر",
        }
        try:
            fin_year = int(self.request.GET.get("fy", today.year))
            fin_month = int(self.request.GET.get("fm", today.month))
            if not (1 <= fin_month <= 12):
                fin_year, fin_month = today.year, today.month
        except (ValueError, TypeError):
            fin_year, fin_month = today.year, today.month

        fin_is_current = (fin_year == today.year and fin_month == today.month)

        # Prev/next month calculation
        if fin_month == 1:
            prev_y, prev_m = fin_year - 1, 12
        else:
            prev_y, prev_m = fin_year, fin_month - 1
        if fin_month == 12:
            next_y, next_m = fin_year + 1, 1
        else:
            next_y, next_m = fin_year, fin_month + 1

        try:
            dep = Depense.objects.filter(
                date_depense__year=fin_year, date_depense__month=fin_month
            ).aggregate(Sum("montant"))["montant__sum"] or 0
            rec = Recette.objects.filter(
                date_recette__year=fin_year, date_recette__month=fin_month
            ).aggregate(Sum("montant"))["montant__sum"] or 0
            ctx["finance"] = {
                "depenses_mois": dep,
                "recettes_mois": rec,
                "net": rec - dep,
            }
        except Exception:
            ctx["finance"] = {"depenses_mois": 0, "recettes_mois": 0, "net": 0}

        ctx["fin_year"] = fin_year
        ctx["fin_month"] = fin_month
        ctx["fin_month_label"] = ARABIC_MONTHS.get(fin_month, "")
        ctx["fin_is_current"] = fin_is_current
        ctx["fin_prev_y"] = prev_y
        ctx["fin_prev_m"] = prev_m
        ctx["fin_next_y"] = next_y
        ctx["fin_next_m"] = next_m

        # Approaching deadlines (avertissements + recours within 7 days)
        approaching_deadlines = []
        for av in Avertissement.objects.filter(
            date_echeance__range=(today, deadline_horizon),
            resultat="en_attente"
        ).select_related("affaire", "type_avertissement")[:10]:
            approaching_deadlines.append({
                "type": "إنذار",
                "title": str(av.type_avertissement),
                "affaire": av.affaire.reference_interne,
                "affaire_pk": av.affaire_id,
                "echeance": av.date_echeance,
                "jours": av.jours_restants,
            })
        for r in VoieDeRecours.objects.filter(
            date_echeance_recours__range=(today, deadline_horizon),
        ).select_related("decision__affaire", "type_recours")[:10]:
            approaching_deadlines.append({
                "type": "طعن",
                "title": str(r.type_recours),
                "affaire": r.decision.affaire.reference_interne,
                "affaire_pk": r.decision.affaire_id,
                "echeance": r.date_echeance_recours,
                "jours": r.jours_restants_recours,
            })
        approaching_deadlines.sort(key=lambda x: x["echeance"])
        ctx["approaching_deadlines"] = approaching_deadlines

        # Phase distribution
        from django.db.models import Count
        phase_dist = (
            Affaire.objects.values("phase")
            .annotate(count=Count("id"))
            .order_by("phase")
        )
        phase_labels = dict(PhaseAffaire.choices)
        ctx["phase_distribution"] = [
            {"phase": phase_labels.get(p["phase"], p["phase"]), "phase_code": p["phase"], "count": p["count"]}
            for p in phase_dist
        ]

        return ctx

# =============================================================
# AFFAIRES
# =============================================================

class AffaireList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, DjangoFilterListMixin, HTMXPartialListMixin, ListView):
    model = Affaire
    template_name = "avocat/affaire_list.html"
    permission_required = "cabinet.view_affaire"
    paginate_by = 20
    filterset_class = AffaireFilter

    search_fields = [
        "reference_interne", "reference_tribunal", "objet",
        "juridiction__nomtribunal_ar", "juridiction__nomtribunal_fr",
        "type_affaire__libelle", "avocat_responsable__nom",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("type_affaire", "statut_affaire", "juridiction", "avocat_responsable").order_by("-date_ouverture")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["view_mode"] = self.request.GET.get("view", "table")
        return ctx


class AffaireDetail(SecureBase, NoPostOnReadOnlyMixin, DetailView):
    model = Affaire
    template_name = "avocat/affaire_detail.html"
    permission_required = "cabinet.view_affaire"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        affaire = self.object
        phase = affaire.phase
        has_decision = Decision.objects.filter(affaire=affaire).exists()

        # Phase-aware workflow locks
        ctx["can_add_avertissement"] = phase in (PhaseAffaire.PRELIMINAIRE,)
        ctx["can_add_audience"] = phase in (PhaseAffaire.PRELIMINAIRE, PhaseAffaire.PREMIERE_INSTANCE, PhaseAffaire.APPEL, PhaseAffaire.CASSATION)
        ctx["can_add_decision"] = phase in (PhaseAffaire.PREMIERE_INSTANCE, PhaseAffaire.APPEL, PhaseAffaire.CASSATION)
        ctx["can_add_recours"] = has_decision and phase in (PhaseAffaire.PREMIERE_INSTANCE, PhaseAffaire.APPEL, PhaseAffaire.CASSATION)
        ctx["can_add_execution"] = has_decision and phase in (PhaseAffaire.PREMIERE_INSTANCE, PhaseAffaire.APPEL, PhaseAffaire.CASSATION, PhaseAffaire.EXECUTION)

        # Legacy locks (keep for backward compat)
        ctx["lock_predecision"] = not has_decision
        ctx["lock_postdecision"] = has_decision

        # Phase indicator data
        phases_ordered = [
            (PhaseAffaire.PRELIMINAIRE, "التمهيدية"),
            (PhaseAffaire.PREMIERE_INSTANCE, "الابتدائية"),
            (PhaseAffaire.APPEL, "الاستئناف"),
            (PhaseAffaire.CASSATION, "النقض"),
            (PhaseAffaire.EXECUTION, "التنفيذ"),
            (PhaseAffaire.CLOTURE, "مقفلة"),
        ]
        current_idx = next((i for i, (val, _) in enumerate(phases_ordered) if val == phase), 0)
        phase_steps = []
        for i, (val, label) in enumerate(phases_ordered):
            if i < current_idx:
                status = "completed"
            elif i == current_idx:
                status = "active"
            else:
                status = "pending"
            phase_steps.append({"value": val, "label": label, "status": status})
        ctx["phase_steps"] = phase_steps
        ctx["current_phase"] = phase

        # Workflow path indicator
        has_avertissement = Avertissement.objects.filter(affaire=affaire).exists()
        if has_avertissement:
            ctx["workflow_path"] = "إنذار → دعوى"
            ctx["workflow_path_code"] = "B"
        elif phase == PhaseAffaire.PRELIMINAIRE:
            ctx["workflow_path"] = "مسار لم يُحدد بعد"
            ctx["workflow_path_code"] = "?"
        else:
            ctx["workflow_path"] = "دعوى مباشرة"
            ctx["workflow_path_code"] = "C"

        # Document checklist
        requirements = DocumentRequirement.objects.filter(phase=phase)
        existing_titles = set(
            PieceJointe.objects.filter(affaire=affaire).values_list("titre", flat=True)
        )
        doc_checklist = []
        for req in requirements:
            doc_checklist.append({
                "nom": req.nom_document,
                "obligatoire": req.obligatoire,
                "present": req.nom_document in existing_titles,
            })
        ctx["doc_checklist"] = doc_checklist

        # Last mahakim sync
        ctx["last_mahakim_sync"] = (
            MahakimSyncResult.objects.filter(affaire=affaire).order_by("-date_sync").first()
        )

        return ctx

class _AffaireFormMixin(HTMXModalFormMixin):
    """Shared logic for AffaireCreate / AffaireUpdate."""
    form_class = AffaireForm
    page_template = "cabinet/affaire_form.html"

    def get_template_names(self):
        if self.htmx():
            return ["modals/_affaire_form.html"]
        return [self.page_template]

    def form_invalid(self, form):
        if self.htmx():
            return self.render_modal("modals/_affaire_form.html", {
                "form": form, "title": "نموذج القضية", "action": self.request.path
            })
        return super().form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json(
                self.success_message,
                redirect=str(reverse_lazy("cabinet:affaire_detail", args=[self.object.pk])),
                closeModal=True,
            )
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("cabinet:affaire_detail", args=[self.object.pk])

class AffaireCreate(SecureBase, _AffaireFormMixin, CreateView):
    model = Affaire
    permission_required = "cabinet.add_affaire"
    success_message = "تم إنشاء القضية."

class AffaireUpdate(SecureBase, _AffaireFormMixin, UpdateView):
    model = Affaire
    permission_required = "cabinet.change_affaire"
    success_message = "تم تحديث القضية."

class AffaireDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Affaire
    permission_required = "cabinet.delete_affaire"
    def get_success_url(self): return reverse_lazy("cabinet:affaire_list")

# =============================================================
# JURIDICTION
# =============================================================

class JuridictionList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Juridiction
    template_name = "avocat/juridiction_list.html"
    partial_template_name = "avocat/juridiction_table.html"
    permission_required = "cabinet.view_juridiction"
    paginate_by = 20  # optionnel

    # champs cherchables (ar/fr + FK)
    search_fields = [
        "code",
        "nomtribunal_ar", "nomtribunal_fr",
        "villetribunal_ar", "villetribunal_fr",
        "type__libelle", "type__libelle_fr", "type__code_type",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("type", "TribunalParent").order_by("id")


class JuridictionDetail(SecureBase, DetailView):
    model = Juridiction
    template_name = "avocat/juridiction_detail.html"
    permission_required = "cabinet.view_juridiction"

class JuridictionCreate(SecureBase, ModalCreateView, CreateView):
    model = Juridiction
    form_class = JuridictionForm
    permission_required = "cabinet.add_juridiction"
    success_message = "تم إنشاء المحكمة."
    page_template = "cabinet/juridiction_form.html"
    def get_success_url(self): return self.request.GET.get("next") or reverse_lazy("cabinet:juridiction_list")

class JuridictionUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Juridiction
    form_class = JuridictionForm
    permission_required = "cabinet.change_juridiction"
    success_message = "تم تحديث المحكمة."
    page_template = "cabinet/juridiction_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:juridiction_detail", args=[self.object.pk])

class JuridictionDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Juridiction
    permission_required = "cabinet.delete_juridiction"
    def get_success_url(self): return reverse_lazy("cabinet:juridiction_list")

# =============================================================
# AVOCAT & BARREAU
# =============================================================

class AvocatList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Avocat
    template_name = "avocat/avocat_list.html"
    permission_required = "cabinet.view_avocat"
    paginate_by = 20  # optionnel

    # champs cherchables (ar/fr + FK)
    search_fields = [
        "nom", "barreau"
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("barreau").order_by("id")



class AvocatDetail(SecureBase, DetailView):
    model = Avocat
    template_name = "avocat/avocat_detail.html"
    permission_required = "cabinet.view_avocat"

class AvocatCreate(SecureBase, ModalCreateView, CreateView):
    model = Avocat
    form_class = AvocatForm
    permission_required = "cabinet.add_avocat"
    success_message = "تم إضافة المحامي."
    page_template = "avocat/avocat_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:avocat_detail", args=[self.object.pk])

class AvocatUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Avocat
    form_class = AvocatForm
    permission_required = "cabinet.change_avocat"
    success_message = "تم تعديل بيانات المحامي."
    page_template = "avocat/avocat_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:avocat_detail", args=[self.object.pk])

class AvocatDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Avocat
    permission_required = "cabinet.delete_avocat"
    def get_success_url(self): return reverse_lazy("cabinet:avocat_list")

class BarreauList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = Barreau
    template_name = "avocat/barreau_list.html"
    context_object_name = "object_list"
    permission_required = "cabinet.view_barreau"
    paginate_by = 20  # optionnel

    # champs cherchables (ar/fr + FK)
    search_fields = [
        "code",
        "juridiction_appel",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("juridiction_appel").order_by("id")


class BarreauDetail(SecureBase, DetailView):
    model = Barreau
    template_name = "avocat/barreau_detail.html"
    permission_required = "cabinet.view_barreau"

class BarreauCreate(SecureBase, ModalCreateView, CreateView):
    model = Barreau
    form_class = BarreauForm
    permission_required = "cabinet.add_barreau"
    success_message = "تمّ حفظ الهيئة."
    page_template = "avocat/barreau_form.html"
    refresh_target = "#ref-list"
    def get_success_url(self): return reverse_lazy("cabinet:barreau_list")

class BarreauUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Barreau
    form_class = BarreauForm
    permission_required = "cabinet.change_barreau"
    success_message = "تمّ تحديث الهيئة."
    page_template = "avocat/barreau_form.html"
    refresh_target = "#ref-list"
    def get_success_url(self): return reverse_lazy("cabinet:barreau_list")

class BarreauDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Barreau
    permission_required = "cabinet.delete_barreau"
    def get_success_url(self): return reverse_lazy("cabinet:barreau_list")

# =============================================================
# WORKFLOW: Audience / Mesure / Expertise / Decision / Notification
# =============================================================

# ----- Audience
class AudienceList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, DjangoFilterListMixin, HTMXPartialListMixin, ListView):
    model = Audience
    template_name = "avocat/audience_list.html"
    permission_required = "cabinet.view_audience"
    paginate_by = 20
    filterset_class = AudienceFilter

    search_fields = [
        "affaire__reference_interne", "type_audience__libelle",
        "resultat__libelle", "proces_verbal",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "type_audience", "resultat").order_by("-date_audience")


class AudienceDetail(SecureBase, DetailView):
    model = Audience
    template_name = "avocat/audience_detail.html"
    permission_required = "cabinet.view_audience"

class AudienceCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Audience
    form_class = AudienceForm
    permission_required = "cabinet.add_audience"
    success_message = "تمّ حفظ الجلسة."
    modal_template = "modals/_audience_form.html"
    page_template = "cabinet/audience_form.html"
    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get("affaire")
        if affaire_id:
            initial["affaire"] = get_object_or_404(Affaire, pk=affaire_id)
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ الجلسة.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ الجلسة.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:audience_list")

class AudienceUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Audience
    form_class = AudienceForm
    permission_required = "cabinet.change_audience"
    success_message = "تمّ تحديث الجلسة."
    modal_template = "modals/_audience_form.html"
    page_template = "cabinet/audience_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث الجلسة.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث الجلسة.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:audience_list")

class AudienceDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Audience
    permission_required = "cabinet.delete_audience"
    def get_success_url(self): return reverse_lazy("cabinet:audience_list")

# ----- Mesure
class MesureList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Mesure
    template_name = "avocat/mesure_list.html"
    permission_required = "cabinet.view_mesure"
    paginate_by = 20

    search_fields = [
        "type_mesure__libelle", "notes",
        "audience__affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("audience", "type_mesure", "statut").order_by("-date_ordonnee")


class MesureDetail(SecureBase, DetailView):
    model = Mesure
    template_name = "avocat/mesure_detail.html"
    permission_required = "cabinet.view_mesure"

class MesureCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Mesure
    form_class = MesureForm
    permission_required = "cabinet.add_mesure"
    success_message = "تمّ حفظ الإجراء."
    page_template = "cabinet/mesure_form.html"
    def get_initial(self):
        initial = super().get_initial()
        aff_pk = self.request.GET.get("affaire")
        if aff_pk:
            aud = (Audience.objects.filter(affaire_id=aff_pk).order_by("-date_audience", "-pk").first())
            if aud:
                initial["audience"] = aud
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ الإجراء.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ الإجراء.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:mesure_list")

class MesureUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Mesure
    form_class = MesureForm
    permission_required = "cabinet.change_mesure"
    success_message = "تمّ تحديث الإجراء."
    page_template = "cabinet/mesure_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث الإجراء.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث الإجراء.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:mesure_list")

class MesureDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Mesure
    permission_required = "cabinet.delete_mesure"
    def get_success_url(self): return reverse_lazy("cabinet:mesure_list")

# ----- Expertise + Expert
class ExpertiseList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Expertise
    template_name = "avocat/expertise_list.html"
    permission_required = "cabinet.view_expertise"
    paginate_by = 20

    search_fields = [
        "expert_nom", "affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire").order_by("-date_ordonnee")


class ExpertiseDetail(SecureBase, DetailView):
    model = Expertise
    template_name = "avocat/expertise_detail.html"
    permission_required = "cabinet.view_expertise"

class ExpertiseCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Expertise
    form_class = ExpertiseForm
    permission_required = "cabinet.add_expertise"
    success_message = "تمّ حفظ الخبرة."
    modal_template = "modals/_expertise_form.html"
    page_template = "cabinet/expertise_form.html"
    def get_initial(self):
        initial = super().get_initial()
        aff = self.request.GET.get("affaire")
        if aff:
            initial["affaire"] = get_object_or_404(Affaire, pk=aff)
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ الخبرة.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ الخبرة.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:expertise_list")

class ExpertiseUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Expertise
    form_class = ExpertiseForm
    permission_required = "cabinet.change_expertise"
    success_message = "تمّ تحديث الخبرة."
    modal_template = "modals/_expertise_form.html"
    page_template = "cabinet/expertise_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث الخبرة.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث الخبرة.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:expertise_list")

class ExpertiseDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Expertise
    permission_required = "cabinet.delete_expertise"
    def get_success_url(self): return reverse_lazy("cabinet:expertise_list")

class ExpertCreate(SecureBase, ModalCreateView, CreateView):
    """Création d’un Expert depuis un select2 (+ Ajouter جديد)."""
    model = Expert
    form_class = ExpertForm
    permission_required = "cabinet.add_expert"
    success_message = "تم إضافة الخبير."
    page_template = "cabinet/expert_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            select_id = self.request.GET.get("select_id") or self.request.POST.get("select_id")
            # injecter option + sélectionner (compatible select2)
            html = f"""
            <script>
              (function(){{
                 var sel = document.getElementById("{select_id}");
                 if(sel){{
                   var opt = new Option("{self.object.nom}", "{self.object.pk}", true, true);
                   sel.add(opt);
                   if (window.jQuery && jQuery.fn.select2) {{ jQuery(sel).trigger('change'); }}
                 }}
                 var m=document.getElementById('mainModal');
                 if(m) (bootstrap.Modal.getInstance(m)||new bootstrap.Modal(m)).hide();
              }})();
            </script>
            """
            return self.success_json(html=html, closeModal=True)
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:expertise_list")

# ----- Decision
class DecisionList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Decision
    template_name = "avocat/decision_list.html"
    permission_required = "cabinet.view_decision"
    paginate_by = 20

    search_fields = [
        "numero_decision", "affaire__reference_interne",
        "formation", "resumé",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire").order_by("-date_prononce")


class DecisionDetail(SecureBase, DetailView):
    model = Decision
    template_name = "avocat/decision_detail.html"
    permission_required = "cabinet.view_decision"

class DecisionCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Decision
    form_class = DecisionForm
    permission_required = "cabinet.add_decision"
    success_message = "تمّ حفظ الحكم."
    page_template = "cabinet/decision_form.html"
    def get_initial(self):
        initial = super().get_initial()
        aff = self.request.GET.get("affaire")
        if aff:
            initial["affaire"] = get_object_or_404(Affaire, pk=aff)
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ الحكم.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ الحكم.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:decision_list")

class DecisionUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Decision
    form_class = DecisionForm
    permission_required = "cabinet.change_decision"
    success_message = "تمّ تحديث الحكم."
    page_template = "cabinet/decision_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث الحكم.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث الحكم.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:decision_list")

class DecisionDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Decision
    permission_required = "cabinet.delete_decision"
    def get_success_url(self): return reverse_lazy("cabinet:decision_list")

# ----- Notification
class NotificationList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Notification
    template_name = "avocat/notification_list.html"
    permission_required = "cabinet.view_notification"
    paginate_by = 20

    search_fields = [
        "demande_numero", "huissier_nom",
        "decision__numero_decision", "decision__affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("decision", "decision__affaire").order_by("-date_depot_demande")


class NotificationDetail(SecureBase, DetailView):
    model = Notification
    template_name = "avocat/notification_detail.html"
    permission_required = "cabinet.view_notification"

class NotificationCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Notification
    form_class = NotificationForm
    permission_required = "cabinet.add_notification"
    success_message = "تمّ حفظ التبليغ."
    modal_template = "modals/_notification_form.html"
    page_template = "cabinet/notification_form.html"
    def get_initial(self):
        initial = super().get_initial()
        aff = self.request.GET.get("affaire")
        if aff:
            dec = Decision.objects.filter(affaire_id=aff).order_by("-date_prononce", "-pk").first()
            if dec: initial["decision"] = dec
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ التبليغ.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ التبليغ.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:notification_list")

class NotificationUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Notification
    form_class = NotificationForm
    permission_required = "cabinet.change_notification"
    success_message = "تمّ تحديث التبليغ."
    modal_template = "modals/_notification_form.html"
    page_template = "cabinet/notification_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث التبليغ.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث التبليغ.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:notification_list")

class NotificationDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Notification
    permission_required = "cabinet.delete_notification"
    def get_success_url(self): return reverse_lazy("cabinet:notification_list")

# ----- Voie de recours
class VoieDeRecoursList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = VoieDeRecours
    template_name = "avocat/voiederecours_list.html"
    permission_required = "cabinet.view_voiederecours"
    paginate_by = 20

    search_fields = [
        "numero_recours", "decision__numero_decision",
        "decision__affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("decision", "type_recours", "statut", "juridiction").order_by("-date_depot")


class VoieDeRecoursDetail(SecureBase, DetailView):
    model = VoieDeRecours
    template_name = "avocat/voiederecours_detail.html"
    permission_required = "cabinet.view_voiederecours"

class VoieDeRecoursCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = VoieDeRecours
    form_class = VoieDeRecoursForm
    permission_required = "cabinet.add_voiederecours"
    success_message = "تمّ حفظ الطعن."
    page_template = "cabinet/voiederecours_form.html"
    def get_initial(self):
        initial = super().get_initial()
        aff = self.request.GET.get("affaire")
        if aff:
            dec = Decision.objects.filter(affaire_id=aff).order_by("-date_prononce", "-pk").first()
            if dec: initial["decision"] = dec
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ الطعن.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ الطعن.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:voiederecours_list")

class VoieDeRecoursUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = VoieDeRecours
    form_class = VoieDeRecoursForm
    permission_required = "cabinet.change_voiederecours"
    success_message = "تمّ تحديث الطعن."
    page_template = "cabinet/voiederecours_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث الطعن.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث الطعن.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:voiederecours_list")

class VoieDeRecoursDelete(SecureBase, ModalDeleteView, DeleteView):
    model = VoieDeRecours
    permission_required = "cabinet.delete_voiederecours"
    def get_success_url(self): return reverse_lazy("cabinet:voiederecours_list")

# ----- Exécution
class ExecutionList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Execution
    template_name = "avocat/execution_list.html"
    permission_required = "cabinet.view_execution"
    paginate_by = 20

    search_fields = [
        "decision__numero_decision", "decision__affaire__reference_interne",
        "type_execution__libelle",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("decision", "type_execution", "statut").order_by("-date_demande")


class ExecutionDetail(SecureBase, DetailView):
    model = Execution
    template_name = "avocat/execution_detail.html"
    permission_required = "cabinet.view_execution"


class ExecutionCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Execution
    form_class = ExecutionForm
    permission_required = "cabinet.add_execution"
    success_message = "تمّ حفظ التنفيذ."
    modal_template = "modals/_execution_form.html"
    page_template = "cabinet/execution_form.html"
    def get_initial(self):
        initial = super().get_initial()
        aff = self.request.GET.get("affaire")
        if aff:
            dec = Decision.objects.filter(affaire_id=aff).order_by("-date_prononce", "-pk").first()
            if dec: initial["decision"] = dec
        return initial
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ التنفيذ.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ التنفيذ.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:execution_list")

class ExecutionUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Execution
    form_class = ExecutionForm
    permission_required = "cabinet.change_execution"
    success_message = "تمّ تحديث التنفيذ."
    modal_template = "modals/_execution_form.html"
    page_template = "cabinet/execution_form.html"
    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث التنفيذ.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[_affaire_pk_from_step(self.object)]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث التنفيذ.")
        return super().form_valid(form)
    def get_success_url(self): return reverse_lazy("cabinet:execution_list")

class ExecutionDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Execution
    permission_required = "cabinet.delete_execution"
    def get_success_url(self): return reverse_lazy("cabinet:execution_list")

# =============================================================
# AUTRES ENTITÉS SIMPLES
# =============================================================

class AlerteList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Alerte
    template_name = "avocat/alerte_list.html"
    permission_required = "cabinet.view_alerte"
    paginate_by = 20

    search_fields = [
        "message", "destinataire",
        "type_alerte__libelle",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("type_alerte").order_by("-date_alerte")


class AlerteDetail(SecureBase, DetailView):
    model = Alerte
    template_name = "avocat/alerte_detail.html"
    permission_required = "cabinet.view_alerte"

class AlerteCreate(SecureBase, ModalCreateView, CreateView):
    model = Alerte
    form_class = AlerteForm
    permission_required = "cabinet.add_alerte"
    success_message = "تمّ حفظ التنبيه."
    page_template = "cabinet/alerte_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:alerte_list")

class AlerteUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Alerte
    form_class = AlerteForm
    permission_required = "cabinet.change_alerte"
    success_message = "تمّ تحديث التنبيه."
    page_template = "cabinet/alerte_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:alerte_list")

class AlerteDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Alerte
    permission_required = "cabinet.delete_alerte"
    def get_success_url(self): return reverse_lazy("cabinet:alerte_list")

class TacheList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Tache
    template_name = "avocat/tache_list.html"
    permission_required = "cabinet.view_tache"
    paginate_by = 20

    search_fields = [
        "titre", "description",
        "affaire__reference_interne", "assigne_a__nom_complet",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "assigne_a", "statut").order_by("-echeance")


class TacheDetail(SecureBase, DetailView):
    model = Tache
    template_name = "avocat/tache_detail.html"
    permission_required = "cabinet.view_tache"

class TacheCreate(SecureBase, ModalCreateView, CreateView):
    model = Tache
    form_class = TacheForm
    permission_required = "cabinet.add_tache"
    success_message = "تمّ حفظ المهمة."
    page_template = "cabinet/tache_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:tache_list")

class TacheUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Tache
    form_class = TacheForm
    permission_required = "cabinet.change_tache"
    success_message = "تمّ تحديث المهمة."
    page_template = "cabinet/tache_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:tache_list")

class TacheDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Tache
    permission_required = "cabinet.delete_tache"
    def get_success_url(self): return reverse_lazy("cabinet:tache_list")

class PieceJointeList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, DjangoFilterListMixin, HTMXPartialListMixin, ListView):
    model = PieceJointe
    template_name = "avocat/piecejointe_list.html"
    permission_required = "cabinet.view_piecejointe"
    paginate_by = 20
    filterset_class = PieceJointeFilter

    search_fields = [
        "titre", "affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire").order_by("-date_ajout")


class PieceJointeDetail(SecureBase, DetailView):
    model = PieceJointe
    template_name = "avocat/piecejointe_detail.html"
    permission_required = "cabinet.view_piecejointe"

class PieceJointeCreate(SecureBase, ModalCreateView, CreateView):
    model = PieceJointe
    form_class = PieceJointeForm
    permission_required = "cabinet.add_piecejointe"
    success_message = "تمّ حفظ المرفق."
    page_template = "cabinet/piecejointe_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:piecejointe_list")

class PieceJointeUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = PieceJointe
    form_class = PieceJointeForm
    permission_required = "cabinet.change_piecejointe"
    success_message = "تمّ تحديث المرفق."
    page_template = "cabinet/piecejointe_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:piecejointe_list")

class PieceJointeDelete(SecureBase, ModalDeleteView, DeleteView):
    model = PieceJointe
    permission_required = "cabinet.delete_piecejointe"
    def get_success_url(self): return reverse_lazy("cabinet:piecejointe_list")

# ----- Parties / Liens Affaire<->Partie/Avocat
class PartieList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Partie
    template_name = "avocat/partie_list.html"
    permission_required = "cabinet.view_partie"
    paginate_by = 20

    search_fields = [
        "nom_complet", "cin_ou_rc", "telephone", "email",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("avocat").order_by("nom_complet")


class PartieDetail(SecureBase, DetailView):
    model = Partie
    template_name = "avocat/partie_detail.html"
    permission_required = "cabinet.view_partie"

class PartieCreate(SecureBase, ModalCreateView, CreateView):
    model = Partie
    form_class = PartieForm
    permission_required = "cabinet.add_partie"
    success_message = "تمّ حفظ الطرف."
    page_template = "cabinet/partie_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:partie_list")

class PartieUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Partie
    form_class = PartieForm
    permission_required = "cabinet.change_partie"
    success_message = "تمّ تحديث الطرف."
    page_template = "cabinet/partie_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:partie_list")

class PartieDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Partie
    permission_required = "cabinet.delete_partie"
    def get_success_url(self): return reverse_lazy("cabinet:partie_list")

class AffaireAvocatList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = AffaireAvocat
    template_name = "avocat/affaireavocat_list.html"
    permission_required = "cabinet.view_affaireavocat"
    paginate_by = 20

    search_fields = [
        "avocat__nom", "affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "avocat").order_by("id")


class AffaireAvocatDetail(SecureBase, DetailView):
    model = AffaireAvocat
    template_name = "avocat/affaireavocat_detail.html"
    permission_required = "cabinet.view_affaireavocat"

class AffaireAvocatCreate(SecureBase, ModalCreateView, CreateView):
    model = AffaireAvocat
    form_class = AffaireAvocatForm
    permission_required = "cabinet.add_affaireavocat"
    success_message = "تمّ ربط المحامي بالملف."
    page_template = "cabinet/affaireavocat_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:affaireavocat_list")

class AffaireAvocatUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = AffaireAvocat
    form_class = AffaireAvocatForm
    permission_required = "cabinet.change_affaireavocat"
    success_message = "تمّ تحديث الربط."
    page_template = "cabinet/affaireavocat_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:affaireavocat_list")

class AffaireAvocatDelete(SecureBase, ModalDeleteView, DeleteView):
    model = AffaireAvocat
    permission_required = "cabinet.delete_affaireavocat"
    def get_success_url(self): return reverse_lazy("cabinet:affaireavocat_list")

class AffairePartieList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = AffairePartie
    template_name = "avocat/affairepartie_list.html"
    permission_required = "cabinet.view_affairepartie"
    paginate_by = 20

    search_fields = [
        "partie__nom_complet", "affaire__reference_interne",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "partie").order_by("id")


class AffairePartieDetail(SecureBase, DetailView):
    model = AffairePartie
    template_name = "avocat/affairepartie_detail.html"
    permission_required = "cabinet.view_affairepartie"

class AffairePartieCreate(SecureBase, ModalCreateView, CreateView):
    model = AffairePartie
    form_class = AffairePartieForm
    permission_required = "cabinet.add_affairepartie"
    success_message = "تمّ ربط الطرف بالملف."
    page_template = "cabinet/affairepartie_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:affairepartie_list")

class AffairePartieUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = AffairePartie
    form_class = AffairePartieForm
    permission_required = "cabinet.change_affairepartie"
    success_message = "تمّ تحديث الربط."
    page_template = "cabinet/affairepartie_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:affairepartie_list")

class AffairePartieDelete(SecureBase, ModalDeleteView, DeleteView):
    model = AffairePartie
    permission_required = "cabinet.delete_affairepartie"
    def get_success_url(self): return reverse_lazy("cabinet:affairepartie_list")

# =============================================================
# PARTIAL: TIMELINE D’UNE AFFAIRE (HTMX)
# =============================================================

def affaire_timeline_partial(request, pk):
    affaire = get_object_or_404(Affaire, pk=pk)
    events: list[dict] = []
    today = timezone.localdate()
    _vb = reverse("cabinet:document_viewer")

    # إنذارات
    for av in Avertissement.objects.filter(affaire=affaire).select_related("type_avertissement").order_by("date_envoi"):
        deadline_info = ""
        deadline_badge = ""
        if av.date_echeance:
            j = av.jours_restants
            if j is not None:
                if j <= 0:
                    deadline_info = "انتهى الأجل"
                    deadline_badge = "danger"
                elif j <= 5:
                    deadline_info = f"باقي {j} أيام"
                    deadline_badge = "danger"
                elif j <= 10:
                    deadline_info = f"باقي {j} يوم"
                    deadline_badge = "warning"
                else:
                    deadline_info = f"باقي {j} يوم"
                    deadline_badge = "success"
        _av_file = bool(av.document) or bool(av.preuve_envoi)
        _av_url = ""
        if av.document:
            _av_url = f"{_vb}?model=avertissement&pk={av.pk}&field=document"
        elif av.preuve_envoi:
            _av_url = f"{_vb}?model=avertissement&pk={av.pk}&field=preuve_envoi"
        events.append({
            "date": av.date_envoi, "date_str": ar_dt(av.date_envoi),
            "type": "إنذار", "title": str(av.type_avertissement),
            "meta": f"{av.destinataire_nom} — {av.get_resultat_display()}",
            "badge": "terracotta",
            "deadline_info": deadline_info, "deadline_badge": deadline_badge,
            "has_file": _av_file, "viewer_url": _av_url,
        })

    # جلسات
    for a in Audience.objects.filter(affaire=affaire).select_related("type_audience", "resultat").order_by("date_audience"):
        events.append({
            "date": a.date_audience, "date_str": ar_dt(a.date_audience),
            "type": "جلسة", "title": str(a.type_audience),
            "meta": str(a.resultat) if a.resultat_id else "", "badge": "warning",
            "has_file": False, "viewer_url": "",
        })
    # إجراءات
    for m in Mesure.objects.filter(audience__affaire=affaire).select_related("type_mesure", "statut").order_by("id"):
        dt = getattr(m, "date_ordonnee", None) or getattr(m, "date", None)
        events.append({
            "date": dt, "date_str": ar_dt(dt),
            "type": "إجراء",
            "title": str(m.type_mesure),
            "meta": str(m.statut) if m.statut_id else "",
            "badge": "primary",
            "has_file": False, "viewer_url": "",
        })
    # خبرات
    for e in Expertise.objects.filter(affaire=affaire).order_by("date_ordonnee", "date_depot"):
        _exp_file = bool(e.rapport)
        _exp_url = f"{_vb}?model=expertise&pk={e.pk}&field=rapport" if _exp_file else ""
        if e.date_ordonnee:
            events.append({"date": e.date_ordonnee, "date_str": ar_dt(e.date_ordonnee),
                           "type": "خبرة", "title": f"أمرت: {e.expert_nom or ''}",
                           "meta": "خبرة مضادة" if getattr(e, "contre_expertise", False) else "", "badge": "dark",
                           "has_file": _exp_file, "viewer_url": _exp_url})
        if e.date_depot:
            events.append({"date": e.date_depot, "date_str": ar_dt(e.date_depot),
                           "type": "خبرة", "title": "إيداع الخبرة",
                           "meta": e.expert_nom or "", "badge": "dark",
                           "has_file": _exp_file, "viewer_url": _exp_url})
    # أحكام
    for d in Decision.objects.filter(affaire=affaire).order_by("date_prononce"):
        events.append({"date": d.date_prononce, "date_str": ar_dt(d.date_prononce),
                       "type": "حكم", "title": f"حكم رقم {d.numero_decision or ''}",
                       "meta": "قابل للطعن" if getattr(d, "susceptible_recours", False) else "غير قابل للطعن",
                       "badge": "secondary", "is_phase_marker": True,
                       "has_file": False, "viewer_url": ""})
    # تبليغات
    for n in Notification.objects.filter(decision__affaire=affaire).order_by("date_signification"):
        _not_file = bool(n.preuve)
        _not_url = f"{_vb}?model=notification&pk={n.pk}&field=preuve" if _not_file else ""
        events.append({"date": n.date_signification, "date_str": ar_dt(n.date_signification),
                       "type": "تبليغ", "title": f"طلب {n.demande_numero or ''}",
                       "meta": f"مفوض: {n.huissier_nom or ''}", "badge": "info",
                       "has_file": _not_file, "viewer_url": _not_url})
    # طرق الطعن
    for r in VoieDeRecours.objects.filter(decision__affaire=affaire).select_related("type_recours", "statut").order_by("date_depot"):
        deadline_info = ""
        deadline_badge = ""
        if r.date_echeance_recours:
            j = r.jours_restants_recours
            if j is not None:
                if j <= 0:
                    deadline_info = "انتهى الأجل"
                    deadline_badge = "danger"
                elif j <= 5:
                    deadline_info = f"باقي {j} أيام"
                    deadline_badge = "danger"
                elif j <= 10:
                    deadline_info = f"باقي {j} يوم"
                    deadline_badge = "warning"
                else:
                    deadline_info = f"باقي {j} يوم"
                    deadline_badge = "success"
        events.append({"date": r.date_depot, "date_str": ar_dt(r.date_depot),
                       "type": "طعن", "title": str(r.type_recours),
                       "meta": str(r.statut) if r.statut_id else "", "badge": "success",
                       "deadline_info": deadline_info, "deadline_badge": deadline_badge,
                       "has_file": False, "viewer_url": ""})
    # تنفيذ
    for ex in Execution.objects.filter(decision__affaire=affaire).select_related("type_execution", "statut").order_by("date_demande"):
        events.append({"date": ex.date_demande, "date_str": ar_dt(ex.date_demande),
                       "type": "تنفيذ", "title": str(ex.type_execution),
                       "meta": str(ex.statut) if ex.statut_id else "", "badge": "success",
                       "has_file": False, "viewer_url": ""})
    # مرفقات
    for p in PieceJointe.objects.filter(affaire=affaire).order_by("date_ajout"):
        _pj_file = bool(p.fichier)
        _pj_url = f"{_vb}?model=piecejointe&pk={p.pk}" if _pj_file else ""
        events.append({"date": p.date_ajout, "date_str": ar_dt(p.date_ajout),
                       "type": "مرفق", "title": p.titre or "",
                       "meta": getattr(p, "get_type_piece_display", lambda: (p.type_piece or ""))(), "badge": "light",
                       "has_file": _pj_file, "viewer_url": _pj_url})

    from datetime import datetime as _dt, date as _d
    def _sort_key(ev):
        d = ev["date"]
        if isinstance(d, _d) and not isinstance(d, _dt):
            return _dt(d.year, d.month, d.day)
        return d.replace(tzinfo=None) if d.tzinfo else d

    events = [ev for ev in events if ev["date"]]
    events.sort(key=_sort_key)
    return render(request, "affaires/_timeline.html", {"affaire": affaire, "events": events})

class ExpertList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Expert
    template_name = 'avocat/expert_list.html'
    permission_required = 'cabinet.view_expert'
    paginate_by = 20

    search_fields = [
        "nom_complet", "specialite", "email",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by("nom_complet")


class ExpertDetail(SecureBase, DetailView):
    model = Expert
    template_name = 'avocat/expert_detail.html'
    permission_required = 'cabinet.view_expert'
class ExpertUpdate(SecureBase, UpdateView):
    model = Expert
    form_class = ExpertForm
    permission_required = 'cabinet.change_expert'
    success_url = reverse_lazy('cabinet:expert_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث الخبرة.')
        if self.htmx():
            return self.success_json('تمّ تحديث الخبرة.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل خبرة', 'action': request.path})
        return super().get(request, *args, **kwargs)

class ExpertDelete(SecureBase, DeleteView):
    model = Expert
    permission_required = 'cabinet.delete_expert'
    success_url = reverse_lazy('cabinet:expert_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف الخبرة.')
        if self.htmx():
            return self.success_json('تمّ حذف الخبرة.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)

class UtilisateurList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Utilisateur
    template_name = 'avocat/utilisateur_list.html'
    permission_required = 'cabinet.view_utilisateur'
    paginate_by = 20

    search_fields = [
        "nom_complet",
        "email",
        "role__libelle", "role__libelle_fr",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("role").order_by("nom_complet")


class UtilisateurDetail(SecureBase, DetailView):
    model = Utilisateur
    template_name = 'avocat/utilisateur_detail.html'
    permission_required = 'cabinet.view_utilisateur'

class UtilisateurCreate(SecureBase, CreateView):
    model = Utilisateur
    form_class = UtilisateurForm
    permission_required = 'cabinet.add_utilisateur'
    success_url = reverse_lazy('cabinet:utilisateur_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ إضافة المستخدم.')
        if self.htmx():
            return self.success_json('تمّ إضافة المستخدم.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class()
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة مستخدم', 'action': request.path})
        return super().get(request, *args, **kwargs)

class UtilisateurUpdate(SecureBase, UpdateView):
    model = Utilisateur
    form_class = UtilisateurForm
    permission_required = 'cabinet.change_utilisateur'
    success_url = reverse_lazy('cabinet:utilisateur_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث المستخدم.')
        if self.htmx():
            return self.success_json('تمّ تحديث المستخدم.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل مستخدم', 'action': request.path})
        return super().get(request, *args, **kwargs)

class UtilisateurDelete(SecureBase, DeleteView):
    model = Utilisateur
    permission_required = 'cabinet.delete_utilisateur'
    success_url = reverse_lazy('cabinet:utilisateur_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, 'تمّ حذف المستخدم.')
        if self.htmx():
            return self.success_json('تمّ حذف المستخدم.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class RecetteList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, DjangoFilterListMixin, HTMXPartialListMixin, ListView):
    model = Recette
    template_name = 'avocat/recette_list.html'
    permission_required = 'cabinet.view_recette'
    paginate_by = 20
    filterset_class = RecetteFilter

    search_fields = [
        "affaire__reference_interne",
        "type_recette__libelle", "type_recette__libelle_fr",
        "source",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "type_recette").order_by("-date_recette")


class RecetteDetail(SecureBase, DetailView):
    model = Recette
    template_name = 'avocat/recette_detail.html'
    permission_required = 'cabinet.view_recette'

class RecetteCreate(SecureBase, CreateView):
    model = Recette
    form_class = RecetteForm
    permission_required = 'cabinet.add_recette'
    success_url = reverse_lazy('cabinet:recette_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id:
            initial['affaire'] = affaire_id
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ الدخل.')
        if self.htmx():
            return self.success_json('تمّ حفظ الدخل.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة دخل', 'action': request.path})
        return super().get(request, *args, **kwargs)

class RecetteUpdate(SecureBase, UpdateView):
    model = Recette
    form_class = RecetteForm
    permission_required = 'cabinet.change_recette'
    success_url = reverse_lazy('cabinet:recette_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث الدخل.')
        if self.htmx():
            return self.success_json('تمّ تحديث الدخل.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل دخل', 'action': request.path})
        return super().get(request, *args, **kwargs)

class RecetteDelete(SecureBase, DeleteView):
    model = Recette
    permission_required = 'cabinet.delete_recette'
    success_url = reverse_lazy('cabinet:recette_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف الدخل.')
        if self.htmx():
            return self.success_json('تمّ حذف الدخل.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class DepenseList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, DjangoFilterListMixin, HTMXPartialListMixin, ListView):
    model = Depense
    template_name = 'avocat/depense_list.html'
    permission_required = 'cabinet.view_depense'
    paginate_by = 20
    filterset_class = DepenseFilter

    search_fields = [
        "affaire__reference_interne",
        "type_depense__libelle", "type_depense__libelle_fr",
        "beneficiaire",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "type_depense").order_by("-date_depense")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Stats on the FILTERED queryset (respects active filters)
        fs = getattr(self, "filterset", None)
        stats_qs = fs.qs if fs else self.get_queryset()

        # Total
        agg = stats_qs.aggregate(total=Sum("montant"))
        ctx["depense_total"] = agg["total"] or 0

        # By type
        by_type = (
            stats_qs.values("type_depense__libelle")
            .annotate(total=Sum("montant"))
            .order_by("-total")[:10]
        )
        ctx["stats_by_type"] = [
            {"label": r["type_depense__libelle"] or "—", "total": r["total"]}
            for r in by_type
        ]

        # By beneficiary
        by_benef = (
            stats_qs.exclude(beneficiaire__isnull=True).exclude(beneficiaire="")
            .values("beneficiaire")
            .annotate(total=Sum("montant"))
            .order_by("-total")[:10]
        )
        ctx["stats_by_beneficiaire"] = [
            {"label": r["beneficiaire"], "total": r["total"]}
            for r in by_benef
        ]

        return ctx


class DepenseDetail(SecureBase, DetailView):
    model = Depense
    template_name = 'avocat/depense_detail.html'
    permission_required = 'cabinet.view_depense'

class DepenseCreate(SecureBase, CreateView):
    model = Depense
    form_class = DepenseForm
    permission_required = 'cabinet.add_depense'
    success_url = reverse_lazy('cabinet:depense_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id:
            initial['affaire'] = affaire_id
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ المصروف.')
        if self.htmx():
            return self.success_json('تمّ حفظ المصروف.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة مصروف', 'action': request.path})
        return super().get(request, *args, **kwargs)

class DepenseUpdate(SecureBase, UpdateView):
    model = Depense
    form_class = DepenseForm
    permission_required = 'cabinet.change_depense'
    success_url = reverse_lazy('cabinet:depense_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث المصروف.')
        if self.htmx():
            return self.success_json('تمّ تحديث المصروف.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل مصروف', 'action': request.path})
        return super().get(request, *args, **kwargs)

class DepenseDelete(SecureBase, DeleteView):
    model = Depense
    permission_required = 'cabinet.delete_depense'
    success_url = reverse_lazy('cabinet:depense_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف المصروف.')
        if self.htmx():
            return self.success_json('تمّ حذف المصروف.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)



# -------------------------------------------------------------
# Partial HTMX pour Timeline (déjà référencé par urls.py)
# -------------------------------------------------------------
def ar_dt(dt):
    if not dt:
        return ""
    from datetime import datetime as _dt
    fmt = "DATETIME_FORMAT" if isinstance(dt, _dt) else "DATE_FORMAT"
    return date_format(dt, fmt, use_l10n=True)

#-- Créations imbriquées par Affaire ----
class AudienceCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Audience            # جلسة
    form_class = AudienceForm
    modal_template = "modals/_audience_form.html"
    template_name = "cabinet/audience_form.html"
    permission_required = "cabinet.add_audience"
    success_message = "تمت إضافة الجلسة."

    def get_affaire(self):
        affaire_pk = self.kwargs.get("affaire_pk")
        return get_object_or_404(Affaire, pk=affaire_pk)

    def dispatch(self, request, *args, **kwargs):
        self.affaire = self.get_affaire()
        if self.affaire.has_decision():  # verrou post-décision
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.affaire = self.get_affaire()  # ← injecte l'affaire
        obj.save()
        self.object = obj
        return self.success_json("تمت إضافة الجلسة.", refreshTarget="#timeline",
                                 refreshUrl=reverse_lazy("cabinet:affaire_timeline", args=[self.kwargs["affaire_id"]]))

class MesureCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Mesure              # إجراء
    form_class = MesureForm
    template_name = "cabinet/mesure_form.html"
    permission_required = "cabinet.add_mesure"
    success_message = "تمت إضافة الإجراء."

class ExpertiseCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Expertise           # خبرة
    form_class = ExpertiseForm
    modal_template = "modals/_expertise_form.html"
    template_name = "cabinet/expertise_form.html"
    permission_required = "cabinet.add_expertise"
    success_message = "تمت إضافة الخبرة."

class DecisionCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Decision            # حكم
    form_class = DecisionForm
    template_name = "cabinet/decision_form.html"
    permission_required = "cabinet.add_decision"
    success_message = "تمت إضافة الحكم."

class NotificationCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Notification        # تبليغ
    form_class = NotificationForm
    modal_template = "modals/_notification_form.html"
    template_name = "cabinet/notification_form.html"
    permission_required = "cabinet.add_notification"
    success_message = "تمت إضافة التبليغ."

class RecoursCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = VoieDeRecours       # طعن
    form_class = VoieDeRecoursForm
    template_name = "cabinet/voiederecours_form.html"
    permission_required = "cabinet.add_voiederecours"
    success_message = "تم تسجيل الطعن."

class ExecutionCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Execution           # تنفيذ
    form_class = ExecutionForm
    modal_template = "modals/_execution_form.html"
    template_name = "cabinet/execution_form.html"
    permission_required = "cabinet.add_execution"
    success_message = "تم فتح ملف التنفيذ."

# =============================================================
# AVERTISSEMENT (إنذار)
# =============================================================

class AvertissementList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Avertissement
    template_name = "avocat/avertissement_list.html"
    permission_required = "cabinet.view_avertissement"
    paginate_by = 20

    search_fields = [
        "affaire__reference_interne", "type_avertissement__libelle",
        "destinataire_nom", "objet_avertissement",
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("affaire", "type_avertissement").order_by("-date_envoi")


class AvertissementDetail(SecureBase, DetailView):
    model = Avertissement
    template_name = "avocat/avertissement_detail.html"
    permission_required = "cabinet.view_avertissement"


class AvertissementCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Avertissement
    form_class = AvertissementForm
    permission_required = "cabinet.add_avertissement"
    success_message = "تمّ حفظ الإنذار."
    modal_template = "modals/_avertissement_form.html"
    page_template = "cabinet/avertissement_form.html"

    def get_initial(self):
        initial = super().get_initial()
        aff = self.request.GET.get("affaire")
        if aff:
            initial["affaire"] = get_object_or_404(Affaire, pk=aff)
        return initial

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ حفظ الإنذار.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[self.object.affaire_id]),
                                     closeModal=True)
        messages.success(self.request, "تمّ حفظ الإنذار.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cabinet:avertissement_list")


class AvertissementUpdate(SecureBase, HTMXModalFormMixin, UpdateView):
    model = Avertissement
    form_class = AvertissementForm
    permission_required = "cabinet.change_avertissement"
    success_message = "تمّ تحديث الإنذار."
    modal_template = "modals/_avertissement_form.html"
    page_template = "cabinet/avertissement_form.html"

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json("تمّ تحديث الإنذار.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[self.object.affaire_id]),
                                     closeModal=True)
        messages.success(self.request, "تمّ تحديث الإنذار.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cabinet:avertissement_list")


class AvertissementDelete(SecureBase, ModalDeleteView, DeleteView):
    model = Avertissement
    permission_required = "cabinet.delete_avertissement"
    def get_success_url(self): return reverse_lazy("cabinet:avertissement_list")


class AvertissementCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Avertissement
    form_class = AvertissementForm
    modal_template = "modals/_avertissement_form.html"
    template_name = "cabinet/avertissement_form.html"
    permission_required = "cabinet.add_avertissement"
    success_message = "تمت إضافة الإنذار."

    def get_affaire(self):
        return get_object_or_404(Affaire, pk=self.kwargs.get("affaire_id"))

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.affaire = self.get_affaire()
        obj.save()
        self.object = obj
        if self.htmx():
            return self.success_json("تمت إضافة الإنذار.", refreshTarget="#timeline",
                                     refreshUrl=reverse("cabinet:affaire_timeline", args=[self.kwargs["affaire_id"]]),
                                     closeModal=True)
        messages.success(self.request, "تمت إضافة الإنذار.")
        return redirect(reverse("cabinet:affaire_detail", args=[self.kwargs["affaire_id"]]))

    def get_success_url(self):
        return reverse_lazy("cabinet:affaire_detail", args=[self.kwargs["affaire_id"]])


# =============================================================
# MAHAKIM.MA SYNC — مزامنة مع بوابة محاكم
# =============================================================

import threading
import logging as _logging

_mahakim_logger = _logging.getLogger(__name__)


@login_required
def mahakim_preview_single(request, pk):
    """Preview modal before syncing a single affaire."""
    affaire = get_object_or_404(Affaire, pk=pk)
    last_sync = MahakimSyncResult.objects.filter(affaire=affaire).order_by("-date_sync").first()
    html = render_to_string("modals/_mahakim_preview.html", {
        "mode": "preview_single",
        "affaire": affaire,
        "last_sync": last_sync,
    }, request=request)
    return HttpResponse(html)


@login_required
def mahakim_preview_all(request):
    """Preview modal before syncing all affaires."""
    qs = Affaire.objects.filter(
        numero_dossier__isnull=False, code_categorie__isnull=False, annee_dossier__isnull=False,
    ).exclude(numero_dossier="").exclude(annee_dossier="")
    total = qs.count()
    synced_ids = set(MahakimSyncResult.objects.filter(
        affaire__in=qs, success=True
    ).values_list("affaire_id", flat=True).distinct())
    html = render_to_string("modals/_mahakim_preview.html", {
        "mode": "preview_all",
        "total_syncable": total,
        "already_synced": len(synced_ids),
        "never_synced": total - len(synced_ids),
    }, request=request)
    return HttpResponse(html)


def sync_affaire_mahakim(request, pk):
    """Sync une seule affaire avec mahakim.ma (HTMX button)."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "غير مسموح"}, status=403)

    affaire = get_object_or_404(Affaire, pk=pk)

    if not all([affaire.numero_dossier, affaire.code_categorie, affaire.annee_dossier]):
        return JsonResponse({
            "ok": False,
            "message": "يجب ملء رقم الملف وصنف القضية والسنة قبل المزامنة مع محاكم"
        })

    try:
        from .services.mahakim_scraper import MahakimScraper

        type_juridiction = None
        if hasattr(affaire.juridiction, 'type') and affaire.juridiction.type:
            type_juridiction = str(affaire.juridiction.type)

        with MahakimScraper(headless=True, timeout=30) as scraper:
            result = scraper.scrape_affaire(
                numero=affaire.numero_dossier,
                code_categorie=affaire.code_categorie.code,
                annee=affaire.annee_dossier,
                type_juridiction=type_juridiction,
            )

        sync_obj = MahakimSyncResult.objects.create(
            affaire=affaire,
            statut_mahakim=result.get("statut_mahakim"),
            prochaine_audience=result.get("prochaine_audience"),
            juge=result.get("juge"),
            observations=result.get("observations"),
            raw_html=(result.get("raw_html") or "")[:50000],
            success=result.get("success", False),
            error_message=result.get("error_message"),
        )

        if result["success"]:
            return JsonResponse({
                "ok": True,
                "message": f"تمت المزامنة بنجاح — الحالة: {result.get('statut_mahakim', '—')}",
                "data": {
                    "statut": result.get("statut_mahakim"),
                    "prochaine_audience": str(result.get("prochaine_audience") or ""),
                    "juge": result.get("juge"),
                },
            })
        else:
            return JsonResponse({
                "ok": False,
                "message": result.get("error_message", "فشلت المزامنة"),
            })

    except ImportError:
        return JsonResponse({
            "ok": False,
            "message": "مكتبة Selenium غير مثبتة. قم بتثبيتها: pip install selenium",
        })
    except Exception as e:
        _mahakim_logger.exception("Erreur sync mahakim pour affaire %s", pk)
        return JsonResponse({
            "ok": False,
            "message": f"خطأ: {str(e)[:200]}",
        })


class MahakimSyncListView(SecureBase, NoPostOnReadOnlyMixin, ListView):
    """Page dédiée de synchronisation mahakim.ma."""
    model = Affaire
    template_name = "cabinet/mahakim_sync.html"
    permission_required = ()
    paginate_by = 50

    def get_queryset(self):
        return (
            Affaire.objects.filter(
                numero_dossier__isnull=False,
                code_categorie__isnull=False,
                annee_dossier__isnull=False,
            )
            .exclude(numero_dossier="")
            .exclude(annee_dossier="")
            .select_related("code_categorie", "juridiction", "type_affaire", "statut_affaire")
            .order_by("-date_ouverture")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Ajouter le dernier sync pour chaque affaire
        affaire_ids = [a.pk for a in ctx["object_list"]]
        latest_syncs = {}
        for sync in MahakimSyncResult.objects.filter(affaire_id__in=affaire_ids).order_by("affaire_id", "-date_sync"):
            if sync.affaire_id not in latest_syncs:
                latest_syncs[sync.affaire_id] = sync
        # Build sync_data list for template
        sync_data = []
        for affaire in ctx["object_list"]:
            sync_data.append({
                "affaire": affaire,
                "sync": latest_syncs.get(affaire.pk),
            })
        ctx["sync_data"] = sync_data
        ctx["total_syncable"] = self.get_queryset().count()
        return ctx


def sync_all_mahakim(request):
    """Lance la synchronisation de toutes les affaires en arrière-plan."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "غير مسموح"}, status=403)

    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST فقط"}, status=405)

    from django.core.management import call_command

    def _run_sync():
        try:
            call_command("sync_mahakim")
        except Exception as e:
            _mahakim_logger.exception("Erreur sync_all_mahakim: %s", e)

    thread = threading.Thread(target=_run_sync, daemon=True)
    thread.start()

    return JsonResponse({
        "ok": True,
        "message": "بدأت المزامنة في الخلفية. أعد تحميل الصفحة بعد دقائق لرؤية النتائج.",
    })


# =============================================================
# DOCUMENT VIEWER (معاينة المرفقات)
# =============================================================

# Registry: model_name → (Model, file_field, permission)
_FILE_REGISTRY = {
    "piecejointe": (PieceJointe, "fichier", "cabinet.view_piecejointe"),
    "depense": (Depense, "piece", "cabinet.view_depense"),
    "recette": (Recette, "piece", "cabinet.view_recette"),
    "expertise": (Expertise, "rapport", "cabinet.view_expertise"),
    "notification": (Notification, "preuve", "cabinet.view_notification"),
    "avertissement": (Avertissement, "preuve_envoi", "cabinet.view_avertissement"),
}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
_PDF_EXTS = {".pdf"}


def _detect_doc_type(filename):
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _IMAGE_EXTS:
        return "image"
    return "other"


@ensure_csrf_cookie
def document_viewer(request):
    """Vue HTMX qui renvoie le contenu modal pour visionner un document."""
    if not request.user.is_authenticated:
        return HttpResponse("غير مسموح", status=403)

    model_name = request.GET.get("model", "").lower()
    pk = request.GET.get("pk")
    field_name = request.GET.get("field")  # optionnel

    if model_name not in _FILE_REGISTRY:
        return HttpResponse("نموذج غير معروف", status=400)

    Model, default_field, perm = _FILE_REGISTRY[model_name]

    if not request.user.has_perm(perm):
        return HttpResponse("غير مسموح", status=403)

    obj = get_object_or_404(Model, pk=pk)
    field = field_name or default_field
    file_obj = getattr(obj, field, None)

    if not file_obj:
        return HttpResponse("لا يوجد ملف مرفق", status=404)

    file_url = file_obj.url
    doc_type = _detect_doc_type(file_obj.name)
    title = str(obj)

    html = render_to_string("modals/_document_viewer.html", {
        "title": title,
        "file_url": file_url,
        "doc_type": doc_type,
    }, request=request)
    return HttpResponse(html)


# =============================================================
# PRINT DOCUMENTS (طباعة المستندات)
# =============================================================

def print_documents(request):
    """Page autonome d'impression de documents filtrés."""
    if not request.user.is_authenticated:
        return HttpResponse("غير مسموح", status=403)

    source = request.GET.get("source", "").lower()

    SOURCE_MAP = {
        "depense": (Depense, "piece", "cabinet.view_depense", DepenseFilter),
        "recette": (Recette, "piece", "cabinet.view_recette", RecetteFilter),
        "piecejointe": (PieceJointe, "fichier", "cabinet.view_piecejointe", PieceJointeFilter),
    }

    if source not in SOURCE_MAP:
        return HttpResponse("مصدر غير صالح", status=400)

    Model, file_field, perm, FilterClass = SOURCE_MAP[source]

    if not request.user.has_perm(perm):
        return HttpResponse("غير مسموح", status=403)

    qs = Model.objects.all()
    fs = FilterClass(request.GET, queryset=qs)
    qs = fs.qs[:100]  # max 100 documents

    documents = []
    for obj in qs:
        f = getattr(obj, file_field, None)
        if f:
            doc_type = _detect_doc_type(f.name)
            documents.append({
                "title": str(obj),
                "url": f.url,
                "type": doc_type,
            })

    return render(request, "print/documents.html", {
        "documents": documents,
        "source_label": {"depense": "المصاريف", "recette": "الإيرادات", "piecejointe": "المرفقات"}.get(source, ""),
        "count": len(documents),
    })


# ====== دليل الاستعمال ======
@login_required
def user_guide(request):
    return render(request, "guide/user_guide.html", {"today": timezone.localdate()})
