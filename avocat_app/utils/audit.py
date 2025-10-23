# -*- coding: utf-8 -*-
import sys
from functools import lru_cache
from django.conf import settings
from django.db import connection, ProgrammingError, OperationalError
from django.utils import timezone

# IMPORTANT: import tardif du modèle pour éviter les import cycles dans les migrations
def get_audit_model():
    from avocat_app.models import AuditLog, AuditAction  # import local
    return AuditLog, AuditAction

def is_migration_command():
    argv = getattr(sys, "argv", [])
    return any(cmd in argv for cmd in ("migrate", "makemigrations", "test", "collectstatic"))

@lru_cache
def audit_table_exists():
    """Vérifie une fois si la table d'audit est présente en DB."""
    try:
        AuditLog, _ = get_audit_model()
        table = AuditLog._meta.db_table
        return table in connection.introspection.table_names()
    except Exception:
        return False

def log_audit_safe(**kwargs):
    """
    Écrit une ligne d'audit en toute sécurité :
    - ne fait rien pendant migrate/makemigrations/test/collectstatic
    - ne fait rien si AUDIT_ENABLED=False
    - ne fait rien si la table n'existe pas encore
    - ignore les erreurs de schéma (ProgrammingError/OperationalError)
    """
    if not getattr(settings, "AUDIT_ENABLED", True):
        return
    if is_migration_command():
        return
    if not audit_table_exists():
        return

    try:
        AuditLog, _ = get_audit_model()
        # ajoute timestamp par défaut si non fourni
        kwargs.setdefault("timestamp", timezone.now())
        AuditLog.objects.create(**kwargs)
    except (ProgrammingError, OperationalError):
        # table pas prête / migration en cours — on ignore
        return
