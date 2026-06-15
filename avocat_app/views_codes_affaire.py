"""Page CRUD dédiée pour les CodeCategorieAffaire (521 codes du XLSX).

Suit le patron UX standard du CLAUDE.md :
  - Liste + pagination côté client (10/25/50)
  - Recherche instantanée (≥2 chars)
  - Modal d'ajout/édition (AJAX)
  - Sélection multiple pour suppression de masse (= archivage)
  - 100 % AJAX (pas de rechargement)
  - Filtres : code_type (chambre), sous_type, categorie_globale

Routes (montées dans urls.py) :
  GET  /ref/codes-affaire/                  → page HTML
  GET  /ref/codes-affaire/list/             → JSON pour tableau (recherche + filtres)
  POST /ref/codes-affaire/create/           → JSON {ok, item}
  POST /ref/codes-affaire/<pk>/update/      → JSON {ok, item}
  POST /ref/codes-affaire/archive/          → JSON {ok, archived} (soft delete N items)
"""
from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .models import CodeCategorieAffaire


def _serialize(c: CodeCategorieAffaire) -> dict:
    return {
        "id": c.pk,
        "code": c.code,
        "libelle": c.libelle,
        "code_type": c.code_type or "",
        "type_libelle": c.type_libelle or "",
        "sous_type": c.sous_type or "",
        "categorie_globale": c.categorie_globale or "",
        "categorie_globale_label": c.get_categorie_globale_display() if c.categorie_globale else "",
        "domaine": c.domaine,
        "domaine_label": c.get_domaine_display(),
        "niveau": c.niveau,
        "is_archived": c.is_deleted,
    }


@login_required
@require_GET
def codes_affaire_page(request):
    """Rend la page de gestion (liste + modal). Les données sont chargées en AJAX."""
    # Choices pour les filtres dropdown
    return render(request, "ref/codes_affaire.html", {
        "title": "رموز قضايا المحاكم",
        "categories_globales": CodeCategorieAffaire.CATEGORIE_GLOBALE_CHOICES,
        "domaines": CodeCategorieAffaire.DOMAINE_CHOICES,
    })


@login_required
@require_GET
def codes_affaire_list(request):
    """JSON pour le tableau : recherche libre + filtres + (optionnellement) archivés."""
    qs = CodeCategorieAffaire.objects.all()
    include_archived = request.GET.get("include_archived") == "1"
    if not include_archived:
        qs = qs.filter(is_deleted=False)

    q = (request.GET.get("q") or "").strip()
    code_type = request.GET.get("code_type") or ""
    sous_type = request.GET.get("sous_type") or ""
    categorie_globale = request.GET.get("categorie_globale") or ""

    if q and len(q) >= 2:
        qs = qs.filter(Q(code__icontains=q) | Q(libelle__icontains=q) | Q(type_libelle__icontains=q))
    if code_type:
        qs = qs.filter(code_type=code_type)
    if sous_type:
        qs = qs.filter(sous_type=sous_type)
    if categorie_globale:
        qs = qs.filter(categorie_globale=categorie_globale)

    qs = qs.order_by("code_type", "code")[:1000]  # cap raisonnable
    items = [_serialize(c) for c in qs]

    # Métadonnées pour les filtres
    distinct_types = (CodeCategorieAffaire.objects
                      .filter(is_deleted=False).exclude(code_type="")
                      .values("code_type", "type_libelle")
                      .order_by("code_type").distinct())
    distinct_sous = (CodeCategorieAffaire.objects
                     .filter(is_deleted=False).exclude(sous_type="")
                     .values_list("sous_type", flat=True)
                     .order_by("sous_type").distinct())
    return JsonResponse({
        "ok": True,
        "items": items,
        "meta": {
            "total": len(items),
            "code_types": [{"code_type": t["code_type"], "libelle": t["type_libelle"] or ""}
                           for t in distinct_types],
            "sous_types": list(distinct_sous),
        },
    })


