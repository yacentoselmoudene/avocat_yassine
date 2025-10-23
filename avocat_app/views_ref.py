# avocat_app/views_ref.py
from django.urls import reverse_lazy
from django.views.generic import ListView, DeleteView
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .views_mixins import ModalCreateView, ModalUpdateView , SoftDeleteQuerysetMixin # du kit précédent
from .forms import (
    TypeDepenseForm, TypeRecetteForm, RoleUtilisateurForm, StatutTacheForm, TypeAlerteForm
)
from .models import TypeDepense, TypeRecette, RoleUtilisateur, StatutTache, TypeAlerte

from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

class SecureBase(LoginRequiredMixin, PermissionRequiredMixin):
    login_url = reverse_lazy("authui:login")
    permission_required = ""

class ModalDeleteView(DeleteView):
    template_name = "modals/_confirm.html"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get("HX-Request"):
            return JsonResponse({
                "ok": True,
                "message": "تم الحذف.",
                "refreshTarget": "#ref-list",
                "refreshUrl": self.get_success_url(),
            })
        return super().delete(request, *args, **kwargs)

class RestoreView(SecureBase, View):
    model = None   # à définir dans sous-classes

    def post(self, request, pk):
        obj = get_object_or_404(self.model.all_objects, pk=pk)  # inclut supprimés
        obj.restore()
        return JsonResponse({
            "ok": True, "message": "تمت الاستعادة.",
            "refreshTarget": "#ref-list",
            "refreshUrl": self.request.GET.get("next") or self.request.POST.get("next") or request.path.rsplit("/", 3)[0] + "/"
        })


# ========== TypeDepense ==========
class TypeDepenseList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeDepense
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typedepense"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع المصاريف",
            "create_url": reverse_lazy("cabinet:typedepense_create"),
            "update_name": "cabinet:typedepense_update",
            "delete_name": "cabinet:typedepense_delete",
        })
        return ctx

class TypeDepenseCreate(SecureBase, ModalCreateView):
    model = TypeDepense
    form_class = TypeDepenseForm
    permission_required = "cabinet.add_typedepense"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet:typedepense_list")

class TypeDepenseUpdate(SecureBase, ModalUpdateView):
    model = TypeDepense
    form_class = TypeDepenseForm
    permission_required = "cabinet.change_typedepense"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet:typedepense_list")

class TypeDepenseDelete(SecureBase, ModalDeleteView):
    model = TypeDepense
    permission_required = "cabinet.delete_typedepense"
    def get_success_url(self): return reverse_lazy("cabinet:typedepense_list")

# ========== TypeRecette ==========
class TypeRecetteList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeRecette
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typerecette"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع المداخيل",
            "create_url": reverse_lazy("cabinet:typerecette_create"),
            "update_name": "cabinet:typerecette_update",
            "delete_name": "cabinet:typerecette_delete",
        })
        return ctx

class TypeRecetteCreate(SecureBase, ModalCreateView):
    model = TypeRecette
    form_class = TypeRecetteForm
    permission_required = "cabinet.add_typerecette"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet:typerecette_list")

class TypeRecetteUpdate(SecureBase, ModalUpdateView):
    model = TypeRecette
    form_class = TypeRecetteForm
    permission_required = "cabinet.change_typerecette"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet:typerecette_list")

class TypeRecetteDelete(SecureBase, ModalDeleteView):
    model = TypeRecette
    permission_required = "cabinet.delete_typerecette"
    def get_success_url(self): return reverse_lazy("cabinet:typerecette_list")

# ========== RoleUtilisateur ==========
class RoleUtilisateurList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = RoleUtilisateur
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_roleutilisateur"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أدوار المستخدمين",
            "create_url": reverse_lazy("cabinet:roleutilisateur_create"),
            "update_name": "cabinet:roleutilisateur_update",
            "delete_name": "cabinet:roleutilisateur_delete",
        })
        return ctx

class RoleUtilisateurCreate(SecureBase, ModalCreateView):
    model = RoleUtilisateur
    form_class = RoleUtilisateurForm
    permission_required = "cabinet.add_roleutilisateur"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet:roleutilisateur_list")

class RoleUtilisateurUpdate(SecureBase, ModalUpdateView):
    model = RoleUtilisateur
    form_class = RoleUtilisateurForm
    permission_required = "cabinet.change_roleutilisateur"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet:roleutilisateur_list")

class RoleUtilisateurDelete(SecureBase, ModalDeleteView):
    model = RoleUtilisateur
    permission_required = "cabinet.delete_roleutilisateur"
    def get_success_url(self): return reverse_lazy("cabinet:roleutilisateur_list")

# ========== StatutTache ==========
class StatutTacheList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = StatutTache
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_statuttache"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "حالات المهام",
            "create_url": reverse_lazy("cabinet:statuttache_create"),
            "update_name": "cabinet:statuttache_update",
            "delete_name": "cabinet:statuttache_delete",
        })
        return ctx

class StatutTacheCreate(SecureBase, ModalCreateView):
    model = StatutTache
    form_class = StatutTacheForm
    permission_required = "cabinet.add_statuttache"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet:statuttache_list")

class StatutTacheUpdate(SecureBase, ModalUpdateView):
    model = StatutTache
    form_class = StatutTacheForm
    permission_required = "cabinet.change_statuttache"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet:statuttache_list")

class StatutTacheDelete(SecureBase, ModalDeleteView):
    model = StatutTache
    permission_required = "cabinet.delete_statuttache"
    def get_success_url(self): return reverse_lazy("cabinet:statuttache_list")

# ========== TypeAlerte ==========
class TypeAlerteList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeAlerte
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typealerte"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet:typealerte_create"),
            "update_name": "cabinet:typealerte_update",
            "delete_name": "cabinet:typealerte_delete",
        })
        return ctx

class TypeAlerteCreate(SecureBase, ModalCreateView):
    model = TypeAlerte
    form_class = TypeAlerteForm
    permission_required = "cabinet.add_typealerte"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet:typealerte_list")

class TypeAlerteUpdate(SecureBase, ModalUpdateView):
    model = TypeAlerte
    form_class = TypeAlerteForm
    permission_required = "cabinet.change_typealerte"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet:typealerte_list")

class TypeAlerteDelete(SecureBase, ModalDeleteView):
    model = TypeAlerte
    permission_required = "cabinet.delete_typealerte"
    def get_success_url(self): return reverse_lazy("cabinet:typealerte_list")

