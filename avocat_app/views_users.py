"""Gestion utilisateurs + permissions UI (onglets, boutons).

Modèle simple :
- Liste des users Django (auth_user)
- Édition par user : actif, groupes, permissions individuelles
- Groupes prédéfinis (Admin / Avocat / Secrétaire / Stagiaire / ReadOnly)
- Permissions UI custom (voir onglet X, voir bouton Y) stockées dans les
  Permission Django via codename custom : ui.view_tab_*, ui.use_action_*

Les permissions UI sont définies dans UI_PERMISSIONS et créées au démarrage
via la commande seed_ui_permissions.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods


# Permissions UI : (codename, libellé arabe)
UI_PERMISSIONS = [
    # Onglets (navbar)
    ("ui_tab_dashboard", "عرض لوحة التحكم"),
    ("ui_tab_affaires", "عرض قائمة القضايا"),
    ("ui_tab_audiences", "عرض الجلسات"),
    ("ui_tab_juridictions", "عرض المحاكم"),
    ("ui_tab_avocats", "عرض المحامين"),
    ("ui_tab_parties", "عرض الأطراف"),
    ("ui_tab_recours", "عرض الطعون"),
    ("ui_tab_executions", "عرض التنفيذ"),
    ("ui_tab_depenses", "عرض المصاريف"),
    ("ui_tab_recettes", "عرض المداخيل"),
    ("ui_tab_taches", "عرض المهام"),
    ("ui_tab_pieces", "عرض الوثائق"),
    ("ui_tab_audit", "عرض سجل التدقيق"),
    ("ui_tab_settings", "عرض الإعدادات (المراجع)"),
    ("ui_tab_users", "إدارة المستخدمين"),
    ("ui_tab_whatsapp", "إدارة واتساب"),
    ("ui_tab_jurisprudence", "البحث في الاجتهادات"),
    # Boutons / actions
    ("ui_btn_add", "إضافة عناصر"),
    ("ui_btn_edit", "تعديل عناصر"),
    ("ui_btn_delete", "حذف عناصر"),
    ("ui_btn_print", "طباعة PDF"),
    ("ui_btn_export", "تصدير البيانات"),
    ("ui_btn_ai_analyze", "تحليل القرارات بالذكاء الاصطناعي"),
    ("ui_btn_mahakim_sync", "مزامنة محاكم"),
    ("ui_btn_send_whatsapp", "إرسال واتساب"),
]


def _get_ui_content_type():
    """ContentType artificiel pour rattacher les permissions UI."""
    ct, _ = ContentType.objects.get_or_create(app_label="ui", model="permission")
    return ct


def _ensure_ui_permissions():
    """Crée les permissions UI manquantes dans la table Permission."""
    ct = _get_ui_content_type()
    existing = set(Permission.objects.filter(content_type=ct).values_list("codename", flat=True))
    to_create = []
    for codename, label in UI_PERMISSIONS:
        if codename not in existing:
            to_create.append(Permission(codename=codename, name=label, content_type=ct))
    if to_create:
        Permission.objects.bulk_create(to_create)


def is_admin(u):
    return u.is_authenticated and (u.is_superuser or u.groups.filter(name="Admin").exists())


@login_required
@user_passes_test(is_admin)
def user_list(request):
    _ensure_ui_permissions()
    users = User.objects.all().order_by("username").prefetch_related("groups")
    return render(request, "cabinet/users/user_list.html", {
        "users": users,
        "groups": Group.objects.all().order_by("name"),
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET", "POST"])
def user_edit(request, user_id: int):
    _ensure_ui_permissions()
    target = get_object_or_404(User, pk=user_id)
    ct = _get_ui_content_type()
    ui_perms = Permission.objects.filter(content_type=ct).order_by("codename")

    if request.method == "POST":
        target.is_active = request.POST.get("is_active") == "1"
        target.is_staff = request.POST.get("is_staff") == "1"
        target.first_name = request.POST.get("first_name", "").strip()
        target.last_name = request.POST.get("last_name", "").strip()
        target.email = request.POST.get("email", "").strip()
        target.save()

        # Groupes
        group_ids = request.POST.getlist("groups")
        target.groups.set(Group.objects.filter(pk__in=group_ids))

        # Permissions UI
        ui_codes = request.POST.getlist("ui_perms")
        ui_perm_objs = Permission.objects.filter(content_type=ct, codename__in=ui_codes)
        # Garder les perms non-UI, remplacer les perms UI
        current_non_ui = target.user_permissions.exclude(content_type=ct)
        target.user_permissions.set(list(current_non_ui) + list(ui_perm_objs))

        # Nouveau password (optionnel)
        new_pwd = request.POST.get("new_password", "").strip()
        if new_pwd:
            if len(new_pwd) < 8:
                messages.error(request, "كلمة المرور قصيرة جدًا (8 أحرف على الأقل).")
            else:
                target.set_password(new_pwd)
                target.save()
                messages.success(request, "تم تحديث كلمة المرور.")

        messages.success(request, "تم حفظ المستخدم.")
        return redirect("cabinet:user_edit", user_id=target.pk)

    user_ui_codes = set(
        target.user_permissions.filter(content_type=ct).values_list("codename", flat=True)
    )
    user_group_ids = set(target.groups.values_list("pk", flat=True))

    # Grouper les permissions UI par catégorie (tab_/btn_)
    tab_perms = [p for p in ui_perms if p.codename.startswith("ui_tab_")]
    btn_perms = [p for p in ui_perms if p.codename.startswith("ui_btn_")]

    return render(request, "cabinet/users/user_edit.html", {
        "target": target,
        "groups": Group.objects.all().order_by("name"),
        "user_group_ids": user_group_ids,
        "tab_perms": tab_perms,
        "btn_perms": btn_perms,
        "user_ui_codes": user_ui_codes,
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def user_create(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "").strip()

    if not username or not password:
        return JsonResponse({"ok": False, "message": "اسم المستخدم وكلمة المرور مطلوبان."}, status=400)
    if len(password) < 8:
        return JsonResponse({"ok": False, "message": "كلمة المرور قصيرة (8+ أحرف)."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"ok": False, "message": "اسم المستخدم موجود مسبقًا."}, status=400)

    u = User.objects.create_user(username=username, email=email, password=password)
    return JsonResponse({
        "ok": True,
        "message": "تم إنشاء المستخدم.",
        "redirect": reverse("cabinet:user_edit", args=[u.pk]),
    })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def user_delete(request, user_id: int):
    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        return JsonResponse({"ok": False, "message": "لا يمكن حذف المستخدم الرئيسي.", "closeModal": True}, status=400)
    if target.pk == request.user.pk:
        return JsonResponse({"ok": False, "message": "لا يمكنك حذف حسابك.", "closeModal": True}, status=400)
    target.is_active = False
    target.save(update_fields=["is_active"])
    return JsonResponse({
        "ok": True,
        "message": "تم تعطيل المستخدم.",
        "closeModal": True,
        "removeTarget": f"#user-row-{target.pk}",
    })
