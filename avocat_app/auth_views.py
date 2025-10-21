from django.contrib import messages
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse_lazy

from .forms import ArabicLoginForm
from .models import AuthToken
from .services.token_utils import set_token_cookie, clear_token_cookie
from .models_audit import AuditLog, AuditAction  # إذا كنت فعّلت سجل التدقيق

class LoginView(DjangoLoginView):
    template_name = "auth/login.html"
    authentication_form = ArabicLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        # ملاحظة: FK اسمها "utilisateur"
        token = AuthToken.issue(user=user, request=self.request)
        set_token_cookie(response, token.token)

        # سجل تدقيق (اختياري)
        try:
            AuditLog.objects.create(
                actor=user, action=AuditAction.LOGIN,
                app_label="auth", model="user", object_pk=str(user.pk),
                object_repr=str(user), changes=None,
                path=self.request.path, method=self.request.method,
                ip=self.request.META.get("REMOTE_ADDR"),
                user_agent=self.request.META.get("HTTP_USER_AGENT")[:256],
                session_key=getattr(self.request, "session", None).session_key,
                token_id=getattr(self.request, "auth_token_id", None)
            )
        except Exception:
            pass

        messages.success(self.request, "تم تسجيل الدخول بنجاح.")
        return response

def logout_view(request):
    tok = request.COOKIES.get("auth_token")
    if tok:
        AuthToken.objects.filter(token=tok).update(is_active=False)
    if request.user.is_authenticated:
        AuthToken.objects.filter(user=request.user, is_active=True).update(is_active=False)

    logout(request)
    response = redirect(reverse_lazy("authui:login"))
    clear_token_cookie(response)

    # سجل تدقيق (اختياري)
    try:
        AuditLog.objects.create(
            actor=request.user if request.user.is_authenticated else None, action=AuditAction.LOGOUT,
            app_label="auth", model="user", object_pk=str(request.user.pk) if request.user.is_authenticated else None,
            object_repr=str(request.user) if request.user.is_authenticated else "",
            changes=None, path=request.path, method=request.method,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT")[:256],
            session_key=getattr(request, "session", None).session_key,
            token_id=getattr(request, "auth_token_id", None)
        )
    except Exception:
        pass

    messages.info(request, "تم تسجيل الخروج بنجاح.")
    return response

def log_email(request, obj, subject):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=AuditAction.EMAIL,
        app_label=obj._meta.app_label, model=obj._meta.model_name,
        object_pk=str(obj.pk), object_repr=str(obj),
        changes={"subject": [None, subject]},
        path=request.path, method=request.method,
        ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT")[:256],
        session_key=getattr(request, "session", None).session_key,
        token_id=getattr(request, "auth_token_id", None)
    )
