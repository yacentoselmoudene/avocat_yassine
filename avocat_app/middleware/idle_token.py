# avocat_app/middleware/idle_token.py
from django.conf import settings
from django.contrib import auth, messages
from django.http import JsonResponse, HttpResponseRedirect
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
    🔐 يتحقق من صلاحية التوكن ويجدد انتهاءه عند النشاط.
    إذا انتهى التوكن أو لم يوجد، يعيد التوجيه مباشرة إلى صفحة تسجيل الدخول.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        # تجاهل مسارات الدخول وكلمات المرور
        if any(path.startswith(p) for p in SAFE_PREFIXES):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return self.get_response(request)

        token_value = get_token_from_request(request)
        if not token_value:
            # ❌ لا يوجد توكن = يعاد التوجيه فورًا
            return self._redirect_to_login(request, "انتهت جلستك، يرجى تسجيل الدخول مجددًا.")

        try:
            with transaction.atomic():
                try:
                    token = AuthToken.objects.select_for_update().get(user=user, token=token_value)
                except (AuthToken.DoesNotExist, DatabaseError):
                    token = AuthToken.objects.filter(user=user, token=token_value).first()

                if not token:
                    return self._redirect_to_login(request, "جلسة غير صالحة أو منتهية، الرجاء تسجيل الدخول.")

                if is_token_expired(token) or not token.is_active:
                    token.revoke()
                    return self._redirect_to_login(request, "انتهت الجلسة بسبب عدم النشاط.")

                # تحديث آخر نشاط إذا مضى وقت كافٍ
                if (timezone.now() - token.last_seen).total_seconds() >= MIN_TOUCH_INTERVAL:
                    token.touch()

                # نمرر الـtoken للـAuditLog إن لزم
                request.auth_token_id = str(token.id)
        except DatabaseError:
            return self._redirect_to_login(request, "خطأ في التحقق من الجلسة، يرجى تسجيل الدخول مجددًا.")

        return self.get_response(request)

    # === دالة إعادة التوجيه إلى تسجيل الدخول ===
    def _redirect_to_login(self, request, reason: str):
        """
        إذا انتهى التوكن أو الجلسة، يعيد المستخدم إلى صفحة تسجيل الدخول،
        ويمسح الكوكي. يدعم HTMX/AJAX وطلبات عادية.
        """
        auth.logout(request)
        login_url = settings.LOGIN_URL or reverse("authui:login")

        # 🔸 في حالة HTMX
        if request.headers.get("HX-Request"):
            response = JsonResponse({
                "ok": False,
                "detail": reason,
                "redirect": login_url
            })
            response["HX-Redirect"] = login_url
            clear_token_cookie(response)
            return response

        # 🔸 في حالة AJAX (fetch / XMLHttpRequest)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            response = JsonResponse({
                "ok": False,
                "redirect": login_url,
                "message": reason,
            }, status=401)
            clear_token_cookie(response)
            return response

        # 🔸 في الطلبات العادية (navigateur classique)
        messages.warning(request, reason)
        response = HttpResponseRedirect(login_url)
        clear_token_cookie(response)
        return response
