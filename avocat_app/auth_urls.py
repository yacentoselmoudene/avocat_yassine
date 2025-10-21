# avocat_app/auth_urls.py
from django.urls import path
from .auth_views import LoginView, logout_view
from django.contrib.auth import views as auth_views

app_name = "authui"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),

    # بقية مسارات إعادة/تغيير كلمة المرور كما هي
    path("password-change/", auth_views.PasswordChangeView.as_view(template_name="auth/password_change.html", success_url="/"), name="password_change"),
    path("password-reset/", auth_views.PasswordResetView.as_view(template_name="auth/password_reset.html", email_template_name="auth/password_reset_email.txt", success_url="/auth/password-reset/done/"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="auth/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="auth/password_reset_confirm.html", success_url="/auth/reset/complete/"), name="password_reset_confirm"),
    path("reset/complete/", auth_views.PasswordResetCompleteView.as_view(template_name="auth/password_reset_complete.html"), name="password_reset_complete"),
]
