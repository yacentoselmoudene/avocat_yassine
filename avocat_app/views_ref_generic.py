# -*- coding: utf-8 -*-
# FILE: avocat_app/views_ref_generic.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .views_mixins import SecureBase  # ta base Login+Perms+success_json(...)
from .models import (
    TypeDepense, TypeRecette, RoleUtilisateur, StatutTache, TypeAlerte,
    TypeRecours, StatutExecution, TypeExecution, StatutAffaire, TypeAffaire,
    TypeAudience, ResultatAudience, DegreJuridiction, TypeJuridiction,
)
from .forms import ArabicModelForm  # base de tes ModelForms ar

# ---------------------------
# Mixins HTMX (légers)
# ---------------------------
class HTMXViewMixin:
    def htmx(self) -> bool:
        return self.request.headers.get("HX-Request", "").lower() == "true"

    def render_modal(self, template: str, context: Dict[str, Any]) -> HttpResponse:
        html = render_to_string(template, context=context, request=self.request)
        return HttpResponse(html)

class HTMXModalFormMixin(HTMXViewMixin):
    """Rend toujours le partial en HTMX, et une page complète (optionnelle) sinon."""
    page_template: Optional[str] = None
    success_message: str = "تم الحفظ."

    def get_template_names(self):
        if self.htmx():
            return ["modals/_form.html"]
        # si tu veux une page complète quand accès direct:
        return [self.page_template or "modals/_form.html"]

    def form_invalid(self, form):
        if self.htmx():
            return self.render_modal("modals/_form.html", {
                "form": form, "title": getattr(self, "modal_title", "نموذج"), "action": self.request.path
            })
        return super().form_invalid(form)

# ---------------------------
# Fabrique de ModelForm simple
# ---------------------------

def make_ref_form(modelino, fieldsino, labels=None, widgets=None):
    """
    Construit un ModelForm pour `model` avec la liste `fields`.
    `labels` (ar) et `widgets` sont optionnels.
    """

    labelsino = labels or {}
    widgetsino = widgets or {}
    class _RefForm(ArabicModelForm):
        class Meta:
            model = modelino
            fields = fieldsino
            labels = labelsino
            widgets = widgetsino
    return _RefForm

# ---------------------------
# Déclaration de chaque Ref
# ---------------------------
@dataclass
class RefConfig:
    model: Any
    fields: list[str]
    list_title: str
    form_title_create: str
    form_title_update: str

# Tous tes référentiels “libellé”
REFS: Dict[str, RefConfig] = {
    "typedepenses": RefConfig(
        model=TypeDepense, fields=["libelle"],
        list_title="أنواع المصاريف", form_title_create="إضافة نوع مصاريف", form_title_update="تعديل نوع مصاريف"),
    "typerecettes": RefConfig(
        model=TypeRecette, fields=["libelle"],
        list_title="أنواع المداخيل", form_title_create="إضافة نوع مداخيل", form_title_update="تعديل نوع مداخيل"),
    "roles": RefConfig(
        model=RoleUtilisateur, fields=["libelle"],
        list_title="أدوار المستخدمين", form_title_create="إضافة دور", form_title_update="تعديل دور"),
    "statuts-tache": RefConfig(
        model=StatutTache, fields=["libelle"],
        list_title="حالات المهام", form_title_create="إضافة حالة", form_title_update="تعديل حالة"),
    "types-alerte": RefConfig(
        model=TypeAlerte, fields=["libelle"],
        list_title="أنواع التنبيهات", form_title_create="إضافة نوع تنبيه", form_title_update="تعديل نوع تنبيه"),
    "typerecours": RefConfig(
        model=TypeRecours, fields=["libelle"],
        list_title="أنواع الطعون", form_title_create="إضافة نوع طعن", form_title_update="تعديل نوع طعن"),
    "typeexecution": RefConfig(
        model=TypeExecution, fields=["libelle"],
        list_title="أنواع التنفيذ", form_title_create="إضافة نوع تنفيذ", form_title_update="تعديل نوع تنفيذ"),
    "statutexecution": RefConfig(
        model=StatutExecution, fields=["libelle"],
        list_title="حالات التنفيذ", form_title_create="إضافة حالة تنفيذ", form_title_update="تعديل حالة تنفيذ"),
    "statutaffaire": RefConfig(
        model=StatutAffaire, fields=["libelle"],
        list_title="حالات القضايا", form_title_create="إضافة حالة قضية", form_title_update="تعديل حالة قضية"),
    "typeaffaire": RefConfig(
        model=TypeAffaire, fields=["libelle"],
        list_title="أنواع القضايا", form_title_create="إضافة نوع قضية", form_title_update="تعديل نوع قضية"),
    "typeaudience": RefConfig(
        model=TypeAudience, fields=["libelle"],
        list_title="أنواع الجلسات", form_title_create="إضافة نوع جلسة", form_title_update="تعديل نوع جلسة"),
    "resultataudience": RefConfig(
        model=ResultatAudience, fields=["libelle"],
        list_title="نتائج الجلسات", form_title_create="إضافة نتيجة", form_title_update="تعديل نتيجة"),
    "degres-juridiction": RefConfig(
        model=DegreJuridiction, fields=["libelle"],
        list_title="درجات المحاكم", form_title_create="إضافة درجة", form_title_update="تعديل درجة"),
    "typejuridiction": RefConfig(
        model=TypeJuridiction, fields=["libelle"],
        list_title="أنواع المحاكم", form_title_create="إضافة نوع محكمة", form_title_update="تعديل نوع محكمة"),
}

