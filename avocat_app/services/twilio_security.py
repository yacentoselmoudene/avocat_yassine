"""Validation de la signature Twilio sur les webhooks entrants.

Twilio signe chaque requête avec HMAC-SHA1 de l'URL + paramètres.
Cf. https://www.twilio.com/docs/usage/security#validating-requests
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import urlparse

from django.conf import settings


def validate_twilio_signature(request) -> bool:
    """Retourne True si la signature X-Twilio-Signature est valide.

    En l'absence de TWILIO_AUTH_TOKEN, retourne True (mode dev/test).
    """
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "") or ""
    if not auth_token:
        return True

    signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
    if not signature:
        return False

    # Reconstruction de l'URL complète
    url = request.build_absolute_uri()
    # Twilio attend l'URL sans le port standard, etc. — on garde tel quel
    parsed = urlparse(url)
    # Concaténer URL + params triés
    params = sorted(request.POST.items())
    payload = url + "".join(k + v for k, v in params)
    mac = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode()
    return hmac.compare_digest(expected, signature)
