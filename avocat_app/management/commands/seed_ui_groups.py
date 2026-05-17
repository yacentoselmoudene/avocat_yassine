"""Crée les groupes par défaut avec leurs permissions UI.

Usage:
    python manage.py seed_ui_groups

Groupes créés:
- Admin     : toutes les perms UI
- Avocat    : voir tous les onglets metier, créer/modifier (sauf users, settings)
- Secretaire: voir affaires/audiences/parties, saisir données, pas de finance/IA
- Stagiaire : lecture seule sur affaires/audiences/parties
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from avocat_app.views_users import UI_PERMISSIONS, _get_ui_content_type, _ensure_ui_permissions


GROUP_SPECS = {
    "Admin": {
        "all": True,
    },
    "Avocat": {
        "tabs": [
            "ui_tab_dashboard", "ui_tab_affaires", "ui_tab_audiences",
            "ui_tab_juridictions", "ui_tab_avocats", "ui_tab_parties",
            "ui_tab_recours", "ui_tab_executions",
            "ui_tab_depenses", "ui_tab_recettes",
            "ui_tab_taches", "ui_tab_pieces",
            "ui_tab_jurisprudence", "ui_tab_settings",
        ],
        "btns": [
            "ui_btn_add", "ui_btn_edit", "ui_btn_delete",
            "ui_btn_print", "ui_btn_export",
            "ui_btn_ai_analyze", "ui_btn_mahakim_sync",
            "ui_btn_send_whatsapp",
        ],
    },
    "Secretaire": {
        "tabs": [
            "ui_tab_dashboard", "ui_tab_affaires", "ui_tab_audiences",
            "ui_tab_juridictions", "ui_tab_avocats", "ui_tab_parties",
            "ui_tab_taches", "ui_tab_pieces", "ui_tab_settings",
        ],
        "btns": [
            "ui_btn_add", "ui_btn_edit", "ui_btn_print",
        ],
    },
    "Stagiaire": {
        "tabs": [
            "ui_tab_dashboard", "ui_tab_affaires", "ui_tab_audiences",
            "ui_tab_juridictions", "ui_tab_parties",
            "ui_tab_jurisprudence",
        ],
        "btns": [
            "ui_btn_print",
        ],
    },
}


class Command(BaseCommand):
    help = "Crée les groupes par défaut (Admin/Avocat/Secretaire/Stagiaire) avec leurs perms UI."

    def handle(self, *args, **options):
        _ensure_ui_permissions()
        ct = _get_ui_content_type()
        all_ui_perms = list(Permission.objects.filter(content_type=ct))
        by_code = {p.codename: p for p in all_ui_perms}

        for group_name, spec in GROUP_SPECS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if spec.get("all"):
                perms = all_ui_perms
            else:
                codes = list(spec.get("tabs", [])) + list(spec.get("btns", []))
                perms = [by_code[c] for c in codes if c in by_code]
            group.permissions.set(perms)
            action = "créé" if created else "mis à jour"
            self.stdout.write(self.style.SUCCESS(
                f"  • Groupe '{group_name}' {action} avec {len(perms)} permissions UI."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\n{len(GROUP_SPECS)} groupes traités. Total UI perms : {len(all_ui_perms)}."
        ))
