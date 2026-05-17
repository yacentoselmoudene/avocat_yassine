"""Vues pour les paramètres du cabinet + impression PDF des listes /ref/."""
from __future__ import annotations

from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import CabinetParams
from .ref_registry import REF_REGISTRY


@login_required
@require_http_methods(["GET", "POST"])
def cabinet_params_view(request):
    """Page de paramètres du cabinet (singleton).

    Affiche un formulaire qui édite l'unique instance CabinetParams.
    """
    obj = CabinetParams.get_solo()

    if request.method == "POST":
        text_fields = [
            "nom_cabinet_ar", "nom_cabinet_fr", "nom_avocat_ar", "nom_avocat_fr",
            "barreau", "numero_carte_pro", "adresse", "ville",
            "telephone", "fax", "email", "site_web", "ice", "rib",
            "devise_ar", "pied_page_ar",
        ]
        for f in text_fields:
            if f in request.POST:
                setattr(obj, f, request.POST.get(f, "").strip())

        if "logo_cabinet" in request.FILES:
            obj.logo_cabinet = request.FILES["logo_cabinet"]
        if "logo_ministere" in request.FILES:
            obj.logo_ministere = request.FILES["logo_ministere"]
        if request.POST.get("clear_logo_cabinet") == "1":
            obj.logo_cabinet = None
        if request.POST.get("clear_logo_ministere") == "1":
            obj.logo_ministere = None

        obj.save()
        messages.success(request, "تم حفظ إعدادات المكتب.")
        return redirect("cabinet:cabinet_params")

    return render(request, "cabinet/cabinet_params.html", {"obj": obj})


@login_required
def ref_print_pdf(request, refname: str):
    """Génère un PDF de la liste d'un référentiel avec en-tête/pied de page cabinet."""
    cfg = REF_REGISTRY.get(refname)
    if not cfg:
        return HttpResponse("Référentiel inconnu", status=404)

    model = cfg.get("model")
    fields = cfg.get("fields", ["libelle"])
    labels = cfg.get("labels", {})
    list_title = cfg.get("list_title") or refname

    qs = model.objects.all()
    if hasattr(model, "is_deleted"):
        qs = qs.filter(is_deleted=False)
    items = list(qs.order_by("libelle"))

    params = CabinetParams.get_solo()

    context = {
        "params": params,
        "title": list_title,
        "items": items,
        "fields": fields,
        "labels": labels,
        "generated_at": timezone.now(),
        "request": request,
    }

    html = render_to_string("pdf/ref_list_pdf.html", context, request=request)

    try:
        from xhtml2pdf import pisa
    except ImportError:
        return HttpResponse(html)

    pdf_buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=pdf_buffer, encoding="utf-8")
    if result.err:
        return HttpResponse(html)

    pdf_buffer.seek(0)
    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{refname}.pdf"'
    return response
