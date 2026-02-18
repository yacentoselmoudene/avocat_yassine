# =============================================================
# FILE: views.py (extrait mis à jour)
# - Ajoute des réponses JSON uniformes (ok, html, refreshTarget, refreshUrl)
# - Cible par défaut: rafraîchir #timeline d'une Affaire après Create/Update
# - Gère HTMX modals pour Create/Update/Delete
# - Sécurisé: LoginRequired + Permissions + CSRF cookie
# =============================================================
from __future__ import annotations

from typing import Any, Dict
from django.utils.formats import date_format
from .views_mixins import CreateView, UpdateView, NoPostOnReadOnlyMixin, HTMXViewMixin, \
    SoftDeleteQuerysetMixin, ModalCreateView, ModalUpdateView, ModalDeleteView, HTMXModalFormMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

# avocat_app/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from .views_mixins import HTMXModalFormMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages

from .models import Affaire, Juridiction, Avocat, Audience
from .forms import AffaireForm, JuridictionForm, AvocatForm, AudienceForm
from django.utils import timezone
from django.views.generic import TemplateView
from django.db.models import Sum
from datetime import timedelta

from .models import Affaire, Audience, Recette, Depense

# views.py (ajoute ces mixins puis la vue)

from django.db.models import Q
from django.shortcuts import render


from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte, Expert, Barreau
)

from .forms import (
    JuridictionForm, AvocatForm, AffaireForm, PartieForm, AffairePartieForm, AffaireAvocatForm,
    AudienceForm, MesureForm, ExpertiseForm, DecisionForm, NotificationForm, VoieDeRecoursForm,
    ExecutionForm, DepenseForm, RecetteForm, PieceJointeForm, UtilisateurForm, TacheForm, AlerteForm, ExpertForm,
    BarreauForm
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
"""    
class SecureBase(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required: str | tuple[str, ...] = ()
    raise_exception = True

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)

    def htmx(self) -> bool:
        return self.request.headers.get('HX-Request', '').lower() == 'true'

    def success_json(self, message: str, affaire_pk: int | None = None) -> JsonResponse:
        html = render_to_string('modals/_success_toast.html', {'message': message}, request=self.request)
        payload: Dict[str, Any] = {'ok': True, 'html': html}
        if affaire_pk:
            payload.update({
                'refreshTarget': '#timeline',
                'refreshUrl': reverse('cabinet:affaire_timeline', args=[affaire_pk])
            })
        return JsonResponse(payload)

    def render_modal(self, template: str, context: Dict[str, Any]) -> HttpResponse:
        html = render_to_string(template, context=context, request=self.request)
        return HttpResponse(html)
"""

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


class HTMXPartialListMixin:
    """Si la requête est HTMX, ne renvoie que le partial du tableau."""
    partial_template_name: str = None  # à définir sur la vue

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("HX-Request") and self.partial_template_name:
            return render(self.request, self.partial_template_name, context)
        return super().render_to_response(context, **response_kwargs)



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
        try:
            ctx["finance"] = {
                "depenses_mois": Depense.objects.filter(
                    date_depense__year=today.year, date_depense__month=today.month
                ).aggregate(Sum("montant"))["montant__sum"] or 0,
                "recettes_mois": Recette.objects.filter(
                    date_recette__year=today.year, date_recette__month=today.month
                ).aggregate(Sum("montant"))["montant__sum"] or 0,
            }
        except Exception:
            ctx["finance"] = {"depenses_mois": 0, "recettes_mois": 0}
        return ctx

# =============================================================
# AFFAIRES
# =============================================================

class AffaireList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Affaire
    template_name = "avocat/affaire_list.html"
    permission_required = "cabinet.view_affaire"
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class AffaireDetail(SecureBase, NoPostOnReadOnlyMixin, DetailView):
    model = Affaire
    template_name = "avocat/affaire_detail.html"
    permission_required = "cabinet.view_affaire"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Verrous UX: قبل/بعد الحكم
        has_decision = Decision.objects.filter(affaire=self.object).exists()
        ctx["lock_predecision"] = not has_decision
        ctx["lock_postdecision"] = has_decision
        return ctx

class AffaireCreate(SecureBase, ModalCreateView, CreateView):
    model = Affaire
    form_class = AffaireForm
    permission_required = "cabinet.add_affaire"
    success_message = "تم إنشاء القضية."
    page_template = "cabinet/affaire_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:affaire_detail", args=[self.object.pk])

