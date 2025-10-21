# =============================================================
# FILE: views.py
# Objectif:
#  - Sécurité côté serveur maximale raisonnable (Login + Permissions)
#  - UX performante: Toggle Table/Cards, recherche, pagination
#  - Popups (modals) pour créer/mettre à jour/supprimer via HTMX
#  - Réponses partielles si HX-Request (htmx), sinon pages complètes
#  - Querysets optimisées (select_related/prefetch_related)
# =============================================================
from __future__ import annotations

from typing import Any, Dict, Optional

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)

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
# Mixins de sécurité/UX réutilisables
# -------------------------------------------------------------
class SecureBase(LoginRequiredMixin, PermissionRequiredMixin):
    """Mix-in de base: nécessite connexion + permission par vue.
    - Définit pagination, ordre par défaut
    - Assure présence du cookie CSRF (utile pour HTMX POST)
    """
    permission_required: str | tuple[str, ...] = ()
    raise_exception = True  # 403 au lieu de rediriger
    paginate_by = 20
    ordering = '-pk'

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)

    # Recherche simple sécurisée (q=...)
    search_fields: tuple[str, ...] = ()

    def filter_by_search(self, qs):
        q = (self.request.GET.get('q') or '').strip()
        if not q or not self.search_fields:
            return qs
        cond = Q()
        for f in self.search_fields:
            cond |= Q(**{f"{f}__icontains": q})
        return qs.filter(cond)

    # Gestion du mode d'affichage (toggle): 'table' ou 'cards'
    def get_view_mode(self) -> str:
        mode = self.request.GET.get('view')
        if mode in {'table', 'cards'}:
            self.request.session['list_view_mode'] = mode
        return self.request.session.get('list_view_mode', 'table')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['view_mode'] = self.get_view_mode()
        ctx['query'] = (self.request.GET.get('q') or '').strip()
        return ctx

    # Réponses partielles si HTMX pour modals
    def render_modal(self, request: HttpRequest, template: str, context: Dict[str, Any]) -> HttpResponse:
        html = render_to_string(template, context=context, request=request)
        return HttpResponse(html)

    def htmx(self) -> bool:
        return self.request.headers.get('HX-Request', '').lower() == 'true'


class OptimizedAffaireQueryMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if isinstance(self, ListView):
            qs = qs.select_related('juridiction', 'avocat_responsable')
        return qs


# -------------------------------------------------------------
# VUES: Juridiction (exemple complet avec toggle + htmx modals)
# -------------------------------------------------------------
class JuridictionList(SecureBase, ListView):
    model = Juridiction
    permission_required = 'cabinet.view_juridiction'
    search_fields = ('nom', 'ville')

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self.filter_by_search(qs)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'المحاكم'
        ctx['create_url'] = reverse('cabinet:juridiction_create')
        return ctx


class JuridictionDetail(SecureBase, DetailView):
    model = Juridiction
    permission_required = 'cabinet.view_juridiction'


class JuridictionCreate(SecureBase, CreateView):
    model = Juridiction
    form_class = JuridictionForm
    permission_required = 'cabinet.add_juridiction'
    success_url = reverse_lazy('cabinet:juridiction_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ الحفظ بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحفظ بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        # Si HTMX: renvoyer uniquement le corps du formulaire للمودال
        if self.htmx():
            form = self.form_class()
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'إضافة جهة قضائية', 'action': request.path})
        return super().get(request, *args, **kwargs)


