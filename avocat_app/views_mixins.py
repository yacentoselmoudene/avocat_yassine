# -*- coding: utf-8 -*-
# =============================================================
# FILE: avocat_app/views.py  —  version compacte et fonctionnelle
# =============================================================
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.formats import date_format
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
)

from .models import (
    Juridiction, Avocat, Affaire, Partie, AffairePartie, AffaireAvocat,
    Audience, Mesure, Expertise, Decision, Notification, VoieDeRecours,
    Execution, Depense, Recette, PieceJointe, Utilisateur, Tache, Alerte,
    Expert, Barreau
)
from .forms import (
    JuridictionForm, AvocatForm, AffaireForm, PartieForm, AffairePartieForm, AffaireAvocatForm,
    AudienceForm, MesureForm, ExpertiseForm, DecisionForm, NotificationForm, VoieDeRecoursForm,
    ExecutionForm, DepenseForm, RecetteForm, PieceJointeForm, UtilisateurForm, TacheForm,
    AlerteForm, ExpertForm, BarreauForm
)

# =============================================================
# MIXINS GÉNÉRIQUES
# =============================================================

class SoftDeleteQuerysetMixin:
    """Superuser voit tout via all_objects; autres: objets actifs."""
    def get_queryset(self):
        model = getattr(self, "model", None)
        if model is None:
            return super().get_queryset()
        if getattr(self.request.user, "is_superuser", False) and hasattr(model, "all_objects"):
            return model.all_objects.all()
        if hasattr(model, "objects"):
            return model.objects.all()
        return super().get_queryset()

class NoPostOnReadOnlyMixin:
    """Empêche un POST par erreur sur une vue 'read-only' (List/Detail)."""
    def post(self, request, *args, **kwargs):
        return JsonResponse({"ok": False, "detail": "Méthode non autorisée."}, status=405)

class HTMXViewMixin:
    """Utilitaires HTMX."""
    def htmx(self) -> bool:
        return bool(self.request.headers.get("HX-Request"))

    def success_json(self, message: str | None = None, **payload) -> JsonResponse:
        """
        Renvoie un JSON standard pour le gestionnaire global (base.html):
          { ok: true, message?, refreshTarget?, refreshUrl?, closeModal?, html? }
        """
        data = {"ok": True}
        if message:
            data["message"] = message
        data.update(payload)
        return JsonResponse(data)

    def render_modal(self, template_name: str, context: dict) -> HttpResponse:
        """Rend un fragment HTML (formulaire ou confirm) pour le modal."""
        html = render_to_string(template_name, context=context, request=self.request)
        return HttpResponse(html)

class HTMXModalFormMixin(HTMXViewMixin):
    """Rend le _form en GET HTMX; renvoie JSON au succès POST HTMX."""
    page_template: str | None = None        # rendu page complète si non-HTMX
    success_message: str = "تم الحفظ."

    def get_template_names(self):
        if self.htmx():
            return ["modals/_form.html"]
        return [self.page_template or "modals/_form.html"]

    def form_invalid(self, form):
        # En HTMX: renvoyer le formulaire (avec erreurs) dans le modal
        if self.htmx():
            return self.render_modal("modals/_form.html", {
                "form": form, "title": getattr(self, "modal_title", "نموذج"), "action": self.request.path
            })
        return super().form_invalid(form)

class ModalCreateView(HTMXModalFormMixin, CreateView):
    """Create en modal: JSON success (closeModal + refresh*) ou redirection classique."""
    refresh_target = "#ref-list"  # par défaut pour les référentiels

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json(
                self.success_message, refreshTarget=self.refresh_target,
                refreshUrl=str(self.get_success_url()), closeModal=True
            )
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

class ModalUpdateView(HTMXModalFormMixin, UpdateView):
    refresh_target = "#ref-list"

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self.success_json(
                self.success_message, refreshTarget=self.refresh_target,
                refreshUrl=str(self.get_success_url()), closeModal=True
            )
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

class ModalDeleteView(HTMXViewMixin, DeleteView):
    """Delete en modal: GET=confirm, POST=delete→JSON."""
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_modal("modals/_confirm.html", {
            "title": "تأكيد الحذف", "action": request.path
        })

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()  # soft delete si implémenté au modèle
        if self.htmx():
            return self.success_json(
                "تم الحذف.", refreshTarget="#ref-list",
                refreshUrl=str(self.get_success_url()), closeModal=True
            )
        messages.success(self.request, "تم الحذف.")
        return super().delete(request, *args, **kwargs)

class SecureBase(LoginRequiredMixin, PermissionRequiredMixin, HTMXViewMixin):
    """Base sécurisée (login + permission)."""
    login_url = reverse_lazy("authui:login")
    raise_exception = False
    permission_required: str | tuple[str, ...] = ()

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().dispatch(request, *args, **kwargs)

# =============================================================
# OUTILS SPÉCIFIQUES AFFAIRE
# =============================================================

def _affaire_pk_from_step(obj) -> Any | None:
    """Récupère la PK de l'affaire liée à une étape."""
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
    if isinstance(obj, PieceJointe):
        return obj.affaire_id
    return None

def ar_dt(dt):
    if not dt:
        return ""
    return date_format(dt, "DATETIME_FORMAT", use_l10n=True)

