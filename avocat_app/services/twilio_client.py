"""Client Twilio pour l'envoi de messages WhatsApp.

Conçu pour ne JAMAIS faire planter l'app si:
- la lib `twilio` n'est pas installée;
- les credentials sont absents;
- TWILIO_DRY_RUN=True (mode démo).

Dans tous les cas non-réels, un enregistrement WhatsAppMessage est tout de
même créé avec un statut adapté (`dry_run` ou `failed`), pour traçabilité.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    ok: bool
    status: str
    sid: Optional[str] = None
    error: Optional[str] = None


def _normalize_to_e164(phone: str, default_country_code: str = "+212") -> Optional[str]:
    """Normalise un numéro marocain en E.164. Retourne None si invalide.
    Accepte: 0612345678, 212612345678, +212612345678, 06 12 34 56 78.
    """
    if not phone:
        return None
    digits = re.sub(r"[^\d+]", "", str(phone))
    if digits.startswith("+"):
        return digits if len(digits) >= 9 else None
    if digits.startswith("00"):
        return "+" + digits[2:]
    if digits.startswith("0"):
        return default_country_code + digits[1:]
    if digits.startswith("212"):
        return "+" + digits
    return None


def _twilio_credentials():
    return (
        getattr(settings, "TWILIO_ACCOUNT_SID", None),
        getattr(settings, "TWILIO_AUTH_TOKEN", None),
        getattr(settings, "TWILIO_WHATSAPP_FROM", None),
    )


def send_whatsapp(to_number: str, body: str, *, content_sid: Optional[str] = None) -> SendResult:
    """Envoie un message WhatsApp via Twilio.

    En l'absence de credentials ou en mode dry-run, renvoie un SendResult OK
    avec status='dry_run' pour que les couches supérieures puissent quand
    même journaliser l'intention.
    """
    sid, token, from_number = _twilio_credentials()
    dry_run = bool(getattr(settings, "TWILIO_DRY_RUN", False))

    normalized = _normalize_to_e164(to_number)
    if not normalized:
        return SendResult(ok=False, status="failed", error="رقم هاتف غير صالح")

    if dry_run or not (sid and token and from_number):
        logger.info("[twilio] dry-run send to=%s body=%r", normalized, body[:120])
        return SendResult(ok=True, status="dry_run")

    try:
        from twilio.rest import Client  # type: ignore
    except ImportError:
        logger.warning("twilio package not installed; falling back to dry-run")
        return SendResult(ok=True, status="dry_run", error="twilio not installed")

    try:
        client = Client(sid, token)
        kwargs = {
            "from_": f"whatsapp:{from_number}" if not from_number.startswith("whatsapp:") else from_number,
            "to": f"whatsapp:{normalized}",
        }
        if content_sid:
            kwargs["content_sid"] = content_sid
        else:
            kwargs["body"] = body
        msg = client.messages.create(**kwargs)
        return SendResult(ok=True, status="sent", sid=msg.sid)
    except Exception as e:
        logger.exception("Twilio send failed")
        return SendResult(ok=False, status="failed", error=str(e))


def send_audience_reminder(audience, partie=None, template=None, *, manual: bool = False) -> "WhatsAppMessage | None":
    """Envoie un rappel d'audience J-1 (ou manuel) au client/partie.

    `partie` : instance Partie ; si None, choisit la première partie de l'affaire
               avec un numéro de téléphone.
    `template` : instance WhatsAppTemplate ; si None, utilise le premier
                 template actif de kind='audience_j1'.

    Crée et retourne un WhatsAppMessage (peut être en statut failed/dry_run).
    """
    from ..models import WhatsAppMessage, WhatsAppTemplate, AffairePartie

    if audience is None:
        return None

    if template is None:
        template = WhatsAppTemplate.objects.filter(
            kind="audience_j1", is_active=True
        ).order_by("created_at").first()

    if partie is None:
        # Première Partie liée à l'affaire qui a un téléphone
        link = (
            AffairePartie.objects.select_related("partie")
            .filter(affaire=audience.affaire, actif=True, partie__telephone__isnull=False)
            .exclude(partie__telephone="")
            .first()
        )
        partie = link.partie if link else None

    if partie is None or not partie.telephone:
        # Aucun destinataire identifié → journaliser un échec
        return WhatsAppMessage.objects.create(
            affaire=audience.affaire,
            audience=audience,
            template=template,
            to_number="",
            to_name="",
            body="",
            status="failed",
            error_message="لا يوجد طرف بهاتف صالح",
        )

    avocat_resp = getattr(audience.affaire, "avocat_responsable", None)
    juridiction = audience.affaire.juridiction
    ctx = {
        "client": partie.nom_complet,
        "ref": audience.affaire.reference_interne,
        "tribunal": juridiction.nomtribunal_ar or juridiction.nomtribunal_fr or "",
        "date": audience.date_audience.strftime("%d/%m/%Y") if audience.date_audience else "",
        "heure": audience.date_audience.strftime("%H:%M") if audience.date_audience else "",
        "avocat": avocat_resp.nom if avocat_resp else "",
    }

    if template:
        body = template.render(ctx)
        content_sid = template.twilio_content_sid or None
    else:
        body = (
            f"تذكير: لكم جلسة بتاريخ {ctx['date']} على الساعة {ctx['heure']} "
            f"بمحكمة {ctx['tribunal']} في الملف {ctx['ref']}."
        )
        content_sid = None

    result = send_whatsapp(partie.telephone, body, content_sid=content_sid)

    msg = WhatsAppMessage.objects.create(
        affaire=audience.affaire,
        audience=audience,
        template=template,
        to_number=_normalize_to_e164(partie.telephone) or partie.telephone,
        to_name=partie.nom_complet,
        body=body,
        status=result.status,
        twilio_sid=result.sid,
        error_message=result.error or "",
        sent_at=timezone.now() if result.ok else None,
    )
    return msg