class AffaireUpdate(SecureBase, ModalUpdateView, UpdateView):
    model = Affaire
    form_class = AffaireForm
    permission_required = "cabinet.change_affaire"
    success_message = "تم تحديث القضية."
    page_template = "cabinet/affaire_form.html"
    def get_success_url(self): return reverse_lazy("cabinet:affaire_detail", args=[self.object.pk])

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
class AudienceList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Audience
    template_name = "avocat/audience_list.html"
    permission_required = "cabinet.view_audience"
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class AudienceDetail(SecureBase, DetailView):
    model = Audience
    template_name = "avocat/audience_detail.html"
    permission_required = "cabinet.view_audience"

class AudienceCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Audience
    form_class = AudienceForm
    permission_required = "cabinet.add_audience"
    success_message = "تمّ حفظ الجلسة."
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class ExpertiseDetail(SecureBase, DetailView):
    model = Expertise
    template_name = "avocat/expertise_detail.html"
    permission_required = "cabinet.view_expertise"

class ExpertiseCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Expertise
    form_class = ExpertiseForm
    permission_required = "cabinet.add_expertise"
    success_message = "تمّ حفظ الخبرة."
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class NotificationDetail(SecureBase, DetailView):
    model = Notification
    template_name = "avocat/notification_detail.html"
    permission_required = "cabinet.view_notification"

class NotificationCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Notification
    form_class = NotificationForm
    permission_required = "cabinet.add_notification"
    success_message = "تمّ حفظ التبليغ."
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class ExecutionDetail(SecureBase, DetailView):
    model = Execution
    template_name = "avocat/execution_detail.html"
    permission_required = "cabinet.view_execution"
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class ExecutionCreate(SecureBase, HTMXModalFormMixin, CreateView):
    model = Execution
    form_class = ExecutionForm
    permission_required = "cabinet.add_execution"
    success_message = "تمّ حفظ التنفيذ."
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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

