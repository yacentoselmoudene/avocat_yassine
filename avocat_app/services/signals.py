# =============================
# FILE: signals.py
# Signal post_save لِـ Notification لخلق تنبيهات تلقائية
# =============================
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import Notification
from .alerts import create_appeal_alerts_for_notification

@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance: Notification, created, **kwargs):
    # عند إنشاء أو تعديل Notification مع تاريخ تبليغ
    if instance.date_signification:
        create_appeal_alerts_for_notification(instance)

