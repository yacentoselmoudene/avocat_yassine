# =============================================
# FILE: services/alerts.py  (Version avec règles par type d'affaire + envoi Email/SMS)
# =============================================
from datetime import date, datetime, timedelta
from typing import Optional
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ..models import Notification, Alerte, TypeAlerte
from .notifier import dispatch_alert

# Valeurs par défaut (toujours disponibles en fallback)
APPEAL_DEADLINE_DAYS = getattr(settings, 'APPEAL_DEADLINE_DAYS', 30)
APPEAL_REMINDERS_DAYS = getattr(settings, 'APPEAL_REMINDERS_DAYS', [7, 3, 1])
ALERTE_CHANNELS = getattr(settings, 'ALERTE_CHANNELS', ['InApp'])  # ['Email','SMS','InApp']
DEFAULT_DESTINATAIRE = getattr(settings, 'ALERTE_DEFAULT_RECIPIENT', 'Avocat responsable')

# Règles spécifiques حسب نوع القضية (يمكن تعديلها في settings.py)
# مثال افتراضي: مدني 30 يومًا، أسرة 15 يومًا، جنحي/سير 10 أيام…
APPEAL_RULES = getattr(settings, 'APPEAL_RULES', {
    'Civil': 30,
    'Famille': 15,
    'Social': 30,
    'Commercial': 30,
    'Location': 30,
    'Pénal': 10,
    'Pénal-Routier': 10,
    'Pénal-Contravention': 10,
    'Pénal-Flagrant': 10,
})


def get_appeal_days_for_affaire_type(affaire_type: str) -> int:
    """Retourne délai (jours) selon le type d'affaire; sinon fallback par défaut."""
    return APPEAL_RULES.get(affaire_type, APPEAL_DEADLINE_DAYS)


def compute_appeal_deadline(date_signif: date, affaire_type: Optional[str] = None) -> str:
    """سلسلة YYYY-MM-DD تمثل آخر يوم للاستئناف بحسب نوع القضية إن توفّر."""
    if not date_signif:
        return "—"
    days = get_appeal_days_for_affaire_type(affaire_type) if affaire_type else APPEAL_DEADLINE_DAYS
    deadline = date_signif + timedelta(days=days)
    return deadline.strftime('%Y-%m-%d')


def build_alert_message(decision_num: str, affaire_ref: str, deadline: date) -> str:
    return (
        f"تنبيه: آخر أجل لاستئناف الحكم رقم {decision_num} في ملف {affaire_ref} هو {deadline:%Y-%m-%d}. "
        f"المرجو اتخاذ الإجراء المناسب قبل انصرام الأجل."
    )


@transaction.atomic
def create_appeal_alerts_for_notification(notification: Notification) -> int:
    """ينشئ تنبيهات InApp/Email/SMS قبل الأجل وفق القنوات المضبوطة."""
    if not notification.date_signification:
        return 0

    decision = notification.decision
    affaire = decision.affaire
    days = get_appeal_days_for_affaire_type(affaire.type_affaire)
    deadline = notification.date_signification + timedelta(days=days)

    created = 0
    for d in APPEAL_REMINDERS_DAYS:
        when = deadline - timedelta(days=d)
        if when < date.today():
            continue
        dt = datetime(when.year, when.month, when.day, 9, 0, tzinfo=timezone.get_current_timezone())
        for channel in ALERTE_CHANNELS:
            alert, made = Alerte.objects.get_or_create(
                type_alerte=TypeAlerte.ECHEANCE_RECOURS,
                reference_id=decision.id,
                date_alerte=dt,
                moyen=channel,
                defaults={
                    'destinataire': DEFAULT_DESTINATAIRE,
                    'message': build_alert_message(decision.numero_decision, affaire.reference_interne, deadline),
                }
            )
            if made:
                created += 1
                dispatch_alert(alert)  # envoi selon القناة

    # تنبيه يوم الأجل نفسه (الساعة 9 صباحًا)
    dt_deadline = datetime(deadline.year, deadline.month, deadline.day, 9, 0, tzinfo=timezone.get_current_timezone())
    for channel in ALERTE_CHANNELS:
        alert, made = Alerte.objects.get_or_create(
            type_alerte=TypeAlerte.ECHEANCE_RECOURS,
            reference_id=decision.id,
            date_alerte=dt_deadline,
            moyen=channel,
            defaults={
                'destinataire': DEFAULT_DESTINATAIRE,
                'message': build_alert_message(decision.numero_decision, affaire.reference_interne, deadline),
            }
        )
        if made:
            created += 1
            dispatch_alert(alert)

    return created

def remove_appeal_alerts_for_decision(decision_id: int) -> int:
    """Supprime toutes les alertes liées à une décision donnée."""
    deleted, _ = Alerte.objects.filter(
        type_alerte=TypeAlerte.ECHEANCE_RECOURS,
        reference_id=decision_id
    ).delete()
    return deleted

def remove_appeal_alerts_for_notification(notification: Notification) -> int:
    """Supprime toutes les alertes liées à une notification donnée."""
    decision = notification.decision
    return remove_appeal_alerts_for_decision(decision.id)

