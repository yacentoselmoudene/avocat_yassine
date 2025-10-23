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
from .views_mixins import ModalCreateView, ModalUpdateView, NoPostOnReadOnlyMixin
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

from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte, Expert
)

from .forms import (
    JuridictionForm, AvocatForm, AffaireForm, PartieForm, AffairePartieForm, AffaireAvocatForm,
    AudienceForm, MesureForm, ExpertiseForm, DecisionForm, NotificationForm, VoieDeRecoursForm,
    ExecutionForm, DepenseForm, RecetteForm, PieceJointeForm, UtilisateurForm, TacheForm, AlerteForm, ExpertForm
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

class DashboardView(SecureBase, TemplateView):
    """الصفحة الرئيسية بعد تسجيل الدخول - لوحة التحكم"""
    template_name = "dashboard/index.html"
    permission_required = "cabinet.view_affaire"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        upcoming_limit = today + timedelta(days=14)

        # إحصاءات عامة
        ctx["stats"] = {
            "affaires_total": Affaire.objects.count(),
            "affaires_ouvertes": Affaire.objects.filter(statut_affaire__libelle__in=["Ouverte", "EnCours", "جارية"]).count()
                if hasattr(Affaire, "statut_affaire") else Affaire.objects.count(),
            "audiences_a_venir": Audience.objects.filter(date_audience__range=(today, upcoming_limit)).count(),
        }

        # جلسات قادمة
        ctx["next_audiences"] = (
            Audience.objects
            .select_related("affaire")
            .filter(date_audience__gte=today)
            .order_by("date_audience")[:6]
        )

        # آخر القضايا المضافة
        ctx["recent_affaires"] = (
            Affaire.objects.select_related("juridiction")
            .order_by("-date_ouverture")[:6]
        )

        # ملخص مالي للشهر الحالي
        try:
            ctx["finance"] = {
                "depenses_mois": Depense.objects.filter(
                    date_depense__month=today.month,
                    date_depense__year=today.year
                ).aggregate(Sum("montant"))["montant__sum"] or 0,
                "recettes_mois": Recette.objects.filter(
                    date_recette__month=today.month,
                    date_recette__year=today.year
                ).aggregate(Sum("montant"))["montant__sum"] or 0,
            }
        except Exception:
            ctx["finance"] = {"depenses_mois": 0, "recettes_mois": 0}

        return ctx

# =============================
# AFFAIRES
# =============================
class AffaireList(SecureBase, ListView):
    model = Affaire
    template_name = 'avocat/affaire_list.html'
    permission_required = 'cabinet.view_affaire'
    paginate_by = 20

class AffaireDetail(SecureBase, NoPostOnReadOnlyMixin, DetailView):
    model = Affaire
    template_name = "avocat/affaire_detail.html"
    permission_required = "cabinet.view_affaire"
    post_redirect_name = "cabinet:affaire_create"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lock_predecision"] = not self.object.has_decision()  # True => pas de decision
        ctx["lock_postdecision"] = self.object.has_decision()  # True => décision présente
        return ctx

class AffaireDelete(SecureBase, DeleteView):
    model = Affaire
    template_name = 'avocat/affaire_confirm_delete.html'
    success_url = reverse_lazy('cabinet:affaire_list')
    permission_required = 'cabinet.delete_affaire'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('HX-Request'):
            return self.success_json('تم حذف القضية.', redirect=str(self.success_url))
        messages.success(request, 'تم حذف القضية.')
        return super().delete(request, *args, **kwargs)

# =============================
# JURIDICTIONS
# =============================

class JuridictionList(SecureBase, NoPostOnReadOnlyMixin, ListView):
    model = Juridiction
    template_name = "avocat/juridiction_list.html"
    permission_required = "cabinet.view_juridiction"
    post_redirect_name = "cabinet:juridiction_create"


class JuridictionDetail(SecureBase, DetailView):
    model = Juridiction
    template_name = 'avocat/juridiction_detail.html'
    permission_required = 'cabinet.view_juridiction'

class JuridictionDelete(SecureBase, DeleteView):
    model = Juridiction
    template_name = 'avocat/juridiction_confirm_delete.html'
    success_url = reverse_lazy('cabinet:juridiction_list')
    permission_required = 'cabinet.delete_juridiction'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('HX-Request'):
            return self.success_json('تم حذف المحكمة.', redirect=str(self.success_url))
        messages.success(request, 'تم حذف المحكمة.')
        return super().delete(request, *args, **kwargs)

# =============================
# AVOCATS
# =============================
class AvocatList(SecureBase, ListView):
    model = Avocat
    template_name = 'avocat/avocat_list.html'
    permission_required = 'cabinet.view_avocat'

class AvocatDetail(SecureBase, DetailView):
    model = Avocat
    template_name = 'avocat/avocat_detail.html'
    permission_required = 'cabinet.view_avocat'

class AvocatCreate(SecureBase, CreateView):
    model = Avocat
    form_class = AvocatForm
    template_name = "avocat/avocat_form.html"
    permission_required = "cabinet.add_avocat"

    def form_valid(self, form):
        print("Form is valid, saving avocat...")
        print("for details :", form.cleaned_data)
        self.object = form.save()

        if self.request.headers.get('HX-Request'):
            return self.success_json(
                "تم إضافة المحامي.",
                refreshTarget="#timeline",
                refreshUrl=reverse_lazy("cabinet:avocat_detail", args=[self.object.pk]),
                # يمكنك أيضًا إرسال html بدلاً من message إن كان الـJS ينتظره:
                # html=f"<div>تم إضافة المحامي: {self.object}</div>"
            )

        messages.success(self.request, "تم إضافة المحامي.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cabinet:avocat_detail", args=[self.object.pk])
"""
class AvocatCreate(SecureBase, CreateView):
    model = Avocat
    form_class = AvocatForm
    template_name = 'avocat/avocat_form.html'
    permission_required = 'cabinet.add_avocat'


    def form_valid(self, form):
        print("Form is valid, saving avocat...")
        print("for details :", form.cleaned_data)
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم إضافة المحامي.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:avocat_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم إضافة المحامي.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:avocat_detail', args=[self.object.pk])
"""
class AvocatUpdate(SecureBase, UpdateView):
    model = Avocat
    form_class = AvocatForm
    template_name = 'avocat/avocat_form.html'
    permission_required = 'cabinet.change_avocat'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم تعديل بيانات المحامي.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:avocat_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم تعديل بيانات المحامي.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:avocat_detail', args=[self.object.pk])

class AvocatDelete(SecureBase, DeleteView):
    model = Avocat
    template_name = 'avocat/avocat_confirm_delete.html'
    success_url = reverse_lazy('cabinet:avocat_list')
    permission_required = 'cabinet.delete_avocat'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('HX-Request'):
            return self.success_json('تم حذف المحامي.', redirect=str(self.success_url))
        messages.success(request, 'تم حذف المحامي.')
        return super().delete(request, *args, **kwargs)

# =============================
# AUDIENCES
# ============================
# -------------------------------------------------------------
# Exemples complets: Audience / Mesure / Expertise / Decision / Notification
# Appliquer le même motif aux autres models de workflow
# -------------------------------------------------------------
class AudienceList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/audience_list.html'
    permission_required = 'cabinet.view_audience'

class AudienceDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/audience_detail.html'
    permission_required = 'cabinet.view_audience'
class AudienceCreate(SecureBase, CreateView):
    model = Audience
    form_class = AudienceForm
    permission_required = 'cabinet.add_audience'
    success_url = reverse_lazy('cabinet:audience_list')

    def get_initial(self):
        initial = super().get_initial()
        # Pré-remplir l'affaire depuis ?affaire=ID si fourni
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            initial['affaire'] = get_object_or_404(Affaire, pk=int(affaire_id))
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ الجلسة.')
        if self.htmx():
            return self.success_json('تمّ حفظ الجلسة.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة جلسة', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AudienceUpdate(SecureBase, UpdateView):
    model = Audience
    form_class = AudienceForm
    permission_required = 'cabinet.change_audience'
    success_url = reverse_lazy('cabinet:audience_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث الجلسة.')
        if self.htmx():
            return self.success_json('تمّ تحديث الجلسة.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل جلسة', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AudienceDelete(SecureBase, DeleteView):
    model = Audience
    permission_required = 'cabinet.delete_audience'
    success_url = reverse_lazy('cabinet:audience_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف الجلسة.')
        if self.htmx():
            return self.success_json('تمّ حذف الجلسة.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class MesureList(SecureBase, ListView):
    model = Mesure
    template_name = 'avocat/mesure_list.html'
    permission_required = 'cabinet.view_audience'

class MesureDetail(SecureBase, DetailView):
    model = Mesure
    template_name = 'avocat/mesure_detail.html'
    permission_required = 'cabinet.view_audience'

class MesureCreate(SecureBase, CreateView):
    model = Mesure
    form_class = MesureForm
    permission_required = 'cabinet.add_mesure'
    success_url = reverse_lazy('cabinet:mesure_list')

    def get_initial(self):
        initial = super().get_initial()
        # si ?affaire=X passé, préselectionner audience la plus récente de l'affaire
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            aud = Audience.objects.filter(affaire_id=int(affaire_id)).order_by('-date_audience', '-pk').first()
            if aud:
                initial['audience'] = aud
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ الإجراء.')
        if self.htmx():
            return self.success_json('تمّ حفظ الإجراء.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة إجراء', 'action': request.path})
        return super().get(request, *args, **kwargs)

class MesureUpdate(SecureBase, UpdateView):
    model = Mesure
    form_class = MesureForm
    permission_required = 'cabinet.change_mesure'
    success_url = reverse_lazy('cabinet:mesure_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث الإجراء.')
        if self.htmx():
            return self.success_json('تمّ تحديث الإجراء.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل إجراء', 'action': request.path})
        return super().get(request, *args, **kwargs)

class MesureDelete(SecureBase, DeleteView):
    model = Mesure
    permission_required = 'cabinet.delete_mesure'
    success_url = reverse_lazy('cabinet:mesure_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف الإجراء.')
        if self.htmx():
            return self.success_json('تمّ حذف الإجراء.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)

class ExpertList(SecureBase, ListView):
    model = Expert
    template_name = 'avocat/expertise_list.html'
    permission_required = 'cabinet.view_audience'

class ExpertDetail(SecureBase, DetailView):
    model = Expert
    template_name = 'avocat/expertise_detail.html'
    permission_required = 'cabinet.view_audience'
class ExpertCreate(SecureBase, ModalCreateView):
    model = Expert  # crée un petit modèle Expert(nom, spécialité)
    form_class = ExpertForm
    success_message = "تم إضافة الخبير."

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request"):
            select_id = self.request.GET.get("select_id") or self.request.POST.get("select_id")
            # renvoie un script pour injecter l’option + la sélectionner
            html = f"""
            <script>
              (function(){{
                 var sel = document.getElementById("{select_id}");
                 if(sel){{
                   var opt = new Option("{self.object.nom}", "{self.object.pk}", true, true);
                   sel.add(opt);
                   $(sel).trigger('change'); // notifie Select2
                 }}
                 bootstrap.Modal.getInstance(document.getElementById('mainModal')).hide();
              }})();
            </script>
          """
            return self.success_json(html=html)
        return super().form_valid(form)

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


class ExpertiseList(SecureBase, ListView):
    model = Expertise
    template_name = 'avocat/expert_list.html'
    permission_required = 'cabinet.view_audience'

class ExpertiseDetail(SecureBase, DetailView):
    model = Expertise
    template_name = 'avocat/expert_detail.html'
    permission_required = 'cabinet.view_audience'


class ExpertiseCreate(SecureBase, CreateView):
    model = Expertise
    form_class = ExpertiseForm
    permission_required = 'cabinet.add_expert'
    success_url = reverse_lazy('cabinet:expert_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            initial['affaire'] = get_object_or_404(Affaire, pk=int(affaire_id))
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ الخبرة.')
        if self.htmx():
            return self.success_json('تمّ حفظ الخبرة.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة خبرة', 'action': request.path})
        return super().get(request, *args, **kwargs)

class ExpertiseUpdate(SecureBase, UpdateView):
    model = Expertise
    form_class = ExpertiseForm
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

class ExpertiseDelete(SecureBase, DeleteView):
    model = Expertise
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


class DecisionList(SecureBase, ListView):
    model = Decision
    template_name = 'avocat/decision_list.html'
    permission_required = 'cabinet.view_audience'

class DecisionDetail(SecureBase, DetailView):
    model = Decision
    template_name = 'avocat/decision_detail.html'
    permission_required = 'cabinet.view_audience'

class DecisionCreate(SecureBase, CreateView):
    model = Decision
    form_class = DecisionForm
    permission_required = 'cabinet.add_decision'
    success_url = reverse_lazy('cabinet:decision_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            initial['affaire'] = get_object_or_404(Affaire, pk=int(affaire_id))
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ الحكم.')
        if self.htmx():
            return self.success_json('تمّ حفظ الحكم.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة حكم', 'action': request.path})
        return super().get(request, *args, **kwargs)

class DecisionUpdate(SecureBase, UpdateView):
    model = Decision
    form_class = DecisionForm
    permission_required = 'cabinet.change_decision'
    success_url = reverse_lazy('cabinet:decision_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث الحكم.')
        if self.htmx():
            return self.success_json('تمّ تحديث الحكم.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل حكم', 'action': request.path})
        return super().get(request, *args, **kwargs)

class DecisionDelete(SecureBase, DeleteView):
    model = Decision
    permission_required = 'cabinet.delete_decision'
    success_url = reverse_lazy('cabinet:decision_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف الحكم.')
        if self.htmx():
            return self.success_json('تمّ حذف الحكم.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class NotificationList(SecureBase, ListView):
    model = Notification
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class NotificationDetail(SecureBase, DetailView):
    model = Notification
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class NotificationCreate(SecureBase, CreateView):
    model = Notification
    form_class = NotificationForm
    permission_required = 'cabinet.add_notification'
    success_url = reverse_lazy('cabinet:notification_list')

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

class NotificationUpdate(SecureBase, UpdateView):
    model = Notification
    form_class = NotificationForm
    permission_required = 'cabinet.change_notification'
    success_url = reverse_lazy('cabinet:notification_list')

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

class NotificationDelete(SecureBase, DeleteView):
    model = Notification
    permission_required = 'cabinet.delete_notification'
    success_url = reverse_lazy('cabinet:notification_list')

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


class AlerteList(SecureBase, ListView):
    model = Alerte
    template_name = 'avocat/alerte_list.html'
    permission_required = 'cabinet.view_audience'

class AlerteDetail(SecureBase, DetailView):
    model = Alerte
    template_name = 'avocat/alerte_detail.html'
    permission_required = 'cabinet.view_audience'

class AlerteCreate(SecureBase, CreateView):
    model = Alerte
    form_class = AlerteForm
    permission_required = 'cabinet.add_alerte'
    success_url = reverse_lazy('cabinet:alerte_list')

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

class AlerteUpdate(SecureBase, UpdateView):
    model = Alerte
    form_class = AlerteForm
    permission_required = 'cabinet.change_alerte'
    success_url = reverse_lazy('cabinet:alerte_list')

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

class AlerteDelete(SecureBase, DeleteView):
    model = Alerte
    permission_required = 'cabinet.delete_alerte'
    success_url = reverse_lazy('cabinet:alerte_list')

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


class TacheList(SecureBase, ListView):
    model = Tache
    template_name = 'avocat/tache_list.html'
    permission_required = 'cabinet.view_audience'

class TacheDetail(SecureBase, DetailView):
    model = Tache
    template_name = 'avocat/tache_detail.html'
    permission_required = 'cabinet.view_audience'

class TacheCreate(SecureBase, CreateView):
    model = Tache
    form_class = TacheForm
    permission_required = 'cabinet.add_tache'
    success_url = reverse_lazy('cabinet:tache_list')

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

class TacheUpdate(SecureBase, UpdateView):
    model = Tache
    form_class = TacheForm
    permission_required = 'cabinet.change_tache'
    success_url = reverse_lazy('cabinet:tache_list')

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

class TacheDelete(SecureBase, DeleteView):
    model = Tache
    permission_required = 'cabinet.delete_tache'
    success_url = reverse_lazy('cabinet:tache_list')

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


class UtilisateurList(SecureBase, ListView):
    model = Utilisateur
    template_name = 'avocat/utilisateur_list.html'
    permission_required = 'cabinet.view_audience'

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


class PieceJointeList(SecureBase, ListView):
    model = PieceJointe
    template_name = 'avocat/piecejointe_list.html'
    permission_required = 'cabinet.view_audience'

class PieceJointeDetail(SecureBase, DetailView):
    model = PieceJointe
    template_name = 'avocat/piecejointe_detail.html'
    permission_required = 'cabinet.view_audience'

class PieceJointeCreate(SecureBase, CreateView):
    model = PieceJointe
    form_class = PieceJointeForm
    permission_required = 'cabinet.add_piecejointe'
    success_url = reverse_lazy('cabinet:piecejointe_list')

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

class PieceJointeUpdate(SecureBase, UpdateView):
    model = PieceJointe
    form_class = PieceJointeForm
    permission_required = 'cabinet.change_piecejointe'
    success_url = reverse_lazy('cabinet:piecejointe_list')

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

class PieceJointeDelete(SecureBase, DeleteView):
    model = PieceJointe
    permission_required = 'cabinet.delete_piecejointe'
    success_url = reverse_lazy('cabinet:piecejointe_list')

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


class RecetteList(SecureBase, ListView):
    model = Recette
    template_name = 'avocat/recette_list.html'
    permission_required = 'cabinet.view_audience'

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


class DepenseList(SecureBase, ListView):
    model = Depense
    template_name = 'avocat/depense_list.html'
    permission_required = 'cabinet.view_audience'

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





class AffaireAvocatList(SecureBase, ListView):
    model = AffaireAvocat
    template_name = 'avocat/affaireavocat_list.html'
    permission_required = 'cabinet.view_audience'

class AffaireAvocatDetail(SecureBase, DetailView):
    model = AffaireAvocat
    template_name = 'avocat/affaireavocat_detail.html'
    permission_required = 'cabinet.view_audience'

class AffaireAvocatCreate(SecureBase, CreateView):
    model = AffaireAvocat
    form_class = AffaireAvocatForm
    permission_required = 'cabinet.add_affaireavocat'
    success_url = reverse_lazy('cabinet:affaireavocat_list')

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

class AffaireAvocatUpdate(SecureBase, UpdateView):
    model = AffaireAvocat
    form_class = AffaireAvocatForm
    permission_required = 'cabinet.change_affaireavocat'
    success_url = reverse_lazy('cabinet:affaireavocat_list')

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

class AffaireAvocatDelete(SecureBase, DeleteView):
    model = AffaireAvocat
    permission_required = 'cabinet.delete_affaireavocat'
    success_url = reverse_lazy('cabinet:affaireavocat_list')

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


class AffairePartieList(SecureBase, ListView):
    model = AffairePartie
    template_name = 'avocat/affairepartie_list.html'
    permission_required = 'cabinet.view_audience'

class AffairePartieDetail(SecureBase, DetailView):
    model = AffairePartie
    template_name = 'avocat/affairepartie_detail.html'
    permission_required = 'cabinet.view_audience'

class AffairePartieCreate(SecureBase, CreateView):
    model = AffairePartie
    form_class = AffairePartieForm
    permission_required = 'cabinet.add_affairepartie'
    success_url = reverse_lazy('cabinet:affairepartie_list')

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

class AffairePartieUpdate(SecureBase, UpdateView):
    model = AffairePartie
    form_class = AffairePartieForm
    permission_required = 'cabinet.change_affairepartie'
    success_url = reverse_lazy('cabinet:affairepartie_list')

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

class AffairePartieDelete(SecureBase, DeleteView):
    model = AffairePartie
    permission_required = 'cabinet.delete_affairepartie'
    success_url = reverse_lazy('cabinet:affairepartie_list')

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


class PartieList(SecureBase, ListView):
    model = Partie
    template_name = 'avocat/partie_list.html'
    permission_required = 'cabinet.view_audience'

class PartieDetail(SecureBase, DetailView):
    model = Partie
    template_name = 'avocat/partie_detail.html'
    permission_required = 'cabinet.view_audience'

class PartieCreate(SecureBase, CreateView):
    model = Partie
    form_class = PartieForm
    permission_required = 'cabinet.add_partie'
    success_url = reverse_lazy('cabinet:partie_list')

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

class PartieUpdate(SecureBase, UpdateView):
    model = Partie
    form_class = PartieForm
    permission_required = 'cabinet.change_partie'
    success_url = reverse_lazy('cabinet:partie_list')

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

class PartieDelete(SecureBase, DeleteView):
    model = Partie
    permission_required = 'cabinet.delete_partie'
    success_url = reverse_lazy('cabinet:partie_list')

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
# VoieDeRecours / Execution — même motif, raccourcis
# -------------------------------------------------------------

class VoieDeRecoursList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/voiederecours_list.html'
    permission_required = 'cabinet.view_audience'

class VoieDeRecoursDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/voiederecours_detail.html'
    permission_required = 'cabinet.view_audience'

class VoieDeRecoursCreate(SecureBase, CreateView):
    model = VoieDeRecours
    form_class = VoieDeRecoursForm
    permission_required = 'cabinet.add_voiederecours'
    success_url = reverse_lazy('cabinet:voiederecours_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            dec = Decision.objects.filter(affaire_id=int(affaire_id)).order_by('-date_prononce', '-pk').first()
            if dec:
                initial['decision'] = dec
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ الطعن.')
        if self.htmx():
            return self.success_json('تمّ حفظ الطعن.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة طريق طعن', 'action': request.path})
        return super().get(request, *args, **kwargs)

class VoieDeRecoursUpdate(SecureBase, UpdateView):
    model = VoieDeRecours
    form_class = VoieDeRecoursForm
    permission_required = 'cabinet.change_voiederecours'
    success_url = reverse_lazy('cabinet:voiederecours_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث الطعن.')
        if self.htmx():
            return self.success_json('تمّ تحديث الطعن.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل طريق طعن', 'action': request.path})
        return super().get(request, *args, **kwargs)

class VoieDeRecoursDelete(SecureBase, DeleteView):
    model = VoieDeRecours
    permission_required = 'cabinet.delete_voiederecours'
    success_url = reverse_lazy('cabinet:voiederecours_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف طريق الطعن.')
        if self.htmx():
            return self.success_json('تمّ حذف طريق الطعن.', affaire_pk)
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal('modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


class ExecutionList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/execution_list.html'
    permission_required = 'cabinet.view_audience'

class ExecutionDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/execution_detail.html'
    permission_required = 'cabinet.view_audience'

class ExecutionCreate(SecureBase, CreateView):
    model = Execution
    form_class = ExecutionForm
    permission_required = 'cabinet.add_execution'
    success_url = reverse_lazy('cabinet:execution_list')

    def get_initial(self):
        initial = super().get_initial()
        affaire_id = self.request.GET.get('affaire')
        if affaire_id and affaire_id.isdigit():
            dec = Decision.objects.filter(affaire_id=int(affaire_id)).order_by('-date_prononce', '-pk').first()
            if dec:
                initial['decision'] = dec
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ حفظ التنفيذ.')
        if self.htmx():
            return self.success_json('تمّ حفظ التنفيذ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class(initial=self.get_initial())
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'إضافة تنفيذ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class ExecutionUpdate(SecureBase, UpdateView):
    model = Execution
    form_class = ExecutionForm
    permission_required = 'cabinet.change_execution'
    success_url = reverse_lazy('cabinet:execution_list')

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'تمّ تحديث التنفيذ.')
        if self.htmx():
            return self.success_json('تمّ تحديث التنفيذ.', _affaire_pk_from_step(self.object))
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal('modals/_form.html', {'form': form, 'title': 'تعديل تنفيذ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class ExecutionDelete(SecureBase, DeleteView):
    model = Execution
    permission_required = 'cabinet.delete_execution'
    success_url = reverse_lazy('cabinet:execution_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        affaire_pk = _affaire_pk_from_step(self.object)
        self.object.delete()
        messages.success(request, 'تمّ حذف التنفيذ.')
        if self.htmx():
            return self.success_json('تمّ حذف التنفيذ.', affaire_pk)
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

def affaire_timeline_partial(request, pk):
    affaire = get_object_or_404(Affaire, pk=pk)
    events = []

    # جلسات
    for a in Audience.objects.filter(affaire=affaire).select_related("affaire").order_by("date_audience"):
        events.append({
            "date": a.date_audience,
            "date_str": ar_dt(a.date_audience),
            "type": "جلسة",
            "title": a.get_type_audience_display(),  # ← LABEL عربي si choices arabes
            "meta": a.resultat or "",
            "badge": "warning",
        })

    # إجراءات
    for m in Mesure.objects.filter(audience__affaire=affaire).select_related("audience").order_by("id"):
        events.append({
            "date": getattr(m, "date_ordonnee", None) or getattr(m, "date", None),
            "date_str": ar_dt(getattr(m, "date_ordonnee", None) or getattr(m, "date", None)),
            "type": "إجراء",
            "title": m.get_type_mesure_display() if hasattr(m, "get_type_mesure_display") else "إجراء",
            "meta": m.get_statut_display() if hasattr(m, "get_statut_display") else (m.statut or ""),
            "badge": "primary",
        })

    # خبرات
    for e in Expertise.objects.filter(affaire=affaire).order_by("date_ordonnee", "date_depot"):
        if e.date_ordonnee:
            events.append({
                "date": e.date_ordonnee, "date_str": ar_dt(e.date_ordonnee),
                "type": "خبرة", "title": f"أمرت: {e.expert_nom or ''}",
                "meta": "خبرة مضادة" if getattr(e, "contre_expertise", False) else "",
                "badge": "dark",
            })
        if e.date_depot:
            events.append({
                "date": e.date_depot, "date_str": ar_dt(e.date_depot),
                "type": "خبرة", "title": "إيداع الخبرة",
                "meta": e.expert_nom or "", "badge": "dark",
            })

    # أحكام
    for d in Decision.objects.filter(affaire=affaire).order_by("date_prononce"):
        events.append({
            "date": d.date_prononce, "date_str": ar_dt(d.date_prononce),
            "type": "حكم",
            "title": f"حكم رقم {d.numero_decision or ''}",
            "meta": "قابل للطعن" if getattr(d, "susceptible_recours", False) else "غير قابل للطعن",
            "badge": "secondary",
        })

    # تبليغات
    for n in Notification.objects.filter(decision__affaire=affaire).select_related("decision").order_by("date_signification"):
        events.append({
            "date": n.date_signification, "date_str": ar_dt(n.date_signification),
            "type": "تبليغ",
            "title": f"طلب {n.demande_numero or ''}",
            "meta": f"مفوض: {n.huissier_nom or ''}",
            "badge": "info",
        })

    # طرق الطعن
    for r in VoieDeRecours.objects.filter(decision__affaire=affaire).select_related("decision").order_by("date_depot"):
        events.append({
            "date": r.date_depot, "date_str": ar_dt(r.date_depot),
            "type": "طعن",
            "title": r.get_type_recours_display() if hasattr(r, "get_type_recours_display") else (r.type_recours or ""),
            "meta": r.get_statut_display() if hasattr(r, "get_statut_display") else (r.statut or ""),
            "badge": "success",
        })

    # تنفيذ
    for ex in Execution.objects.filter(decision__affaire=affaire).select_related("decision").order_by("date_demande"):
        events.append({
            "date": ex.date_demande, "date_str": ar_dt(ex.date_demande),
            "type": "تنفيذ",
            "title": ex.get_type_execution_display() if hasattr(ex, "get_type_execution_display") else (ex.type_execution or ""),
            "meta": ex.get_statut_display() if hasattr(ex, "get_statut_display") else (ex.statut or ""),
            "badge": "success",
        })

    # مرفقات
    for p in PieceJointe.objects.filter(affaire=affaire).order_by("date_ajout"):
        events.append({
            "date": p.date_ajout, "date_str": ar_dt(p.date_ajout),
            "type": "مرفق",
            "title": p.titre or "",
            "meta": p.get_type_piece_display() if hasattr(p, "get_type_piece_display") else (p.type_piece or ""),
            "badge": "light",
        })

    # فرز حسب التاريخ
    print(events)
    events = [ev for ev in events if ev["date"]]
    events.sort(key=lambda x: x["date"])  # croissant

    return render(request, "affaires/_timeline.html", {"affaire": affaire, "events": events})

# ---- Créations imbriquées par Affaire ----
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



# ---- Juridiction ----************************
class JuridictionCreate(SecureBase, ModalCreateView):
    model = Juridiction
    form_class = JuridictionForm
    permission_required = "cabinet.add_juridiction"
    success_message = "تم إنشاء المحكمة."
    page_template = "cabinet/juridiction_form.html"  # si tu veux aussi un rendu page complète
    def get_success_url(self):
        return self.request.GET.get("next") or reverse_lazy("cabinet:juridiction_list")

class JuridictionUpdate(SecureBase, ModalUpdateView):
    model = Juridiction
    form_class = JuridictionForm
    permission_required = "cabinet.change_juridiction"
    success_message = "تم تحديث المحكمة."
    page_template = "cabinet/juridiction_form.html"
    def get_success_url(self):
        return reverse_lazy("cabinet:juridiction_detail", args=[self.object.pk])

# ---- Affaire ----
class AffaireCreate(SecureBase, ModalCreateView):
    model = Affaire
    form_class = AffaireForm
    permission_required = "cabinet.add_affaire"
    success_message = "تم إنشاء القضية."
    page_template = "cabinet/affaire_form.html"
    def get_success_url(self):
        return reverse_lazy("cabinet:affaire_detail", args=[self.object.pk])

class AffaireUpdate(SecureBase, ModalUpdateView):
    model = Affaire
    form_class = AffaireForm
    permission_required = "cabinet.change_affaire"
    success_message = "تم تحديث القضية."
    page_template = "cabinet/affaire_form.html"
    def get_success_url(self):
        return reverse_lazy("cabinet:affaire_detail", args=[self.object.pk])