# =============================
# FILE: apps.py
# تفعيل إشارات signals عند جاهزية التطبيق
# =============================
from django.apps import AppConfig

class AvocatAppConfig(AppConfig):
    name = 'avocat_app'
    verbose_name = "Gestion du Cabinet d'Avocats"

    def ready(self):
        from .services import signals  # noqa: F401 — ensure signal registration

