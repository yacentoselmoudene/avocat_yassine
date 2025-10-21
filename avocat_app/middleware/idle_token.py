from django.conf import settings
from django.contrib import auth, messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.db import transaction, DatabaseError

from ..models import AuthToken
from ..services.token_utils import get_token_from_request, clear_token_cookie, is_token_expired

SAFE_PREFIXES = (
    "/auth/login",
    "/auth/password",
    "/admin/login",
    "/static/",
    "/media/",
    "/favicon",
)

MIN_TOUCH_INTERVAL = int(getattr(settings, "TOKEN_MIN_TOUCH_INTERVAL_SECONDS", 60))

class IdleTokenAuthMiddleware:
    """
    يتحقق من صلاحية التوكن ويجدد انتهاءه عند النشاط.
    ينهي الجلسة بعد 5 دقائق من عدم النشاط (قابلة للتهيئة).
    يدعم HTMX بإرجاع HX-Redirect.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if any(path.startswith(p) for p in SAFE_PREFIXES):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return self.get_response(request)

        token_value = get_token_from_request(request)
        if not token_value:
            return self._expire_and_redirect(request, "انتهت جلستك. الرجاء تسجيل الدخول مجددًا.")

        # نحصر التعامل مع التوكن داخل معاملة قصيرة
        try:
            with transaction.atomic():
                token = self._get_token_for_update(user_id=user.pk, token_value=token_value)
                if token is None:
                    return self._expire_and_redirect(request, "انتهت جلستك. الرجاء تسجيل الدخول مجددًا.")

                # منتهٍ أو معطّل؟
                if is_token_expired(token):
                    token.revoke()
                    return self._expire_and_redirect(request, "انتهت الجلسة بسبب عدم النشاط لأكثر من ٥ دقائق.")

                # تقليل الكتابة: حدّث فقط عند الحاجة
                if (timezone.now() - token.last_seen).total_seconds() >= MIN_TOUCH_INTERVAL:
                    token.touch()

                # شارك المعرف للـaudit
                request.auth_token_id = token.id
        except DatabaseError:
            # في أسوأ الأحوال: إن فشلت atomic/locks لأي سبب، عامِلها كجلسة منتهية.
            return self._expire_and_redirect(request, "انتهت جلستك. الرجاء تسجيل الدخول مجددًا.")

        return self.get_response(request)

    # محاولة استخدام select_for_update، مع سقوط إلى get() عند عدم الدعم
    def _get_token_for_update(self, user_id, token_value):
        try:
            return (AuthToken.objects
                    .select_for_update()
                    .get(user_id=user_id, token=token_value))
        except Exception:
            # مثال: SQLite لا يدعم select_for_update
            try:
                return AuthToken.objects.get(user_id=user_id, token=token_value)
            except AuthToken.DoesNotExist:
                return None

    def _login_url(self):
        return settings.LOGIN_URL or reverse("authui:login")

    def _expire_and_redirect(self, request, reason: str):
        auth.logout(request)
        if request.headers.get("HX-Request", "").lower() == "true":
            resp = JsonResponse({"ok": False, "detail": reason, "redirect": self._login_url()})
            resp["HX-Redirect"] = self._login_url()
            clear_token_cookie(resp)
            return resp
        messages.warning(request, reason)
        response = redirect(self._login_url())
        clear_token_cookie(response)
        return response
