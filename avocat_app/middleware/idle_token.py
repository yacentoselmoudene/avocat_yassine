# cabinet/middleware/idle_token.py
from __future__ import annotations

from typing import Iterable
from django.conf import settings
from django.contrib import messages, auth
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from avocat_app.models import AuthToken
from avocat_app.services.token_utils import (
    get_token_from_request,
    clear_token_cookie,
    is_token_expired,
    get_client_ip,
)

# مسارات عامة/مستثناة من فحص التوكن (قابلة للتخصيص من settings)
DEFAULT_SAFE_PREFIXES: tuple[str, ...] = (
    "/auth/login",
    "/auth/password",
    "/admin/login",
    "/static/",
    "/media/",
    "/favicon",
)

SAFE_PATH_PREFIXES: Iterable[str] = getattr(
    settings, "IDLE_TOKEN_SAFE_PATH_PREFIXES", DEFAULT_SAFE_PREFIXES
)

# فاصل زمني أدنى لتحديث last_seen لتقليل الكتابة (بالثواني)
MIN_TOUCH_INTERVAL = int(getattr(settings, "TOKEN_MIN_TOUCH_INTERVAL_SECONDS", 60))


class IdleTokenAuthMiddleware:
    """
    يفرض وجود توكن نشط مرتبط بالمستخدم المُصادَق عليه.
    - عند عدم النشاط > TOKEN_IDLE_TIMEOUT_SECONDS: يبطل التوكن، يُسجّل الخروج، ويوجّه لصفحة الدخول.
    - يعامل HTMX برأس HX-Redirect + JSON حتى لا يكسر الـmodal/partial.
    - يحدّث last_seen كل MIN_TOUCH_INTERVAL فقط.
    - يضع request.auth_token_id ليساعد في التدقيق.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # تخطّي المسارات الآمنة
        path = request.path or ""
        if any(path.startswith(p) for p in SAFE_PATH_PREFIXES):
            return self.get_response(request)

        # إن لم يكن المستخدم مسجلاً: لا نتحقق من التوكن (سيتولى login view)
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return self.get_response(request)

        token_key = get_token_from_request(request)
        if not token_key:
            return self._expire_and_redirect(request, reason="انتهت جلستك. الرجاء تسجيل الدخول مجددًا.")

        try:
            token = AuthToken.objects.select_for_update(skip_locked=True).get(user=user, key=token_key)
        except AuthToken.DoesNotExist:
            return self._expire_and_redirect(request, reason="انتهت جلستك. الرجاء تسجيل الدخول مجددًا.")

        # اختبار الانتهاء بالخمول/التعطيل
        if is_token_expired(token):
            token.revoke()
            return self._expire_and_redirect(request, reason="انتهت الجلسة بسبب عدم النشاط لأكثر من ٥ دقائق.")

        # تقليل الكتابة: حدّث last_seen فقط عند الحاجة
        if (timezone.now() - token.last_seen).total_seconds() >= MIN_TOUCH_INTERVAL:
            token.touch()

        # شارِك معرف التوكن لطبقات التدقيق لاحقًا
        request.auth_token_id = token.id  # يُستخدم في audit logs

        # (اختياري) تزكية أمان: قارن الـIP/Agent لو أردت التشدّد
        # if token.ip_addr and token.ip_addr != get_client_ip(request): ...
        # if token.user_agent and token.user_agent != request.META.get("HTTP_USER_AGENT"): ...

        return self.get_response(request)

    # -------- Helpers --------
    def _login_url(self) -> str:
        return settings.LOGIN_URL or reverse("authui:login")

    def _expire_and_redirect(self, request: HttpRequest, reason: str) -> HttpResponse:
        """
        عند انتهاء الجلسة:
          - احذف الكوكي
          - سجّل الخروج
          - أعد توجيه المستخدم (HTML) أو أرسل HX-Redirect لطلبات HTMX
        """
        auth.logout(request)

        # طلب HTMX؟ أعد JSON صغير مع HX-Redirect
        if request.headers.get("HX-Request", "").lower() == "true":
            resp = JsonResponse({"ok": False, "detail": reason, "redirect": self._login_url()})
            resp["HX-Redirect"] = self._login_url()
            # حذف الكوكي
            clear_token_cookie(resp)
            return resp

        # طلب عادي: رسائل + Redirect
        messages.warning(request, reason)
        response: HttpResponseRedirect = redirect(self._login_url())
        clear_token_cookie(response)
        return response
