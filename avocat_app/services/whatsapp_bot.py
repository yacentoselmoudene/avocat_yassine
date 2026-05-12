"""Bot WhatsApp entrant — interprète les messages reçus via webhook Twilio.

Commandes reconnues (en arabe, français, anglais) :
- "ملف" / "dossier" / "status"   → liste les affaires actives de la partie
- "جلسة" / "audience" / "prochaine" → prochaine audience
- "فاتورة" / "facture" / "solde"   → balance financière
- "مساعدة" / "aide" / "help"       → menu des commandes
- texte libre                       → menu par défaut

Si le numéro n'est pas reconnu comme Partie, le bot répond poliment et
propose de contacter le cabinet.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from django.utils import timezone

from ..models import Affaire, AffairePartie, Audience, Depense, Recette, Partie, WhatsAppMessage

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    p = re.sub(r"[^\d+]", "", str(phone))
    # Twilio prefixes WhatsApp numbers with "whatsapp:+"
    p = p.replace("whatsapp:", "")
    return p


def _find_partie_by_phone(phone_e164: str) -> Optional[Partie]:
    """Cherche une Partie par téléphone normalisé.
    Compare la fin du numéro (8 derniers chiffres) pour tolérer les formats."""
    if not phone_e164:
        return None
    last8 = re.sub(r"\D", "", phone_e164)[-8:]
    if not last8:
        return None
    candidates = Partie.objects.exclude(telephone__isnull=True).exclude(telephone__exact="")
    for p in candidates:
        digits = re.sub(r"\D", "", p.telephone or "")
        if digits.endswith(last8):
            return p
    return None


def _menu_text() -> str:
    return (
        "👋 مرحبا بكم في خدمة المكتب عبر واتساب.\n"
        "أرسل واحدة من الكلمات التالية:\n"
        "• *ملف* — حالة ملفاتي\n"
        "• *جلسة* — جلستي القادمة\n"
        "• *فاتورة* — رصيدي المالي\n"
        "• *مساعدة* — هذه القائمة"
    )


def _format_dossiers(partie: Partie) -> str:
    affaires = (
        Affaire.objects
        .select_related("juridiction", "type_affaire", "statut_affaire")
        .filter(affairepartie__partie=partie, affairepartie__actif=True)
        .distinct()[:5]
    )
    if not affaires:
        return "لا توجد ملفات نشطة باسمكم في النظام."
    lines = ["📁 ملفاتكم النشطة:"]
    for a in affaires:
        lines.append(
            f"• {a.reference_interne} — {a.type_affaire} — "
            f"{a.statut_affaire} — {a.juridiction.nomtribunal_ar or ''}"
        )
    return "\n".join(lines)


def _format_next_audience(partie: Partie) -> str:
    now = timezone.now()
    aud = (
        Audience.objects
        .select_related("affaire", "affaire__juridiction", "type_audience")
        .filter(affaire__affairepartie__partie=partie,
                affaire__affairepartie__actif=True,
                date_audience__gte=now)
        .order_by("date_audience")
        .first()
    )
    if not aud:
        return "لا توجد جلسات قادمة في ملفاتكم."
    return (
        f"📅 جلستكم القادمة:\n"
        f"• الملف: {aud.affaire.reference_interne}\n"
        f"• النوع: {aud.type_audience}\n"
        f"• التاريخ: {aud.date_audience.strftime('%d/%m/%Y على الساعة %H:%M')}\n"
        f"• المحكمة: {aud.affaire.juridiction.nomtribunal_ar or ''}"
    )


def _format_balance(partie: Partie) -> str:
    from django.db.models import Sum
    affaires_ids = Affaire.objects.filter(
        affairepartie__partie=partie, affairepartie__actif=True
    ).values_list("id", flat=True)
    if not affaires_ids:
        return "لا توجد بيانات مالية مرتبطة بكم."
    dep = Depense.objects.filter(affaire_id__in=affaires_ids).aggregate(Sum("montant"))["montant__sum"] or 0
    rec = Recette.objects.filter(affaire_id__in=affaires_ids).aggregate(Sum("montant"))["montant__sum"] or 0
    return (
        f"💰 الوضعية المالية لملفاتكم:\n"
        f"• المصاريف: {dep} درهم\n"
        f"• المداخيل: {rec} درهم\n"
        f"• الصافي: {rec - dep} درهم"
    )


# Pattern keyword routing
_KEYWORDS_DOSSIER = ("ملف", "ملفات", "dossier", "dossiers", "status", "etat", "statut")
_KEYWORDS_AUDIENCE = ("جلسة", "جلستي", "audience", "prochaine", "موعد")
_KEYWORDS_BALANCE = ("فاتورة", "فواتير", "facture", "solde", "رصيد", "balance")
_KEYWORDS_HELP = ("مساعدة", "aide", "help", "menu", "start", "بدء")


def _route_command(body: str, partie: Optional[Partie]) -> str:
    """Retourne le texte de réponse selon la commande détectée."""
    text = (body or "").strip().lower()

    if not partie:
        if any(k in text for k in _KEYWORDS_HELP):
            return _menu_text() + "\n\n⚠️ رقمكم غير مسجل لدينا. الرجاء التواصل مع المكتب لتسجيل رقمكم."
        return (
            "⚠️ رقمكم غير مسجل في قاعدة بيانات المكتب.\n"
            "الرجاء الاتصال بالمكتب لتسجيل رقمكم وبدء الاستفادة من الخدمة."
        )

    if any(k in text for k in _KEYWORDS_DOSSIER):
        return _format_dossiers(partie)
    if any(k in text for k in _KEYWORDS_AUDIENCE):
        return _format_next_audience(partie)
    if any(k in text for k in _KEYWORDS_BALANCE):
        return _format_balance(partie)
    return _menu_text()


def handle_inbound_message(from_number: str, body: str, *, profile_name: str = "",
                           message_sid: str = "") -> str:
    """Point d'entrée appelé par le webhook Twilio.

    Stocke le message inbound, route la commande, persiste le message outbound
    de réponse (sans appel API — Twilio renvoie la réponse via TwiML), et
    retourne le texte à inclure dans la réponse TwiML.
    """
    phone = _normalize_phone(from_number)
    partie = _find_partie_by_phone(phone)

    # Journaliser le message reçu
    WhatsAppMessage.objects.create(
        direction="inbound",
        affaire=None,
        to_number=phone,
        to_name=(partie.nom_complet if partie else profile_name) or "",
        body=body or "",
        status="received",
        twilio_sid=message_sid or "",
    )

    reply = _route_command(body, partie)

    # Journaliser la réponse (status='sent' car Twilio va la transmettre via TwiML)
    WhatsAppMessage.objects.create(
        direction="outbound",
        to_number=phone,
        to_name=(partie.nom_complet if partie else profile_name) or "",
        body=reply,
        status="sent",
        sent_at=timezone.now(),
    )

    return reply
