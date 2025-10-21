# =============================================================
# FILE: views.py (extrait mis à jour)
# - Ajoute des réponses JSON uniformes (ok, html, refreshTarget, refreshUrl)
# - Cible par défaut: rafraîchir #timeline d'une Affaire après Create/Update
# - Gère HTMX modals pour Create/Update/Delete
# - Sécurisé: LoginRequired + Permissions + CSRF cookie
# =============================================================
from __future__ import annotations

from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte
)

from .forms import (
    JuridictionForm, AvocatForm, AffaireForm, PartieForm, AffairePartieForm, AffaireAvocatForm,
    AudienceForm, MesureForm, ExpertiseForm, DecisionForm, NotificationForm, VoieDeRecoursForm,
    ExecutionForm, DepenseForm, RecetteForm, PieceJointeForm, UtilisateurForm, TacheForm, AlerteForm
)

# -------------------------------------------------------------
# Utilitaires communs
# -------------------------------------------------------------
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
            "affaires_ouvertes": Affaire.objects.filter(statut_affaire__in=["Ouverte", "EnCours", "جارية"]).count()
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

class AffaireDetail(SecureBase, DetailView):
    model = Affaire
    template_name = 'avocat/affaire_detail.html'
    permission_required = 'cabinet.view_affaire'

class AffaireCreate(SecureBase, CreateView):
    model = Affaire
    form_class = AffaireForm
    template_name = 'avocat/affaire_form.html'
    permission_required = 'cabinet.add_affaire'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم إنشاء القضية بنجاح.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:affaire_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم إنشاء القضية بنجاح.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:affaire_detail', args=[self.object.pk])

class AffaireUpdate(SecureBase, UpdateView):
    model = Affaire
    form_class = AffaireForm
    template_name = 'avocat/affaire_form.html'
    permission_required = 'cabinet.change_affaire'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم تحديث القضية بنجاح.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:affaire_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم تحديث القضية بنجاح.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:affaire_detail', args=[self.object.pk])

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
class JuridictionList(SecureBase, ListView):
    model = Juridiction
    template_name = 'avocat/juridiction_list.html'
    permission_required = 'cabinet.view_juridiction'

class JuridictionDetail(SecureBase, DetailView):
    model = Juridiction
    template_name = 'avocat/juridiction_detail.html'
    permission_required = 'cabinet.view_juridiction'

class JuridictionCreate(SecureBase, CreateView):
    model = Juridiction
    form_class = JuridictionForm
    template_name = 'avocat/juridiction_form.html'
    permission_required = 'cabinet.add_juridiction'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم إنشاء المحكمة.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:juridiction_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم إنشاء المحكمة.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:juridiction_detail', args=[self.object.pk])

