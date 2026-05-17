"""Template tags pour les permissions UI (onglets, boutons).

Usage :
    {% load ui_perms %}
    {% if user|can_see:"ui_tab_affaires" %}
        <a href="...">Affaires</a>
    {% endif %}

Les superusers et users non-authentifiés sont gérés ainsi :
- Superuser : tout autorisé
- Anonyme : rien autorisé
- Standard : autorisé si la permission UI lui est attachée (ou via un groupe).
"""
from django import template

register = template.Library()


@register.filter(name="can_see")
def can_see(user, codename: str) -> bool:
    """Vérifie une permission UI (sans préfixe app)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.has_perm(f"ui.{codename}")