# ---------------------------
# Base pour les vues Ref
# ---------------------------
class RefBase(SecureBase):
    permission_required = ""  # on met sur chaque vue
    refname_kwarg = "refname"
    context_object_name = "items"  # pour la liste

    def get_ref(self) -> RefConfig:
        refname = self.kwargs.get(self.refname_kwarg)
        cfg = REFS.get(refname)
        if not cfg:
            raise LookupError(f"Référentiel inconnu: {refname}")
        return cfg

    def get_queryset(self):
        cfg = self.get_ref()
        qs = cfg.model.objects.all()
        # si tu utilises un SoftDelete: qs = qs.filter(is_deleted=False)
        return qs.order_by("libelle")

    # utilitaire commun aux vues HTMX (succès uniforme)
    def _success_json_refresh_list(self) -> JsonResponse:
        refname = self.kwargs.get(self.refname_kwarg)
        return self.success_json(
            "تمت العملية بنجاح.",
            refreshTarget="#ref-list",
            refreshUrl=reverse("cabinet_ref:ref_list", args=[refname]),
            closeModal=True,
        )

# ---------------------------
# LIST
# ---------------------------
class RefList(RefBase, ListView):
    permission_required = "cabinet.view_ref"  # ou spécifique
    template_name = "ref/libelle_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cfg = self.get_ref()
        ctx.update({
            "title": cfg.list_title,
            "create_url": reverse_lazy("cabinet_ref:ref_create", args=[self.kwargs["refname"]]),
            "update_name": "cabinet_ref:ref_update",
            "delete_name": "cabinet_ref:ref_delete",
            "refname": self.kwargs["refname"],
        })
        return ctx

# ---------------------------
# CREATE
# ---------------------------
class RefCreate(RefBase, HTMXModalFormMixin, CreateView):
    permission_required = "cabinet.add_ref"  # ou fin par ref
    page_template = "ref/libelle_form.html"  # si accès complet

    def get_form_class(self):
        cfg = self.get_ref()
        return make_ref_form(cfg.model, cfg.fields, labels={"libelle": "الاسم"})

    def get(self, request, *args, **kwargs):
        if self.htmx():
            form = self.get_form()
            return self.render_modal("modals/_form.html", {
                "form": form, "title": self.get_ref().form_title_create, "action": request.path
            })
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self._success_json_refresh_list()
        messages.success(self.request, "تمت الإضافة.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cabinet_ref:ref_list", args=[self.kwargs["refname"]])

# ---------------------------
# UPDATE
# ---------------------------
class RefUpdate(RefBase, HTMXModalFormMixin, UpdateView):
    permission_required = "cabinet.change_ref"
    page_template = "ref/libelle_form.html"

    def get_form_class(self):
        cfg = self.get_ref()
        return make_ref_form(cfg.model, cfg.fields, labels={"libelle": "الاسم"})

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            form = self.get_form()
            return self.render_modal("modals/_form.html", {
                "form": form, "title": self.get_ref().form_title_update, "action": request.path
            })
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        if self.htmx():
            return self._success_json_refresh_list()
        messages.success(self.request, "تم التحديث.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("cabinet_ref:ref_list", args=[self.kwargs["refname"]])

# ---------------------------
# DELETE
# ---------------------------
class RefDelete(RefBase, HTMXModalFormMixin, DeleteView):
    permission_required = "cabinet.delete_ref"
    page_template = "ref/libelle_confirm_delete.html"

    def get(self, request, *args, **kwargs):
        if self.htmx():
            self.object = self.get_object()
            return self.render_modal("modals/_confirm.html", {
                "title": "تأكيد الحذف", "action": request.path
            })
        return super().get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # si SoftDelete:
        # self.object.is_deleted = True; self.object.save(update_fields=["is_deleted"])
        self.object.delete()
        if self.htmx():
            return self._success_json_refresh_list()
        messages.success(self.request, "تم الحذف.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("cabinet_ref:ref_list", args=[self.kwargs["refname"]])