class PieceJointeList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = PieceJointe
    template_name = "avocat/piecejointe_list.html"
    permission_required = "cabinet.view_piecejointe"
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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
        return qs.select_related("type", "idTribunalParent").order_by("id")


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

    # جلسات
    for a in Audience.objects.filter(affaire=affaire).order_by("date_audience"):
        events.append({
            "date": a.date_audience, "date_str": ar_dt(a.date_audience),
            "type": "جلسة", "title": a.get_type_audience_display(),
            "meta": a.resultat or "", "badge": "warning",
        })
    # إجراءات
    for m in Mesure.objects.filter(audience__affaire=affaire).order_by("id"):
        dt = getattr(m, "date_ordonnee", None) or getattr(m, "date", None)
        events.append({
            "date": dt, "date_str": ar_dt(dt),
            "type": "إجراء",
            "title": getattr(m, "get_type_mesure_display", lambda: "إجراء")(),
            "meta": getattr(m, "get_statut_display", lambda: (m.statut or ""))(),
            "badge": "primary",
        })
    # خبرات
    for e in Expertise.objects.filter(affaire=affaire).order_by("date_ordonnee", "date_depot"):
        if e.date_ordonnee:
            events.append({"date": e.date_ordonnee, "date_str": ar_dt(e.date_ordonnee),
                           "type": "خبرة", "title": f"أمرت: {e.expert_nom or ''}",
                           "meta": "خبرة مضادة" if getattr(e, "contre_expertise", False) else "", "badge": "dark"})
        if e.date_depot:
            events.append({"date": e.date_depot, "date_str": ar_dt(e.date_depot),
                           "type": "خبرة", "title": "إيداع الخبرة",
                           "meta": e.expert_nom or "", "badge": "dark"})
    # أحكام
    for d in Decision.objects.filter(affaire=affaire).order_by("date_prononce"):
        events.append({"date": d.date_prononce, "date_str": ar_dt(d.date_prononce),
                       "type": "حكم", "title": f"حكم رقم {d.numero_decision or ''}",
                       "meta": "قابل للطعن" if getattr(d, "susceptible_recours", False) else "غير قابل للطعن",
                       "badge": "secondary"})
    # تبليغات
    for n in Notification.objects.filter(decision__affaire=affaire).order_by("date_signification"):
        events.append({"date": n.date_signification, "date_str": ar_dt(n.date_signification),
                       "type": "تبليغ", "title": f"طلب {n.demande_numero or ''}",
                       "meta": f"مفوض: {n.huissier_nom or ''}", "badge": "info"})
    # طرق الطعن
    for r in VoieDeRecours.objects.filter(decision__affaire=affaire).order_by("date_depot"):
        events.append({"date": r.date_depot, "date_str": ar_dt(r.date_depot),
                       "type": "طعن", "title": getattr(r, "get_type_recours_display", lambda: (r.type_recours or ""))(),
                       "meta": getattr(r, "get_statut_display", lambda: (r.statut or ""))(), "badge": "success"})
    # تنفيذ
    for ex in Execution.objects.filter(decision__affaire=affaire).order_by("date_demande"):
        events.append({"date": ex.date_demande, "date_str": ar_dt(ex.date_demande),
                       "type": "تنفيذ", "title": getattr(ex, "get_type_execution_display", lambda: (ex.type_execution or ""))(),
                       "meta": getattr(ex, "get_statut_display", lambda: (ex.statut or ""))(), "badge": "success"})
    # مرفقات
    for p in PieceJointe.objects.filter(affaire=affaire).order_by("date_ajout"):
        events.append({"date": p.date_ajout, "date_str": ar_dt(p.date_ajout),
                       "type": "مرفق", "title": p.titre or "",
                       "meta": getattr(p, "get_type_piece_display", lambda: (p.type_piece or ""))(), "badge": "light"})

    events = [ev for ev in events if ev["date"]]
    events.sort(key=lambda x: x["date"])
    return render(request, "affaires/_timeline.html", {"affaire": affaire, "events": events})

class ExpertList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Expert
    template_name = 'avocat/expertise_list.html'
    permission_required = 'cabinet.view_audience'
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class ExpertDetail(SecureBase, DetailView):
    model = Expert
    template_name = 'avocat/expertise_detail.html'
    permission_required = 'cabinet.view_audience'
class ExpertUpdate(SecureBase, UpdateView):
    model = Expert
    form_class = ExpertForm
    permission_required = 'cabinet.change_expertise'
    success_url = reverse_lazy('cabinet:expertise_list')

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
    permission_required = 'cabinet.delete_expertise'
    success_url = reverse_lazy('cabinet:expertise_list')

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
    permission_required = 'cabinet.view_audience'
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class UtilisateurDetail(SecureBase, DetailView):
    model = Utilisateur
    template_name = 'avocat/utilisateur_detail.html'
    permission_required = 'cabinet.view_audience'

