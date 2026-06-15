"""Desktop-only views: sync trigger, setup wizard, status.

The setup endpoint is INTENTIONALLY public — it's the first-launch wizard
and the local SQLite has no users yet to gate it behind. It validates the
submitted credentials against the central API; on success it shadows the
user into the local DB so /auth/login/ works with the same password.
"""
import json
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from avocat_app.models import SyncOutbox

log = logging.getLogger("desktop")


@require_GET
@login_required
def status(request):
    pending = SyncOutbox.objects.filter(pushed_at__isnull=True).count()
    return JsonResponse({
        "desktop_mode": True,
        "remote_api": settings.DESKTOP_REMOTE_API,
        "pending_changes": pending,
        "credentials_set": settings.DESKTOP_CREDENTIALS_PATH.exists(),
    })


@require_POST
@login_required
def trigger_sync(request):
    from .sync_engine import full_sync
    try:
        result = full_sync()
        return JsonResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        log.exception("sync failed")
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)


def _validate_against_central(username: str, password: str) -> tuple[bool, str]:
    """POST to central /api/auth/token/. Returns (ok, detail)."""
    try:
        r = requests.post(
            f"{settings.DESKTOP_REMOTE_API}/auth/token/",
            json={"username": username, "password": password},
            timeout=15,
        )
    except requests.RequestException as exc:
        return False, f"تعذّر الاتصال بالخادم: {exc}"
    if r.status_code == 200:
        return True, "ok"
    if r.status_code == 401:
        return False, "اسم المستخدم أو كلمة المرور غير صحيحة (الخادم رفض)"
    return False, f"الخادم أرجع HTTP {r.status_code}"


def _shadow_local_user(username: str, password: str) -> None:
    """Create or refresh a local Django user with the matching password.

    is_superuser=True because there's only one operator per desktop install
    and we want them to bypass the RoleUtilisateur permission grid that
    hasn't been populated yet (config tables only sync after first sync).
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_active": True, "is_staff": True, "is_superuser": True},
    )
    user.set_password(password)
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    log.info("local user %s %s", username, "created" if created else "refreshed")


@csrf_exempt
@require_POST
def setup_credentials(request):
    """POST {username, password}. Public — first-launch only path to a usable
    install. Validates against central, then shadows the user locally."""
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON غير صالح"}, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return JsonResponse({"ok": False, "error": "username/password مطلوبان"}, status=400)

    ok, detail = _validate_against_central(username, password)
    if not ok:
        return JsonResponse({"ok": False, "error": detail}, status=400)

    # Cache for the sync engine.
    settings.DESKTOP_CREDENTIALS_PATH.write_text(
        json.dumps({"username": username, "password": password})
    )
    try:
        settings.DESKTOP_CREDENTIALS_PATH.chmod(0o600)
    except OSError:
        pass

    # Mirror into local Django auth so /auth/login/ accepts the same creds.
    _shadow_local_user(username, password)

    return JsonResponse({
        "ok": True,
        "message": "تم الحفظ. يمكنك الآن تسجيل الدخول بنفس بيانات الاعتماد.",
        "next": "/auth/login/",
    })


@csrf_exempt
def setup_page(request):
    if request.method == "POST":
        return setup_credentials(request)
    return render(request, "desktop/setup.html", {
        "remote_api": settings.DESKTOP_REMOTE_API,
        "configured": settings.DESKTOP_CREDENTIALS_PATH.exists(),
    })
