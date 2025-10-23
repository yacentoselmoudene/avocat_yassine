# avocat_app/views_mixins.py
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView



class HTMXModalFormMixin:
    """
    - GET HTMX  : rend un formulaire partiel (modals/_form.html) avec action_url correct.
    - POST HTMX : renvoie JSON (ok, message, refreshTarget, refreshUrl).
    - Non-HTMX  : rendu normal avec template page complète.
    """
    htmx_template = "modals/_form.html"
    page_template = None           # si tu veux une page complète; sinon _form.html suffit
    success_message = "تم الحفظ بنجاح."
    refresh_target = "#timeline"

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return [self.htmx_template]
        if self.page_template:
            return [self.page_template]
        # fallback : formulaire partiel
        return [self.htmx_template]

    def get_action_url(self):
        """
        URL de soumission du formulaire.
        Par défaut, c’est self.request.path (correct pour CreateView/UpdateView).
        Si tu inclus un formulaire ailleurs, passe action_url dans le contexte.
        """
        return self.request.path

    def get_success_url(self):
        """
        Par défaut, si la vue parente n’a pas de success_url, on évite l’exception.
        À redéfinir si besoin.
        """
        return super().get_success_url() if hasattr(super(), "get_success_url") else reverse_lazy("cabinet:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("action_url", self.get_action_url())
        return ctx

    def success_json(self, message=None, **payload):
        data = {"ok": True, "message": message or self.success_message}
        data.update(payload)
        return JsonResponse(data)

class ModalCreateView(HTMXModalFormMixin, CreateView):
    pass

class ModalUpdateView(HTMXModalFormMixin, UpdateView):
    pass

from django.shortcuts import redirect
class NoPostOnReadOnlyMixin:
    """
    Si un POST arrive par erreur sur une vue lecture seule (List/Detail),
    on redirige proprement (au lieu d'un 405).
    """
    post_redirect_name = None  # ex: "cabinet:avocat_create"

    def post(self, request, *args, **kwargs):
        if self.post_redirect_name:
            return redirect(self.post_redirect_name)
        # sinon 405 maîtrisé
        return JsonResponse({"ok": False, "detail": "Méthode non autorisée ici."}, status=405)

class SoftDeleteQuerysetMixin:
    """Retourne all_objects pour superuser; sinon objects."""
    def get_queryset(self):
        base = super().get_queryset()
        model = getattr(self, "model", None) or base.model
        if self.request.user.is_superuser:
            return model.all_objects.all()
        return model.objects.all()