class UtilisateurCreate(SecureBase, CreateView):
    model = Utilisateur
    form_class = UtilisateurForm
    permission_required = 'cabinet.add_utilisateur'
    success_url = reverse_lazy('cabinet:utilisateur_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            # Préremplir la dernière decision de l'affaire si dispo
            dec = Decision.objects.filter(affaire_id=int(affaire_id)).order_by('-date_prononce', '-pk').first()
            if dec:
                initial['decision'] = dec
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ التبليغ.')
        if self.htmx():
            return self.success_json('تمّ حفظ التبليغ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة تبليغ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class UtilisateurUpdate(SecureBase, UpdateView):
    model = Utilisateur
    form_class = UtilisateurForm
    permission_required = 'cabinet.change_utilisateur'
    success_url = reverse_lazy('cabinet:utilisateur_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث التبليغ.')
        if self.htmx():
            return self.success_json('تمّ تحديث التبليغ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل تبليغ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class UtilisateurDelete(SecureBase, DeleteView):
    model = Utilisateur
    permission_required = 'cabinet.delete_utilisateur'
    success_url = reverse_lazy('cabinet:utilisateur_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف التبليغ.')
        if self.htmx():
            return self.success_json('تمّ حذف التبليغ.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class RecetteList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Recette
    template_name = 'avocat/recette_list.html'
    permission_required = 'cabinet.view_audience'
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class RecetteDetail(SecureBase, DetailView):
    model = Recette
    template_name = 'avocat/recette_detail.html'
    permission_required = 'cabinet.view_audience'

class RecetteCreate(SecureBase, CreateView):
    model = Recette
    form_class = RecetteForm
    permission_required = 'cabinet.add_recette'
    success_url = reverse_lazy('cabinet:recette_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            # Préremplir la dernière decision de l'affaire si dispo
            dec = Decision.objects.filter(affaire_id=int(affaire_id)).order_by('-date_prononce', '-pk').first()
            if dec:
                initial['decision'] = dec
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ التبليغ.')
        if self.htmx():
            return self.success_json('تمّ حفظ التبليغ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة تبليغ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class RecetteUpdate(SecureBase, UpdateView):
    model = Recette
    form_class = RecetteForm
    permission_required = 'cabinet.change_recette'
    success_url = reverse_lazy('cabinet:recette_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث التبليغ.')
        if self.htmx():
            return self.success_json('تمّ تحديث التبليغ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل تبليغ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class RecetteDelete(SecureBase, DeleteView):
    model = Recette
    permission_required = 'cabinet.delete_recette'
    success_url = reverse_lazy('cabinet:recette_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف التبليغ.')
        if self.htmx():
            return self.success_json('تمّ حذف التبليغ.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class DepenseList(SecureBase, NoPostOnReadOnlyMixin, SearchListMixin, HTMXPartialListMixin, ListView):
    model = Depense
    template_name = 'avocat/depense_list.html'
    permission_required = 'cabinet.view_audience'
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
        return qs.select_related("type", "idTribunalParent").order_by("id")


class DepenseDetail(SecureBase, DetailView):
    model = Depense
    template_name = 'avocat/depense_detail.html'
    permission_required = 'cabinet.view_audience'

class DepenseCreate(SecureBase, CreateView):
    model = Depense
    form_class = DepenseForm
    permission_required = 'cabinet.add_depense'
    success_url = reverse_lazy('cabinet:depense_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            # Préremplir la dernière decision de l'affaire si dispo
            dec = Decision.objects.filter(affaire_id=int(affaire_id)).order_by('-date_prononce', '-pk').first()
            if dec:
                initial['decision'] = dec
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ التبليغ.')
        if self.htmx():
            return self.success_json('تمّ حفظ التبليغ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة تبليغ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class DepenseUpdate(SecureBase, UpdateView):
    model = Depense
    form_class = DepenseForm
    permission_required = 'cabinet.change_depense'
    success_url = reverse_lazy('cabinet:depense_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث التبليغ.')
        if self.htmx():
            return self.success_json('تمّ تحديث التبليغ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل تبليغ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class DepenseDelete(SecureBase, DeleteView):
    model = Depense
    permission_required = 'cabinet.delete_depense'
    success_url = reverse_lazy('cabinet:depense_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف التبليغ.')
        if self.htmx():
            return self.success_json('تمّ حذف التبليغ.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)



# -------------------------------------------------------------
# Partial HTMX pour Timeline (déjà référencé par urls.py)
# -------------------------------------------------------------
from django.contrib.auth.decorators import login_required, permission_required

def ar_dt(dt):
    if not dt:
        return ""
    # respectera LOCALE + formats ar si configurés
    return date_format(dt, "DATETIME_FORMAT", use_l10n=True)

#-- Créations imbriquées par Affaire ----
class AudienceCreateForAffaire(SecureBase, HTMXModalFormMixin, CreateView):
    model = Audience            # جلسة
    form_class = AudienceForm
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
    template_name = "cabinet/execution_form.html"
    permission_required = "cabinet.add_execution"
    success_message = "تم فتح ملف التنفيذ."
