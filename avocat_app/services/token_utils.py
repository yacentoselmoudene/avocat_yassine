# avocat_app/services/token_utils.py
from __future__ import annotations

from typing import Optional
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from ..models import AuthToken

COOKIE_NAME = getattr(settings, "AUTH_TOKEN_COOKIE_NAME", "auth_token")
COOKIE_PATH = getattr(settings, "AUTH_TOKEN_COOKIE_PATH", "/")
COOKIE_SAMESITE = getattr(settings, "AUTH_TOKEN_COOKIE_SAMESITE", "Lax")
COOKIE_SECURE = getattr(settings, "AUTH_TOKEN_COOKIE_SECURE", True)
COOKIE_HTTPONLY = getattr(settings, "AUTH_TOKEN_COOKIE_HTTPONLY", True)

# مهلة الخمول (افتراضي 5 دقائق = 300 ثانية)
IDLE_TIMEOUT = int(getattr(settings, "TOKEN_IDLE_TIMEOUT_SECONDS", 300))


def set_token_cookie(response: HttpResponse, token_key: str) -> None:
    """
    يضع كوكي التوكن على الاستجابة.
    لا نحدّد max_age لنجعل العمر مرتبطًا بجلسة المتصفح؛
    الانتهاء الحقيقي يُدار بالخادم عبر last_seen.
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token_key,
        path=COOKIE_PATH,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )


def clear_token_cookie(response: HttpResponse) -> None:
    """يحذف كوكي التوكن من الاستجابة."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        samesite=COOKIE_SAMESITE,
    )


def get_token_from_request(request: HttpRequest) -> Optional[str]:
    """يعيد قيمة كوكي التوكن من الطلب إن وُجد."""
    return request.COOKIES.get(COOKIE_NAME)


def get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    يُستخلص الـIP الفعلي مع دعم X-Forwarded-For خلف الوكيل.
    يعتمد على إعدادات النشر لديك (Trusted Proxies).
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # أول عنوان عادة هو العميل
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def is_token_expired(token: AuthToken) -> bool:
    """
    يعتبر التوكن منتهيًا إذا:
      - عُطِّل (is_active=False)، أو
      - تجاوز last_seen مهلة الخمول.
    """
    if not token.is_active:
        return True
    idle_seconds = (timezone.now() - token.last_seen).total_seconds()
    return idle_seconds > IDLE_TIMEOUT

def touch_token(token: AuthToken) -> None:
    """
    يُحدّث last_seen للتوكن إلى الوقت الحالي.
    يُستخدم لإعادة تعيين مهلة الخمول.
    """
    token.last_seen = timezone.now()
    token.save(update_fields=["last_seen"])

def should_touch_token(token: AuthToken) -> bool:
    """
    يحدد ما إذا كان يجب تحديث last_seen للتوكن بناءً على
    الحد الأدنى لفاصل اللمس لتقليل عمليات الكتابة.
    """
    min_interval = int(getattr(settings, "TOKEN_MIN_TOUCH_INTERVAL_SECONDS", 60))
    idle_seconds = (timezone.now() - token.last_seen).total_seconds()
    return idle_seconds >= min_interval

def issue_token_for_user(user, request: Optional[HttpRequest] = None) -> AuthToken:
    """
    يصدر توكنًا جديدًا للمستخدم المحدد.
    يمكن ربط الطلب بالتوكن لأغراض التدقيق.
    """
    token = AuthToken.objects.create(user=user, issued_ip=get_client_ip(request) if request else None)
    return token

def revoke_token(token: AuthToken) -> None:
    """يعطل التوكن المحدد."""
    token.is_active = False
    token.save(update_fields=["is_active"])

def revoke_all_tokens_for_user(user) -> None:
    """يعطل جميع التوكنات النشطة للمستخدم المحدد."""
    AuthToken.objects.filter(user=user, is_active=True).update(is_active=False)

def get_token_by_key(token_key: str) -> Optional[AuthToken]:
    """يسترجع التوكن بواسطة المفتاح إن وُجد."""
    try:
        return AuthToken.objects.get(key=token_key)
    except AuthToken.DoesNotExist:
        return None

def validate_token(token: AuthToken) -> bool:
    """
    يتحقق من صلاحية التوكن:
      - نشط (is_active=True)
      - غير منتهي الصلاحية (حسب مهلة الخمول)
    """
    return token.is_active and not is_token_expired(token)

def authenticate_request(request: HttpRequest) -> Optional[AuthToken]:
    """
    يحاول مصادقة الطلب باستخدام توكن من الكوكيز.
    يعيد التوكن إذا كان صالحًا، وإلا يعيد None.
    """
    token_key = get_token_from_request(request)
    if not token_key:
        return None
    token = get_token_by_key(token_key)
    if token and validate_token(token):
        return token
    return None

def refresh_token_if_needed(token: AuthToken) -> None:
    """
    يُحدّث last_seen للتوكن إذا لزم الأمر بناءً على
    الحد الأدنى لفاصل اللمس لتقليل عمليات الكتابة.
    """
    if should_touch_token(token):
        touch_token(token)