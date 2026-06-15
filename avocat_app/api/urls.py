"""Sync API URLs — mounted under /api/ in the project urls."""
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .sync_views import sync_tables, sync_pull, sync_push
from .files_views import file_endpoint

app_name = "api"

urlpatterns = [
    path("auth/token/",   TokenObtainPairView.as_view(), name="auth_token"),
    path("auth/refresh/", TokenRefreshView.as_view(),    name="auth_refresh"),
    path("auth/verify/",  TokenVerifyView.as_view(),     name="auth_verify"),

    path("sync/tables/", sync_tables, name="sync_tables"),
    path("sync/pull/",   sync_pull,   name="sync_pull"),
    path("sync/push/",   sync_push,   name="sync_push"),

    path("files/<uuid:piece_id>/", file_endpoint, name="files"),
]
