"""Desktop-only URLs — mounted under /desktop/ when DESKTOP_MODE is True."""
from django.urls import path
from . import views

app_name = "desktop"

urlpatterns = [
    path("status/", views.status, name="status"),
    path("sync/",   views.trigger_sync, name="sync"),
    path("setup/",  views.setup_page, name="setup"),
]