def _parse_payload(request) -> dict:
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return {}
    return dict(request.POST.items())


@login_required
@permission_required("cabinet.add_codecategorieaffaire", raise_exception=True)
@require_POST
@csrf_protect
def codes_affaire_create(request):
    data = _parse_payload(request)
    code = (data.get("code") or "").strip()
    libelle = (data.get("libelle") or "").strip()
    if not code or not libelle:
        return JsonResponse({"ok": False, "error": "code وlibelle مطلوبان."}, status=400)
    if CodeCategorieAffaire.objects.filter(code=code).exists():
        return JsonResponse({"ok": False, "error": f"الرمز {code} مستعمل بالفعل."}, status=400)

    c = CodeCategorieAffaire.objects.create(
        code=code,
        libelle=libelle,
        code_type=(data.get("code_type") or "").strip(),
        type_libelle=(data.get("type_libelle") or "").strip(),
        sous_type=(data.get("sous_type") or "").strip(),
        categorie_globale=(data.get("categorie_globale") or "").strip(),
        domaine=(data.get("domaine") or "civil").strip(),
        niveau=(data.get("niveau") or "premiere_instance").strip(),
    )
    return JsonResponse({"ok": True, "item": _serialize(c), "message": "تم إنشاء الرمز."})


@login_required
@permission_required("cabinet.change_codecategorieaffaire", raise_exception=True)
@require_POST
@csrf_protect
def codes_affaire_update(request, pk: int):
    try:
        c = CodeCategorieAffaire.objects.get(pk=pk)
    except CodeCategorieAffaire.DoesNotExist:
        return JsonResponse({"ok": False, "error": "غير موجود."}, status=404)
    data = _parse_payload(request)
    for fld in ("code", "libelle", "code_type", "type_libelle", "sous_type",
                "categorie_globale", "domaine", "niveau"):
        if fld in data:
            setattr(c, fld, (data.get(fld) or "").strip())
    if not c.code or not c.libelle:
        return JsonResponse({"ok": False, "error": "code وlibelle مطلوبان."}, status=400)
    c.save()
    return JsonResponse({"ok": True, "item": _serialize(c), "message": "تم تحديث الرمز."})


@login_required
@permission_required("cabinet.delete_codecategorieaffaire", raise_exception=True)
@require_POST
@csrf_protect
def codes_affaire_archive(request):
    """Archive (soft delete) une liste d'IDs. Action de masse depuis cases à cocher."""
    data = _parse_payload(request)
    ids_raw = data.get("ids") or []
    if isinstance(ids_raw, str):
        ids_raw = [x for x in ids_raw.split(",") if x.strip()]
    try:
        ids = [int(x) for x in ids_raw]
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "ids غير صالحة."}, status=400)
    if not ids:
        return JsonResponse({"ok": False, "error": "لا توجد عناصر للأرشفة."}, status=400)
    n = CodeCategorieAffaire.objects.filter(pk__in=ids, is_deleted=False).update(is_deleted=True)
    return JsonResponse({"ok": True, "archived": n, "ids": ids,
                         "message": f"تم أرشفة {n} عنصر(ات)."})


@login_required
@permission_required("cabinet.change_codecategorieaffaire", raise_exception=True)
@require_POST
@csrf_protect
def codes_affaire_restore(request):
    """Désarchive (restore) une liste d'IDs."""
    data = _parse_payload(request)
    ids_raw = data.get("ids") or []
    if isinstance(ids_raw, str):
        ids_raw = [x for x in ids_raw.split(",") if x.strip()]
    try:
        ids = [int(x) for x in ids_raw]
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "ids غير صالحة."}, status=400)
    n = CodeCategorieAffaire.objects.filter(pk__in=ids, is_deleted=True).update(is_deleted=False)
    return JsonResponse({"ok": True, "restored": n, "message": f"تم استرجاع {n} عنصر(ات)."})
