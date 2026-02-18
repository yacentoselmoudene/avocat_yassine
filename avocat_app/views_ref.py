# avocat_app/views_ref.py
from django.urls import reverse_lazy
from django.views.generic import ListView, DeleteView
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .views_mixins import ModalCreateView, ModalUpdateView, ModalDeleteView, \
    HTMXViewMixin  # du kit précédent
from .forms import (
    TypeDepenseForm, TypeRecetteForm, RoleUtilisateurForm, StatutTacheForm, TypeAlerteForm,
    StatutExecutionForm, StatutRecoursForm, StatutAffaireForm, TypeAudienceForm, TypeRecoursForm,
    TypeExecutionForm, ResultatAudienceForm, DegreJuridictionForm, TypeJuridictionForm, TypeAffaireForm
)
from .models import (TypeDepense, TypeRecette, RoleUtilisateur, StatutTache, TypeAlerte, StatutExecution, StatutRecours,
                     StatutAffaire, TypeAudience, TypeRecours, TypeExecution, ResultatAudience, DegreJuridiction,
                     TypeJuridiction, TypeAffaire)

from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

class SecureBase(LoginRequiredMixin, PermissionRequiredMixin):
    login_url = reverse_lazy("authui:login")
    permission_required = ""

class ModalDeleteView1111(DeleteView):
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
"""

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
            "create_url": reverse_lazy("cabinet_ref:typedepense_create"),
            "update_name": "cabinet_ref:typedepense_update",
            "delete_name": "cabinet_ref:typedepense_delete",
        })
        return ctx

class TypeDepenseCreate(SecureBase, ModalCreateView):
    model = TypeDepense
    form_class = TypeDepenseForm
    permission_required = "cabinet.add_typedepense"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typedepense_list")

class TypeDepenseUpdate(SecureBase, ModalUpdateView):
    model = TypeDepense
    form_class = TypeDepenseForm
    permission_required = "cabinet.change_typedepense"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typedepense_list")

class TypeDepenseDelete(SecureBase, ModalDeleteView):
    model = TypeDepense
    permission_required = "cabinet.delete_typedepense"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typedepense_list")

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
            "create_url": reverse_lazy("cabinet_ref:typerecette_create"),
            "update_name": "cabinet_ref:typerecette_update",
            "delete_name": "cabinet_ref:typerecette_delete",
        })
        return ctx

class TypeRecetteCreate(SecureBase, ModalCreateView):
    model = TypeRecette
    form_class = TypeRecetteForm
    permission_required = "cabinet.add_typerecette"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typerecette_list")

class TypeRecetteUpdate(SecureBase, ModalUpdateView):
    model = TypeRecette
    form_class = TypeRecetteForm
    permission_required = "cabinet.change_typerecette"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typerecette_list")

class TypeRecetteDelete(SecureBase, ModalDeleteView):
    model = TypeRecette
    permission_required = "cabinet.delete_typerecette"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typerecette_list")

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
            "create_url": reverse_lazy("cabinet_ref:roleutilisateur_create"),
            "update_name": "cabinet_ref:roleutilisateur_update",
            "delete_name": "cabinet_ref:roleutilisateur_delete",
        })
        return ctx

class RoleUtilisateurCreate(SecureBase, ModalCreateView):
    model = RoleUtilisateur
    form_class = RoleUtilisateurForm
    permission_required = "cabinet.add_roleutilisateur"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:roleutilisateur_list")

class RoleUtilisateurUpdate(SecureBase, ModalUpdateView):
    model = RoleUtilisateur
    form_class = RoleUtilisateurForm
    permission_required = "cabinet.change_roleutilisateur"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:roleutilisateur_list")

class RoleUtilisateurDelete(SecureBase, ModalDeleteView):
    model = RoleUtilisateur
    permission_required = "cabinet.delete_roleutilisateur"
    def get_success_url(self): return reverse_lazy("cabinet_ref:roleutilisateur_list")

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
            "create_url": reverse_lazy("cabinet_ref:statuttache_create"),
            "update_name": "cabinet_ref:statuttache_update",
            "delete_name": "cabinet_ref:statuttache_delete",
        })
        return ctx

class StatutTacheCreate(SecureBase, ModalCreateView):
    model = StatutTache
    form_class = StatutTacheForm
    permission_required = "cabinet.add_statuttache"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statuttache_list")

class StatutTacheUpdate(SecureBase, ModalUpdateView):
    model = StatutTache
    form_class = StatutTacheForm
    permission_required = "cabinet.change_statuttache"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statuttache_list")

class StatutTacheDelete(SecureBase, ModalDeleteView):
    model = StatutTache
    permission_required = "cabinet.delete_statuttache"
    def get_success_url(self): return reverse_lazy("cabinet_ref:statuttache_list")

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
            "create_url": reverse_lazy("cabinet_ref:typealerte_create"),
            "update_name": "cabinet_ref:typealerte_update",
            "delete_name": "cabinet_ref:typealerte_delete",
        })
        return ctx

class TypeAlerteCreate(SecureBase, ModalCreateView):
    model = TypeAlerte
    form_class = TypeAlerteForm
    permission_required = "cabinet.add_typealerte"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typealerte_list")

class TypeAlerteUpdate(SecureBase, ModalUpdateView):
    model = TypeAlerte
    form_class = TypeAlerteForm
    permission_required = "cabinet.change_typealerte"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typealerte_list")

class TypeAlerteDelete(SecureBase, ModalDeleteView):
    model = TypeAlerte
    permission_required = "cabinet.delete_typealerte"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typealerte_list")


class DegreJuridictionList(SecureBase, NoPostOnReadOnlyMixin ,SoftDeleteQuerysetMixin, ListView):
    model = DegreJuridiction
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_degrejuridiction"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:degrejuridiction_create"),
            "update_name": "cabinet_ref:degrejuridiction_update",
            "delete_name": "cabinet_ref:degrejuridiction_delete",
        })
        return ctx

class DegreJuridictionCreate(SecureBase, ModalCreateView):
    model = DegreJuridiction
    form_class = DegreJuridictionForm
    permission_required = "cabinet.add_degrejuridiction"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:degrejuridiction_list")

class DegreJuridictionUpdate(SecureBase, ModalUpdateView):
    model = DegreJuridiction
    form_class = DegreJuridictionForm
    permission_required = "cabinet.change_degrejuridiction"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:degrejuridiction_list")

class DegreJuridictionDelete(SecureBase, HTMXViewMixin, DeleteView):
    model = DegreJuridiction
    permission_required = "cabinet.delete_degrejuridiction"
    template_name = "modals/_confirm.html"  # rendu du modal en GET
    success_url = reverse_lazy("cabinet_ref:degrejuridiction_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # action explicite = URL courante (delete) => le POST ne partira pas vers la liste
        ctx["action_url"] = self.request.path
        ctx["title"] = "تأكيد الحذف"
        ctx["question"] = "هل تريد حقًا حذف هذا العنصر؟"
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()  # soft delete si tu l’as surchargé
        if self.htmx():
            return self.success_json(
                "تم الحذف.",
                refreshTarget="#ref-list",
                refreshUrl=str(self.success_url),
                closeModal=True,
            )
        return super().delete(request, *args, **kwargs)


class TypeAffaireList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeAffaire
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typeaffaire"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:typeaffaire_create"),
            "update_name": "cabinet_ref:typeaffaire_update",
            "delete_name": "cabinet_ref:typeaffaire_delete",
        })
        return ctx

class TypeAffaireCreate(SecureBase, ModalCreateView):
    model = TypeAffaire
    form_class = TypeAffaireForm
    permission_required = "cabinet.add_typeaffaire"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeaffaire_list")

class TypeAffaireUpdate(SecureBase, ModalUpdateView):
    model = TypeAffaire
    form_class = TypeAffaireForm
    permission_required = "cabinet.change_typeaffaire"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeaffaire_list")

class TypeAffaireDelete(SecureBase, ModalDeleteView):
    model = TypeAffaire
    permission_required = "cabinet.delete_typeaffaire"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeaffaire_list")




class TypeJuridictionList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeJuridiction
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typejuridiction"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:typejuridiction_create"),
            "update_name": "cabinet_ref:typejuridiction_update",
            "delete_name": "cabinet_ref:typejuridiction_delete",
        })
        return ctx

class TypeJuridictionCreate(SecureBase, ModalCreateView):
    model = TypeJuridiction
    form_class = TypeJuridictionForm
    permission_required = "cabinet.add_typejuridiction"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typejuridiction_list")

class TypeJuridictionUpdate(SecureBase, ModalUpdateView):
    model = TypeJuridiction
    form_class = TypeJuridictionForm
    permission_required = "cabinet.change_typejuridiction"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typejuridiction_list")

class TypeJuridictionDelete(SecureBase, ModalDeleteView):
    model = TypeJuridiction
    permission_required = "cabinet.delete_typejuridiction"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typejuridiction_list")




class StatutExecutionList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = StatutExecution
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_statutexecution"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:statutexecution_create"),
            "update_name": "cabinet_ref:statutexecution_update",
            "delete_name": "cabinet_ref:statutexecution_delete",
        })
        return ctx

class StatutExecutionCreate(SecureBase, ModalCreateView):
    model = StatutExecution
    form_class = StatutExecutionForm
    permission_required = "cabinet.add_statutexecution"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutexecution_list")

class StatutExecutionUpdate(SecureBase, ModalUpdateView):
    model = StatutExecution
    form_class = StatutExecutionForm
    permission_required = "cabinet.change_statutexecution"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutexecution_list")

class StatutExecutionDelete(SecureBase, ModalDeleteView):
    model = StatutExecution
    permission_required = "cabinet.delete_statutexecution"
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutexecution_list")



class StatutRecoursList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = StatutRecours
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_statutrecours"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:statutrecours_create"),
            "update_name": "cabinet_ref:statutrecours_update",
            "delete_name": "cabinet_ref:statutrecours_delete",
        })
        return ctx

class StatutRecoursCreate(SecureBase, ModalCreateView):
    model = StatutRecours
    form_class = StatutRecoursForm
    permission_required = "cabinet.add_statutrecours"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutrecours_list")

class StatutRecoursUpdate(SecureBase, ModalUpdateView):
    model = StatutRecours
    form_class = StatutRecoursForm
    permission_required = "cabinet.change_statutrecours"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutrecours_list")

class StatutRecoursDelete(SecureBase, ModalDeleteView):
    model = StatutRecours
    permission_required = "cabinet.delete_statutrecours"
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutrecours_list")


class StatutAffaireList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = StatutAffaire
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_statutaffaire"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:statutaffaire_create"),
            "update_name": "cabinet_ref:statutaffaire_update",
            "delete_name": "cabinet_ref:statutaffaire_delete",
        })
        return ctx

class StatutAffaireCreate(SecureBase, ModalCreateView):
    model = StatutAffaire
    form_class = StatutAffaireForm
    permission_required = "cabinet.add_statutaffaire"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutaffaire_list")

class StatutAffaireUpdate(SecureBase, ModalUpdateView):
    model = StatutAffaire
    form_class = StatutAffaireForm
    permission_required = "cabinet.change_statutaffaire"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutaffaire_list")

class StatutAffaireDelete(SecureBase, ModalDeleteView):
    model = StatutAffaire
    permission_required = "cabinet.delete_statutaffaire"
    def get_success_url(self): return reverse_lazy("cabinet_ref:statutaffaire_list")


class TypeAudienceList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeAudience
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typeaudience"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:typeaudience_create"),
            "update_name": "cabinet_ref:typeaudience_update",
            "delete_name": "cabinet_ref:typeaudience_delete",
        })
        return ctx

class TypeAudienceCreate(SecureBase, ModalCreateView):
    model = TypeAudience
    form_class = TypeAudienceForm
    permission_required = "cabinet.add_typeaudience"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeaudience_list")

class TypeAudienceUpdate(SecureBase, ModalUpdateView):
    model = TypeAudience
    form_class = TypeAudienceForm
    permission_required = "cabinet.change_typeaudience"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeaudience_list")

class TypeAudienceDelete(SecureBase, ModalDeleteView):
    model = TypeAudience
    permission_required = "cabinet.delete_typeaudience"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeaudience_list")


class TypeRecoursList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeRecours
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typerecours"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:typerecours_create"),
            "update_name": "cabinet_ref:typerecours_update",
            "delete_name": "cabinet_ref:typerecours_delete",
        })
        return ctx

class TypeRecoursCreate(SecureBase, ModalCreateView):
    model = TypeRecours
    form_class = TypeRecoursForm
    permission_required = "cabinet.add_typerecours"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typerecours_list")

class TypeRecoursUpdate(SecureBase, ModalUpdateView):
    model = TypeRecours
    form_class = TypeRecoursForm
    permission_required = "cabinet.change_typerecours"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typerecours_list")

class TypeRecoursDelete(SecureBase, ModalDeleteView):
    model = TypeRecours
    permission_required = "cabinet.delete_typerecours"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typerecours_list")


class TypeExecutionList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = TypeExecution
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_typeexecution"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:typeexecution_create"),
            "update_name": "cabinet_ref:typeexecution_update",
            "delete_name": "cabinet_ref:typeexecution_delete",
        })
        return ctx

class TypeExecutionCreate(SecureBase, ModalCreateView):
    model = TypeExecution
    form_class = TypeExecutionForm
    permission_required = "cabinet.add_typeexecution"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeexecution_list")

class TypeExecutionUpdate(SecureBase, ModalUpdateView):
    model = TypeExecution
    form_class = TypeExecutionForm
    permission_required = "cabinet.change_typeexecution"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeexecution_list")

class TypeExecutionDelete(SecureBase, ModalDeleteView):
    model = TypeExecution
    permission_required = "cabinet.delete_typeexecution"
    def get_success_url(self): return reverse_lazy("cabinet_ref:typeexecution_list")


class ResultatAudienceList(SecureBase, SoftDeleteQuerysetMixin, ListView):
    model = ResultatAudience
    template_name = "ref/libelle_list.html"
    context_object_name = "items"
    permission_required = "cabinet.view_resultataudience"
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "title": "أنواع التنبيهات",
            "create_url": reverse_lazy("cabinet_ref:resultataudience_create"),
            "update_name": "cabinet_ref:resultataudience_update",
            "delete_name": "cabinet_ref:resultataudience_delete",
        })
        return ctx

class ResultatAudienceCreate(SecureBase, ModalCreateView):
    model = ResultatAudience
    form_class = ResultatAudienceForm
    permission_required = "cabinet.add_resultataudience"
    success_message = "تمت الإضافة."
    def get_success_url(self): return reverse_lazy("cabinet_ref:resultataudience_list")

class ResultatAudienceUpdate(SecureBase, ModalUpdateView):
    model = ResultatAudience
    form_class = ResultatAudienceForm
    permission_required = "cabinet.change_resultataudience"
    success_message = "تم التحديث."
    def get_success_url(self): return reverse_lazy("cabinet_ref:resultataudience_list")

class ResultatAudienceDelete(SecureBase, ModalDeleteView):
    model = ResultatAudience
    permission_required = "cabinet.delete_resultataudience"
    def get_success_url(self): return reverse_lazy("cabinet_ref:resultataudience_list")
"""