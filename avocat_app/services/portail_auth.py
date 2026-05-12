"""Authentification portail client via magic link.

Modèle de sécurité :
- Token aléatoire de 48 octets URL-safe, stocké en clair en base.
- Validité 24h par défaut.
- Cookie portail signé HMAC après usage du token.
- Pas de session Django (read-only, séparé du back-office).
"""
from __future__ import annotations

import hmac
import hashlib
import re
import secrets
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.utils import timezone

from ..models import Partie, PortailAccess


PORTAIL_COOKIE_NAME = "portail_session"
PORTAIL_COOKIE_AGE_SECONDS = 60 * 60 * 12  # 12h
DEFAULT_TOKEN_TTL_HOURS = 24


def _normalize_phone(p: str) -> str:
    if not p:
        return ""
    digits = re.sub(r"[^\d+]", "", p)
    digits = digits.replace("whatsapp:", "")
    return digits


def find_partie(identifier: str) -> Optional[Partie]:
    """Recherche une Partie par téléphone ou email."""
    if not identifier:
        return None
    identifier = identifier.strip()
    # Email
    if "@" in identifier:
        return Partie.objects.filter(email__iexact=identifier).first()
    # Téléphone : matcher sur les 8 derniers chiffres
    digits = re.sub(r"\D", "", identifier)
    if not digits:
        return None
    last8 = digits[-8:]
    for p in Partie.objects.exclude(telephone__isnull=True).exclude(telephone__exact=""):
        tdigits = re.sub(r"\D", "", p.telephone or "")
        if tdigits.endswith(last8):
            return p
    return None


def issue_token(partie: Partie, *, request=None, ttl_hours: int = DEFAULT_TOKEN_TTL_HOURS) -> PortailAccess:
    token = secrets.token_urlsafe(48)
    return PortailAccess.objects.create(
        partie=partie,
        token=token,
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
        ip_address=(request.META.get("REMOTE_ADDR") if request else None),
        user_agent=((request.META.get("HTTP_USER_AGENT") or "")[:256] if request else None),
    )


def send_magic_link(partie: Partie, token: str, *, base_url: str = "") -> dict:
    """Envoie le magic link par email et/ou WhatsApp.
    Retourne {"email": bool, "whatsapp": bool, "url": str}."""
    full_url = f"{base_url}/portail/access/{token}/"
    sent = {"email": False, "whatsapp": False, "url": full_url}

    # Email
    if partie.email:
        try:
            from django.core.mail import send_mail
            send_mail(
                subject="رابط الدخول إلى البوابة",
                message=(
                    f"السيد(ة) {partie.nom_complet}،\n\n"
                    f"للاطلاع على ملفاتكم وجلساتكم، اضغطوا على الرابط التالي:\n"
                    f"{full_url}\n\n"
                    f"⚠️ الرابط صالح لمدة 24 ساعة فقط ولا يجب مشاركته.\n"
                ),
                from_email=None,
                recipient_list=[partie.email],
                fail_silently=True,
            )
            sent["email"] = True
        except Exception:
            pass

    # WhatsApp
    if partie.telephone:
        try:
            from .twilio_client import send_whatsapp
            body = (
                f"السيد(ة) {partie.nom_complet}،\n"
                f"رابط الدخول إلى بوابتكم (صالح 24 ساعة):\n{full_url}"
            )
            result = send_whatsapp(partie.telephone, body)
            sent["whatsapp"] = result.ok
        except Exception:
            pass

    return sent


# ============================================================
# Cookie portail signé
# ============================================================

def _signing_secret() -> bytes:
    return (getattr(settings, "PORTAIL_COOKIE_SECRET", "") or settings.SECRET_KEY or "dev").encode("utf-8")


def make_cookie_value(partie_id: str, access_id: str) -> str:
    """Signe partie_id + access_id avec HMAC pour cookie portail."""
    payload = f"{partie_id}|{access_id}|{int(timezone.now().timestamp())}"
    sig = hmac.new(_signing_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def verify_cookie_value(value: str) -> Optional[Tuple[str, str]]:
    """Vérifie le cookie, retourne (partie_id, access_id) si valide."""
    if not value:
        return None
    try:
        parts = value.split("|")
        if len(parts) != 4:
            return None
        partie_id, access_id, ts, sig = parts
        payload = f"{partie_id}|{access_id}|{ts}"
        expected = hmac.new(_signing_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        # Vérifier âge du cookie
        ts_int = int(ts)
        if (timezone.now().timestamp() - ts_int) > PORTAIL_COOKIE_AGE_SECONDS:
            return None
        return partie_id, access_id
    except (ValueError, TypeError):
        return None


def get_partie_from_request(request) -> Optional[Partie]:
    """Retourne la Partie identifiée par le cookie portail, ou None."""
    cookie = request.COOKIES.get(PORTAIL_COOKIE_NAME)
    pair = verify_cookie_value(cookie)
    if not pair:
        return None
    partie_id, access_id = pair
    access = PortailAccess.objects.select_related("partie").filter(pk=access_id, partie_id=partie_id).first()
    if not access or access.revoked:
        return None
    return access.partie
