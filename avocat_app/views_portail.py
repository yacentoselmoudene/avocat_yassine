"""Vues du portail client (espace privé Partie, accès magic link)."""
from __future__ import annotations

from django.contrib import messages
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import Affaire, Audience, Decision, Depense, Recette, AffairePartie
from .services.portail_auth import (
    PORTAIL_COOKIE_AGE_SECONDS,
    PORTAIL_COOKIE_NAME,
    find_partie,
    get_partie_from_request,
    issue_token,
    make_cookie_value,
    send_magic_link,
)


@csrf_protect
@require_http_methods(["GET", "POST"])
def portail_login(request: HttpRequest) -> HttpResponse:
    """Page de saisie identifiant (email ou téléphone). Envoie le magic link."""
    if request.method == "POST":
        identifier = (request.POST.get("identifier") or "").strip()
        partie = find_partie(identifier)
        # Toujours répondre par un message générique (anti-énumération)
        if partie:
            tok = issue_token(partie, request=request)
            base_url = f"{request.scheme}://{request.get_host()}"
            send_magic_link(partie, tok.token, base_url=base_url)
        return render(request, "portail/login_sent.html", {"identifier": identifier})

    return render(request, "portail/login.html")


def portail_access(request: HttpRequest, token: str) -> HttpResponse:
    """Valide le token magic link et installe le cookie portail."""
    from .models import PortailAccess
    access = PortailAccess.objects.select_related("partie").filter(token=token).first()
    if not access or not access.is_valid:
        return render(request, "portail/error.html", {
            "title": "رابط غير صالح",
            "detail": "الرابط منتهي الصلاحية أو ملغى. الرجاء طلب رابط جديد.",
        }, status=400)

    if not access.used_at:
        access.used_at = timezone.now()
        access.save(update_fields=["used_at"])

    cookie = make_cookie_value(str(access.partie_id), str(access.pk))
    response = redirect("cabinet:portail_dashboard")
    response.set_cookie(
        PORTAIL_COOKIE_NAME, cookie,
        max_age=PORTAIL_COOKIE_AGE_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure(),
    )
    return response


def portail_logout(request: HttpRequest) -> HttpResponse:
    response = redirect("cabinet:portail_login")
    response.delete_cookie(PORTAIL_COOKIE_NAME)
    return response


def _require_portail_partie(request):
    partie = get_partie_from_request(request)
    if not partie:
        return None
    return partie


def portail_dashboard(request: HttpRequest) -> HttpResponse:
    partie = _require_portail_partie(request)
    if not partie:
        return redirect("cabinet:portail_login")

    affaires = (
        Affaire.objects
        .select_related("juridiction", "type_affaire", "statut_affaire", "avocat_responsable")
        .filter(affairepartie__partie=partie, affairepartie__actif=True)
        .distinct()
    )
    affaire_ids = list(affaires.values_list("id", flat=True))

    next_audiences = (
        Audience.objects
        .select_related("affaire", "affaire__juridiction", "type_audience")
        .filter(affaire_id__in=affaire_ids, date_audience__gte=timezone.now())
        .order_by("date_audience")[:5]
    )

    recent_decisions = (
        Decision.objects
        .select_related("affaire")
        .filter(affaire_id__in=affaire_ids)
        .order_by("-date_prononce")[:5]
    )

    dep = Depense.objects.filter(affaire_id__in=affaire_ids).aggregate(Sum("montant"))["montant__sum"] or 0
    rec = Recette.objects.filter(affaire_id__in=affaire_ids).aggregate(Sum("montant"))["montant__sum"] or 0

    return render(request, "portail/dashboard.html", {
        "partie": partie,
        "affaires": affaires,
        "next_audiences": next_audiences,
        "recent_decisions": recent_decisions,
        "finance": {"depenses": dep, "recettes": rec, "net": rec - dep},
    })


def portail_affaire_detail(request: HttpRequest, pk) -> HttpResponse:
    partie = _require_portail_partie(request)
    if not partie:
        return redirect("cabinet:portail_login")

    affaire = (
        Affaire.objects
        .select_related("juridiction", "type_affaire", "statut_affaire", "avocat_responsable")
        .filter(pk=pk, affairepartie__partie=partie, affairepartie__actif=True)
        .first()
    )
    if not affaire:
        return render(request, "portail/error.html", {
            "title": "ملف غير متوفر",
            "detail": "هذا الملف غير مرتبط بكم.",
        }, status=404)

    audiences = (
        Audience.objects.select_related("type_audience")
        .filter(affaire=affaire).order_by("-date_audience")[:30]
    )
    decisions = Decision.objects.filter(affaire=affaire).order_by("-date_prononce")

    return render(request, "portail/affaire_detail.html", {
        "partie": partie,
        "affaire": affaire,
        "audiences": audiences,
        "decisions": decisions,
    })
