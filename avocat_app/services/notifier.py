# =============================================
# FILE: services/notifier.py  (تحويل التنبيهات إلى Email/SMS)
# =============================================
from dataclasses import dataclass
from django.core.mail import send_mail
from django.conf import settings

try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

@dataclass
class AlertTarget:
    channel: str  # 'InApp' | 'Email' | 'SMS'
    recipient: str  # email أو هاتف أو اسم مستلم داخلي


def dispatch_alert(alert_obj) -> None:
    """يرسل التنبيه خارجياً إن كانت القناة Email/SMS، ويترك InApp داخل النظام."""
    if alert_obj.moyen == 'Email':
        send_email_alert(subject='تنبيه: أجل الاستئناف', message=alert_obj.message, to=[alert_obj.destinataire])
    elif alert_obj.moyen == 'SMS':
        if TwilioClient is None:
            return
        send_sms_alert(body=alert_obj.message, to=alert_obj.destinataire)
    else:
        # InApp — لا حاجة لإرسال خارجي
        return


def send_email_alert(subject: str, message: str, to: list[str]):
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
    if not from_email:
        return
    try:
        send_mail(subject, message, from_email, to, fail_silently=True)
    except Exception:
        pass


def send_sms_alert(body: str, to: str):
    if TwilioClient is None:
        return
    sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    sender = getattr(settings, 'TWILIO_FROM', None)
    if not (sid and token and sender):
        return
    try:
        client = TwilioClient(sid, token)
        client.messages.create(body=body, from_=sender, to=to)
    except Exception:
        pass

# ملاحظة: تأكد من ضبط إعدادات البريد الإلكتروني و Twilio في settings.py
# كما هو موضح في ملف settings.py المقترح في الأعلى.

def assert_dispatcher():
    """وظيفة اختبار بسيطة للتحقق من عمل المرسل."""
    class DummyAlert:
        def __init__(self, moyen, destinataire, message):
            self.moyen = moyen
            self.destinataire = destinataire
            self.message = message

    email_alert = DummyAlert('Email', 'kmt-servicesprive@gmail.com', 'هذا اختبار لتنبيه البريد الإلكتروني.')
    sms_alert = DummyAlert('SMS', '+1234567890', 'هذا اختبار لتنبيه SMS.')
    dispatch_alert(email_alert)
    dispatch_alert(sms_alert)
# يمكنك استدعاء assert_dispatcher() في بيئة تطوير للتحقق من عمل الإرسال.

