# -*- coding: utf-8 -*-
"""
avocat_app/services/deadline_alerts.py
Scans approaching deadlines and creates Alerte records.
Can be called from a management command or scheduled task.
"""
from datetime import timedelta
from django.utils import timezone
from ..models import Avertissement, VoieDeRecours, Alerte, TypeAlerte


def check_approaching_deadlines(days_threshold=5):
    """
    Scan avertissements and recours with deadlines within `days_threshold` days.
    Creates Alerte records for those not already alerted.
    """
    today = timezone.localdate()
    horizon = today + timedelta(days=days_threshold)
    created = 0

    # Get or create alert type
    type_alerte, _ = TypeAlerte.objects.get_or_create(
        libelle="أجل قريب",
        defaults={"libelle_fr": "Deadline approaching"}
    )

    # Check avertissements
    for av in Avertissement.objects.filter(
        date_echeance__range=(today, horizon),
        resultat="en_attente",
    ).select_related("affaire", "type_avertissement"):
        # Check if alert already exists
        exists = Alerte.objects.filter(
            reference_id=av.pk,
            type_alerte=type_alerte,
        ).exists()
        if not exists:
            Alerte.objects.create(
                type_alerte=type_alerte,
                reference_id=av.pk,
                date_alerte=timezone.now(),
                moyen="InApp",
                destinataire="النظام",
                message=f"إنذار قريب الأجل: {av.type_avertissement} — {av.affaire.reference_interne} — باقي {av.jours_restants} يوم",
            )
            created += 1

    # Check voies de recours
    for r in VoieDeRecours.objects.filter(
        date_echeance_recours__range=(today, horizon),
    ).select_related("decision__affaire", "type_recours"):
        exists = Alerte.objects.filter(
            reference_id=r.pk,
            type_alerte=type_alerte,
        ).exists()
        if not exists:
            Alerte.objects.create(
                type_alerte=type_alerte,
                reference_id=r.pk,
                date_alerte=timezone.now(),
                moyen="InApp",
                destinataire="النظام",
                message=f"أجل طعن قريب: {r.type_recours} — {r.decision.affaire.reference_interne} — باقي {r.jours_restants_recours} يوم",
            )
            created += 1

    return created