class JuridictionUpdate(SecureBase, UpdateView):
    model = Juridiction
    form_class = JuridictionForm
    permission_required = 'cabinet.change_juridiction'
    success_url = reverse_lazy('cabinet:juridiction_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ التحديث بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ التحديث بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'تعديل جهة قضائية', 'action': request.path})
        return super().get(request, *args, **kwargs)


class JuridictionDelete(SecureBase, DeleteView):
    model = Juridiction
    permission_required = 'cabinet.delete_juridiction'
    success_url = reverse_lazy('cabinet:juridiction_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, 'تمّ الحذف.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحذف.'}, request=request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal(request, 'modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


# -------------------------------------------------------------
# Gabarit générique pour le reste des modèles (CRUD sécurisés)
#  - Pour réduire la taille, on applique le même pattern
#  - Optimisations spécifiques sur Affaire (select_related)
# -------------------------------------------------------------
class AvocatList(SecureBase, ListView):
    model = Avocat
    permission_required = 'cabinet.view_avocat'
    search_fields = ('nom', 'barreau', 'email', 'telephone')

    def get_queryset(self):
        return self.filter_by_search(super().get_queryset())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'المحامون'
        ctx['create_url'] = reverse('cabinet:avocat_create')
        return ctx

class AvocatDetail(SecureBase, DetailView):
    model = Avocat
    permission_required = 'cabinet.view_avocat'

class AvocatCreate(SecureBase, CreateView):
    model = Avocat
    form_class = AvocatForm
    permission_required = 'cabinet.add_avocat'
    success_url = reverse_lazy('cabinet:avocat_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ الحفظ بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحفظ بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class()
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'إضافة محامٍ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AvocatUpdate(SecureBase, UpdateView):
    model = Avocat
    form_class = AvocatForm
    permission_required = 'cabinet.change_avocat'
    success_url = reverse_lazy('cabinet:avocat_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ التحديث بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ التحديث بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'تعديل محامٍ', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AvocatDelete(SecureBase, DeleteView):
    model = Avocat
    permission_required = 'cabinet.delete_avocat'
    success_url = reverse_lazy('cabinet:avocat_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, 'تمّ الحذف.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحذف.'}, request=request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal(request, 'modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


# ---------------- Affaire ----------------
class AffaireList(SecureBase, OptimizedAffaireQueryMixin, ListView):
    model = Affaire
    permission_required = 'cabinet.view_affaire'
    search_fields = ('reference_interne', 'reference_tribunal', 'objet')

    def get_queryset(self):
        qs = super().get_queryset()
        qs = self.filter_by_search(qs)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'القضايا'
        ctx['create_url'] = reverse('cabinet:affaire_create')
        # Chronologie compacte: آخر جلسة/قياس/حكم لكل ملف (للعرض قبل إضافة خطوة)
        # (يمكن استخدامها في القالب لعرض Timeline خفيف)
        ids = [a.pk for a in ctx['object_list']]
        from django.db.models import Max
        latest_aud = Audience.objects.filter(affaire_id__in=ids).values('affaire_id').annotate(last=Max('date_audience'))
        latest_dec = Decision.objects.filter(affaire_id__in=ids).values('affaire_id').annotate(last=Max('date_prononce'))
        latest_mes = Mesure.objects.filter(audience__affaire_id__in=ids).values('audience__affaire_id').annotate(last=Max('pk'))
        ctx['latest_audience'] = {x['affaire_id']: x['last'] for x in latest_aud}
        ctx['latest_decision'] = {x['affaire_id']: x['last'] for x in latest_dec}
        ctx['latest_mesure'] = {x['audience__affaire_id']: x['last'] for x in latest_mes}
        return ctx

class AffaireDetail(SecureBase, DetailView):
    model = Affaire
    permission_required = 'cabinet.view_affaire'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        a: Affaire = self.object
        # Chronology complète pour Timeline (optimisée)
        ctx['audiences'] = Audience.objects.filter(affaire=a).select_related('affaire').order_by('date_audience')
        ctx['mesures'] = Mesure.objects.filter(audience__affaire=a).select_related('audience').order_by('pk')
        ctx['expertises'] = Expertise.objects.filter(affaire=a).order_by('date_ordonnee')
        ctx['decisions'] = Decision.objects.filter(affaire=a).order_by('date_prononce')
        ctx['notifications'] = Notification.objects.filter(decision__affaire=a).order_by('date_signification')
        ctx['recours'] = VoieDeRecours.objects.filter(decision__affaire=a).order_by('date_depot')
        ctx['executions'] = Execution.objects.filter(decision__affaire=a).order_by('date_demande')
        return ctx

class AffaireCreate(SecureBase, CreateView):
    model = Affaire
    form_class = AffaireForm
    permission_required = 'cabinet.add_affaire'
    success_url = reverse_lazy('cabinet:affaire_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ الحفظ بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحفظ بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class()
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'إضافة قضية', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AffaireUpdate(SecureBase, UpdateView):
    model = Affaire
    form_class = AffaireForm
    permission_required = 'cabinet.change_affaire'
    success_url = reverse_lazy('cabinet:affaire_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ التحديث بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ التحديث بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'تعديل قضية', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AffaireDelete(SecureBase, DeleteView):
    model = Affaire
    permission_required = 'cabinet.delete_affaire'
    success_url = reverse_lazy('cabinet:affaire_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, 'تمّ الحذف.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحذف.'}, request=request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal(request, 'modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


# ---------------- Générateur de CRUD pour le reste ----------------
# Pour limiter la répétition, on applique le même schéma aux autres modèles.
# (Vous avez déjà les classes dans une version antérieure — conservez la même structure
#  et ajoutez les méthodes get() HTMX + form_valid() comme ci-dessus.)

# Exemple compact pour Audience (le même pattern s'applique aux autres: Mesure, Expertise, Decision, ...)
class AudienceList(SecureBase, ListView):
    model = Audience
    permission_required = 'cabinet.view_audience'
    search_fields = ('affaire__reference_interne', 'type_audience')

    def get_queryset(self):
        return self.filter_by_search(super().get_queryset().select_related('affaire'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'الجلسات'
        ctx['create_url'] = reverse('cabinet:audience_create')
        return ctx

class AudienceDetail(SecureBase, DetailView):
    model = Audience
    permission_required = 'cabinet.view_audience'

class AudienceCreate(SecureBase, CreateView):
    model = Audience
    form_class = AudienceForm
    permission_required = 'cabinet.add_audience'
    success_url = reverse_lazy('cabinet:audience_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ الحفظ بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحفظ بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.form_class()
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'إضافة جلسة', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AudienceUpdate(SecureBase, UpdateView):
    model = Audience
    form_class = AudienceForm
    permission_required = 'cabinet.change_audience'
    success_url = reverse_lazy('cabinet:audience_list')

    def form_valid(self, form):
        messages.success(self.request, 'تمّ التحديث بنجاح.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ التحديث بنجاح.'}, request=self.request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.form_class(instance=self.object)
            return self.render_modal(request, 'modals/_form.html', {'form': form, 'title': 'تعديل جلسة', 'action': request.path})
        return super().get(request, *args, **kwargs)

class AudienceDelete(SecureBase, DeleteView):
    model = Audience
    permission_required = 'cabinet.delete_audience'
    success_url = reverse_lazy('cabinet:audience_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(request, 'تمّ الحذف.')
        if self.htmx():
            html = render_to_string('modals/_success_toast.html', {'message': 'تمّ الحذف.'}, request=request)
            return JsonResponse({'ok': True, 'html': html, 'redirect': self.success_url})
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal(request, 'modals/_confirm.html', {'title': 'تأكيد الحذف', 'action': request.path})
        return super().get(request, *args, **kwargs)


# -------------------------------------------------------------
# Notes d'intégration côté templates/JS pour l'UX souhaitée:
# -------------------------------------------------------------
# 1) Ajoutez HTMX + un modal Bootstrap dans base.html (dans block extra_js):

#
# 2) Boutons "إضافة" و"تعديل" داخل les listes/détails:
#    <a href="{% url 'cabinet:affaire_create' %}" class="btn btn-primary"
#       hx-get="{% url 'cabinet:affaire_create' %}" hx-target="#modalBody" hx-trigger="click"
#       hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}' data-bs-toggle="modal" data-bs-target="#mainModal">
#       إضافة قضية
#    </a>
#
# 3) Gabarits HTMX:
#    - modals/_form.html : contient uniquement <form ...> الحقول والأزرار.
#    - modals/_confirm.html : نص تأكيد + زر "حذف" يرسل POST.
#    - modals/_success_toast.html : رسالة نجاح صغيرة لعرض Toast.
#
# 4) Toggle Table/Cards:
#    - ضع أزرار في رأس الصفحة:
#      <div class="btn-group" role="group">
#        <a class="btn btn-outline-secondary {% if view_mode == 'table' %}active{% endif %}" href="?view=table">جدول</a>
#        <a class="btn btn-outline-secondary {% if view_mode == 'cards' %}active{% endif %}" href="?view=cards">بطاقات</a>
#      </div>
#
# 5) Sécurité additionnelle:
#    - Chaque vue exige permission_* adéquate (add/change/delete/view)
#    - ensure_csrf_cookie sur dispatch (cookie présent même sur GET)
#    - Filtrage de recherche côté serveur par champs whitelists
#    - Réponses JSON pour HTMX avec redirection de sécurité côté client
#
# 6) Appliquer le même pattern (Create/Update/Delete avec HTMX) aux autres modèles:
#    Mesure, Expertise, Decision, Notification, VoieDeRecours, Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte.