class JuridictionUpdate(SecureBase, UpdateView):
    model = Juridiction
    form_class = JuridictionForm
    template_name = 'avocat/juridiction_form.html'
    permission_required = 'cabinet.change_juridiction'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم تحديث المحكمة.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:juridiction_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم تحديث المحكمة.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:juridiction_detail', args=[self.object.pk])

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
    template_name = 'avocat/avocat_form.html'
    permission_required = 'cabinet.add_avocat'

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request'):
            return self.success_json('تم إضافة المحامي.', refreshTarget='#timeline', refreshUrl=reverse_lazy('cabinet:avocat_detail', args=[self.object.pk]))
        messages.success(self.request, 'تم إضافة المحامي.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('cabinet:avocat_detail', args=[self.object.pk])

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
    model = Audience
    template_name = 'avocat/mesure_list.html'
    permission_required = 'cabinet.view_audience'

class MesureDetail(SecureBase, DetailView):
    model = Audience
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


class ExpertiseList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/expertise_list.html'
    permission_required = 'cabinet.view_audience'

class ExpertiseDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/expertise_detail.html'
    permission_required = 'cabinet.view_audience'

class ExpertiseCreate(SecureBase, CreateView):
    model = Expertise
    form_class = ExpertiseForm
    permission_required = 'cabinet.add_expertise'
    success_url = reverse_lazy('cabinet:expertise_list')

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

class ExpertiseDelete(SecureBase, DeleteView):
    model = Expertise
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


class DecisionList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/decision_list.html'
    permission_required = 'cabinet.view_audience'

class DecisionDetail(SecureBase, DetailView):
    model = Audience
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
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class NotificationDetail(SecureBase, DetailView):
    model = Audience
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
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class AlerteDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class AlerteCreate(SecureBase, CreateView):
    model = Alerte
    form_class = AlerteForm
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

class AlerteUpdate(SecureBase, UpdateView):
    model = Alerte
    form_class = AlerteForm
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

class AlerteDelete(SecureBase, DeleteView):
    model = Alerte
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


class TacheList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class TacheDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class TacheCreate(SecureBase, CreateView):
    model = Tache
    form_class = TacheForm
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

class TacheUpdate(SecureBase, UpdateView):
    model = Tache
    form_class = TacheForm
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

class TacheDelete(SecureBase, DeleteView):
    model = Tache
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


class UtilisateurList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class UtilisateurDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class UtilisateurCreate(SecureBase, CreateView):
    model = Utilisateur
    form_class = UtilisateurForm
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

class UtilisateurUpdate(SecureBase, UpdateView):
    model = Utilisateur
    form_class = UtilisateurForm
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

class UtilisateurDelete(SecureBase, DeleteView):
    model = Utilisateur
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


class PieceJointeList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class PieceJointeDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class PieceJointeCreate(SecureBase, CreateView):
    model = PieceJointe
    form_class = PieceJointeForm
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

class PieceJointeUpdate(SecureBase, UpdateView):
    model = PieceJointe
    form_class = PieceJointeForm
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

class PieceJointeDelete(SecureBase, DeleteView):
    model = PieceJointe
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


class RecetteList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class RecetteDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class RecetteCreate(SecureBase, CreateView):
    model = Recette
    form_class = RecetteForm
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

class RecetteUpdate(SecureBase, UpdateView):
    model = Recette
    form_class = RecetteForm
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

class RecetteDelete(SecureBase, DeleteView):
    model = Recette
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


class DepenseList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class DepenseDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class DepenseCreate(SecureBase, CreateView):
    model = Depense
    form_class = DepenseForm
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

class DepenseUpdate(SecureBase, UpdateView):
    model = Depense
    form_class = DepenseForm
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

class DepenseDelete(SecureBase, DeleteView):
    model = Depense
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





class AffaireAvocatList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class AffaireAvocatDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class AffaireAvocatCreate(SecureBase, CreateView):
    model = AffaireAvocat
    form_class = AffaireAvocatForm
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

class AffaireAvocatUpdate(SecureBase, UpdateView):
    model = AffaireAvocat
    form_class = AffaireAvocatForm
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

class AffaireAvocatDelete(SecureBase, DeleteView):
    model = AffaireAvocat
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


class AffairePartieList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class AffairePartieDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class AffairePartieCreate(SecureBase, CreateView):
    model = AffairePartie
    form_class = AffairePartieForm
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

class AffairePartieUpdate(SecureBase, UpdateView):
    model = AffairePartie
    form_class = AffairePartieForm
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

class AffairePartieDelete(SecureBase, DeleteView):
    model = AffairePartie
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


class PartieList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class PartieDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
    permission_required = 'cabinet.view_audience'

class PartieCreate(SecureBase, CreateView):
    model = Partie
    form_class = PartieForm
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

class PartieUpdate(SecureBase, UpdateView):
    model = Partie
    form_class = PartieForm
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

class PartieDelete(SecureBase, DeleteView):
    model = Partie
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


# -------------------------------------------------------------
# VoieDeRecours / Execution — même motif, raccourcis
# -------------------------------------------------------------

class VoieDeRecoursList(SecureBase, ListView):
    model = Audience
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class VoieDeRecoursDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
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
    template_name = 'avocat/notification_list.html'
    permission_required = 'cabinet.view_audience'

class ExecutionDetail(SecureBase, DetailView):
    model = Audience
    template_name = 'avocat/notification_detail.html'
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

@login_required
@permission_required('cabinet.view_affaire', raise_exception=True)
def affaire_timeline_partial(request: HttpRequest, pk: int):
    affaire = get_object_or_404(Affaire, pk=pk)
    ctx = {
        'object': affaire,
        'audiences': Audience.objects.filter(affaire=affaire).order_by('date_audience'),
        'mesures': Mesure.objects.filter(audience__affaire=affaire).order_by('pk'),
        'expertises': Expertise.objects.filter(affaire=affaire).order_by('date_ordonnee'),
        'decisions': Decision.objects.filter(affaire=affaire).order_by('date_prononce'),
        'notifications': Notification.objects.filter(decision__affaire=affaire).order_by('date_signification'),
        'recours': VoieDeRecours.objects.filter(decision__affaire=affaire).order_by('date_depot'),
        'executions': Execution.objects.filter(decision__affaire=affaire).order_by('date_demande'),
    }
    return render(request, 'affaires/_timeline.html', ctx)
